#!/usr/bin/env python3
"""
Ingest laps data from OpenF1 API into bronze.laps_raw table.

Maps OpenF1 'laps' endpoint fields to bronze.laps_raw columns:
- session_key -> openf1_session_key
- meeting_key -> openf1_meeting_key
- lap_duration -> lap_duration_s
- duration_sector_1 -> duration_s1_s
- duration_sector_2 -> duration_s2_s
- duration_sector_3 -> duration_s3_s
- i1_speed -> i1_speed_kph
- i2_speed -> i2_speed_kph
- st_speed -> st_speed_kph
- segments_sector_1 -> s1_segments
- segments_sector_2 -> s2_segments
- segments_sector_3 -> s3_segments
- All other fields map directly
"""

import os
import sys
import time
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

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


def fetch_with_retry(url: str, params: Optional[Dict] = None) -> Optional[List[Dict]]:
    """
    Fetch data from OpenF1 API with rate limiting and 429 error handling.
    
    Args:
        url: API endpoint URL
        params: Query parameters
        
    Returns:
        List of records or None if failed after all retries
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
                return data
            
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
            
            else:
                logger.error(f"API request failed with status {response.status_code}: {response.text}")
                response.raise_for_status()
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            if retry_count < MAX_429_RETRIES - 1:
                retry_count += 1
                continue
            raise
    
    return None


def map_lap_to_bronze(lap: Dict) -> Dict:
    """
    Map OpenF1 lap record to bronze.laps_raw schema.
    
    Args:
        lap: Raw lap record from OpenF1 API
        
    Returns:
        Mapped record for bronze table
    """
    return {
        'openf1_session_key': lap.get('session_key'),
        'driver_number': lap.get('driver_number'),
        'lap_number': lap.get('lap_number'),
        'date_start': lap.get('date_start'),
        'lap_duration_s': lap.get('lap_duration'),  # Map 'lap_duration' to 'lap_duration_s'
        'duration_s1_s': lap.get('duration_sector_1'),  # Map 'duration_sector_1' to 'duration_s1_s'
        'duration_s2_s': lap.get('duration_sector_2'),  # Map 'duration_sector_2' to 'duration_s2_s'
        'duration_s3_s': lap.get('duration_sector_3'),  # Map 'duration_sector_3' to 'duration_s3_s'
        'i1_speed_kph': lap.get('i1_speed'),  # Map 'i1_speed' to 'i1_speed_kph'
        'i2_speed_kph': lap.get('i2_speed'),  # Map 'i2_speed' to 'i2_speed_kph'
        'st_speed_kph': lap.get('st_speed'),  # Map 'st_speed' to 'st_speed_kph'
        'is_pit_out_lap': lap.get('is_pit_out_lap'),
        's1_segments': lap.get('segments_sector_1'),  # Map 'segments_sector_1' to 's1_segments'
        's2_segments': lap.get('segments_sector_2'),  # Map 'segments_sector_2' to 's2_segments'
        's3_segments': lap.get('segments_sector_3'),  # Map 'segments_sector_3' to 's3_segments'
        'openf1_meeting_key': lap.get('meeting_key'),
        'ingested_at': datetime.now(timezone.utc)
    }


def insert_laps(conn, laps: List[Dict]) -> int:
    """
    Insert laps into bronze.laps_raw table.
    
    Args:
        conn: Database connection
        laps: List of mapped lap records
        
    Returns:
        Number of records inserted
    """
    if not laps:
        logger.warning("No laps to insert")
        return 0
    
    insert_sql = """
        INSERT INTO bronze.laps_raw (
            openf1_session_key,
            driver_number,
            lap_number,
            date_start,
            lap_duration_s,
            duration_s1_s,
            duration_s2_s,
            duration_s3_s,
            i1_speed_kph,
            i2_speed_kph,
            st_speed_kph,
            is_pit_out_lap,
            s1_segments,
            s2_segments,
            s3_segments,
            openf1_meeting_key,
            ingested_at
        ) VALUES (
            %(openf1_session_key)s,
            %(driver_number)s,
            %(lap_number)s,
            %(date_start)s,
            %(lap_duration_s)s,
            %(duration_s1_s)s,
            %(duration_s2_s)s,
            %(duration_s3_s)s,
            %(i1_speed_kph)s,
            %(i2_speed_kph)s,
            %(st_speed_kph)s,
            %(is_pit_out_lap)s,
            %(s1_segments)s,
            %(s2_segments)s,
            %(s3_segments)s,
            %(openf1_meeting_key)s,
            %(ingested_at)s
        )
    """
    
    try:
        with conn.cursor() as cur:
            mapped_laps = [map_lap_to_bronze(l) for l in laps]
            cur.executemany(insert_sql, mapped_laps)
            conn.commit()
            inserted_count = len(mapped_laps)
            logger.info(f"Successfully inserted {inserted_count} laps into bronze.laps_raw")
            return inserted_count
    except psycopg.Error as e:
        conn.rollback()
        logger.error(f"Database insert failed: {e}")
        raise


def get_existing_session_keys_with_laps(conn) -> set:
    """
    Get all session keys that already have lap data in bronze.laps_raw.
    
    Returns:
        Set of session keys (as strings) that already have lap data
    """
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT DISTINCT openf1_session_key FROM bronze.laps_raw WHERE openf1_session_key IS NOT NULL")
            existing = {str(row[0]) for row in cur.fetchall()}
            logger.info(f"Found {len(existing)} session keys with existing lap data in bronze")
            return existing
    except psycopg.Error as e:
        logger.error(f"Failed to fetch existing session keys: {e}")
        return set()


def get_session_keys(conn) -> List[str]:
    """
    Get session keys from bronze.sessions_raw that don't have lap data yet.
    
    Args:
        conn: Database connection
        
    Returns:
        List of session keys that need lap data
    """
    try:
        existing_with_laps = get_existing_session_keys_with_laps(conn)
        with conn.cursor() as cur:
            cur.execute("SELECT DISTINCT openf1_session_key FROM bronze.sessions_raw WHERE openf1_session_key IS NOT NULL ORDER BY openf1_session_key")
            all_session_keys = [row[0] for row in cur.fetchall()]
            
            # Filter to only sessions that don't have lap data yet
            new_session_keys = [k for k in all_session_keys if str(k) not in existing_with_laps]
            
            logger.info(f"Found {len(all_session_keys)} total sessions, {len(new_session_keys)} need lap data")
            return new_session_keys
    except psycopg.Error as e:
        logger.error(f"Failed to fetch session keys: {e}")
        raise


def main():
    """Main ingestion function."""
    logger.info("Starting laps ingestion from OpenF1 API")
    
    # Get database connection
    conn = get_db_connection()
    
    try:
        # Get all session keys from bronze.sessions_raw
        session_keys = get_session_keys(conn)
        
        if not session_keys:
            logger.warning("No session keys found in bronze.sessions_raw")
            return
        
        total_inserted = 0
        total_failed = 0
        
        # Process each session
        for idx, session_key in enumerate(session_keys, 1):
            logger.info(f"Processing session {idx}/{len(session_keys)}: {session_key}")
            
            # Fetch laps for this session
            url = f"{OPENF1_BASE_URL}/laps"
            params = {"session_key": session_key}
            
            laps = fetch_with_retry(url, params=params)
            
            if laps is None:
                logger.error(f"Failed to fetch laps for session_key {session_key} after all retries")
                total_failed += 1
                continue
            
            if not laps:
                logger.debug(f"No laps returned for session_key {session_key}")
                continue
            
            # Insert this batch
            try:
                inserted = insert_laps(conn, laps)
                total_inserted += inserted
                logger.info(f"Inserted {inserted} laps for session {session_key} (total: {total_inserted})")
            except Exception as e:
                logger.error(f"Failed to insert laps for session_key {session_key}: {e}")
                total_failed += 1
                continue
        
        logger.info(f"Ingestion complete: {total_inserted} laps inserted across {len(session_keys)} sessions")
        if total_failed > 0:
            logger.warning(f"Failed to process {total_failed} sessions")
    
    finally:
        conn.close()


if __name__ == "__main__":
    main()

