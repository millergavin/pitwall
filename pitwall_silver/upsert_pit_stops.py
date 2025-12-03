#!/usr/bin/env python3
"""
Upsert pit stops data from bronze.pit_stops_raw into silver.pit_stops.

Resolves session_id by joining pit_stops_raw.openf1_session_key to sessions.openf1_session_key.
Resolves driver_id using driver_number + openf1_session_key lookup in driver_id_by_session view.

Maps from bronze.pit_stops_raw with conversions:
- date → date (text to timestamptz)
- lap_number → lap_number (text to int)
- pit_duration_s → pit_duration_ms (convert seconds to milliseconds)

Resolves lap_id by joining laps on (session_id, driver_id, lap_number).
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


def get_pit_stops_from_bronze(conn) -> List[Dict]:
    """
    Get pit stop records from bronze.pit_stops_raw with resolved session_id.
    """
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT DISTINCT
                    psr.openf1_session_key,
                    psr.driver_number,
                    psr.date,
                    psr.lap_number,
                    psr.pit_duration_s,
                    s.session_id
                FROM bronze.pit_stops_raw psr
                INNER JOIN silver.sessions s 
                    ON psr.openf1_session_key = s.openf1_session_key
                WHERE psr.openf1_session_key IS NOT NULL
                  AND psr.driver_number IS NOT NULL
                  AND psr.date IS NOT NULL
                  AND psr.lap_number IS NOT NULL
                ORDER BY psr.date
            """)
            
            records = []
            for row in cur.fetchall():
                records.append({
                    'openf1_session_key': row[0],
                    'driver_number': row[1],
                    'date': row[2],
                    'lap_number': row[3],
                    'pit_duration_s': row[4],
                    'session_id': row[5]
                })
            
            logger.info(f"Found {len(records)} pit stop records in bronze.pit_stops_raw with resolved session_id")
            return records
    except psycopg.Error as e:
        logger.error(f"Failed to fetch pit stops from bronze: {e}")
        raise


