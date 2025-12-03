#!/usr/bin/env python3
"""
Upsert intervals data from bronze.intervals_raw into silver.intervals.

Resolves session_id by joining intervals_raw.openf1_session_key to sessions.openf1_session_key.
Resolves driver_id using driver_number + openf1_session_key lookup in driver_id_by_session view.

Maps from bronze.intervals_raw with conversions:
- date → date (text to timestamptz)
- gap_to_leader_s → gap_to_leader_ms (convert seconds to milliseconds)
- interval_s → interval_ms (convert seconds to milliseconds)
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


def convert_seconds_to_ms(seconds_str: Optional[str]) -> Optional[int]:
    """Convert seconds (as string) to milliseconds (as int)."""
    if not seconds_str or seconds_str.strip() == '':
        return None
    try:
        seconds = float(seconds_str)
        return int(seconds * 1000)
    except (ValueError, TypeError):
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


def get_intervals_from_bronze(conn) -> List[Dict]:
    """
    Get interval records from bronze.intervals_raw with resolved session_id.
    """
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT DISTINCT
                    ir.openf1_session_key,
                    ir.driver_number,
                    ir.date,
                    ir.gap_to_leader_s,
                    ir.interval_s,
                    s.session_id
                FROM bronze.intervals_raw ir
                INNER JOIN silver.sessions s 
                    ON ir.openf1_session_key = s.openf1_session_key
                WHERE ir.openf1_session_key IS NOT NULL
                  AND ir.driver_number IS NOT NULL
                  AND ir.date IS NOT NULL
                ORDER BY ir.date
            """)
            
            records = []
            for row in cur.fetchall():
                records.append({
                    'openf1_session_key': row[0],
                    'driver_number': row[1],
                    'date': row[2],
                    'gap_to_leader_s': row[3],
                    'interval_s': row[4],
                    'session_id': row[5]
                })
            
            logger.info(f"Found {len(records)} interval records in bronze.intervals_raw with resolved session_id")
            return records
    except psycopg.Error as e:
        logger.error(f"Failed to fetch intervals from bronze: {e}")
        raise


def upsert_intervals(conn, records: List[Dict], driver_id_map: Dict[Tuple[str, int], str]) -> int:
    """
    Upsert interval records into silver.intervals table.
    """
    if not records:
        logger.warning("No interval records to upsert")
        return 0
    
    insert_sql = """
        INSERT INTO silver.intervals (
            session_id,
            driver_id,
            date,
            gap_to_leader_ms,
            interval_ms
        ) VALUES (
            %s, %s, %s, %s, %s
        )
    """
    
    inserted_count = 0
    skipped_count = 0
    batch_size = 1000

    try:
        with conn.cursor() as cur:
            inserts_data = []
            
            for record in records:
                # Parse data types
                date_parsed = parse_timestamp(record['date'])
                if not date_parsed:
                    logger.warning(f"Skipping record due to invalid date: {record.get('date')}")
                    skipped_count += 1
                    continue
                
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
                
                # Convert times from seconds to milliseconds
                gap_to_leader_ms = convert_seconds_to_ms(record['gap_to_leader_s'])
                interval_ms = convert_seconds_to_ms(record['interval_s'])
                
                # Insert new record
                inserts_data.append((
                    record['session_id'],
                    driver_id,
                    date_parsed,
                    gap_to_leader_ms,
                    interval_ms
                ))
            
            logger.info(f"Will insert {len(inserts_data)} new records")
            
            # Perform batch inserts
            if inserts_data:
                logger.info("Inserting new interval records...")
                cur.executemany(insert_sql, inserts_data)
                inserted_count = len(inserts_data)
                logger.info(f"  Inserted {inserted_count} records")
            
            conn.commit()
            logger.info(f"Successfully upserted {inserted_count} interval records into silver.intervals")
            if skipped_count > 0:
                logger.warning(f"Skipped {skipped_count} records due to validation issues")
            return inserted_count
                    
    except psycopg.Error as e:
        conn.rollback()
        logger.error(f"Database upsert failed: {e}")
        raise


def main():
    """Main upsert function."""
    logger.info("Starting intervals upsert from bronze.intervals_raw to silver.intervals")
    
    conn = get_db_connection()
    
    try:
        # Load driver_id mappings
        logger.info("Loading driver_id mappings...")
        driver_id_map = get_driver_id_map(conn)
        
        # Get interval records from bronze with resolved session_id
        logger.info("Fetching interval records from bronze.intervals_raw with resolved session_id...")
        records = get_intervals_from_bronze(conn)
        
        if not records:
            logger.warning("No interval records found in bronze.intervals_raw")
            return
        
        # Upsert intervals
        logger.info("Upserting interval records into silver.intervals...")
        upserted = upsert_intervals(conn, records, driver_id_map)
        
        logger.info("="*60)
        logger.info("INTERVALS UPSERT COMPLETE")
        logger.info("="*60)
        logger.info(f"Upserted: {upserted} records")
        
        # Show summary
        logger.info("\nSummary:")
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) as total_records,
                       COUNT(DISTINCT session_id) as unique_sessions,
                       COUNT(DISTINCT driver_id) as unique_drivers,
                       COUNT(CASE WHEN gap_to_leader_ms IS NOT NULL THEN 1 END) as with_gap,
                       COUNT(CASE WHEN interval_ms IS NOT NULL THEN 1 END) as with_interval
                FROM silver.intervals
            """)
            total, sessions, drivers, with_gap, with_interval = cur.fetchone()
            logger.info(f"  Total records in silver.intervals: {total}")
            logger.info(f"  Unique sessions: {sessions}")
            logger.info(f"  Unique drivers: {drivers}")
            logger.info(f"  Records with gap_to_leader_ms: {with_gap}")
            logger.info(f"  Records with interval_ms: {with_interval}")

        logger.info("\nSample Records:")
        with conn.cursor() as cur:
            cur.execute("""
                SELECT interval_id, session_id, driver_id, date, gap_to_leader_ms, interval_ms
                FROM silver.intervals
                ORDER BY date DESC
                LIMIT 5
            """)
            for row in cur.fetchall():
                logger.info(f"  {row[0]} | {row[1]} | {row[2]} | {row[3]} | Gap: {row[4]}ms | Interval: {row[5]}ms")
    
    finally:
        conn.close()


if __name__ == "__main__":
    main()


