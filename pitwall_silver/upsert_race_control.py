#!/usr/bin/env python3
"""
Upsert race control data from bronze.race_control_raw into silver.race_control.

Resolves session_id by joining race_control_raw.openf1_session_key to sessions.openf1_session_key.
Resolves driver_id using driver_number + openf1_session_key lookup in driver_id_by_session view,
with fallback to parsing "CAR {n}" from message text.

Maps from bronze.race_control_raw with conversions:
- category → category (text)
- date → date (text to timestamptz)
- flag → flag (text, nullable)
- lap_number → lap_number (text to int, nullable)
- message → message (text, nullable)
- scope → scope (text, nullable)

Derives referenced_lap_number by parsing "LAP {n}" from message text.
Resolves referenced_lap_id by joining laps on (session_id, driver_id, lap_number).

Deduplicates on (session_id, date, flag, lap_number, message, scope).
"""

import os
import re
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


def extract_car_number_from_message(message: Optional[str]) -> Optional[int]:
    """
    Extract driver number from message text using "CAR {n}" pattern.
    
    Examples:
    - "WAVED BLUE FLAG FOR CAR 11 (PER) TIMED AT 11:43:52" → 11
    - "CAR 4" → 4
    
    Returns:
        Driver number as int, or None if not found
    """
    if not message:
        return None
    
    # Pattern: "CAR" followed by whitespace and a number
    # Case-insensitive, handles variations like "CAR 11", "CAR11", etc.
    pattern = r'CAR\s+(\d+)'
    match = re.search(pattern, message, re.IGNORECASE)
    if match:
        try:
            return int(match.group(1))
        except ValueError:
            return None
    return None


def extract_lap_number_from_message(message: Optional[str]) -> Optional[int]:
    """
    Extract referenced lap number from message text using "LAP {n}" pattern.
    
    Examples:
    - "LAP 15" → 15
    - "PENALTY ON LAP 23" → 23
    
    Returns:
        Lap number as int, or None if not found
    """
    if not message:
        return None
    
    # Pattern: "LAP" followed by whitespace and a number
    # Case-insensitive, handles variations like "LAP 15", "LAP15", etc.
    pattern = r'LAP\s+(\d+)'
    match = re.search(pattern, message, re.IGNORECASE)
    if match:
        try:
            return int(match.group(1))
        except ValueError:
            return None
    return None


def resolve_driver_id(conn, openf1_session_key: Optional[str], driver_number: Optional[int], message: Optional[str]) -> Optional[str]:
    """
    Resolve driver_id using driver_number + openf1_session_key lookup.
    
    Primary method: Use driver_number + openf1_session_key from driver_id_by_session view.
    Fallback: Parse "CAR {n}" from message, extract driver_number, then lookup.
    
    Returns:
        driver_id as string, or None if not found
    """
    if not openf1_session_key:
        return None
    
    # Primary method: use driver_number if available
    if driver_number is not None:
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT driver_id
                    FROM silver.driver_id_by_session
                    WHERE openf1_session_key = %s
                      AND driver_number = %s
                    LIMIT 1
                """, (openf1_session_key, driver_number))
                row = cur.fetchone()
                if row:
                    return row[0]
        except psycopg.Error as e:
            logger.warning(f"Failed to resolve driver_id for session {openf1_session_key}, driver {driver_number}: {e}")
    
    # Fallback: parse "CAR {n}" from message
    extracted_driver_number = extract_car_number_from_message(message)
    if extracted_driver_number is not None:
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT driver_id
                    FROM silver.driver_id_by_session
                    WHERE openf1_session_key = %s
                      AND driver_number = %s
                    LIMIT 1
                """, (openf1_session_key, extracted_driver_number))
                row = cur.fetchone()
                if row:
                    logger.debug(f"Resolved driver_id from message 'CAR {extracted_driver_number}' for session {openf1_session_key}")
                    return row[0]
        except psycopg.Error as e:
            logger.warning(f"Failed to resolve driver_id from message for session {openf1_session_key}: {e}")
    
    return None


