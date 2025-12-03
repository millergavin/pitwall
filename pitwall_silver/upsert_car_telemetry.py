#!/usr/bin/env python3
"""
Upsert car telemetry data from bronze.car_telemetry_raw into silver.car_telemetry.

Resolves session_id by joining car_telemetry_raw.openf1_session_key to sessions.openf1_session_key.
Resolves driver_id using driver_number + openf1_session_key lookup in driver_id_by_session view.

Maps from bronze.car_telemetry_raw with conversions:
- date → date (text to timestamptz)
- drs → drs (text to int)
- n_gear → n_gear (text to int)
- rpm → rpm (text to int)
- speed_kph → speed_kph (text to int)
- throttle → throttle (text to int)
- brake → brake (text to int)

Optimized for large datasets (~100M rows) with:
- Session-based filtering (only processes unprocessed sessions)
- COPY protocol for fast bulk inserts
- Minimal JOIN overhead
"""

import os
import logging
from typing import Dict, List, Optional, Tuple, Set
from datetime import datetime
from io import StringIO

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

# Batch processing configuration
RECORDS_PER_SESSION_BATCH = 100000  # Process up to 100k records per session batch
COPY_BATCH_SIZE = 50000  # Use COPY for batches of 50k records


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
        return None


def get_session_id_map(conn) -> Dict[str, str]:
    """
    Get a mapping of openf1_session_key -> session_id.
    
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


def get_unprocessed_sessions(conn) -> Set[str]:
    """
    Get list of sessions that have unprocessed telemetry data.
    
    Returns sessions where bronze has data but silver doesn't have complete data.
    """
    try:
        with conn.cursor() as cur:
            # Get sessions with bronze data that aren't fully in silver
            cur.execute("""
                WITH bronze_sessions AS (
                    SELECT DISTINCT openf1_session_key
                    FROM bronze.car_telemetry_raw
                    WHERE openf1_session_key IS NOT NULL
                ),
                silver_sessions AS (
                    SELECT DISTINCT s.openf1_session_key
                    FROM silver.car_telemetry ct
                    JOIN silver.sessions s ON ct.session_id = s.session_id
                )
                SELECT bs.openf1_session_key
                FROM bronze_sessions bs
                LEFT JOIN silver_sessions ss ON bs.openf1_session_key = ss.openf1_session_key
                WHERE ss.openf1_session_key IS NULL
                   OR bs.openf1_session_key IN (
                       -- Also include sessions where row counts don't match
                       SELECT ctr.openf1_session_key
                       FROM bronze.car_telemetry_raw ctr
                       GROUP BY ctr.openf1_session_key
                       HAVING COUNT(*) > (
                           SELECT COUNT(*)
                           FROM silver.car_telemetry ct
                           JOIN silver.sessions s ON ct.session_id = s.session_id
                           WHERE s.openf1_session_key = ctr.openf1_session_key
                       )
                   )
            """)
            sessions = {str(row[0]) for row in cur.fetchall()}
        logger.info(f"Found {len(sessions)} sessions with unprocessed telemetry data")
        return sessions
    except psycopg.Error as e:
        logger.error(f"Failed to get unprocessed sessions: {e}")
        raise


def get_session_record_count(conn, session_keys: Set[str]) -> int:
    """Get total count of records for specific sessions."""
    if not session_keys:
        return 0
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) 
                FROM bronze.car_telemetry_raw
                WHERE openf1_session_key = ANY(%s)
            """, (list(session_keys),))
            return cur.fetchone()[0]
    except psycopg.Error as e:
        logger.error(f"Failed to get count: {e}")
        return 0


