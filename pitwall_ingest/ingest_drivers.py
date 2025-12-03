#!/usr/bin/env python3
"""
Ingest drivers data from OpenF1 API into bronze.drivers_raw table.

Maps OpenF1 'drivers' endpoint fields to bronze.drivers_raw columns:
- session_key -> openf1_session_key
- meeting_key -> openf1_meeting_key
- team_colour -> team_color_hex (British to American spelling)
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


def map_driver_to_bronze(driver: Dict) -> Dict:
    """
    Map OpenF1 driver record to bronze.drivers_raw schema.
    
    Args:
        driver: Raw driver record from OpenF1 API
        
    Returns:
        Mapped record for bronze table
    """
    return {
        'broadcast_name': driver.get('broadcast_name'),
        'team_name': driver.get('team_name'),
        'team_color_hex': driver.get('team_colour'),  # Map 'team_colour' to 'team_color_hex'
        'first_name': driver.get('first_name'),
        'last_name': driver.get('last_name'),
        'full_name': driver.get('full_name'),
        'name_acronym': driver.get('name_acronym'),
        'country_code': driver.get('country_code'),
        'headshot_url': driver.get('headshot_url'),
        'openf1_session_key': driver.get('session_key'),
        'openf1_meeting_key': driver.get('meeting_key'),
        'driver_number': driver.get('driver_number'),
        'ingested_at': datetime.now(timezone.utc)
    }


def insert_drivers(conn, drivers: List[Dict]) -> int:
    """
    Insert drivers into bronze.drivers_raw table.
    
    Args:
        conn: Database connection
        drivers: List of mapped driver records
        
    Returns:
        Number of records inserted
    """
    if not drivers:
        logger.warning("No drivers to insert")
        return 0
    
    insert_sql = """
        INSERT INTO bronze.drivers_raw (
            broadcast_name,
            team_name,
            team_color_hex,
            first_name,
            last_name,
            full_name,
            name_acronym,
            country_code,
            headshot_url,
            openf1_session_key,
            openf1_meeting_key,
            driver_number,
            ingested_at
        ) VALUES (
            %(broadcast_name)s,
            %(team_name)s,
            %(team_color_hex)s,
            %(first_name)s,
            %(last_name)s,
            %(full_name)s,
            %(name_acronym)s,
            %(country_code)s,
            %(headshot_url)s,
            %(openf1_session_key)s,
            %(openf1_meeting_key)s,
            %(driver_number)s,
            %(ingested_at)s
        )
    """
    
    try:
        with conn.cursor() as cur:
            mapped_drivers = [map_driver_to_bronze(d) for d in drivers]
            cur.executemany(insert_sql, mapped_drivers)
            conn.commit()
            inserted_count = len(mapped_drivers)
            logger.info(f"Successfully inserted {inserted_count} drivers into bronze.drivers_raw")
            return inserted_count
    except psycopg.Error as e:
        conn.rollback()
        logger.error(f"Database insert failed: {e}")
        raise


def get_existing_session_keys(conn) -> set:
    """
    Get all existing openf1_session_key values from bronze.drivers_raw.
    
    Returns:
        Set of existing session keys (as strings)
    """
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT DISTINCT openf1_session_key FROM bronze.drivers_raw WHERE openf1_session_key IS NOT NULL")
            existing = {str(row[0]) for row in cur.fetchall()}
            logger.info(f"Found {len(existing)} existing session keys with driver data in bronze")
            return existing
    except psycopg.Error as e:
        logger.error(f"Failed to fetch existing session keys: {e}")
        return set()


def get_new_session_keys(conn) -> List[str]:
    """
    Get session keys from bronze.sessions_raw that don't have driver data yet.
    
    Returns:
        List of session keys that need driver data
    """
    try:
        existing = get_existing_session_keys(conn)
        with conn.cursor() as cur:
            cur.execute("SELECT DISTINCT openf1_session_key FROM bronze.sessions_raw WHERE openf1_session_key IS NOT NULL")
            all_sessions = {str(row[0]) for row in cur.fetchall()}
            new_sessions = all_sessions - existing
            logger.info(f"Found {len(new_sessions)} sessions that need driver data")
            return list(new_sessions)
    except psycopg.Error as e:
        logger.error(f"Failed to fetch new session keys: {e}")
        return []


def main():
    """Main ingestion function."""
    logger.info("Starting drivers ingestion from OpenF1 API")
    
    # Get database connection first to check existing data
    conn = get_db_connection()
    
    try:
        # Get session keys that need driver data
        new_session_keys = get_new_session_keys(conn)
        
        if not new_session_keys:
            logger.info("No new sessions need driver data - fetching all drivers as fallback")
            # Fetch all drivers and filter by what we don't have
            url = f"{OPENF1_BASE_URL}/drivers"
            logger.info(f"Fetching from: {url}")
            
            drivers = fetch_with_retry(url)
            
            if drivers is None:
                logger.error("Failed to fetch drivers after all retries")
                sys.exit(1)
            
            if not drivers:
                logger.warning("No drivers returned from API")
                return
            
            existing_keys = get_existing_session_keys(conn)
            new_drivers = [
                d for d in drivers 
                if str(d.get('session_key')) not in existing_keys
            ]
            
            if not new_drivers:
                logger.info("No new drivers to ingest - database is up to date!")
                return
            
            inserted = insert_drivers(conn, new_drivers)
            logger.info(f"Ingestion complete: {inserted} new drivers inserted")
        else:
            # Fetch drivers for specific sessions
            total_inserted = 0
            for idx, session_key in enumerate(new_session_keys, 1):
                logger.info(f"Processing session {idx}/{len(new_session_keys)}: {session_key}")
                url = f"{OPENF1_BASE_URL}/drivers"
                params = {"session_key": session_key}
                
                drivers = fetch_with_retry(url, params=params)
                
                if drivers is None:
                    logger.error(f"Failed to fetch drivers for session {session_key}")
                    continue
                
                if drivers:
                    inserted = insert_drivers(conn, drivers)
                    total_inserted += inserted
            
            logger.info(f"Ingestion complete: {total_inserted} new drivers inserted")
    finally:
        conn.close()


if __name__ == "__main__":
    main()

