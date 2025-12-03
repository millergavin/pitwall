#!/usr/bin/env python3
"""
Upsert position data from bronze.position_raw into silver.position.

Resolves session_id by joining position_raw.openf1_session_key to sessions.openf1_session_key.
Resolves driver_id using driver_number + openf1_session_key lookup in driver_id_by_session view.

Maps from bronze.position_raw with conversions:
- date → date (text to timestamptz)
- position → position (text to int)
"""

import os
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime

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


def parse_timestamp(timestamp_str: Optional[str]) -> Optional[datetime]:
    """Parse timestamp from TEXT to TIMESTAMPTZ."""
    if not timestamp_str:
        return None
    try:
        # Handle 'Z' for UTC
        return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
    except ValueError:
        logger.warning(f"Could not parse timestamp: {timestamp_str}")
        return None


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


def get_positions_from_bronze(conn) -> List[Dict]:
    """
    Get position records from bronze.position_raw with resolved session_id.
    """
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT DISTINCT
                    pr.openf1_session_key,
                    pr.driver_number,
                    pr.date,
                    pr.position,
                    s.session_id
                FROM bronze.position_raw pr
                INNER JOIN silver.sessions s 
                    ON pr.openf1_session_key = s.openf1_session_key
                WHERE pr.openf1_session_key IS NOT NULL
                  AND pr.driver_number IS NOT NULL
                  AND pr.date IS NOT NULL
                ORDER BY pr.date
            """)
            
            records = []
            for row in cur.fetchall():
                records.append({
                    'openf1_session_key': row[0],
                    'driver_number': row[1],
                    'date': row[2],
                    'position': row[3],
                    'session_id': row[4]
                })
            
            logger.info(f"Found {len(records)} position records in bronze.position_raw with resolved session_id")
            return records
    except psycopg.Error as e:
        logger.error(f"Failed to fetch positions from bronze: {e}")
        raise


def upsert_positions(conn, records: List[Dict], driver_id_map: Dict[Tuple[str, int], str]) -> int:
    """
    Upsert position records into silver.position table with deduplication.
    """
    if not records:
        logger.warning("No position records to upsert")
        return 0
    
    insert_sql = """
        INSERT INTO silver.position (
            session_id,
            driver_id,
            date,
            position
        ) VALUES (
            %s, %s, %s, %s
        )
    """
    
    inserted_count = 0
    skipped_count = 0
    batch_size = 1000

    try:
        with conn.cursor() as cur:
            # Pre-fetch existing records for deduplication
            logger.info("Checking for existing records...")
            existing_records = set()
            cur.execute("""
                SELECT p.session_id, p.driver_id, p.date
                FROM silver.position p
            """)
            for row in cur.fetchall():
                existing_records.add((row[0], row[1], row[2]))
            
            logger.info(f"Found {len(existing_records)} existing position records")
            
            inserts_data = []
            
            for record in records:
                # Parse data types
                date_parsed = parse_timestamp(record['date'])
                if not date_parsed:
                    logger.warning(f"Skipping record due to invalid date: {record.get('date')}")
                    skipped_count += 1
                    continue
                
                position_parsed = parse_int(record['position'])
                
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
                
                # Check for existing record (deduplication)
                dedup_key = (
                    record['session_id'],
                    driver_id,
                    date_parsed
                )
                
                if dedup_key in existing_records:
                    # Skip duplicate
                    skipped_count += 1
                    continue
                
                # Insert new record
                inserts_data.append((
                    record['session_id'],
                    driver_id,
                    date_parsed,
                    position_parsed
                ))
            
            logger.info(f"Will insert {len(inserts_data)} new records")
            
            # Perform batch inserts
            if inserts_data:
                logger.info("Inserting new position records...")
                cur.executemany(insert_sql, inserts_data)
                inserted_count = len(inserts_data)
                logger.info(f"  Inserted {inserted_count} records")
            
            conn.commit()
            logger.info(f"Successfully upserted {inserted_count} position records into silver.position")
            if skipped_count > 0:
                logger.warning(f"Skipped {skipped_count} records due to validation issues or duplicates")
            return inserted_count
                    
    except psycopg.Error as e:
        conn.rollback()
        logger.error(f"Database upsert failed: {e}")
        raise


def main():
    """Main upsert function."""
    logger.info("Starting position upsert from bronze.position_raw to silver.position")
    
    conn = get_db_connection()
    
    try:
        # Load driver_id mappings
        logger.info("Loading driver_id mappings...")
        driver_id_map = get_driver_id_map(conn)
        
        # Get position records from bronze with resolved session_id
        logger.info("Fetching position records from bronze.position_raw with resolved session_id...")
        records = get_positions_from_bronze(conn)
        
        if not records:
            logger.warning("No position records found in bronze.position_raw")
            return
        
        # Upsert positions
        logger.info("Upserting position records into silver.position...")
        upserted = upsert_positions(conn, records, driver_id_map)
        
        logger.info("="*60)
        logger.info("POSITION UPSERT COMPLETE")
        logger.info("="*60)
        logger.info(f"Upserted: {upserted} records")
        
        # Show summary
        logger.info("\nSummary:")
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) as total_records,
                       COUNT(DISTINCT session_id) as unique_sessions,
                       COUNT(DISTINCT driver_id) as unique_drivers,
                       COUNT(CASE WHEN position IS NOT NULL THEN 1 END) as with_position
                FROM silver.position
            """)
            total, sessions, drivers, with_position = cur.fetchone()
            logger.info(f"  Total records in silver.position: {total}")
            logger.info(f"  Unique sessions: {sessions}")
            logger.info(f"  Unique drivers: {drivers}")
            logger.info(f"  Records with position: {with_position}")

        logger.info("\nSample Records:")
        with conn.cursor() as cur:
            cur.execute("""
                SELECT position_id, session_id, driver_id, date, position
                FROM silver.position
                ORDER BY date DESC
                LIMIT 5
            """)
            for row in cur.fetchall():
                logger.info(f"  {row[0]} | {row[1]} | {row[2]} | {row[3]} | Position: {row[4]}")
    
    finally:
        conn.close()


if __name__ == "__main__":
    main()


