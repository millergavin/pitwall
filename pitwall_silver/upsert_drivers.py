#!/usr/bin/env python3
"""
Upsert drivers data from bronze.drivers_raw into silver.drivers.

Maps from bronze.drivers_raw:
- first_name → first_name
- last_name → last_name
- full_name → full_name
- name_acronym → name_acronym
- headshot_url → headshot_url
- country_code → country_code (with alias lookup)

Generates driver_id using format: drv:{firstname}-{lastname}
IMPORTANT: Checks driver_alias table first before generating new driver_id.
Only upserts existing drivers (no new drivers added).
"""

import os
import logging
from typing import Dict, List, Optional, Tuple

import psycopg
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_db_connection():
    """Create and return a database connection."""
    try:
        conn = psycopg.connect(
            host=os.getenv('PGHOST', 'localhost'),
            port=os.getenv('PGPORT', '5433'),
            dbname=os.getenv('PGDATABASE', 'pitwall'),
            user=os.getenv('PGUSER', 'pitwall'),
            password=os.getenv('PGPASSWORD', 'pitwall')
        )
        return conn
    except psycopg.Error as e:
        logger.error(f"Database connection failed: {e}")
        raise


def get_country_code_alias_map(conn) -> Dict[str, str]:
    """
    Get a mapping of country code aliases to actual country codes.
    
    Returns:
        Dictionary mapping alias -> country_code
    """
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT alias, country_code 
                FROM silver.country_code_alias
            """)
            return {row[0]: row[1] for row in cur.fetchall()}
    except psycopg.Error as e:
        logger.error(f"Failed to fetch country code aliases: {e}")
        return {}


def resolve_country_code(country_code: Optional[str], alias_map: Dict[str, str]) -> Optional[str]:
    """
    Resolve country code using alias lookup if needed.
    
    Args:
        country_code: Country code from bronze.drivers_raw
        alias_map: Mapping of aliases to country codes
        
    Returns:
        Resolved country code
    """
    if not country_code:
        return None
    
    # Check if the country_code is an alias
    if country_code in alias_map:
        resolved = alias_map[country_code]
        logger.debug(f"Resolved country code alias '{country_code}' to '{resolved}'")
        return resolved
    
    # Return as-is if not found in alias map
    return country_code


def get_driver_alias_map(conn) -> Dict[str, str]:
    """
    Get a mapping of driver aliases to driver_id.
    
    Returns:
        Dictionary mapping alias -> driver_id
    """
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT alias, driver_id 
                FROM silver.driver_alias
            """)
            return {row[0]: row[1] for row in cur.fetchall()}
    except psycopg.Error as e:
        logger.error(f"Failed to fetch driver alias mapping: {e}")
        return {}


def generate_driver_id(first_name: Optional[str], last_name: Optional[str]) -> Optional[str]:
    """
    Generate driver_id using format: drv:{firstname}-{lastname}
    
    Args:
        first_name: Driver's first name
        last_name: Driver's last name
        
    Returns:
        Generated driver_id or None if required fields are missing
    """
    if not first_name or not last_name:
        return None
    
    # Sanitize names for use in ID (lowercase, replace spaces/special chars with hyphens)
    def sanitize(name: str) -> str:
        if not name:
            return ''
        name = name.lower().strip()
        # Replace spaces and special chars with hyphens
        name = name.replace(' ', '-').replace('/', '-').replace('\\', '-')
        # Remove any other problematic characters
        name = ''.join(c if c.isalnum() or c == '-' else '' for c in name)
        return name
    
    first_sanitized = sanitize(first_name)
    last_sanitized = sanitize(last_name)
    
    return f"drv:{first_sanitized}-{last_sanitized}"


def resolve_driver_id_from_alias(first_name: str, last_name: str, alias_map: Dict[str, str]) -> Optional[str]:
    """
    Resolve driver_id by checking first_name + last_name in driver_alias table.
    
    Args:
        first_name: Driver's first name
        last_name: Driver's last name
        alias_map: Mapping of alias -> driver_id
        
    Returns:
        Resolved driver_id or None if not found
    """
    # Try full name combinations
    full_name_variants = [
        f"{first_name} {last_name}",
        f"{first_name} {last_name.upper()}",
        f"{first_name.upper()} {last_name}",
        f"{first_name.upper()} {last_name.upper()}",
    ]
    
    for variant in full_name_variants:
        if variant in alias_map:
            return alias_map[variant]
    
    return None


