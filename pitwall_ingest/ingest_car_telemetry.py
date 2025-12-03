#!/usr/bin/env python3
"""
Ingest car_telemetry data from OpenF1 API into bronze.car_telemetry_raw table.

Maps OpenF1 'car_data' endpoint fields to bronze.car_telemetry_raw columns:
- session_key -> openf1_session_key
- meeting_key -> openf1_meeting_key
- speed -> speed_kph
- All other fields map directly
"""

import os
import sys
import time
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple

import psycopg
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
OPENF1_BASE_URL = "https://api.openf1.org/v1"
RATE_LIMIT_DELAY = 0.1  # seconds between requests
MAX_429_RETRIES = 5
RETRY_DELAY_429 = 2.0  # seconds to wait when hitting 429
TIME_WINDOW_MINUTES = 30  # minutes per time window chunk for 422 retries


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


def fetch_with_retry(url: str, params: Optional[Dict] = None, return_422: bool = False) -> Tuple[Optional[List[Dict]], Optional[int]]:
    """
    Fetch data from OpenF1 API with rate limiting and 429 error handling.
    
    Args:
        url: API endpoint URL
        params: Query parameters
        return_422: If True, return 422 status code instead of empty list
        
    Returns:
        Tuple of (List of records or None if failed, status_code or None)
        Status code 422 is returned when return_422=True, otherwise None
    """
    retry_count = 0
    
    while retry_count < MAX_429_RETRIES:
        try:
            # Rate limiting delay
            if retry_count > 0:
                logger.info(f"Waiting {RETRY_DELAY_429}s before retry {retry_count}/{MAX_429_RETRIES}...")
                time.sleep(RETRY_DELAY_429)
            else:
                time.sleep(RATE_LIMIT_DELAY)
            
            response = requests.get(url, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Successfully fetched {len(data)} records from {url}")
                return (data, None)
            
            elif response.status_code == 429:
                retry_count += 1
                if retry_count >= MAX_429_RETRIES:
                    logger.error(
                        f"Hit 429 rate limit {MAX_429_RETRIES} times. "
                        f"Current delay is {RATE_LIMIT_DELAY}s. "
                        f"Please increase RATE_LIMIT_DELAY and retry."
                    )
                    sys.exit(1)
                logger.warning(f"Rate limited (429). Retry {retry_count}/{MAX_429_RETRIES}")
                continue
            
            elif response.status_code == 422:
                if return_422:
                    logger.warning(f"422 error (too much data) for {params}")
                    return (None, 422)
                else:
                    logger.warning(f"422 error (too much data) for session. Skipping this session.")
                    return ([], None)
            
            else:
                logger.error(f"API request failed with status {response.status_code}: {response.text}")
                response.raise_for_status()
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            if retry_count < MAX_429_RETRIES - 1:
                retry_count += 1
                continue
            raise
    
    return (None, None)


def map_telemetry_to_bronze(telemetry: Dict) -> Dict:
    """
    Map OpenF1 car_data record to bronze.car_telemetry_raw schema.
    
    Args:
        telemetry: Raw car_data record from OpenF1 API
        
    Returns:
        Mapped record for bronze table
    """
    return {
        'openf1_meeting_key': telemetry.get('meeting_key'),
        'openf1_session_key': telemetry.get('session_key'),
        'date': telemetry.get('date'),
        'driver_number': telemetry.get('driver_number'),
        'brake': telemetry.get('brake'),
        'drs': telemetry.get('drs'),
        'n_gear': telemetry.get('n_gear'),
        'rpm': telemetry.get('rpm'),
        'speed_kph': telemetry.get('speed'),  # Map 'speed' to 'speed_kph'
        'throttle': telemetry.get('throttle'),
        'ingested_at': datetime.now(timezone.utc)
    }


def insert_telemetry(conn, telemetry_records: List[Dict]) -> int:
    """
    Insert telemetry records into bronze.car_telemetry_raw table.
    
    Args:
        conn: Database connection
        telemetry_records: List of mapped telemetry records
        
    Returns:
        Number of records inserted
    """
    if not telemetry_records:
        logger.warning("No telemetry records to insert")
        return 0
    
    insert_sql = """
        INSERT INTO bronze.car_telemetry_raw (
            openf1_meeting_key,
            openf1_session_key,
            date,
            driver_number,
            brake,
            drs,
            n_gear,
            rpm,
            speed_kph,
            throttle,
            ingested_at
        ) VALUES (
            %(openf1_meeting_key)s,
            %(openf1_session_key)s,
            %(date)s,
            %(driver_number)s,
            %(brake)s,
            %(drs)s,
            %(n_gear)s,
            %(rpm)s,
            %(speed_kph)s,
            %(throttle)s,
            %(ingested_at)s
        )
    """
    
    try:
        with conn.cursor() as cur:
            mapped_records = [map_telemetry_to_bronze(t) for t in telemetry_records]
            cur.executemany(insert_sql, mapped_records)
            conn.commit()
            inserted_count = len(mapped_records)
            logger.info(f"Successfully inserted {inserted_count} telemetry records into bronze.car_telemetry_raw")
            return inserted_count
    except psycopg.Error as e:
        conn.rollback()
        logger.error(f"Database insert failed: {e}")
        raise


def get_session_driver_combinations(conn) -> List[tuple]:
    """
    Get all distinct (session_key, driver_number) combinations from bronze.drivers_raw.
    
    Args:
        conn: Database connection
        
    Returns:
        List of (session_key, driver_number) tuples
    """
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT DISTINCT openf1_session_key, driver_number 
                FROM bronze.drivers_raw 
                WHERE openf1_session_key IS NOT NULL 
                  AND driver_number IS NOT NULL 
                ORDER BY openf1_session_key, driver_number
            """)
            combinations = [(row[0], row[1]) for row in cur.fetchall()]
            logger.info(f"Found {len(combinations)} distinct session_key/driver_number combinations to process")
            return combinations
    except psycopg.Error as e:
        logger.error(f"Failed to fetch session/driver combinations: {e}")
        raise


def get_session_time_window(conn, session_key: str) -> Optional[Tuple[str, str]]:
    """
    Get session start and end times from bronze.sessions_raw.
    
    Args:
        conn: Database connection
        session_key: OpenF1 session key
        
    Returns:
        Tuple of (date_start, date_end) or None if not found
    """
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT date_start, date_end 
                FROM bronze.sessions_raw 
                WHERE openf1_session_key = %s
                  AND date_start IS NOT NULL 
                  AND date_end IS NOT NULL
                LIMIT 1
            """, (session_key,))
            row = cur.fetchone()
            if row:
                return (row[0], row[1])
            return None
    except psycopg.Error as e:
        logger.error(f"Failed to fetch session time window: {e}")
        return None