def check_existing_record(conn, session_id: str, driver_id: str, date: datetime, lap_number: int) -> Optional[int]:
    """
    Check if a record with matching key already exists.
    
    Returns:
        pit_stop_id if found, None otherwise
    """
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT pit_stop_id
                FROM silver.pit_stops
                WHERE session_id = %s
                  AND driver_id = %s
                  AND date = %s
                  AND lap_number = %s
                LIMIT 1
            """, (session_id, driver_id, date, lap_number))
            row = cur.fetchone()
            if row:
                return row[0]
    except psycopg.Error as e:
        logger.warning(f"Failed to check existing record: {e}")
    
    return None


def upsert_pit_stops(conn, records: List[Dict], driver_id_map: Dict[Tuple[str, int], str], lap_id_map: Dict[Tuple[str, str, int], int]) -> int:
    """
    Upsert pit stop records into silver.pit_stops table.
    """
    if not records:
        logger.warning("No pit stop records to upsert")
        return 0
    
    insert_sql = """
        INSERT INTO silver.pit_stops (
            session_id,
            driver_id,
            date,
            lap_number,
            lap_id,
            pit_duration_ms
        ) VALUES (
            %s, %s, %s, %s, %s, %s
        )
    """
    
    update_sql = """
        UPDATE silver.pit_stops
        SET
            pit_duration_ms = %s,
            lap_id = %s
        WHERE pit_stop_id = %s
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
                SELECT session_id, driver_id, date, lap_number, pit_stop_id
                FROM silver.pit_stops
            """)
            for row in cur.fetchall():
                key = (row[0], row[1], row[2], row[3])
                existing_records[key] = row[4]
            
            logger.info(f"Found {len(existing_records)} existing pit stop records")
            
            inserts_data = []
            updates_data = []
            
            for record in records:
                # Parse data types
                date_parsed = parse_timestamp(record['date'])
                if not date_parsed:
                    logger.warning(f"Skipping record due to invalid date: {record.get('date')}")
                    skipped_count += 1
                    continue
                
                lap_number_parsed = parse_int(record['lap_number'])
                if lap_number_parsed is None:
                    logger.warning(f"Skipping record due to invalid lap_number: {record.get('lap_number')}")
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
                
                # Convert pit_duration from seconds to milliseconds
                pit_duration_ms = convert_seconds_to_ms(record['pit_duration_s'])
                
                # Resolve lap_id using pre-loaded map
                lap_id_key = (record['session_id'], driver_id, lap_number_parsed)
                lap_id = lap_id_map.get(lap_id_key)
                if not lap_id:
                    logger.debug(f"Skipping record due to unresolved lap_id for session {record.get('session_id')}, driver {driver_id}, lap {lap_number_parsed}")
                    skipped_count += 1
                    continue
                
                # Check for existing record (deduplication)
                dedup_key = (
                    record['session_id'],
                    driver_id,
                    date_parsed,
                    lap_number_parsed
                )
                
                existing_pit_stop_id = existing_records.get(dedup_key)
                
                if existing_pit_stop_id:
                    # Update existing record
                    updates_data.append((
                        pit_duration_ms,
                        lap_id,
                        existing_pit_stop_id
                    ))
                else:
                    # Insert new record
                    inserts_data.append((
                        record['session_id'],
                        driver_id,
                        date_parsed,
                        lap_number_parsed,
                        lap_id,
                        pit_duration_ms
                    ))
            
            logger.info(f"Will insert {len(inserts_data)} new records and update {len(updates_data)} existing records")
            
            # Perform batch inserts
            if inserts_data:
                logger.info("Inserting new pit stop records...")
                cur.executemany(insert_sql, inserts_data)
                inserted_count = len(inserts_data)
                logger.info(f"  Inserted {inserted_count} records")
            
            # Perform batch updates
            if updates_data:
                logger.info("Updating existing pit stop records...")
                cur.executemany(update_sql, updates_data)
                updated_count = len(updates_data)
                logger.info(f"  Updated {updated_count} records")
            
            conn.commit()
            logger.info(f"Successfully upserted {inserted_count + updated_count} pit stop records into silver.pit_stops")
            if skipped_count > 0:
                logger.warning(f"Skipped {skipped_count} records due to validation issues")
            return inserted_count + updated_count
                    
    except psycopg.Error as e:
        conn.rollback()
        logger.error(f"Database upsert failed: {e}")
        raise


def main():
    """Main upsert function."""
    logger.info("Starting pit stops upsert from bronze.pit_stops_raw to silver.pit_stops")
    
    conn = get_db_connection()
    
    try:
        # Load driver_id and lap_id mappings
        logger.info("Loading driver_id mappings...")
        driver_id_map = get_driver_id_map(conn)
        
        logger.info("Loading lap_id mappings...")
        lap_id_map = get_lap_id_map(conn)
        
        # Get pit stop records from bronze with resolved session_id
        logger.info("Fetching pit stop records from bronze.pit_stops_raw with resolved session_id...")
        records = get_pit_stops_from_bronze(conn)
        
        if not records:
            logger.warning("No pit stop records found in bronze.pit_stops_raw")
            return
        
        # Upsert pit stops
        logger.info("Upserting pit stop records into silver.pit_stops...")
        upserted = upsert_pit_stops(conn, records, driver_id_map, lap_id_map)
        
        logger.info("="*60)
        logger.info("PIT STOPS UPSERT COMPLETE")
        logger.info("="*60)
        logger.info(f"Upserted: {upserted} records")
        
        # Show summary
        logger.info("\nSummary:")
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) as total_records,
                       COUNT(DISTINCT session_id) as unique_sessions,
                       COUNT(DISTINCT driver_id) as unique_drivers,
                       COUNT(CASE WHEN pit_duration_ms IS NOT NULL THEN 1 END) as with_duration
                FROM silver.pit_stops
            """)
            total, sessions, drivers, with_duration = cur.fetchone()
            logger.info(f"  Total records in silver.pit_stops: {total}")
            logger.info(f"  Unique sessions: {sessions}")
            logger.info(f"  Unique drivers: {drivers}")
            logger.info(f"  Records with pit_duration_ms: {with_duration}")

        logger.info("\nSample Records:")
        with conn.cursor() as cur:
            cur.execute("""
                SELECT pit_stop_id, session_id, driver_id, date, lap_number, pit_duration_ms
                FROM silver.pit_stops
                ORDER BY date DESC
                LIMIT 5
            """)
            for row in cur.fetchall():
                logger.info(f"  {row[0]} | {row[1]} | {row[2]} | {row[3]} | {row[4]} | {row[5]}")
    
    finally:
        conn.close()


if __name__ == "__main__":
    main()