def get_distinct_drivers_from_bronze(conn) -> List[Dict]:
    """
    Get distinct driver records from bronze.drivers_raw.
    
    Uses the most common (correct) full_name and name_acronym for each
    first_name + last_name combination, filtering out mismatched data
    from F2/support series that share the same driver numbers.
    
    Returns:
        List of driver dictionaries
    """
    try:
        with conn.cursor() as cur:
            # First, get the most common correct full_name/name_acronym for each driver
            # by filtering to only rows where first+last matches full_name
            cur.execute("""
                WITH correct_data AS (
                    -- Only use rows where first_name + last_name matches full_name
                    -- This filters out corrupted data from F2/other series
                    SELECT 
                        first_name,
                        last_name,
                        full_name,
                        name_acronym,
                        country_code,
                        headshot_url,
                        COUNT(*) as occurrence_count
                    FROM bronze.drivers_raw
                    WHERE first_name IS NOT NULL
                      AND last_name IS NOT NULL
                      AND name_acronym IS NOT NULL
                      AND (
                          -- Standard name order: "Max VERSTAPPEN"
                          UPPER(first_name || ' ' || last_name) = UPPER(full_name)
                          -- Asian name order: "ZHOU Guanyu" 
                          OR UPPER(last_name || ' ' || first_name) = UPPER(full_name)
                      )
                    GROUP BY first_name, last_name, full_name, name_acronym, country_code, headshot_url
                ),
                best_data AS (
                    -- Pick the most frequent combination for each driver
                    SELECT DISTINCT ON (first_name, last_name)
                        first_name,
                        last_name,
                        full_name,
                        name_acronym,
                        country_code,
                        headshot_url
                    FROM correct_data
                    ORDER BY first_name, last_name, occurrence_count DESC
                )
                SELECT 
                    first_name,
                    last_name,
                    full_name,
                    name_acronym,
                    country_code,
                    headshot_url
                FROM best_data
                ORDER BY last_name, first_name
            """)
            
            drivers = []
            for row in cur.fetchall():
                drivers.append({
                    'first_name': row[0],
                    'last_name': row[1],
                    'full_name': row[2],
                    'name_acronym': row[3],
                    'country_code': row[4],
                    'headshot_url': row[5]
                })
            
            logger.info(f"Found {len(drivers)} distinct drivers in bronze.drivers_raw (using verified data)")
            return drivers
    except psycopg.Error as e:
        logger.error(f"Failed to fetch drivers from bronze: {e}")
        raise


def upsert_drivers(conn, drivers: List[Dict], alias_map: Dict[str, str], country_alias_map: Dict[str, str]) -> int:
    """
    Upsert drivers into silver.drivers table.
    
    Only upserts existing drivers (checks driver_alias first).
    
    Args:
        conn: Database connection
        drivers: List of driver records from bronze
        alias_map: Driver alias mapping
        country_alias_map: Country code alias mapping
        
    Returns:
        Number of records upserted
    """
    if not drivers:
        logger.warning("No drivers to upsert")
        return 0
    
    upsert_sql = """
        INSERT INTO silver.drivers (
            driver_id,
            first_name,
            last_name,
            full_name,
            name_acronym,
            country_code,
            headshot_url
        ) VALUES (
            %(driver_id)s,
            %(first_name)s,
            %(last_name)s,
            %(full_name)s,
            %(name_acronym)s,
            %(country_code)s,
            %(headshot_url)s
        )
        ON CONFLICT (driver_id) 
        DO UPDATE SET
            first_name = EXCLUDED.first_name,
            last_name = EXCLUDED.last_name,
            full_name = EXCLUDED.full_name,
            name_acronym = EXCLUDED.name_acronym,
            country_code = EXCLUDED.country_code,
            headshot_url = EXCLUDED.headshot_url
    """
    
    try:
        with conn.cursor() as cur:
            upsert_records = []
            skipped = 0
            
            for driver in drivers:
                # First, try to resolve driver_id from alias
                driver_id = resolve_driver_id_from_alias(
                    driver['first_name'],
                    driver['last_name'],
                    alias_map
                )
                
                # If not found in alias, generate it
                if not driver_id:
                    driver_id = generate_driver_id(driver['first_name'], driver['last_name'])
                
                if not driver_id:
                    logger.warning(f"Skipping driver due to missing required fields: {driver.get('first_name')} {driver.get('last_name')}")
                    skipped += 1
                    continue
                
                # Verify driver_id exists in silver.drivers (only upsert existing drivers)
                cur.execute("""
                    SELECT 1 FROM silver.drivers WHERE driver_id = %s
                """, (driver_id,))
                
                if not cur.fetchone():
                    logger.debug(f"Driver {driver_id} not found in silver.drivers. Skipping (only upserting existing drivers).")
                    skipped += 1
                    continue
                
                # Resolve country code
                resolved_country_code = resolve_country_code(
                    driver['country_code'],
                    country_alias_map
                )
                
                # Validate country code exists in countries table (if provided)
                if resolved_country_code:
                    cur.execute("""
                        SELECT 1 FROM silver.countries 
                        WHERE country_code = %s
                    """, (resolved_country_code,))
                    if not cur.fetchone():
                        logger.warning(
                            f"Country code '{resolved_country_code}' not found in silver.countries. "
                            f"Setting to NULL for driver {driver_id}"
                        )
                        resolved_country_code = None
                
                # Validate name_acronym length (should be CHAR(3))
                name_acronym = driver['name_acronym']
                if name_acronym and len(name_acronym) > 3:
                    logger.warning(f"name_acronym '{name_acronym}' is longer than 3 characters. Truncating.")
                    name_acronym = name_acronym[:3]
                
                upsert_records.append({
                    'driver_id': driver_id,
                    'first_name': driver['first_name'],
                    'last_name': driver['last_name'],
                    'full_name': driver.get('full_name'),
                    'name_acronym': name_acronym,
                    'country_code': resolved_country_code,
                    'headshot_url': driver.get('headshot_url')
                })
            
            if not upsert_records:
                logger.warning("No valid drivers to upsert after validation")
                return 0
            
            cur.executemany(upsert_sql, upsert_records)
            conn.commit()
            upserted_count = len(upsert_records)
            logger.info(f"Successfully upserted {upserted_count} drivers into silver.drivers")
            if skipped > 0:
                logger.info(f"Skipped {skipped} drivers (not found in existing drivers or validation issues)")
            return upserted_count
            
    except psycopg.Error as e:
        conn.rollback()
        logger.error(f"Database upsert failed: {e}")
        raise


