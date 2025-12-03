#!/usr/bin/env python3
"""
Upsert driver-team associations from bronze.drivers_raw into silver.driver_teams_by_session.

This table captures which team each driver was with for each session, covering scenarios
like driver substitutions or stand-ins.

Resolves:
- session_id from openf1_session_key
- driver_id from driver_number + openf1_session_key (using driver_id_by_session view)
- team_id from team_name (using team_alias table)
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
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        raise


def get_driver_id_map(conn) -> Dict[Tuple[str, int], str]:
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
        logger.info(f"Loaded {len(driver_id_map)} driver_id mappings")
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


def get_driver_teams_from_bronze(conn) -> List[Dict]:
    """
    Get driver-team associations from bronze.drivers_raw.
    
    Returns:
        List of dictionaries with openf1_session_key, driver_number, team_name
    """
    try:
        with conn.cursor() as cur:
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
                ORDER BY dr.openf1_session_key, dr.driver_number
            """)
            
            records = []
            for row in cur.fetchall():
                records.append({
                    'openf1_session_key': str(row[0]),
                    'driver_number': row[1],
                    'team_name': row[2]
                })
            
            logger.info(f"Found {len(records)} driver-team records in bronze.drivers_raw")
            return records
    except psycopg.Error as e:
        logger.error(f"Failed to fetch driver teams from bronze: {e}")
        raise


def parse_int(value: Optional[str]) -> Optional[int]:
    """Parse string to int, return None if invalid."""
    if value is None or value.strip() == '':
        return None
    try:
        return int(value)
    except ValueError:
        return None


def upsert_driver_teams(conn, records: List[Dict], 
                       driver_id_map: Dict[Tuple[str, int], str],
                       team_id_map: Dict[str, str],
                       session_id_map: Dict[str, str]) -> int:
    """
    Upsert driver-team associations into silver.driver_teams_by_session table.
    """
    if not records:
        logger.warning("No driver-team records to upsert")
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
    
    upserted_count = 0
    skipped_count = 0
    batch_size = 1000

    try:
        with conn.cursor() as cur:
            inserts_data = []
            
            for record in records:
                # Parse driver_number
                driver_number_parsed = parse_int(record['driver_number'])
                if driver_number_parsed is None:
                    logger.warning(f"Skipping record due to invalid driver_number: {record.get('driver_number')}")
                    skipped_count += 1
                    continue
                
                # Resolve session_id
                session_id = session_id_map.get(record['openf1_session_key'])
                if not session_id:
                    logger.debug(f"Skipping record due to unresolved session_id for session_key {record.get('openf1_session_key')}")
                    skipped_count += 1
                    continue
                
                # Resolve driver_id
                driver_id_key = (record['openf1_session_key'], driver_number_parsed)
                driver_id = driver_id_map.get(driver_id_key)
                if not driver_id:
                    logger.debug(f"Skipping record due to unresolved driver_id for session {record.get('openf1_session_key')}, driver {driver_number_parsed}")
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
            
            logger.info(f"Will upsert {len(inserts_data)} records")
            
            # Perform batch inserts/updates
            if inserts_data:
                logger.info("Upserting driver-team records...")
                for i in range(0, len(inserts_data), batch_size):
                    batch = inserts_data[i:i + batch_size]
                    cur.executemany(insert_sql, batch)
                    upserted_count += len(batch)
                conn.commit()
                logger.info(f"  Upserted {upserted_count} records")
            
            if skipped_count > 0:
                logger.warning(f"Skipped {skipped_count} records due to validation issues")
            return upserted_count
                    
    except psycopg.Error as e:
        conn.rollback()
        logger.error(f"Database upsert failed: {e}")
        raise


def main():
    """Main upsert function."""
    logger.info("Starting driver-teams-by-session upsert from bronze.drivers_raw to silver.driver_teams_by_session")
    
    conn = get_db_connection()
    
    try:
        # Load mappings
        logger.info("Loading driver_id mappings...")
        driver_id_map = get_driver_id_map(conn)
        
        logger.info("Loading team_id mappings...")
        team_id_map = get_team_id_map(conn)
        
        logger.info("Loading session_id mappings...")
        session_id_map = get_session_id_map(conn)
        
        # Get driver-team records from bronze
        logger.info("Fetching driver-team records from bronze.drivers_raw...")
        records = get_driver_teams_from_bronze(conn)
        
        if not records:
            logger.warning("No driver-team records found in bronze.drivers_raw")
            return
        
        # Upsert driver teams
        logger.info("Upserting driver-team records into silver.driver_teams_by_session...")
        upserted = upsert_driver_teams(conn, records, driver_id_map, team_id_map, session_id_map)
        
        logger.info("="*60)
        logger.info("DRIVER TEAMS BY SESSION UPSERT COMPLETE")
        logger.info("="*60)
        logger.info(f"Upserted: {upserted} records")
        
        # Show summary
        logger.info("\nSummary:")
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) as total_records,
                       COUNT(DISTINCT session_id) as unique_sessions,
                       COUNT(DISTINCT driver_id) as unique_drivers,
                       COUNT(DISTINCT team_id) as unique_teams
                FROM silver.driver_teams_by_session
            """)
            total, sessions, drivers, teams = cur.fetchone()
            logger.info(f"  Total records in silver.driver_teams_by_session: {total}")
            logger.info(f"  Unique sessions: {sessions}")
            logger.info(f"  Unique drivers: {drivers}")
            logger.info(f"  Unique teams: {teams}")

        logger.info("\nSample Records:")
        with conn.cursor() as cur:
            cur.execute("""
                SELECT dts.session_id, dts.driver_id, dts.team_id
                FROM silver.driver_teams_by_session dts
                ORDER BY dts.session_id, dts.driver_id
                LIMIT 5
            """)
            for row in cur.fetchall():
                logger.info(f"  {row[0]} | {row[1]} | {row[2]}")
    
    finally:
        conn.close()


if __name__ == "__main__":
    main()

