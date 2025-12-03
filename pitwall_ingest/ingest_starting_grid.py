#!/usr/bin/env python3
"""
Ingest starting_grid data from OpenF1 API into bronze.starting_grid_raw table.

Maps OpenF1 'starting_grid' endpoint fields to bronze.starting_grid_raw columns:
- session_key -> openf1_session_key
- meeting_key -> openf1_meeting_key
- lap_duration -> lap_duration_s
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


def map_starting_grid_to_bronze(starting_grid: Dict) -> Dict:
    """
    Map OpenF1 starting_grid record to bronze.starting_grid_raw schema.
    
    Args:
        starting_grid: Raw starting_grid record from OpenF1 API
        
    Returns:
        Mapped record for bronze table
    """
    return {
        'openf1_session_key': starting_grid.get('session_key'),
        'driver_number': starting_grid.get('driver_number'),
        'position': starting_grid.get('position'),
        'lap_duration_s': starting_grid.get('lap_duration'),  # Map 'lap_duration' to 'lap_duration_s'
        'openf1_meeting_key': starting_grid.get('meeting_key'),
        'ingested_at': datetime.now(timezone.utc)
    }


def insert_starting_grid(conn, starting_grid_records: List[Dict]) -> int:
    """
    Insert starting_grid records into bronze.starting_grid_raw table.
    
    Args:
        conn: Database connection
        starting_grid_records: List of mapped starting_grid records
        
    Returns:
        Number of records inserted
    """
    if not starting_grid_records:
        logger.warning("No starting_grid records to insert")
        return 0
    
    insert_sql = """
        INSERT INTO bronze.starting_grid_raw (
            openf1_session_key,
            driver_number,
            position,
            lap_duration_s,
            openf1_meeting_key,
            ingested_at
        ) VALUES (
            %(openf1_session_key)s,
            %(driver_number)s,
            %(position)s,
            %(lap_duration_s)s,
            %(openf1_meeting_key)s,
            %(ingested_at)s
        )
    """
    
    try:
        with conn.cursor() as cur:
            mapped_records = [map_starting_grid_to_bronze(r) for r in starting_grid_records]
            cur.executemany(insert_sql, mapped_records)
            conn.commit()
            inserted_count = len(mapped_records)
            logger.info(f"Successfully inserted {inserted_count} starting_grid records into bronze.starting_grid_raw")
            return inserted_count
    except psycopg.Error as e:
        conn.rollback()
        logger.error(f"Database insert failed: {e}")
        raise


def get_existing_session_keys(conn) -> set:
    """
    Get all existing openf1_session_key values from bronze.starting_grid_raw.
    
    Returns:
        Set of existing session keys (as strings)
    """
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT DISTINCT openf1_session_key FROM bronze.starting_grid_raw WHERE openf1_session_key IS NOT NULL")
            existing = {str(row[0]) for row in cur.fetchall()}
            logger.info(f"Found {len(existing)} existing session keys with starting_grid data in bronze")
            return existing
    except psycopg.Error as e:
        logger.error(f"Failed to fetch existing session keys: {e}")
        return set()


def main():
    """Main ingestion function."""
    logger.info("Starting starting_grid ingestion from OpenF1 API")
    
    # Get database connection first to check existing data
    conn = get_db_connection()
    
    try:
        # Get existing session keys with starting_grid data
        existing_keys = get_existing_session_keys(conn)
        
        # Fetch starting_grid from OpenF1
        url = f"{OPENF1_BASE_URL}/starting_grid"
        logger.info(f"Fetching from: {url}")
        
        starting_grid_records = fetch_with_retry(url)
        
        if starting_grid_records is None:
            logger.error("Failed to fetch starting_grid after all retries")
            sys.exit(1)
        
        if not starting_grid_records:
            logger.warning("No starting_grid records returned from API")
            return
        
        # Filter out already-ingested records by session
        new_records = [
            r for r in starting_grid_records 
            if str(r.get('session_key')) not in existing_keys
        ]
        
        logger.info(f"Found {len(starting_grid_records)} total records, {len(new_records)} are from new sessions")
        
        if not new_records:
            logger.info("No new starting_grid records to ingest - database is up to date!")
            return
        
        # Insert only new records
        inserted = insert_starting_grid(conn, new_records)
        logger.info(f"Ingestion complete: {inserted} new starting_grid records inserted")
    finally:
        conn.close()


if __name__ == "__main__":
    main()

