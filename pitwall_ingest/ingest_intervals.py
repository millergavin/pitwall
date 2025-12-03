#!/usr/bin/env python3
"""
Ingest intervals data from OpenF1 API into bronze.intervals_raw table.

Maps OpenF1 'intervals' endpoint fields to bronze.intervals_raw columns:
- session_key -> openf1_session_key
- meeting_key -> openf1_meeting_key
- gap_to_leader -> gap_to_leader_s
- interval -> interval_s
- All other fields map directly

Uses progressive fallback for 422 errors:
1. Try meeting-scoped
2. Fall back to session-scoped
3. Fall back to driver-session-scoped
"""

import os
import sys
import time
import logging
from datetime import datetime, timezone
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


def map_interval_to_bronze(interval: Dict) -> Dict:
    """
    Map OpenF1 interval record to bronze.intervals_raw schema.
    
    Args:
        interval: Raw interval record from OpenF1 API
        
    Returns:
        Mapped record for bronze table
    """
    return {
        'openf1_meeting_key': interval.get('meeting_key'),
        'openf1_session_key': interval.get('session_key'),
        'driver_number': interval.get('driver_number'),
        'date': interval.get('date'),
        'gap_to_leader_s': interval.get('gap_to_leader'),  # Map 'gap_to_leader' to 'gap_to_leader_s'
        'interval_s': interval.get('interval'),  # Map 'interval' to 'interval_s'
        'ingested_at': datetime.now(timezone.utc)
    }


def insert_intervals(conn, intervals: List[Dict]) -> int:
    """
    Insert intervals into bronze.intervals_raw table.
    
    Args:
        conn: Database connection
        intervals: List of mapped interval records
        
    Returns:
        Number of records inserted
    """
    if not intervals:
        logger.warning("No intervals to insert")
        return 0
    
    insert_sql = """
        INSERT INTO bronze.intervals_raw (
            openf1_meeting_key,
            openf1_session_key,
            driver_number,
            date,
            gap_to_leader_s,
            interval_s,
            ingested_at
        ) VALUES (
            %(openf1_meeting_key)s,
            %(openf1_session_key)s,
            %(driver_number)s,
            %(date)s,
            %(gap_to_leader_s)s,
            %(interval_s)s,
            %(ingested_at)s
        )
    """
    
    try:
        with conn.cursor() as cur:
            mapped_records = [map_interval_to_bronze(i) for i in intervals]
            cur.executemany(insert_sql, mapped_records)
            conn.commit()
            inserted_count = len(mapped_records)
            logger.info(f"Successfully inserted {inserted_count} intervals into bronze.intervals_raw")
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


def get_session_driver_combinations(conn, session_key: Optional[str] = None) -> List[Tuple[str, str]]:
    """Get all distinct (session_key, driver_number) combinations from bronze.drivers_raw."""
    try:
        with conn.cursor() as cur:
            if session_key:
                cur.execute("""
                    SELECT DISTINCT openf1_session_key, driver_number 
                    FROM bronze.drivers_raw 
                    WHERE openf1_session_key IS NOT NULL 
                      AND driver_number IS NOT NULL 
                      AND openf1_session_key = %s
                    ORDER BY openf1_session_key, driver_number
                """, (session_key,))
            else:
                cur.execute("""
                    SELECT DISTINCT openf1_session_key, driver_number 
                    FROM bronze.drivers_raw 
                    WHERE openf1_session_key IS NOT NULL 
                      AND driver_number IS NOT NULL 
                    ORDER BY openf1_session_key, driver_number
                """)
            return [(row[0], row[1]) for row in cur.fetchall()]
    except psycopg.Error as e:
        logger.error(f"Failed to fetch session/driver combinations: {e}")
        raise


def check_existing_intervals(conn, meeting_key: Optional[str] = None, session_key: Optional[str] = None, driver_number: Optional[str] = None) -> bool:
    """Check if intervals data already exists for the given scope."""
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
            if driver_number:
                conditions.append("driver_number = %s")
                params.append(driver_number)
            
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            
            cur.execute(f"""
                SELECT COUNT(*) 
                FROM bronze.intervals_raw 
                WHERE {where_clause}
            """, tuple(params))
            count = cur.fetchone()[0]
            return count > 0
    except psycopg.Error as e:
        logger.error(f"Failed to check existing intervals: {e}")
        return False