def get_driver_id_map_for_teams(conn) -> Dict[Tuple[str, int], str]:
    """
    Get a mapping of (openf1_session_key, driver_number) -> driver_id from driver_id_by_session view.
    
    Returns:
        Dictionary mapping (session_key, driver_number) -> driver_id
    """
    driver_id_map = {}
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT openf1_session_key, driver_number, driver_id
                FROM silver.driver_id_by_session
            """)
            for row in cur.fetchall():
                key = (str(row[0]), row[1])
                driver_id_map[key] = row[2]
        logger.info(f"Loaded {len(driver_id_map)} driver_id mappings for teams")
    except psycopg.Error as e:
        logger.error(f"Failed to fetch driver_id mappings: {e}")
        raise
    return driver_id_map


def get_team_id_map(conn) -> Dict[str, str]:
    """
    Get a mapping of team_name -> team_id from team_alias table.
    
    Returns:
        Dictionary mapping team_name -> team_id
    """
    team_id_map = {}
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT alias, team_id
                FROM silver.team_alias
            """)
            for row in cur.fetchall():
                team_id_map[row[0]] = row[1]
        logger.info(f"Loaded {len(team_id_map)} team_id mappings")
    except psycopg.Error as e:
        logger.error(f"Failed to fetch team_id mappings: {e}")
        raise
    return team_id_map


