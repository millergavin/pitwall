#!/usr/bin/env python3
"""
Ingest weather data from OpenF1 API into bronze.weather_raw table.

Maps OpenF1 'weather' endpoint fields to bronze.weather_raw columns:
- session_key -> openf1_session_key
- meeting_key -> openf1_meeting_key
- All other fields map directly

Uses progressive fallback for 422 errors:
1. Try meeting-scoped
2. Fall back to session-scoped
3. Fall back to driver-session-scoped (though weather is typically session-level)
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
RATE_LIMIT_DELAY = 0.5  # seconds between requests
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


def map_weather_to_bronze(weather: Dict) -> Dict:
    """
    Map OpenF1 weather record to bronze.weather_raw schema.
    
    Args:
        weather: Raw weather record from OpenF1 API
        
    Returns:
        Mapped record for bronze table
    """
    return {
        'openf1_meeting_key': weather.get('meeting_key'),
        'openf1_session_key': weather.get('session_key'),
        'date': weather.get('date'),
        'air_temp_c': weather.get('air_temp'),
        'humidity': weather.get('humidity'),
        'pressure': weather.get('pressure'),
        'rainfall': weather.get('rainfall'),
        'track_temp_c': weather.get('track_temp'),
        'wind_direction': weather.get('wind_direction'),
        'wind_speed_mps': weather.get('wind_speed'),
        'ingested_at': datetime.now(timezone.utc)
    }


def insert_weather(conn, weather_records: List[Dict]) -> int:
    """
    Insert weather records into bronze.weather_raw table.
    
    Args:
        conn: Database connection
        weather_records: List of mapped weather records
        
    Returns:
        Number of records inserted
    """
    if not weather_records:
        logger.warning("No weather records to insert")
        return 0
    
    insert_sql = """
        INSERT INTO bronze.weather_raw (
            openf1_meeting_key,
            openf1_session_key,
            date,
            air_temp_c,
            humidity,
            pressure,
            rainfall,
            track_temp_c,
            wind_direction,
            wind_speed_mps,
            ingested_at
        ) VALUES (
            %(openf1_meeting_key)s,
            %(openf1_session_key)s,
            %(date)s,
            %(air_temp_c)s,
            %(humidity)s,
            %(pressure)s,
            %(rainfall)s,
            %(track_temp_c)s,
            %(wind_direction)s,
            %(wind_speed_mps)s,
            %(ingested_at)s
        )
    """
    
    try:
        with conn.cursor() as cur:
            mapped_records = [map_weather_to_bronze(w) for w in weather_records]
            cur.executemany(insert_sql, mapped_records)
            conn.commit()
            inserted_count = len(mapped_records)
            logger.info(f"Successfully inserted {inserted_count} weather records into bronze.weather_raw")
            return inserted_count
    except psycopg.Error as e:
        conn.rollback()
        logger.error(f"Database insert failed: {e}")
        raise


def get_meeting_keys(conn) -> List[str]:
    """Get all distinct meeting keys from bronze.meetings_raw."""
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT DISTINCT openf1_meeting_key 
                FROM bronze.meetings_raw 
                WHERE openf1_meeting_key IS NOT NULL 
                ORDER BY openf1_meeting_key
            """)
            return [row[0] for row in cur.fetchall()]
    except psycopg.Error as e:
        logger.error(f"Failed to fetch meeting keys: {e}")
        raise


def get_session_keys(conn, meeting_key: Optional[str] = None) -> List[str]:
    """Get all distinct session keys from bronze.sessions_raw, optionally filtered by meeting."""
    try:
        with conn.cursor() as cur:
            if meeting_key:
                cur.execute("""
                    SELECT DISTINCT openf1_session_key 
                    FROM bronze.sessions_raw 
                    WHERE openf1_session_key IS NOT NULL 
                      AND openf1_meeting_key = %s
                    ORDER BY openf1_session_key
                """, (meeting_key,))
            else:
                cur.execute("""
                    SELECT DISTINCT openf1_session_key 
                    FROM bronze.sessions_raw 
                    WHERE openf1_session_key IS NOT NULL 
                    ORDER BY openf1_session_key
                """)
            return [row[0] for row in cur.fetchall()]
    except psycopg.Error as e:
        logger.error(f"Failed to fetch session keys: {e}")
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


def check_existing_weather(conn, meeting_key: Optional[str] = None, session_key: Optional[str] = None) -> bool:
    """Check if weather data already exists for the given scope."""
    try:
        with conn.cursor() as cur:
            conditions = []
            params = []
            
            if meeting_key:
                conditions.append("openf1_meeting_key = %s")
                params.append(meeting_key)
            if session_key:
                conditions.append("openf1_session_key = %s")
                params.append(session_key)
            
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            
            cur.execute(f"""
                SELECT COUNT(*) 
                FROM bronze.weather_raw 
                WHERE {where_clause}
            """, tuple(params))
            count = cur.fetchone()[0]
            return count > 0
    except psycopg.Error as e:
        logger.error(f"Failed to check existing weather: {e}")
        return False