def main():
    """Main ingestion function with progressive fallback."""
    logger.info("Starting intervals ingestion from OpenF1 API")
    
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
            if check_existing_intervals(conn, meeting_key=meeting_key):
                logger.debug(f"Skipping meeting {idx}/{len(meeting_keys)}: {meeting_key} (already exists)")
                continue
            
            logger.info(f"Processing meeting {idx}/{len(meeting_keys)}: {meeting_key}")
            
            url = f"{OPENF1_BASE_URL}/intervals"
            params = {"meeting_key": meeting_key}
            
            data, status_code = fetch_with_retry(url, params=params, return_422=True)
            
            if status_code == 422:
                logger.warning(f"422 error for meeting {meeting_key}. Will try session-scoped.")
                failed_meetings.append(meeting_key)
                continue
            
            if data is None:
                logger.error(f"Failed to fetch intervals for meeting {meeting_key}")
                total_failed += 1
                continue
            
            if not data:
                logger.debug(f"No intervals for meeting {meeting_key}")
                continue
            
            try:
                inserted = insert_intervals(conn, data)
                total_inserted += inserted
                logger.info(f"Inserted {inserted} intervals for meeting {meeting_key} (total: {total_inserted})")
            except Exception as e:
                logger.error(f"Failed to insert intervals for meeting {meeting_key}: {e}")
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
                    if check_existing_intervals(conn, session_key=session_key):
                        logger.debug(f"Skipping session {session_key} (already exists)")
                        continue
                    
                    logger.info(f"Processing session {session_key}")
                    
                    url = f"{OPENF1_BASE_URL}/intervals"
                    params = {"session_key": session_key}
                    
                    data, status_code = fetch_with_retry(url, params=params, return_422=True)
                    
                    if status_code == 422:
                        logger.warning(f"422 error for session {session_key}. Will try driver-session-scoped.")
                        failed_sessions.append(session_key)
                        continue
                    
                    if data is None:
                        logger.error(f"Failed to fetch intervals for session {session_key}")
                        total_failed += 1
                        continue
                    
                    if not data:
                        logger.debug(f"No intervals for session {session_key}")
                        continue
                    
                    try:
                        inserted = insert_intervals(conn, data)
                        total_inserted += inserted
                        logger.info(f"Inserted {inserted} intervals for session {session_key} (total: {total_inserted})")
                    except Exception as e:
                        logger.error(f"Failed to insert intervals for session {session_key}: {e}")
                        total_failed += 1
                        continue
            
            # Third pass: Try driver-session-scoped for failed sessions
            if failed_sessions:
                logger.info("="*60)
                logger.info(f"THIRD PASS: Retrying {len(failed_sessions)} sessions with driver-session-scoped ingestion")
                logger.info("="*60)
                
                for session_key in failed_sessions:
                    combinations = get_session_driver_combinations(conn, session_key=session_key)
                    logger.info(f"Processing {len(combinations)} driver combinations for session {session_key}")
                    
                    for driver_number in set(d[1] for d in combinations):
                        if check_existing_intervals(conn, session_key=session_key, driver_number=driver_number):
                            logger.debug(f"Skipping session {session_key}, driver {driver_number} (already exists)")
                            continue
                        
                        logger.info(f"Processing session {session_key}, driver {driver_number}")
                        
                        url = f"{OPENF1_BASE_URL}/intervals"
                        params = {"session_key": session_key, "driver_number": driver_number}
                        
                        data, status_code = fetch_with_retry(url, params=params, return_422=True)
                        
                        if status_code == 422:
                            logger.warning(f"Still 422 error for session {session_key}, driver {driver_number}. Skipping.")
                            total_failed += 1
                            continue
                        
                        if data is None:
                            logger.error(f"Failed to fetch intervals for session {session_key}, driver {driver_number}")
                            total_failed += 1
                            continue
                        
                        if not data:
                            logger.debug(f"No intervals for session {session_key}, driver {driver_number}")
                            continue
                        
                        try:
                            inserted = insert_intervals(conn, data)
                            total_inserted += inserted
                            logger.info(f"Inserted {inserted} intervals for session {session_key}, driver {driver_number} (total: {total_inserted})")
                        except Exception as e:
                            logger.error(f"Failed to insert intervals for session {session_key}, driver {driver_number}: {e}")
                            total_failed += 1
                            continue
        
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