def create_time_windows(date_start_str: str, date_end_str: str, window_minutes: int = TIME_WINDOW_MINUTES) -> List[Tuple[str, str]]:
    """
    Create time window chunks from start to end time.
    
    Args:
        date_start_str: ISO format start datetime string
        date_end_str: ISO format end datetime string
        window_minutes: Size of each window in minutes
        
    Returns:
        List of (window_start, window_end) tuples as ISO format strings
    """
    try:
        # Parse ISO format strings (e.g., "2023-09-24T05:00:00+00:00")
        start_dt = datetime.fromisoformat(date_start_str.replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(date_end_str.replace('Z', '+00:00'))
        
        windows = []
        current_start = start_dt
        
        while current_start < end_dt:
            current_end = min(current_start + timedelta(minutes=window_minutes), end_dt)
            windows.append((
                current_start.isoformat(),
                current_end.isoformat()
            ))
            current_start = current_end
        
        return windows
    except Exception as e:
        logger.error(f"Failed to create time windows: {e}")
        return []


def check_existing_telemetry(conn, session_key: str, driver_number: str) -> bool:
    """
    Check if telemetry data already exists for this session/driver combination.
    
    Args:
        conn: Database connection
        session_key: OpenF1 session key
        driver_number: Driver number
        
    Returns:
        True if data exists, False otherwise
    """
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) 
                FROM bronze.car_telemetry_raw 
                WHERE openf1_session_key = %s 
                  AND driver_number = %s
            """, (session_key, driver_number))
            count = cur.fetchone()[0]
            return count > 0
    except psycopg.Error as e:
        logger.error(f"Failed to check existing telemetry: {e}")
        return False


def main():
    """Main ingestion function."""
    logger.info("Starting car_telemetry ingestion from OpenF1 API")
    
    # Get database connection
    conn = get_db_connection()
    
    try:
        # Get all session_key/driver_number combinations from bronze.drivers_raw
        combinations = get_session_driver_combinations(conn)
        
        if not combinations:
            logger.warning("No session_key/driver_number combinations found in bronze.drivers_raw")
            return
        
        total_inserted = 0
        total_failed = 0
        failed_422 = []  # Track combinations that failed with 422
        
        # First pass: Process each session_key/driver_number combination
        logger.info("="*60)
        logger.info("FIRST PASS: Attempting to fetch all combinations")
        logger.info("="*60)
        
        for idx, (session_key, driver_number) in enumerate(combinations, 1):
            # Skip if we already have data for this combination
            if check_existing_telemetry(conn, session_key, driver_number):
                logger.debug(f"Skipping {idx}/{len(combinations)}: session {session_key}, driver {driver_number} (already exists)")
                continue
            
            logger.info(f"Processing {idx}/{len(combinations)}: session {session_key}, driver {driver_number}")
            
            # Fetch telemetry for this session and driver
            url = f"{OPENF1_BASE_URL}/car_data"
            params = {"session_key": session_key, "driver_number": driver_number}
            
            telemetry, status_code = fetch_with_retry(url, params=params, return_422=True)
            
            if status_code == 422:
                logger.warning(f"422 error for session {session_key}, driver {driver_number}. Will retry with time windows.")
                failed_422.append((session_key, driver_number))
                continue
            
            if telemetry is None:
                logger.error(f"Failed to fetch telemetry for session_key {session_key}, driver {driver_number} after all retries")
                total_failed += 1
                continue
            
            if not telemetry:
                logger.debug(f"No telemetry returned for session_key {session_key}, driver {driver_number}")
                continue
            
            # Insert this batch
            try:
                inserted = insert_telemetry(conn, telemetry)
                total_inserted += inserted
                logger.info(f"Inserted {inserted} telemetry records for session {session_key}, driver {driver_number} (total: {total_inserted})")
            except Exception as e:
                logger.error(f"Failed to insert telemetry for session_key {session_key}, driver {driver_number}: {e}")
                total_failed += 1
                continue
        
        # Second pass: Retry failed 422 combinations with time windows
        if failed_422:
            logger.info("="*60)
            logger.info(f"SECOND PASS: Retrying {len(failed_422)} combinations with time windows")
            logger.info("="*60)
            
            for idx, (session_key, driver_number) in enumerate(failed_422, 1):
                logger.info(f"Retrying {idx}/{len(failed_422)}: session {session_key}, driver {driver_number} with time windows")
                
                # Get session time window
                time_window = get_session_time_window(conn, session_key)
                if not time_window:
                    logger.warning(f"Could not find time window for session {session_key}. Skipping.")
                    total_failed += 1
                    continue
                
                date_start, date_end = time_window
                windows = create_time_windows(date_start, date_end, TIME_WINDOW_MINUTES)
                
                logger.info(f"Breaking session {session_key} into {len(windows)} time windows of {TIME_WINDOW_MINUTES} minutes each")
                
                window_inserted = 0
                window_failed = 0
                
                for window_idx, (window_start, window_end) in enumerate(windows, 1):
                    logger.info(f"  Window {window_idx}/{len(windows)}: {window_start} to {window_end}")
                    
                    url = f"{OPENF1_BASE_URL}/car_data"
                    params = {
                        "session_key": session_key,
                        "driver_number": driver_number,
                        "date_start": window_start,
                        "date_end": window_end
                    }
                    
                    telemetry, status_code = fetch_with_retry(url, params=params, return_422=True)
                    
                    if status_code == 422:
                        logger.warning(f"  Still 422 error even with time window. Trying smaller window...")
                        # Try half the window size
                        smaller_windows = create_time_windows(window_start, window_end, TIME_WINDOW_MINUTES // 2)
                        for small_start, small_end in smaller_windows:
                            small_params = {
                                "session_key": session_key,
                                "driver_number": driver_number,
                                "date_start": small_start,
                                "date_end": small_end
                            }
                            small_telemetry, small_status = fetch_with_retry(url, params=small_params, return_422=True)
                            if small_status == 422:
                                logger.warning(f"    Still 422 with smaller window. Skipping this window.")
                                window_failed += 1
                                continue
                            if small_telemetry:
                                try:
                                    inserted = insert_telemetry(conn, small_telemetry)
                                    window_inserted += inserted
                                except Exception as e:
                                    logger.error(f"    Failed to insert: {e}")
                                    window_failed += 1
                        continue
                    
                    if telemetry is None:
                        logger.warning(f"  Failed to fetch window {window_idx}")
                        window_failed += 1
                        continue
                    
                    if not telemetry:
                        logger.debug(f"  No data in window {window_idx}")
                        continue
                    
                    # Insert this window's data
                    try:
                        inserted = insert_telemetry(conn, telemetry)
                        window_inserted += inserted
                        logger.info(f"  Inserted {inserted} records from window {window_idx}")
                    except Exception as e:
                        logger.error(f"  Failed to insert window {window_idx}: {e}")
                        window_failed += 1
                        continue
                
                total_inserted += window_inserted
                if window_failed > 0:
                    logger.warning(f"Failed to fetch {window_failed} windows for session {session_key}, driver {driver_number}")
                else:
                    logger.info(f"Successfully fetched {window_inserted} records for session {session_key}, driver {driver_number} using time windows")
        
        logger.info("="*60)
        logger.info("INGESTION COMPLETE")
        logger.info("="*60)
        logger.info(f"Total records inserted: {total_inserted:,}")
        logger.info(f"Total combinations processed: {len(combinations)}")
        if total_failed > 0:
            logger.warning(f"Failed to process {total_failed} combinations")
        if failed_422:
            logger.info(f"Retried {len(failed_422)} combinations with time windows")
    
    finally:
        conn.close()


if __name__ == "__main__":
    main()