def process_sessions(conn, session_keys: List[str], session_id_map: Dict[str, str], 
                     driver_id_map: Dict[Tuple[str, int], str]) -> Tuple[int, int]:
    """
    Process telemetry data for specific sessions using fast COPY protocol.
    
    Returns:
        Tuple of (inserted_count, skipped_count)
    """
    try:
        with conn.cursor() as cur:
            # Fetch all records for these sessions from bronze
            cur.execute("""
                SELECT 
                    openf1_session_key,
                    driver_number,
                    date,
                    drs,
                    n_gear,
                    rpm,
                    speed_kph,
                    throttle,
                    brake
                FROM bronze.car_telemetry_raw
                WHERE openf1_session_key = ANY(%s)
                  AND openf1_session_key IS NOT NULL
                  AND driver_number IS NOT NULL
                  AND date IS NOT NULL
                ORDER BY date
            """, (session_keys,))
            
            # Process records and prepare for COPY
            copy_buffer = StringIO()
            skipped_count = 0
            processed_count = 0
            
            for row in cur.fetchall():
                openf1_session_key = str(row[0]) if row[0] else None
                driver_number_str = row[1]
                date_str = row[2]
                
                # Resolve session_id
                session_id = session_id_map.get(openf1_session_key)
                if not session_id:
                    skipped_count += 1
                    continue
                
                # Parse driver_number
                driver_number = parse_int(driver_number_str)
                if driver_number is None:
                    skipped_count += 1
                    continue
                
                # Resolve driver_id
                driver_id_key = (openf1_session_key, driver_number)
                driver_id = driver_id_map.get(driver_id_key)
                if not driver_id:
                    skipped_count += 1
                    continue
                
                # Parse date
                date_parsed = parse_timestamp(date_str)
                if not date_parsed:
                    skipped_count += 1
                    continue
                
                # Parse numeric fields
                drs = parse_int(row[3])
                n_gear = parse_int(row[4])
                rpm = parse_int(row[5])
                speed_kph = parse_int(row[6])
                throttle = parse_int(row[7])
                brake = parse_int(row[8])
                
                # Format for COPY (tab-separated, \N for NULL)
                values = [
                    session_id,
                    driver_id,
                    date_parsed.isoformat() if date_parsed else '\\N',
                    str(drs) if drs is not None else '\\N',
                    str(n_gear) if n_gear is not None else '\\N',
                    str(rpm) if rpm is not None else '\\N',
                    str(speed_kph) if speed_kph is not None else '\\N',
                    str(throttle) if throttle is not None else '\\N',
                    str(brake) if brake is not None else '\\N'
                ]
                copy_buffer.write('\t'.join(values) + '\n')
                processed_count += 1
            
            # Use COPY for fast bulk insert
            inserted_count = 0
            if processed_count > 0:
                copy_buffer.seek(0)
                with cur.copy("""
                    COPY silver.car_telemetry (
                        session_id, driver_id, date, drs, n_gear, rpm, speed_kph, throttle, brake
                    ) FROM STDIN
                """) as copy:
                    while True:
                        data = copy_buffer.read(8192)
                        if not data:
                            break
                        copy.write(data)
                
                inserted_count = processed_count
                conn.commit()
            
            return (inserted_count, skipped_count)
                    
    except psycopg.Error as e:
        conn.rollback()
        logger.error(f"Database processing failed for sessions {session_keys[:3]}...: {e}")
        raise


def main():
    """Main upsert function."""
    logger.info("Starting car telemetry upsert from bronze.car_telemetry_raw to silver.car_telemetry")
    logger.info("="*60)
    
    conn = get_db_connection()
    
    try:
        # Get unprocessed sessions (OPTIMIZATION: only process what's needed)
        logger.info("Identifying unprocessed sessions...")
        unprocessed_sessions = get_unprocessed_sessions(conn)
        
        if not unprocessed_sessions:
            logger.info("No unprocessed sessions found. All data is up to date!")
            return
        
        logger.info(f"Found {len(unprocessed_sessions)} sessions to process")
        
        # Get count for these sessions
        total_count = get_session_record_count(conn, unprocessed_sessions)
        logger.info(f"Total records to process: {total_count:,}")
        
        if total_count == 0:
            logger.warning("No records found for unprocessed sessions")
            return
        
        # Load mappings
        logger.info("Loading session_id mappings...")
        session_id_map = get_session_id_map(conn)
        
        logger.info("Loading driver_id mappings...")
        driver_id_map = get_driver_id_map(conn)
        
        # Process sessions in batches
        logger.info("="*60)
        logger.info("Starting session-based processing with COPY protocol...")
        logger.info(f"Processing {len(unprocessed_sessions)} sessions")
        logger.info("="*60)
        
        total_inserted = 0
        total_skipped = 0
        session_list = list(unprocessed_sessions)
        
        # Process one session at a time for better progress tracking
        for idx, session_key in enumerate(session_list, 1):
            logger.info(f"Processing session {idx}/{len(session_list)}: {session_key}")
            
            try:
                inserted, skipped = process_sessions(conn, [session_key], session_id_map, driver_id_map)
                total_inserted += inserted
                total_skipped += skipped
                
                progress_pct = (idx / len(session_list)) * 100
                logger.info(f"  Session complete: Inserted {inserted:,}, Skipped {skipped:,} | "
                          f"Total: {total_inserted:,} inserted, {total_skipped:,} skipped ({progress_pct:.1f}% sessions)")
                
            except Exception as e:
                logger.error(f"Error processing session {session_key}: {e}")
                # Continue with next session
                continue
        
        logger.info("="*60)
        logger.info("CAR TELEMETRY UPSERT COMPLETE")
        logger.info("="*60)
        logger.info(f"Sessions processed: {len(session_list)}")
        logger.info(f"Total inserted: {total_inserted:,}")
        logger.info(f"Total skipped: {total_skipped:,}")
        if total_count > 0:
            logger.info(f"Success rate: {(total_inserted / total_count * 100):.2f}%")
        
        # Show summary
        logger.info("\nSummary:")
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) as total_records,
                       COUNT(DISTINCT session_id) as unique_sessions,
                       COUNT(DISTINCT driver_id) as unique_drivers
                FROM silver.car_telemetry
            """)
            total, sessions, drivers = cur.fetchone()
            logger.info(f"  Total records in silver.car_telemetry: {total:,}")
            logger.info(f"  Unique sessions: {sessions}")
            logger.info(f"  Unique drivers: {drivers}")
    
    finally:
        conn.close()


if __name__ == "__main__":
    main()