def get_session_id_map(conn) -> Dict[str, str]:
    """
    Get a mapping of openf1_session_key -> session_id from sessions table.
    
    Returns:
        Dictionary mapping openf1_session_key -> session_id
    """
    session_id_map = {}
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT openf1_session_key, session_id
                FROM silver.sessions
            """)
            for row in cur.fetchall():
                session_id_map[str(row[0])] = row[1]
        logger.info(f"Loaded {len(session_id_map)} session_id mappings")
    except psycopg.Error as e:
        logger.error(f"Failed to fetch session_id mappings: {e}")
        raise
    return session_id_map


def parse_int(value: Optional[str]) -> Optional[int]:
    """Parse string to int, return None if invalid."""
    if value is None or value.strip() == '':
        return None
    try:
        return int(value)
    except ValueError:
        return None


def upsert_driver_teams_by_session(conn, driver_id_map: Dict[Tuple[str, int], str],
                                   team_id_map: Dict[str, str],
                                   session_id_map: Dict[str, str]) -> int:
    """
    Upsert driver-team associations into silver.driver_teams_by_session table.
    
    Returns:
        Number of records upserted
    """
    try:
        with conn.cursor() as cur:
            # Get driver-team records from bronze
            cur.execute("""
                SELECT DISTINCT
                    dr.openf1_session_key,
                    dr.driver_number,
                    dr.team_name
                FROM bronze.drivers_raw dr
                WHERE dr.openf1_session_key IS NOT NULL
                  AND dr.driver_number IS NOT NULL
                  AND dr.team_name IS NOT NULL
                  AND dr.team_name != ''
            """)
            
            records = []
            for row in cur.fetchall():
                records.append({
                    'openf1_session_key': str(row[0]),
                    'driver_number': row[1],
                    'team_name': row[2]
                })
            
            logger.info(f"Found {len(records)} driver-team records in bronze.drivers_raw")
            
            if not records:
                return 0
            
            insert_sql = """
                INSERT INTO silver.driver_teams_by_session (
                    session_id,
                    driver_id,
                    team_id
                ) VALUES (
                    %s, %s, %s
                )
                ON CONFLICT (session_id, driver_id) DO UPDATE SET
                    team_id = EXCLUDED.team_id
            """
            
            inserts_data = []
            skipped_count = 0
            
            for record in records:
                # Parse driver_number
                driver_number_parsed = parse_int(record['driver_number'])
                if driver_number_parsed is None:
                    skipped_count += 1
                    continue
                
                # Resolve session_id
                session_id = session_id_map.get(record['openf1_session_key'])
                if not session_id:
                    skipped_count += 1
                    continue
                
                # Resolve driver_id
                driver_id_key = (record['openf1_session_key'], driver_number_parsed)
                driver_id = driver_id_map.get(driver_id_key)
                if not driver_id:
                    skipped_count += 1
                    continue
                
                # Resolve team_id
                team_name = record['team_name'].strip()
                team_id = team_id_map.get(team_name)
                if not team_id:
                    logger.warning(f"Skipping record due to unresolved team_id for team_name: {team_name}")
                    skipped_count += 1
                    continue
                
                # Insert/update record
                inserts_data.append((
                    session_id,
                    driver_id,
                    team_id
                ))
            
            if not inserts_data:
                logger.warning("No valid driver-team records to upsert")
                return 0
            
            # Perform batch inserts/updates
            batch_size = 1000
            upserted_count = 0
            for i in range(0, len(inserts_data), batch_size):
                batch = inserts_data[i:i + batch_size]
                cur.executemany(insert_sql, batch)
                upserted_count += len(batch)
            
            conn.commit()
            logger.info(f"Successfully upserted {upserted_count} driver-team records into silver.driver_teams_by_session")
            if skipped_count > 0:
                logger.warning(f"Skipped {skipped_count} records due to validation issues")
            return upserted_count
            
    except psycopg.Error as e:
        conn.rollback()
        logger.error(f"Database upsert failed for driver_teams_by_session: {e}")
        raise


def main():
    """Main upsert function."""
    logger.info("Starting drivers upsert from bronze.drivers_raw to silver.drivers")
    
    conn = get_db_connection()
    
    try:
        # Get driver alias mapping
        logger.info("Loading driver alias mapping...")
        alias_map = get_driver_alias_map(conn)
        logger.info(f"Loaded {len(alias_map)} driver aliases")
        
        # Get country code alias mapping
        logger.info("Loading country code alias mapping...")
        country_alias_map = get_country_code_alias_map(conn)
        logger.info(f"Loaded {len(country_alias_map)} country code aliases")
        
        # Get distinct drivers from bronze
        logger.info("Fetching distinct drivers from bronze.drivers_raw...")
        drivers = get_distinct_drivers_from_bronze(conn)
        
        if not drivers:
            logger.warning("No drivers found in bronze.drivers_raw")
            return
        
        # Upsert drivers
        logger.info("Upserting drivers into silver.drivers (only existing drivers)...")
        upserted = upsert_drivers(conn, drivers, alias_map, country_alias_map)
        
        logger.info("="*60)
        logger.info("DRIVERS UPSERT COMPLETE")
        logger.info("="*60)
        logger.info(f"Upserted: {upserted} drivers")
        
        # Now upsert driver_teams_by_session
        logger.info("\n" + "="*60)
        logger.info("Starting driver-teams-by-session upsert")
        logger.info("="*60)
        
        # Load mappings for driver_teams_by_session
        logger.info("Loading mappings for driver_teams_by_session...")
        driver_id_map = get_driver_id_map_for_teams(conn)
        team_id_map = get_team_id_map(conn)
        session_id_map = get_session_id_map(conn)
        
        # Upsert driver teams
        logger.info("Upserting driver-team associations...")
        teams_upserted = upsert_driver_teams_by_session(conn, driver_id_map, team_id_map, session_id_map)
        
        logger.info("="*60)
        logger.info("DRIVER TEAMS BY SESSION UPSERT COMPLETE")
        logger.info("="*60)
        logger.info(f"Upserted: {teams_upserted} driver-team associations")
    
    finally:
        conn.close()


if __name__ == "__main__":
    main()

