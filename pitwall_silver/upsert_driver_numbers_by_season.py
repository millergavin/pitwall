#!/usr/bin/env python3
"""
Upsert driver numbers by season from bronze.drivers_raw into silver.driver_numbers_by_season.

Resolves driver_id by checking first_name + last_name in driver_alias table first.
Resolves season from openf1_meeting_key -> meetings.season.

Handles driver_number conflicts with priority:
1. session_type: race > qualifying > practice
2. Most frequent for that driver across sessions in that year
3. Lowest number
"""

import os
import logging
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

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

# Session type priority for conflict resolution (higher number = higher priority)
SESSION_TYPE_PRIORITY = {
    'race': 3,
    'quali': 2,
    'sprint_quali': 2,
    'p1': 1,
    'p2': 1,
    'p3': 1,
    'sprint': 1,  # Sprint sessions are practice-like
}


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


def get_driver_number_data_from_bronze(conn) -> List[Dict]:
    """
    Get driver number data from bronze.drivers_raw with session information.
    
    Joins through sessions to get season and session_type for conflict resolution.
    
    Returns:
        List of driver number dictionaries with driver info, season, session_type, and driver_number
    """
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT DISTINCT
                    dr.first_name,
                    dr.last_name,
                    dr.driver_number,
                    m.season,
                    s.session_type
                FROM bronze.drivers_raw dr
                INNER JOIN silver.sessions s 
                    ON dr.openf1_session_key = s.openf1_session_key
                INNER JOIN silver.meetings m 
                    ON s.meeting_id = m.meeting_id
                WHERE dr.first_name IS NOT NULL
                  AND dr.last_name IS NOT NULL
                  AND dr.driver_number IS NOT NULL
                  AND m.season IS NOT NULL
                  AND s.session_type IS NOT NULL
                ORDER BY m.season, dr.last_name, dr.first_name
            """)
            
            records = []
            for row in cur.fetchall():
                try:
                    records.append({
                        'first_name': row[0],
                        'last_name': row[1],
                        'driver_number': int(row[2]),
                        'season': int(row[3]),
                        'session_type': row[4]
                    })
                except (ValueError, TypeError):
                    logger.warning(f"Invalid driver_number or season: {row}")
                    continue
            
            logger.info(f"Found {len(records)} driver number records in bronze.drivers_raw")
            return records
    except psycopg.Error as e:
        logger.error(f"Failed to fetch driver number data from bronze: {e}")
        raise


def resolve_driver_number_conflicts(records: List[Dict]) -> Dict[Tuple[str, int], int]:
    """
    Resolve driver_number conflicts using priority rules.
    
    Args:
        records: List of driver number records with potential conflicts
        
    Returns:
        Dictionary mapping (driver_id, season) -> resolved_driver_number
    """
    # Group by (driver_id, season)
    grouped = defaultdict(list)
    
    for record in records:
        key = (record['driver_id'], record['season'])
        grouped[key].append(record)
    
    resolved = {}
    
    for (driver_id, season), group_records in grouped.items():
        if len(group_records) == 1:
            # No conflict
            resolved[(driver_id, season)] = group_records[0]['driver_number']
        else:
            # Conflict - apply priority rules
            logger.debug(f"Resolving conflict for driver {driver_id}, season {season}: {len(group_records)} different numbers")
            
            # Priority 1: session_type (race > qualifying > practice)
            max_priority = max(
                SESSION_TYPE_PRIORITY.get(r['session_type'], 0) 
                for r in group_records
            )
            priority_filtered = [
                r for r in group_records 
                if SESSION_TYPE_PRIORITY.get(r['session_type'], 0) == max_priority
            ]
            
            if len(priority_filtered) == 1:
                resolved[(driver_id, season)] = priority_filtered[0]['driver_number']
                logger.debug(f"  Resolved by session_type priority: {priority_filtered[0]['driver_number']}")
                continue
            
            # Priority 2: Most frequent for that driver across sessions in that year
            number_counts = defaultdict(int)
            for r in priority_filtered:
                number_counts[r['driver_number']] += 1
            
            max_count = max(number_counts.values())
            most_frequent = [
                num for num, count in number_counts.items() 
                if count == max_count
            ]
            
            if len(most_frequent) == 1:
                resolved[(driver_id, season)] = most_frequent[0]
                logger.debug(f"  Resolved by frequency: {most_frequent[0]}")
                continue
            
            # Priority 3: Lowest number (stable, deterministic)
            resolved_number = min(most_frequent)
            resolved[(driver_id, season)] = resolved_number
            logger.debug(f"  Resolved by lowest number: {resolved_number}")
    
    return resolved


def upsert_driver_numbers(conn, records: List[Dict], alias_map: Dict[str, str]) -> int:
    """
    Upsert driver numbers into silver.driver_numbers_by_season table.
    
    Args:
        conn: Database connection
        records: List of driver number records from bronze
        alias_map: Driver alias mapping
        
    Returns:
        Number of records upserted
    """
    if not records:
        logger.warning("No driver number records to upsert")
        return 0
    
    # Resolve driver_id for each record
    logger.info("Resolving driver_ids...")
    for record in records:
        # First, try to resolve from alias
        driver_id = resolve_driver_id_from_alias(
            record['first_name'],
            record['last_name'],
            alias_map
        )
        
        # If not found in alias, generate it
        if not driver_id:
            driver_id = generate_driver_id(record['first_name'], record['last_name'])
        
        if not driver_id:
            logger.warning(f"Skipping record due to missing driver_id: {record.get('first_name')} {record.get('last_name')}")
            continue
        
        record['driver_id'] = driver_id
    
    # Filter out records without driver_id
    records_with_id = [r for r in records if 'driver_id' in r]
    
    if not records_with_id:
        logger.warning("No records with valid driver_id after resolution")
        return 0
    
    # Verify all driver_ids exist in silver.drivers
    logger.info("Validating driver_ids against silver.drivers...")
    with conn.cursor() as cur:
        valid_driver_ids = set()
        for record in records_with_id:
            cur.execute("""
                SELECT 1 FROM silver.drivers WHERE driver_id = %s
            """, (record['driver_id'],))
            if cur.fetchone():
                valid_driver_ids.add(record['driver_id'])
        
        records_with_id = [
            r for r in records_with_id 
            if r['driver_id'] in valid_driver_ids
        ]
    
    if not records_with_id:
        logger.warning("No records with valid driver_ids in silver.drivers")
        return 0
    
    # Resolve conflicts
    logger.info("Resolving driver_number conflicts...")
    resolved_numbers = resolve_driver_number_conflicts(records_with_id)
    
    if not resolved_numbers:
        logger.warning("No resolved driver numbers after conflict resolution")
        return 0
    
    # Upsert
    upsert_sql = """
        INSERT INTO silver.driver_numbers_by_season (
            driver_id,
            season,
            driver_number
        ) VALUES (
            %(driver_id)s,
            %(season)s,
            %(driver_number)s
        )
        ON CONFLICT (driver_id, season) 
        DO UPDATE SET
            driver_number = EXCLUDED.driver_number
    """
    
    try:
        with conn.cursor() as cur:
            upsert_records = []
            for (driver_id, season), driver_number in resolved_numbers.items():
                upsert_records.append({
                    'driver_id': driver_id,
                    'season': season,
                    'driver_number': driver_number
                })
            
            if not upsert_records:
                logger.warning("No valid driver number records to upsert after conflict resolution")
                return 0
            
            cur.executemany(upsert_sql, upsert_records)
            conn.commit()
            upserted_count = len(upsert_records)
            logger.info(f"Successfully upserted {upserted_count} driver number records into silver.driver_numbers_by_season")
            return upserted_count
            
    except psycopg.Error as e:
        conn.rollback()
        logger.error(f"Database upsert failed: {e}")
        raise


def main():
    """Main upsert function."""
    logger.info("Starting driver_numbers_by_season upsert from bronze.drivers_raw")
    
    conn = get_db_connection()
    
    try:
        # Get driver alias mapping
        logger.info("Loading driver alias mapping...")
        alias_map = get_driver_alias_map(conn)
        logger.info(f"Loaded {len(alias_map)} driver aliases")
        
        # Get driver number data from bronze
        logger.info("Fetching driver number data from bronze.drivers_raw...")
        records = get_driver_number_data_from_bronze(conn)
        
        if not records:
            logger.warning("No driver number records found in bronze.drivers_raw")
            return
        
        # Upsert driver numbers
        logger.info("Upserting driver numbers into silver.driver_numbers_by_season...")
        upserted = upsert_driver_numbers(conn, records, alias_map)
        
        logger.info("="*60)
        logger.info("DRIVER NUMBERS BY SEASON UPSERT COMPLETE")
        logger.info("="*60)
        logger.info(f"Upserted: {upserted} driver number records")
        
        # Show summary by season
        logger.info("\nSummary by season:")
        with conn.cursor() as cur:
            cur.execute("""
                SELECT season, COUNT(*) as driver_count
                FROM silver.driver_numbers_by_season
                GROUP BY season
                ORDER BY season
            """)
            for row in cur.fetchall():
                logger.info(f"  {row[0]}: {row[1]} drivers")
    
    finally:
        conn.close()


if __name__ == "__main__":
    main()


