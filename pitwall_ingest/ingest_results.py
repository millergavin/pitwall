#!/usr/bin/env python3
"""
Ingest results data from OpenF1 API into bronze.results_raw table.

Maps OpenF1 'session_result' endpoint fields to bronze.results_raw columns:
- session_key -> openf1_session_key
- meeting_key -> openf1_meeting_key
- gap_to_leader -> gap_to_leader_s
- duration -> duration_s
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


def map_result_to_bronze(result: Dict) -> Dict:
    """
    Map OpenF1 session_result record to bronze.results_raw schema.
    
    Args:
        result: Raw result record from OpenF1 API
        
    Returns:
        Mapped record for bronze table
    """
    return {
        'openf1_session_key': result.get('session_key'),
        'driver_number': result.get('driver_number'),
        'position': result.get('position'),
        'gap_to_leader_s': result.get('gap_to_leader'),  # Map 'gap_to_leader' to 'gap_to_leader_s'
        'duration_s': result.get('duration'),  # Map 'duration' to 'duration_s'
        'laps_completed': result.get('laps_completed'),
        'dnf': result.get('dnf'),
        'dns': result.get('dns'),
        'dsq': result.get('dsq'),
        'openf1_meeting_key': result.get('meeting_key'),
        'ingested_at': datetime.now(timezone.utc)
    }


def insert_results(conn, results: List[Dict]) -> int:
    """
    Insert results into bronze.results_raw table.
    
    Args:
        conn: Database connection
        results: List of mapped result records
        
    Returns:
        Number of records inserted
    """
    if not results:
        logger.warning("No results to insert")
        return 0
    
    insert_sql = """
        INSERT INTO bronze.results_raw (
            openf1_session_key,
            driver_number,
            position,
            gap_to_leader_s,
            duration_s,
            laps_completed,
            dnf,
            dns,
            dsq,
            openf1_meeting_key,
            ingested_at
        ) VALUES (
            %(openf1_session_key)s,
            %(driver_number)s,
            %(position)s,
            %(gap_to_leader_s)s,
            %(duration_s)s,
            %(laps_completed)s,
            %(dnf)s,
            %(dns)s,
            %(dsq)s,
            %(openf1_meeting_key)s,
            %(ingested_at)s
        )
    """
    
    try:
        with conn.cursor() as cur:
            mapped_results = [map_result_to_bronze(r) for r in results]
            cur.executemany(insert_sql, mapped_results)
            conn.commit()
            inserted_count = len(mapped_results)
            logger.info(f"Successfully inserted {inserted_count} results into bronze.results_raw")
            return inserted_count
    except psycopg.Error as e:
        conn.rollback()
        logger.error(f"Database insert failed: {e}")
        raise


def get_existing_session_keys(conn) -> set:
    """
    Get all existing openf1_session_key values from bronze.results_raw.
    
    Returns:
        Set of existing session keys (as strings)
    """
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT DISTINCT openf1_session_key FROM bronze.results_raw WHERE openf1_session_key IS NOT NULL")
            existing = {str(row[0]) for row in cur.fetchall()}
            logger.info(f"Found {len(existing)} existing session keys with results data in bronze")
            return existing
    except psycopg.Error as e:
        logger.error(f"Failed to fetch existing session keys: {e}")
        return set()


def main():
    """Main ingestion function."""
    logger.info("Starting results ingestion from OpenF1 API")
    
    # Get database connection first to check existing data
    conn = get_db_connection()
    
    try:
        # Get existing session keys with results
        existing_keys = get_existing_session_keys(conn)
        
        # Fetch results from OpenF1
        url = f"{OPENF1_BASE_URL}/session_result"
        logger.info(f"Fetching from: {url}")
        
        results = fetch_with_retry(url)
        
        if results is None:
            logger.error("Failed to fetch results after all retries")
            sys.exit(1)
        
        if not results:
            logger.warning("No results returned from API")
            return
        
        # Filter out already-ingested results by session
        new_results = [
            r for r in results 
            if str(r.get('session_key')) not in existing_keys
        ]
        
        logger.info(f"Found {len(results)} total results, {len(new_results)} are from new sessions")
        
        if not new_results:
            logger.info("No new results to ingest - database is up to date!")
            return
        
        # Insert only new results
        inserted = insert_results(conn, new_results)
        logger.info(f"Ingestion complete: {inserted} new results inserted")
    finally:
        conn.close()


if __name__ == "__main__":
    main()