def resolve_referenced_lap_id(conn, session_id: Optional[str], driver_id: Optional[str], referenced_lap_number: Optional[int]) -> Optional[int]:
    """
    Resolve referenced_lap_id by joining laps on (session_id, driver_id, lap_number).
    
    Returns:
        lap_id as BIGINT, or None if not found
    """
    if not session_id or not driver_id or referenced_lap_number is None:
        return None
    
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT lap_id
                FROM silver.laps
                WHERE session_id = %s
                  AND driver_id = %s
                  AND lap_number = %s
                LIMIT 1
            """, (session_id, driver_id, referenced_lap_number))
            row = cur.fetchone()
            if row:
                return row[0]  # Return BIGINT directly
    except psycopg.Error as e:
        logger.debug(f"Failed to resolve referenced_lap_id for session {session_id}, driver {driver_id}, lap {referenced_lap_number}: {e}")
    
    return None


def get_race_control_from_bronze(conn) -> List[Dict]:
    """
    Get race control records from bronze.race_control_raw with resolved session_id.
    """
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT DISTINCT
                    rcr.openf1_session_key,
                    rcr.category,
                    rcr.date,
                    rcr.driver_number,
                    rcr.flag,
                    rcr.lap_number,
                    rcr.message,
                    rcr.scope,
                    s.session_id
                FROM bronze.race_control_raw rcr
                INNER JOIN silver.sessions s 
                    ON rcr.openf1_session_key = s.openf1_session_key
                WHERE rcr.openf1_session_key IS NOT NULL
                  AND rcr.category IS NOT NULL
                  AND rcr.date IS NOT NULL
                ORDER BY rcr.date
            """)
            
            records = []
            for row in cur.fetchall():
                records.append({
                    'openf1_session_key': row[0],
                    'category': row[1],
                    'date': row[2],
                    'driver_number': row[3],
                    'flag': row[4],
                    'lap_number': row[5],
                    'message': row[6],
                    'scope': row[7],
                    'session_id': row[8]
                })
            
            logger.info(f"Found {len(records)} race control records in bronze.race_control_raw with resolved session_id")
            return records
    except psycopg.Error as e:
        logger.error(f"Failed to fetch race control from bronze: {e}")
        raise


