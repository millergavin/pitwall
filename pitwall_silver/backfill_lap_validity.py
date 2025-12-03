#!/usr/bin/env python3
"""
Backfill lap validity in silver.laps.

Derives is_pit_in_lap from silver.pit_stops:
- If there is a pit stop with matching pit_stops.lap_id, then laps.is_pit_in_lap = TRUE

Derives is_valid based on lap validity rules:
- FALSE if is_pit_out_lap = TRUE
- FALSE if is_pit_in_lap = TRUE
- FALSE if race_control message contains "deleted" (case insensitive) and race_control.referenced_lap_id matches lap_id
- TRUE otherwise
"""

import os
import logging
from typing import Set

import psycopg
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


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
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        raise


def get_pit_in_lap_ids(conn) -> Set[int]:
    """
    Get set of lap_ids that have matching pit stops.
    
    Returns:
        Set of lap_id values (as integers)
    """
    pit_in_lap_ids = set()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT DISTINCT lap_id
                FROM silver.pit_stops
                WHERE lap_id IS NOT NULL
            """)
            for row in cur.fetchall():
                pit_in_lap_ids.add(row[0])
        logger.info(f"Found {len(pit_in_lap_ids)} lap_ids with pit stops")
    except psycopg.Error as e:
        logger.error(f"Failed to fetch pit in lap IDs: {e}")
        raise
    return pit_in_lap_ids


def get_deleted_lap_ids(conn) -> Set[int]:
    """
    Get set of lap_ids that are marked as deleted in race_control messages.
    
    Returns:
        Set of lap_id values (as integers) that are deleted
    """
    deleted_lap_ids = set()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT DISTINCT referenced_lap_id
                FROM silver.race_control
                WHERE referenced_lap_id IS NOT NULL
                  AND message IS NOT NULL
                  AND LOWER(message) LIKE '%deleted%'
            """)
            for row in cur.fetchall():
                deleted_lap_ids.add(row[0])
        logger.info(f"Found {len(deleted_lap_ids)} lap_ids marked as deleted in race control")
    except psycopg.Error as e:
        logger.error(f"Failed to fetch deleted lap IDs: {e}")
        raise
    return deleted_lap_ids


