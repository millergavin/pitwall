#!/usr/bin/env python3
"""
Upsert stints data from bronze.stints_raw into silver.stints.

Resolves session_id by joining stints_raw.openf1_session_key to sessions.openf1_session_key.
Resolves driver_id using driver_number + openf1_session_key lookup in driver_id_by_session view.

Maps from bronze.stints_raw with conversions:
- lap_start → lap_start (text to int)
- lap_end → lap_end (text to int, nullable)
- tyre_age_at_start → tyre_age_at_start (text to int, nullable)
- compound → tyre_compound (text to enum, nullable)
- stint_number → stint_number (text to int, nullable)

Resolves lap_start_id and lap_end_id by joining laps on (session_id, driver_id, lap_number).
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


def parse_int(value: Optional[str]) -> Optional[int]:
    """Parse string to int, return None if invalid."""
    if value is None or value.strip() == '':
        return None
    try:
        return int(value)
    except ValueError:
        return None


def normalize_tyre_compound(compound: Optional[str]) -> Optional[str]:
    """
    Normalize tyre compound string to match enum values.
    
    Enum values: 'soft', 'medium', 'hard', 'intermediate', 'wet'
    
    Returns:
        Normalized compound string (lowercase) or None if invalid
    """
    if not compound:
        return None
    
    compound_lower = compound.strip().lower()
    
    # Map common variations to enum values
    compound_map = {
        'soft': 'soft',
        'medium': 'medium',
        'hard': 'hard',
        'intermediate': 'intermediate',
        'wet': 'wet',
        # Handle any case variations
        'softs': 'soft',
        'mediums': 'medium',
        'hards': 'hard',
        'intermediates': 'intermediate',
        'wets': 'wet',
    }
    
    return compound_map.get(compound_lower)


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


def get_lap_id_map(conn) -> Dict[Tuple[str, str, int], int]:
    """
    Get a mapping of (session_id, driver_id, lap_number) -> lap_id from laps table.
    
    Returns:
        Dictionary mapping (session_id, driver_id, lap_number) -> lap_id
    """
    lap_id_map = {}
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT session_id, driver_id, lap_number, lap_id
                FROM silver.laps
            """)
            for row in cur.fetchall():
                key = (row[0], row[1], row[2])
                lap_id_map[key] = row[3]
        logger.info(f"Loaded {len(lap_id_map)} lap_id mappings")
    except psycopg.Error as e:
        logger.error(f"Failed to fetch lap_id mappings: {e}")
        raise
    return lap_id_map


