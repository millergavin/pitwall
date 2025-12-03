#!/usr/bin/env python3
"""
Ingest race_control data from OpenF1 API into bronze.race_control_raw table.

Maps OpenF1 'race_control' endpoint fields to bronze.race_control_raw columns:
- session_key -> openf1_session_key
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


def map_race_control_to_bronze(race_control: Dict) -> Dict:
    """
    Map OpenF1 race_control record to bronze.race_control_raw schema.
    
    Args:
        race_control: Raw race_control record from OpenF1 API
        
    Returns:
        Mapped record for bronze table
    """
    return {
        'openf1_session_key': race_control.get('session_key'),
        'category': race_control.get('category'),
        'date': race_control.get('date'),
        'driver_number': race_control.get('driver_number'),
        'flag': race_control.get('flag'),
        'lap_number': race_control.get('lap_number'),
        'message': race_control.get('message'),
        'scope': race_control.get('scope'),
        'sector': race_control.get('sector'),
        'openf1_meeting_key': race_control.get('meeting_key'),
        'ingested_at': datetime.now(timezone.utc)
    }


def insert_race_control(conn, race_control_records: List[Dict]) -> int:
    """
    Insert race_control records into bronze.race_control_raw table.
    
    Args:
        conn: Database connection
        race_control_records: List of mapped race_control records
        
    Returns:
        Number of records inserted
    """
    if not race_control_records:
        logger.warning("No race_control records to insert")
        return 0
    
    insert_sql = """
        INSERT INTO bronze.race_control_raw (
            openf1_session_key,
            category,
            date,
            driver_number,
            flag,
            lap_number,
            message,
            scope,
            sector,
            openf1_meeting_key,
            ingested_at
        ) VALUES (
            %(openf1_session_key)s,
            %(category)s,
            %(date)s,
            %(driver_number)s,
            %(flag)s,
            %(lap_number)s,
            %(message)s,
            %(scope)s,
            %(sector)s,
            %(openf1_meeting_key)s,
            %(ingested_at)s
        )
    """
    
    try:
        with conn.cursor() as cur:
            mapped_records = [map_race_control_to_bronze(r) for r in race_control_records]
            cur.executemany(insert_sql, mapped_records)
            conn.commit()
            inserted_count = len(mapped_records)
            logger.info(f"Successfully inserted {inserted_count} race_control records into bronze.race_control_raw")
            return inserted_count
    except psycopg.Error as e:
        conn.rollback()
        logger.error(f"Database insert failed: {e}")
        raise


def get_existing_session_keys(conn) -> set:
    """
    Get all existing openf1_session_key values from bronze.race_control_raw.
    
    Returns:
        Set of existing session keys (as strings)
    """
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT DISTINCT openf1_session_key FROM bronze.race_control_raw WHERE openf1_session_key IS NOT NULL")
            existing = {str(row[0]) for row in cur.fetchall()}
            logger.info(f"Found {len(existing)} existing session keys with race_control data in bronze")
            return existing
    except psycopg.Error as e:
        logger.error(f"Failed to fetch existing session keys: {e}")
        return set()


def main():
    """Main ingestion function."""
    logger.info("Starting race_control ingestion from OpenF1 API")
    
    # Get database connection first to check existing data
    conn = get_db_connection()
    
    try:
        # Get existing session keys with race_control data
        existing_keys = get_existing_session_keys(conn)
        
        # Fetch race_control from OpenF1
        url = f"{OPENF1_BASE_URL}/race_control"
        logger.info(f"Fetching from: {url}")
        
        race_control_records = fetch_with_retry(url)
        
        if race_control_records is None:
            logger.error("Failed to fetch race_control after all retries")
            sys.exit(1)
        
        if not race_control_records:
            logger.warning("No race_control records returned from API")
            return
        
        # Filter out already-ingested records by session
        new_records = [
            r for r in race_control_records 
            if str(r.get('session_key')) not in existing_keys
        ]
        
        logger.info(f"Found {len(race_control_records)} total records, {len(new_records)} are from new sessions")
        
        if not new_records:
            logger.info("No new race_control records to ingest - database is up to date!")
            return
        
        # Insert only new records
        inserted = insert_race_control(conn, new_records)
        logger.info(f"Ingestion complete: {inserted} new race_control records inserted")
    finally:
        conn.close()


if __name__ == "__main__":
    main()

