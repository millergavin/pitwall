#!/usr/bin/env python3
"""
Ingest meetings data from OpenF1 API into bronze.meetings_raw table.

Maps OpenF1 'meetings' endpoint fields to bronze.meetings_raw columns:
- circuit_key -> openf1_circuit_key
- year -> season
- meeting_key -> openf1_meeting_key
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


def map_meeting_to_bronze(meeting: Dict) -> Dict:
    """
    Map OpenF1 meeting record to bronze.meetings_raw schema.
    
    Args:
        meeting: Raw meeting record from OpenF1 API
        
    Returns:
        Mapped record for bronze table
    """
    return {
        'openf1_circuit_key': meeting.get('circuit_key'),
        'circuit_short_name': meeting.get('circuit_short_name'),
        'country_code': meeting.get('country_code'),
        'location': meeting.get('location'),
        'gmt_offset': meeting.get('gmt_offset'),
        'country_name': meeting.get('country_name'),
        'country_key': meeting.get('country_key'),
        'meeting_name': meeting.get('meeting_name'),
        'season': meeting.get('year'),  # Map 'year' to 'season'
        'meeting_official_name': meeting.get('meeting_official_name'),
        'date_start': meeting.get('date_start'),
        'openf1_meeting_key': meeting.get('meeting_key'),
        'ingested_at': datetime.now(timezone.utc)
    }


def insert_meetings(conn, meetings: List[Dict]) -> int:
    """
    Insert meetings into bronze.meetings_raw table.
    
    Args:
        conn: Database connection
        meetings: List of mapped meeting records
        
    Returns:
        Number of records inserted
    """
    if not meetings:
        logger.warning("No meetings to insert")
        return 0
    
    insert_sql = """
        INSERT INTO bronze.meetings_raw (
            openf1_circuit_key,
            circuit_short_name,
            country_code,
            location,
            gmt_offset,
            country_name,
            country_key,
            meeting_name,
            season,
            meeting_official_name,
            date_start,
            openf1_meeting_key,
            ingested_at
        ) VALUES (
            %(openf1_circuit_key)s,
            %(circuit_short_name)s,
            %(country_code)s,
            %(location)s,
            %(gmt_offset)s,
            %(country_name)s,
            %(country_key)s,
            %(meeting_name)s,
            %(season)s,
            %(meeting_official_name)s,
            %(date_start)s,
            %(openf1_meeting_key)s,
            %(ingested_at)s
        )
    """
    
    try:
        with conn.cursor() as cur:
            mapped_meetings = [map_meeting_to_bronze(m) for m in meetings]
            cur.executemany(insert_sql, mapped_meetings)
            conn.commit()
            inserted_count = len(mapped_meetings)
            logger.info(f"Successfully inserted {inserted_count} meetings into bronze.meetings_raw")
            return inserted_count
    except psycopg.Error as e:
        conn.rollback()
        logger.error(f"Database insert failed: {e}")
        raise


def get_existing_meeting_keys(conn) -> set:
    """
    Get all existing openf1_meeting_key values from bronze.meetings_raw.
    
    Returns:
        Set of existing meeting keys (as strings)
    """
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT DISTINCT openf1_meeting_key FROM bronze.meetings_raw WHERE openf1_meeting_key IS NOT NULL")
            existing = {str(row[0]) for row in cur.fetchall()}
            logger.info(f"Found {len(existing)} existing meeting keys in bronze")
            return existing
    except psycopg.Error as e:
        logger.error(f"Failed to fetch existing meeting keys: {e}")
        return set()


def main():
    """Main ingestion function."""
    logger.info("Starting meetings ingestion from OpenF1 API")
    
    # Get database connection first to check existing data
    conn = get_db_connection()
    
    try:
        # Get existing meeting keys
        existing_keys = get_existing_meeting_keys(conn)
        
        # Fetch meetings from OpenF1
        url = f"{OPENF1_BASE_URL}/meetings"
        logger.info(f"Fetching from: {url}")
        
        meetings = fetch_with_retry(url)
        
        if meetings is None:
            logger.error("Failed to fetch meetings after all retries")
            sys.exit(1)
        
        if not meetings:
            logger.warning("No meetings returned from API")
            return
        
        # Filter out already-ingested meetings
        new_meetings = [
            m for m in meetings 
            if str(m.get('meeting_key')) not in existing_keys
        ]
        
        logger.info(f"Found {len(meetings)} total meetings, {len(new_meetings)} are new")
        
        if not new_meetings:
            logger.info("No new meetings to ingest - database is up to date!")
            return
        
        # Insert only new meetings
        inserted = insert_meetings(conn, new_meetings)
        logger.info(f"Ingestion complete: {inserted} new meetings inserted")
    finally:
        conn.close()


if __name__ == "__main__":
    main()