def get_stints_from_bronze(conn) -> List[Dict]:
    """
    Get stint records from bronze.stints_raw with resolved session_id.
    """
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT DISTINCT
                    sr.openf1_session_key,
                    sr.driver_number,
                    sr.lap_start,
                    sr.lap_end,
                    sr.tyre_age_at_start,
                    sr.compound,
                    sr.stint_number,
                    s.session_id
                FROM bronze.stints_raw sr
                INNER JOIN silver.sessions s 
                    ON sr.openf1_session_key = s.openf1_session_key
                WHERE sr.openf1_session_key IS NOT NULL
                  AND sr.driver_number IS NOT NULL
                  AND sr.lap_start IS NOT NULL
                ORDER BY sr.openf1_session_key, sr.driver_number, sr.lap_start
            """)
            
            records = []
            for row in cur.fetchall():
                records.append({
                    'openf1_session_key': row[0],
                    'driver_number': row[1],
                    'lap_start': row[2],
                    'lap_end': row[3],
                    'tyre_age_at_start': row[4],
                    'compound': row[5],
                    'stint_number': row[6],
                    'session_id': row[7]
                })
            
            logger.info(f"Found {len(records)} stint records in bronze.stints_raw with resolved session_id")
            return records
    except psycopg.Error as e:
        logger.error(f"Failed to fetch stints from bronze: {e}")
        raise


def upsert_stints(conn, records: List[Dict], driver_id_map: Dict[Tuple[str, int], str], lap_id_map: Dict[Tuple[str, str, int], int]) -> int:
    """
    Upsert stint records into silver.stints table.
    """
    if not records:
        logger.warning("No stint records to upsert")
        return 0
    
    insert_sql = """
        INSERT INTO silver.stints (
            session_id,
            driver_id,
            lap_start,
            lap_start_id,
            lap_end,
            lap_end_id,
            tyre_age_at_start,
            tyre_compound,
            stint_number
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
    """
    
    update_sql = """
        UPDATE silver.stints
        SET
            lap_end = %s,
            lap_end_id = %s,
            tyre_age_at_start = %s,
            tyre_compound = %s,
            stint_number = %s
        WHERE stint_id = %s
    """
    
    inserted_count = 0
    updated_count = 0
    skipped_count = 0
    batch_size = 1000

    try:
        with conn.cursor() as cur:
            # Pre-fetch existing records for deduplication
            logger.info("Checking for existing records...")
            existing_records = {}
            cur.execute("""
                SELECT session_id, driver_id, lap_start, stint_id
                FROM silver.stints
            """)
            for row in cur.fetchall():
                key = (row[0], row[1], row[2])
                existing_records[key] = row[3]
            
            logger.info(f"Found {len(existing_records)} existing stint records")
            
            inserts_data = []
            updates_data = []
            
            for record in records:
                # Parse data types
                lap_start_parsed = parse_int(record['lap_start'])
                if lap_start_parsed is None:
                    logger.warning(f"Skipping record due to invalid lap_start: {record.get('lap_start')}")
                    skipped_count += 1
                    continue
                
                lap_end_parsed = parse_int(record['lap_end'])
                tyre_age_at_start_parsed = parse_int(record['tyre_age_at_start'])
                stint_number_parsed = parse_int(record['stint_number'])
                
                # Normalize tyre compound
                tyre_compound = normalize_tyre_compound(record['compound'])
                
                driver_number_parsed = parse_int(record['driver_number'])
                if driver_number_parsed is None:
                    logger.warning(f"Skipping record due to invalid driver_number: {record.get('driver_number')}")
                    skipped_count += 1
                    continue
                
                # Resolve driver_id using pre-loaded map
                driver_id_key = (record['openf1_session_key'], driver_number_parsed)
                driver_id = driver_id_map.get(driver_id_key)
                if not driver_id:
                    logger.debug(f"Skipping record due to unresolved driver_id for session {record.get('openf1_session_key')}, driver {driver_number_parsed}")
                    skipped_count += 1
                    continue
                
                # Resolve lap_start_id using pre-loaded map
                lap_start_id_key = (record['session_id'], driver_id, lap_start_parsed)
                lap_start_id = lap_id_map.get(lap_start_id_key)
                if not lap_start_id:
                    logger.debug(f"Skipping record due to unresolved lap_start_id for session {record.get('session_id')}, driver {driver_id}, lap {lap_start_parsed}")
                    skipped_count += 1
                    continue
                
                # Resolve lap_end_id if lap_end is not null
                lap_end_id = None
                if lap_end_parsed is not None:
                    lap_end_id_key = (record['session_id'], driver_id, lap_end_parsed)
                    lap_end_id = lap_id_map.get(lap_end_id_key)
                    # Note: lap_end_id can be None even if lap_end is provided (lap might not exist)
                
                # Check for existing record (deduplication on session_id, driver_id, lap_start)
                dedup_key = (
                    record['session_id'],
                    driver_id,
                    lap_start_parsed
                )
                
                existing_stint_id = existing_records.get(dedup_key)
                
                if existing_stint_id:
                    # Update existing record
                    updates_data.append((
                        lap_end_parsed,
                        lap_end_id,
                        tyre_age_at_start_parsed,
                        tyre_compound,
                        stint_number_parsed,
                        existing_stint_id
                    ))
                else:
                    # Insert new record
                    inserts_data.append((
                        record['session_id'],
                        driver_id,
                        lap_start_parsed,
                        lap_start_id,
                        lap_end_parsed,
                        lap_end_id,
                        tyre_age_at_start_parsed,
                        tyre_compound,
                        stint_number_parsed
                    ))
            
            logger.info(f"Will insert {len(inserts_data)} new records and update {len(updates_data)} existing records")
            
            # Perform batch inserts
            if inserts_data:
                logger.info("Inserting new stint records...")
                cur.executemany(insert_sql, inserts_data)
                inserted_count = len(inserts_data)
                logger.info(f"  Inserted {inserted_count} records")
            
            # Perform batch updates
            if updates_data:
                logger.info("Updating existing stint records...")
                cur.executemany(update_sql, updates_data)
                updated_count = len(updates_data)
                logger.info(f"  Updated {updated_count} records")
            
            conn.commit()
            logger.info(f"Successfully upserted {inserted_count + updated_count} stint records into silver.stints")
            if skipped_count > 0:
                logger.warning(f"Skipped {skipped_count} records due to validation issues")
            return inserted_count + updated_count
                    
    except psycopg.Error as e:
        conn.rollback()
        logger.error(f"Database upsert failed: {e}")
        raise


def main():
    """Main upsert function."""
    logger.info("Starting stints upsert from bronze.stints_raw to silver.stints")
    
    conn = get_db_connection()
    
    try:
        # Load driver_id and lap_id mappings
        logger.info("Loading driver_id mappings...")
        driver_id_map = get_driver_id_map(conn)
        
        logger.info("Loading lap_id mappings...")
        lap_id_map = get_lap_id_map(conn)
        
        # Get stint records from bronze with resolved session_id
        logger.info("Fetching stint records from bronze.stints_raw with resolved session_id...")
        records = get_stints_from_bronze(conn)
        
        if not records:
            logger.warning("No stint records found in bronze.stints_raw")
            return
        
        # Upsert stints
        logger.info("Upserting stint records into silver.stints...")
        upserted = upsert_stints(conn, records, driver_id_map, lap_id_map)
        
        logger.info("="*60)
        logger.info("STINTS UPSERT COMPLETE")
        logger.info("="*60)
        logger.info(f"Upserted: {upserted} records")
        
        # Show summary
        logger.info("\nSummary:")
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) as total_records,
                       COUNT(DISTINCT session_id) as unique_sessions,
                       COUNT(DISTINCT driver_id) as unique_drivers,
                       COUNT(CASE WHEN lap_end IS NOT NULL THEN 1 END) as with_lap_end,
                       COUNT(CASE WHEN tyre_compound IS NOT NULL THEN 1 END) as with_compound
                FROM silver.stints
            """)
            total, sessions, drivers, with_lap_end, with_compound = cur.fetchone()
            logger.info(f"  Total records in silver.stints: {total}")
            logger.info(f"  Unique sessions: {sessions}")
            logger.info(f"  Unique drivers: {drivers}")
            logger.info(f"  Records with lap_end: {with_lap_end}")
            logger.info(f"  Records with tyre_compound: {with_compound}")

        logger.info("\nSample Records:")
        with conn.cursor() as cur:
            cur.execute("""
                SELECT stint_id, session_id, driver_id, lap_start, lap_end, tyre_compound, stint_number
                FROM silver.stints
                ORDER BY stint_id
                LIMIT 5
            """)
            for row in cur.fetchall():
                logger.info(f"  {row[0]} | {row[1]} | {row[2]} | Start: {row[3]} | End: {row[4]} | Compound: {row[5]} | Stint: {row[6]}")
    
    finally:
        conn.close()


if __name__ == "__main__":
    main()


