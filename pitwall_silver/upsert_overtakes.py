#!/usr/bin/env python3
"""
Upsert overtakes data from bronze.overtakes_raw into silver.overtakes.

Resolves session_id by joining overtakes_raw.openf1_session_key to sessions.openf1_session_key.
Resolves overtaken_driver_id and overtaking_driver_id using driver_number + openf1_session_key lookup in driver_id_by_session view.

Maps from bronze.overtakes_raw with conversions:
- date → date (text to timestamptz)
- position → position (text to int)
"""

import os
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime

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


def parse_int(value: Optional[str]) -> Optional[int]:
    """Parse string to int, return None if invalid."""
    if value is None or value.strip() == '':
        return None
    try:
        return int(value)
    except ValueError:
        return None


def parse_timestamp(timestamp_str: Optional[str]) -> Optional[datetime]:
    """Parse timestamp from TEXT to TIMESTAMPTZ."""
    if not timestamp_str:
        return None
    try:
        # Handle 'Z' for UTC
        return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
    except ValueError:
        logger.warning(f"Could not parse timestamp: {timestamp_str}")
        return None


def get_driver_id_map(conn) -> Dict[Tuple[str, int], str]:
    """
    Get a mapping of (openf1_session_key, driver_number) -> driver_id from driver_id_by_session view.
    
    Returns:
        Dictionary mapping (session_key, driver_number) -> driver_id
    """
    driver_id_map = {}
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT openf1_session_key, driver_number, driver_id
                FROM silver.driver_id_by_session
            """)
            for row in cur.fetchall():
                key = (str(row[0]), row[1])
                driver_id_map[key] = row[2]
        logger.info(f"Loaded {len(driver_id_map)} driver_id mappings")
    except psycopg.Error as e:
        logger.error(f"Failed to fetch driver_id mappings: {e}")
        raise
    return driver_id_map


def get_overtakes_from_bronze(conn) -> List[Dict]:
    """
    Get overtake records from bronze.overtakes_raw with resolved session_id.
    """
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT DISTINCT
                    or_.openf1_session_key,
                    or_.overtaken_driver_number,
                    or_.overtaking_driver_number,
                    or_.position,
                    or_.date,
                    s.session_id
                FROM bronze.overtakes_raw or_
                INNER JOIN silver.sessions s 
                    ON or_.openf1_session_key = s.openf1_session_key
                WHERE or_.openf1_session_key IS NOT NULL
                  AND or_.overtaking_driver_number IS NOT NULL
                  AND or_.position IS NOT NULL
                  AND or_.date IS NOT NULL
                ORDER BY or_.date
            """)
            
            records = []
            for row in cur.fetchall():
                records.append({
                    'openf1_session_key': row[0],
                    'overtaken_driver_number': row[1],
                    'overtaking_driver_number': row[2],
                    'position': row[3],
                    'date': row[4],
                    'session_id': row[5]
                })
            
            logger.info(f"Found {len(records)} overtake records in bronze.overtakes_raw with resolved session_id")
            return records
    except psycopg.Error as e:
        logger.error(f"Failed to fetch overtakes from bronze: {e}")
        raise