def check_existing_record(conn, session_id: str, date: datetime, flag: Optional[str], lap_number: Optional[int], message: Optional[str], scope: Optional[str]) -> Optional[int]:
    """
    Check if a record with matching deduplication key already exists.
    
    Returns:
        message_id if found, None otherwise
    """
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT message_id
                FROM silver.race_control
                WHERE session_id = %s
                  AND date = %s
                  AND (flag IS NULL AND %s IS NULL OR flag = %s)
                  AND (lap_number IS NULL AND %s IS NULL OR lap_number = %s)
                  AND (message IS NULL AND %s IS NULL OR message = %s)
                  AND (scope IS NULL AND %s IS NULL OR scope = %s)
                LIMIT 1
            """, (session_id, date, flag, flag, lap_number, lap_number, message, message, scope, scope))
            row = cur.fetchone()
            if row:
                return row[0]
    except psycopg.Error as e:
        logger.warning(f"Failed to check existing record: {e}")
    
    return None


def upsert_race_control(conn, records: List[Dict]) -> int:
    """
    Upsert race control records into silver.race_control table.
    """
    if not records:
        logger.warning("No race control records to upsert")
        return 0
    
    insert_sql = """
        INSERT INTO silver.race_control (
            session_id,
            category,
            date,
            driver_id,
            flag,
            lap_number,
            message,
            scope,
            referenced_lap,
            referenced_lap_id
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
    """
    
    update_sql = """
        UPDATE silver.race_control
        SET
            category = %s,
            driver_id = %s,
            flag = %s,
            message = %s,
            scope = %s,
            referenced_lap = %s,
            referenced_lap_id = %s
        WHERE message_id = %s
    """
    
    inserted_count = 0
    updated_count = 0
    skipped_count = 0
    batch_size = 1000

    try:
        with conn.cursor() as cur:
            # Pre-fetch existing records for deduplication
            logger.info("Checking for existing records...")
            existing_records = {}
            cur.execute("""
                SELECT session_id, date, flag, lap_number, message, scope, message_id
                FROM silver.race_control
            """)
            for row in cur.fetchall():
                key = (row[0], row[1], row[2], row[3], row[4], row[5])
                existing_records[key] = row[6]
            
            logger.info(f"Found {len(existing_records)} existing race control records")
            
            inserts_data = []
            updates_data = []
            
            for record in records:
                # Parse data types
                date_parsed = parse_timestamp(record['date'])
                if not date_parsed:
                    logger.warning(f"Skipping record due to invalid date: {record.get('date')}")
                    skipped_count += 1
                    continue
                
                lap_number_parsed = parse_int(record['lap_number'])
                driver_number_parsed = parse_int(record['driver_number'])
                
                # Resolve driver_id
                driver_id = resolve_driver_id(
                    conn,
                    record['openf1_session_key'],
                    driver_number_parsed,
                    record['message']
                )
                
                # Derive referenced_lap_number from message
                referenced_lap_number = extract_lap_number_from_message(record['message'])
                
                # Resolve referenced_lap_id
                referenced_lap_id = None
                if driver_id and referenced_lap_number is not None:
                    referenced_lap_id = resolve_referenced_lap_id(
                        conn,
                        record['session_id'],
                        driver_id,
                        referenced_lap_number
                    )
                
                # Check for existing record (deduplication)
                dedup_key = (
                    record['session_id'],
                    date_parsed,
                    record['flag'],
                    lap_number_parsed,
                    record['message'],
                    record['scope']
                )
                
                existing_message_id = existing_records.get(dedup_key)
                
                if existing_message_id:
                    # Update existing record
                    updates_data.append((
                        record['category'],
                        driver_id,
                        record['flag'],
                        record['message'],
                        record['scope'],
                        referenced_lap_number,
                        referenced_lap_id,
                        existing_message_id
                    ))
                else:
                    # Insert new record
                    inserts_data.append((
                        record['session_id'],
                        record['category'],
                        date_parsed,
                        driver_id,
                        record['flag'],
                        lap_number_parsed,
                        record['message'],
                        record['scope'],
                        referenced_lap_number,
                        referenced_lap_id
                    ))
            
            logger.info(f"Will insert {len(inserts_data)} new records and update {len(updates_data)} existing records")
            
            # Perform batch inserts
            if inserts_data:
                logger.info("Inserting new race control records...")
                cur.executemany(insert_sql, inserts_data)
                inserted_count = len(inserts_data)
                logger.info(f"  Inserted {inserted_count} records")
            
            # Perform batch updates
            if updates_data:
                logger.info("Updating existing race control records...")
                for update_data in updates_data:
                    cur.execute(update_sql, update_data)
                updated_count = len(updates_data)
                logger.info(f"  Updated {updated_count} records")
            
            conn.commit()
            logger.info(f"Successfully upserted {inserted_count + updated_count} race control records into silver.race_control")
            if skipped_count > 0:
                logger.warning(f"Skipped {skipped_count} records due to validation issues")
            return inserted_count + updated_count
                    
    except psycopg.Error as e:
        conn.rollback()
        logger.error(f"Database upsert failed: {e}")
        raise


def main():
    """Main upsert function."""
    logger.info("Starting race control upsert from bronze.race_control_raw to silver.race_control")
    
    conn = get_db_connection()
    
    try:
        # Get race control records from bronze with resolved session_id
        logger.info("Fetching race control records from bronze.race_control_raw with resolved session_id...")
        records = get_race_control_from_bronze(conn)
        
        if not records:
            logger.warning("No race control records found in bronze.race_control_raw")
            return
        
        # Upsert race control
        logger.info("Upserting race control records into silver.race_control...")
        upserted = upsert_race_control(conn, records)
        
        logger.info("="*60)
        logger.info("RACE CONTROL UPSERT COMPLETE")
        logger.info("="*60)
        logger.info(f"Upserted: {upserted} records")
        
        # Show summary
        logger.info("\nSummary:")
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) as total_records,
                       COUNT(DISTINCT session_id) as unique_sessions,
                       COUNT(DISTINCT driver_id) as unique_drivers,
                       COUNT(CASE WHEN referenced_lap IS NOT NULL THEN 1 END) as with_referenced_lap,
                       COUNT(CASE WHEN referenced_lap_id IS NOT NULL THEN 1 END) as with_referenced_lap_id
                FROM silver.race_control
            """)
            total, sessions, drivers, with_ref_lap, with_ref_lap_id = cur.fetchone()
            logger.info(f"  Total records in silver.race_control: {total}")
            logger.info(f"  Unique sessions: {sessions}")
            logger.info(f"  Unique drivers: {drivers}")
            logger.info(f"  Records with referenced_lap: {with_ref_lap}")
            logger.info(f"  Records with referenced_lap_id: {with_ref_lap_id}")

        logger.info("\nSample Records:")
        with conn.cursor() as cur:
            cur.execute("""
                SELECT message_id, session_id, category, date, driver_id, flag, message, referenced_lap
                FROM silver.race_control
                ORDER BY date DESC
                LIMIT 5
            """)
            for row in cur.fetchall():
                logger.info(f"  {row[0]} | {row[1]} | {row[2]} | {row[3]} | {row[4]} | {row[5]} | {row[6][:50] if row[6] else None} | {row[7]}")
    
    finally:
        conn.close()


if __name__ == "__main__":
    main()