def main():
    """Main ingestion function with progressive fallback."""
    logger.info("Starting weather ingestion from OpenF1 API")
    
    conn = get_db_connection()
    
    try:
        total_inserted = 0
        total_failed = 0
        
        # Get all meeting keys
        meeting_keys = get_meeting_keys(conn)
        logger.info(f"Found {len(meeting_keys)} meetings to process")
        
        # First pass: Try meeting-scoped
        logger.info("="*60)
        logger.info("FIRST PASS: Attempting meeting-scoped ingestion")
        logger.info("="*60)
        
        failed_meetings = []
        
        for idx, meeting_key in enumerate(meeting_keys, 1):
            if check_existing_weather(conn, meeting_key=meeting_key):
                logger.debug(f"Skipping meeting {idx}/{len(meeting_keys)}: {meeting_key} (already exists)")
                continue
            
            logger.info(f"Processing meeting {idx}/{len(meeting_keys)}: {meeting_key}")
            
            url = f"{OPENF1_BASE_URL}/weather"
            params = {"meeting_key": meeting_key}
            
            data, status_code = fetch_with_retry(url, params=params, return_422=True)
            
            if status_code == 422:
                logger.warning(f"422 error for meeting {meeting_key}. Will try session-scoped.")
                failed_meetings.append(meeting_key)
                continue
            
            if data is None:
                logger.error(f"Failed to fetch weather for meeting {meeting_key}")
                total_failed += 1
                continue
            
            if not data:
                logger.debug(f"No weather for meeting {meeting_key}")
                continue
            
            try:
                inserted = insert_weather(conn, data)
                total_inserted += inserted
                logger.info(f"Inserted {inserted} weather records for meeting {meeting_key} (total: {total_inserted})")
            except Exception as e:
                logger.error(f"Failed to insert weather for meeting {meeting_key}: {e}")
                total_failed += 1
                continue
        
        # Second pass: Try session-scoped for failed meetings
        if failed_meetings:
            logger.info("="*60)
            logger.info(f"SECOND PASS: Retrying {len(failed_meetings)} meetings with session-scoped ingestion")
            logger.info("="*60)
            
            failed_sessions = []
            
            for meeting_key in failed_meetings:
                session_keys = get_session_keys(conn, meeting_key=meeting_key)
                logger.info(f"Processing {len(session_keys)} sessions for meeting {meeting_key}")
                
                for session_key in session_keys:
                    if check_existing_weather(conn, session_key=session_key):
                        logger.debug(f"Skipping session {session_key} (already exists)")
                        continue
                    
                    logger.info(f"Processing session {session_key}")
                    
                    url = f"{OPENF1_BASE_URL}/weather"
                    params = {"session_key": session_key}
                    
                    data, status_code = fetch_with_retry(url, params=params, return_422=True)
                    
                    if status_code == 422:
                        logger.warning(f"422 error for session {session_key}. Will try time windows.")
                        failed_sessions.append(session_key)
                        continue
                    
                    if data is None:
                        logger.error(f"Failed to fetch weather for session {session_key}")
                        total_failed += 1
                        continue
                    
                    if not data:
                        logger.debug(f"No weather for session {session_key}")
                        continue
                    
                    try:
                        inserted = insert_weather(conn, data)
                        total_inserted += inserted
                        logger.info(f"Inserted {inserted} weather records for session {session_key} (total: {total_inserted})")
                    except Exception as e:
                        logger.error(f"Failed to insert weather for session {session_key}: {e}")
                        total_failed += 1
                        continue
            
            # Third pass: Try time-window-scoped for failed sessions
            if failed_sessions:
                logger.info("="*60)
                logger.info(f"THIRD PASS: Retrying {len(failed_sessions)} sessions with time-window-scoped ingestion")
                logger.info("="*60)
                
                for session_key in failed_sessions:
                    logger.info(f"Retrying session {session_key} with time windows")
                    
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
                        
                        url = f"{OPENF1_BASE_URL}/weather"
                        params = {
                            "session_key": session_key,
                            "date_start": window_start,
                            "date_end": window_end
                        }
                        
                        data, status_code = fetch_with_retry(url, params=params, return_422=True)
                        
                        if status_code == 422:
                            logger.warning(f"  Still 422 error even with time window. Trying smaller window...")
                            # Try half the window size
                            smaller_windows = create_time_windows(window_start, window_end, TIME_WINDOW_MINUTES // 2)
                            for small_start, small_end in smaller_windows:
                                small_params = {
                                    "session_key": session_key,
                                    "date_start": small_start,
                                    "date_end": small_end
                                }
                                small_data, small_status = fetch_with_retry(url, params=small_params, return_422=True)
                                if small_status == 422:
                                    logger.warning(f"    Still 422 with smaller window. Skipping this window.")
                                    window_failed += 1
                                    continue
                                if small_data:
                                    try:
                                        inserted = insert_weather(conn, small_data)
                                        window_inserted += inserted
                                    except Exception as e:
                                        logger.error(f"    Failed to insert: {e}")
                                        window_failed += 1
                            continue
                        
                        if data is None:
                            logger.warning(f"  Failed to fetch window {window_idx}")
                            window_failed += 1
                            continue
                        
                        if not data:
                            logger.debug(f"  No data in window {window_idx}")
                            continue
                        
                        # Insert this window's data
                        try:
                            inserted = insert_weather(conn, data)
                            window_inserted += inserted
                            logger.info(f"  Inserted {inserted} records from window {window_idx}")
                        except Exception as e:
                            logger.error(f"  Failed to insert window {window_idx}: {e}")
                            window_failed += 1
                            continue
                    
                    total_inserted += window_inserted
                    if window_failed > 0:
                        logger.warning(f"Failed to fetch {window_failed} windows for session {session_key}")
                    else:
                        logger.info(f"Successfully fetched {window_inserted} records for session {session_key} using time windows")
        
        logger.info("="*60)
        logger.info("INGESTION COMPLETE")
        logger.info("="*60)
        logger.info(f"Total records inserted: {total_inserted:,}")
        if total_failed > 0:
            logger.warning(f"Failed to process {total_failed} scopes")
    
    finally:
        conn.close()


if __name__ == "__main__":
    main()