def upsert_overtakes(conn, records: List[Dict], driver_id_map: Dict[Tuple[str, int], str]) -> int:
    """
    Upsert overtake records into silver.overtakes table.
    """
    if not records:
        logger.warning("No overtake records to upsert")
        return 0
    
    insert_sql = """
        INSERT INTO silver.overtakes (
            session_id,
            overtaken_driver_id,
            overtaking_driver_id,
            position,
            date
        ) VALUES (
            %s, %s, %s, %s, %s
        )
    """
    
    inserted_count = 0
    skipped_count = 0
    batch_size = 1000

    try:
        with conn.cursor() as cur:
            inserts_data = []
            
            for record in records:
                # Parse data types
                date_parsed = parse_timestamp(record['date'])
                if not date_parsed:
                    logger.warning(f"Skipping record due to invalid date: {record.get('date')}")
                    skipped_count += 1
                    continue
                
                position_parsed = parse_int(record['position'])
                if position_parsed is None:
                    logger.warning(f"Skipping record due to invalid position: {record.get('position')}")
                    skipped_count += 1
                    continue
                
                # Resolve overtaken_driver_id (can be NULL)
                overtaken_driver_id = None
                overtaken_driver_number_parsed = parse_int(record['overtaken_driver_number'])
                if overtaken_driver_number_parsed is not None:
                    overtaken_driver_id_key = (record['openf1_session_key'], overtaken_driver_number_parsed)
                    overtaken_driver_id = driver_id_map.get(overtaken_driver_id_key)
                    if not overtaken_driver_id:
                        logger.debug(f"Could not resolve overtaken_driver_id for session {record.get('openf1_session_key')}, driver {overtaken_driver_number_parsed} - will be NULL")
                
                overtaking_driver_number_parsed = parse_int(record['overtaking_driver_number'])
                if overtaking_driver_number_parsed is None:
                    logger.warning(f"Skipping record due to invalid overtaking_driver_number: {record.get('overtaking_driver_number')}")
                    skipped_count += 1
                    continue
                
                # Resolve overtaking_driver_id using pre-loaded map
                overtaking_driver_id_key = (record['openf1_session_key'], overtaking_driver_number_parsed)
                overtaking_driver_id = driver_id_map.get(overtaking_driver_id_key)
                if not overtaking_driver_id:
                    logger.debug(f"Skipping record due to unresolved overtaking_driver_id for session {record.get('openf1_session_key')}, driver {overtaking_driver_number_parsed}")
                    skipped_count += 1
                    continue
                
                # Insert new record
                inserts_data.append((
                    record['session_id'],
                    overtaken_driver_id,
                    overtaking_driver_id,
                    position_parsed,
                    date_parsed
                ))
            
            logger.info(f"Will insert {len(inserts_data)} new records")
            
            # Perform batch inserts
            if inserts_data:
                logger.info("Inserting new overtake records...")
                cur.executemany(insert_sql, inserts_data)
                inserted_count = len(inserts_data)
                logger.info(f"  Inserted {inserted_count} records")
            
            conn.commit()
            logger.info(f"Successfully upserted {inserted_count} overtake records into silver.overtakes")
            if skipped_count > 0:
                logger.warning(f"Skipped {skipped_count} records due to validation issues")
            return inserted_count
                    
    except psycopg.Error as e:
        conn.rollback()
        logger.error(f"Database upsert failed: {e}")
        raise


def main():
    """Main upsert function."""
    logger.info("Starting overtakes upsert from bronze.overtakes_raw to silver.overtakes")
    
    conn = get_db_connection()
    
    try:
        # Load driver_id mappings
        logger.info("Loading driver_id mappings...")
        driver_id_map = get_driver_id_map(conn)
        
        # Get overtake records from bronze with resolved session_id
        logger.info("Fetching overtake records from bronze.overtakes_raw with resolved session_id...")
        records = get_overtakes_from_bronze(conn)
        
        if not records:
            logger.warning("No overtake records found in bronze.overtakes_raw")
            return
        
        # Upsert overtakes
        logger.info("Upserting overtake records into silver.overtakes...")
        upserted = upsert_overtakes(conn, records, driver_id_map)
        
        logger.info("="*60)
        logger.info("OVERTAKES UPSERT COMPLETE")
        logger.info("="*60)
        logger.info(f"Upserted: {upserted} records")
        
        # Show summary
        logger.info("\nSummary:")
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) as total_records,
                       COUNT(DISTINCT session_id) as unique_sessions,
                       COUNT(DISTINCT overtaken_driver_id) as unique_overtaken_drivers,
                       COUNT(DISTINCT overtaking_driver_id) as unique_overtaking_drivers
                FROM silver.overtakes
            """)
            total, sessions, overtaken, overtaking = cur.fetchone()
            logger.info(f"  Total records in silver.overtakes: {total}")
            logger.info(f"  Unique sessions: {sessions}")
            logger.info(f"  Unique overtaken drivers: {overtaken}")
            logger.info(f"  Unique overtaking drivers: {overtaking}")

        logger.info("\nSample Records:")
        with conn.cursor() as cur:
            cur.execute("""
                SELECT overtake_id, session_id, overtaken_driver_id, overtaking_driver_id, position, date
                FROM silver.overtakes
                ORDER BY date DESC
                LIMIT 5
            """)
            for row in cur.fetchall():
                logger.info(f"  {row[0]} | {row[1]} | Overtaken: {row[2]} | Overtaking: {row[3]} | Position: {row[4]} | {row[5]}")
    
    finally:
        conn.close()


if __name__ == "__main__":
    main()

