#!/usr/bin/env python3
"""
Ingest sessions data from OpenF1 API into bronze.sessions_raw table.

Maps OpenF1 'sessions' endpoint fields to bronze.sessions_raw columns:
- meeting_key -> openf1_meeting_key
- session_key -> openf1_session_key
- circuit_key -> openf1_circuit_key
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


def map_session_to_bronze(session: Dict) -> Dict:
    """
    Map OpenF1 session record to bronze.sessions_raw schema.
    
    Args:
        session: Raw session record from OpenF1 API
        
    Returns:
        Mapped record for bronze table
    """
    return {
        'openf1_meeting_key': session.get('meeting_key'),
        'openf1_session_key': session.get('session_key'),
        'date_start': session.get('date_start'),
        'date_end': session.get('date_end'),
        'session_name': session.get('session_name'),
        'openf1_circuit_key': session.get('circuit_key'),
        'circuit_short_name': session.get('circuit_short_name'),
        'country_code': session.get('country_code'),
        'country_key': session.get('country_key'),
        'country_name': session.get('country_name'),
        'gmt_offset': session.get('gmt_offset'),
        'location': session.get('location'),
        'session_type': session.get('session_type'),
        'year': session.get('year'),
        'ingested_at': datetime.now(timezone.utc)
    }


def insert_sessions(conn, sessions: List[Dict]) -> int:
    """
    Insert sessions into bronze.sessions_raw table.
    
    Args:
        conn: Database connection
        sessions: List of mapped session records
        
    Returns:
        Number of records inserted
    """
    if not sessions:
        logger.warning("No sessions to insert")
        return 0
    
    insert_sql = """
        INSERT INTO bronze.sessions_raw (
            openf1_meeting_key,
            openf1_session_key,
            date_start,
            date_end,
            session_name,
            openf1_circuit_key,
            circuit_short_name,
            country_code,
            country_key,
            country_name,
            gmt_offset,
            location,
            session_type,
            year,
            ingested_at
        ) VALUES (
            %(openf1_meeting_key)s,
            %(openf1_session_key)s,
            %(date_start)s,
            %(date_end)s,
            %(session_name)s,
            %(openf1_circuit_key)s,
            %(circuit_short_name)s,
            %(country_code)s,
            %(country_key)s,
            %(country_name)s,
            %(gmt_offset)s,
            %(location)s,
            %(session_type)s,
            %(year)s,
            %(ingested_at)s
        )
    """
    
    try:
        with conn.cursor() as cur:
            mapped_sessions = [map_session_to_bronze(s) for s in sessions]
            cur.executemany(insert_sql, mapped_sessions)
            conn.commit()
            inserted_count = len(mapped_sessions)
            logger.info(f"Successfully inserted {inserted_count} sessions into bronze.sessions_raw")
            return inserted_count
    except psycopg.Error as e:
        conn.rollback()
        logger.error(f"Database insert failed: {e}")
        raise


def get_existing_session_keys(conn) -> set:
    """
    Get all existing openf1_session_key values from bronze.sessions_raw.
    
    Returns:
        Set of existing session keys (as strings)
    """
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT DISTINCT openf1_session_key FROM bronze.sessions_raw WHERE openf1_session_key IS NOT NULL")
            existing = {str(row[0]) for row in cur.fetchall()}
            logger.info(f"Found {len(existing)} existing session keys in bronze")
            return existing
    except psycopg.Error as e:
        logger.error(f"Failed to fetch existing session keys: {e}")
        return set()


def main():
    """Main ingestion function."""
    logger.info("Starting sessions ingestion from OpenF1 API")
    
    # Get database connection first to check existing data
    conn = get_db_connection()
    
    try:
        # Get existing session keys
        existing_keys = get_existing_session_keys(conn)
        
        # Fetch sessions from OpenF1
        url = f"{OPENF1_BASE_URL}/sessions"
        logger.info(f"Fetching from: {url}")
        
        sessions = fetch_with_retry(url)
        
        if sessions is None:
            logger.error("Failed to fetch sessions after all retries")
            sys.exit(1)
        
        if not sessions:
            logger.warning("No sessions returned from API")
            return
        
        # Filter out already-ingested sessions
        new_sessions = [
            s for s in sessions 
            if str(s.get('session_key')) not in existing_keys
        ]
        
        logger.info(f"Found {len(sessions)} total sessions, {len(new_sessions)} are new")
        
        if not new_sessions:
            logger.info("No new sessions to ingest - database is up to date!")
            return
        
        # Insert only new sessions
        inserted = insert_sessions(conn, new_sessions)
        logger.info(f"Ingestion complete: {inserted} new sessions inserted")
    finally:
        conn.close()


if __name__ == "__main__":
    main()