def update_lap_validity(conn, pit_in_lap_ids: Set[int], deleted_lap_ids: Set[int]) -> tuple[int, int]:
    """
    Update is_pit_in_lap and is_valid for all laps.
    
    Returns:
        Tuple of (pit_in_laps_updated, validity_updated)
    """
    try:
        with conn.cursor() as cur:
            # Step 1: Update is_pit_in_lap based on pit_stops
            logger.info("Updating is_pit_in_lap based on pit_stops...")
            cur.execute("""
                UPDATE silver.laps
                SET is_pit_in_lap = TRUE
                WHERE lap_id IN (
                    SELECT DISTINCT lap_id
                    FROM silver.pit_stops
                    WHERE lap_id IS NOT NULL
                )
            """)
            pit_in_updated = cur.rowcount
            logger.info(f"  Set is_pit_in_lap = TRUE for {pit_in_updated} laps")
            
            # Step 2: Set is_pit_in_lap = FALSE for all other laps
            cur.execute("""
                UPDATE silver.laps
                SET is_pit_in_lap = FALSE
                WHERE lap_id NOT IN (
                    SELECT DISTINCT lap_id
                    FROM silver.pit_stops
                    WHERE lap_id IS NOT NULL
                )
            """)
            logger.info(f"  Set is_pit_in_lap = FALSE for {cur.rowcount} laps")
            
            # Step 3: Update is_valid based on all rules
            logger.info("Updating is_valid based on validity rules...")
            
            # First, set all laps to valid (TRUE) by default
            cur.execute("""
                UPDATE silver.laps
                SET is_valid = TRUE
            """)
            logger.info(f"  Set is_valid = TRUE for all {cur.rowcount} laps (default)")
            
            # Then, set invalid for pit out laps
            cur.execute("""
                UPDATE silver.laps
                SET is_valid = FALSE
                WHERE is_pit_out_lap = TRUE
            """)
            pit_out_invalid = cur.rowcount
            logger.info(f"  Set is_valid = FALSE for {pit_out_invalid} pit out laps")
            
            # Set invalid for pit in laps
            cur.execute("""
                UPDATE silver.laps
                SET is_valid = FALSE
                WHERE is_pit_in_lap = TRUE
            """)
            pit_in_invalid = cur.rowcount
            logger.info(f"  Set is_valid = FALSE for {pit_in_invalid} pit in laps")
            
            # Set invalid for deleted laps (from race_control)
            if deleted_lap_ids:
                # Convert set to list for SQL IN clause
                deleted_lap_ids_list = list(deleted_lap_ids)
                cur.execute("""
                    UPDATE silver.laps
                    SET is_valid = FALSE
                    WHERE lap_id = ANY(%s)
                """, (deleted_lap_ids_list,))
                deleted_invalid = cur.rowcount
                logger.info(f"  Set is_valid = FALSE for {deleted_invalid} deleted laps")
            else:
                deleted_invalid = 0
                logger.info("  No deleted laps found in race control")
            
            conn.commit()
            
            # Summary counts
            cur.execute("""
                SELECT 
                    COUNT(*) as total_laps,
                    COUNT(CASE WHEN is_pit_in_lap = TRUE THEN 1 END) as pit_in_laps,
                    COUNT(CASE WHEN is_pit_out_lap = TRUE THEN 1 END) as pit_out_laps,
                    COUNT(CASE WHEN is_valid = TRUE THEN 1 END) as valid_laps,
                    COUNT(CASE WHEN is_valid = FALSE THEN 1 END) as invalid_laps
                FROM silver.laps
            """)
            total, pit_in, pit_out, valid, invalid = cur.fetchone()
            
            logger.info("")
            logger.info("Final Summary:")
            logger.info(f"  Total laps: {total}")
            logger.info(f"  Pit in laps: {pit_in}")
            logger.info(f"  Pit out laps: {pit_out}")
            logger.info(f"  Valid laps: {valid}")
            logger.info(f"  Invalid laps: {invalid}")
            
            return (pit_in_updated, invalid)
            
    except psycopg.Error as e:
        conn.rollback()
        logger.error(f"Database update failed: {e}")
        raise


def main():
    """Main function."""
    logger.info("Starting lap validity backfill")
    logger.info("="*60)
    
    conn = get_db_connection()
    
    try:
        # Get pit in lap IDs
        logger.info("Loading pit in lap IDs from silver.pit_stops...")
        pit_in_lap_ids = get_pit_in_lap_ids(conn)
        
        # Get deleted lap IDs from race control
        logger.info("Loading deleted lap IDs from silver.race_control...")
        deleted_lap_ids = get_deleted_lap_ids(conn)
        
        # Update lap validity
        logger.info("Updating lap validity...")
        pit_in_updated, validity_updated = update_lap_validity(conn, pit_in_lap_ids, deleted_lap_ids)
        
        logger.info("")
        logger.info("="*60)
        logger.info("LAP VALIDITY BACKFILL COMPLETE")
        logger.info("="*60)
        logger.info(f"Updated is_pit_in_lap for {pit_in_updated} laps")
        logger.info(f"Updated is_valid for all laps")
        
        # Show some sample invalid laps
        logger.info("")
        logger.info("Sample Invalid Laps:")
        with conn.cursor() as cur:
            cur.execute("""
                SELECT lap_id, session_id, driver_id, lap_number, 
                       is_pit_out_lap, is_pit_in_lap, is_valid
                FROM silver.laps
                WHERE is_valid = FALSE
                ORDER BY lap_id
                LIMIT 10
            """)
            for row in cur.fetchall():
                logger.info(f"  {row[0]} | {row[1]} | {row[2]} | Lap {row[3]} | "
                          f"Pit Out: {row[4]} | Pit In: {row[5]} | Valid: {row[6]}")
    
    finally:
        conn.close()


if __name__ == "__main__":
    main()


