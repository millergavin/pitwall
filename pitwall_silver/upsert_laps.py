#!/usr/bin/env python3
"""
Upsert laps data from bronze.laps_raw into silver.laps.

Resolves session_id by joining laps_raw.openf1_session_key to sessions.openf1_session_key.
Resolves driver_id by joining on openf1_session_key and driver_number (through sessions -> meetings -> driver_numbers_by_season).

Maps from bronze.laps_raw with conversions:
- lap_number → lap_number (text to int)
- date_start → date_start (text to timestamptz)
- lap_duration_s → lap_duration_ms (convert seconds to milliseconds)
- duration_s1_s → duration_s1_ms (convert seconds to milliseconds)
- duration_s2_s → duration_s2_ms (convert seconds to milliseconds)
- duration_s3_s → duration_s3_ms (convert seconds to milliseconds)
- i1_speed_kph → i1_speed_kph (text to numeric)
- i2_speed_kph → i2_speed_kph (text to numeric)
- st_speed_kph → st_speed_kph (text to numeric)
- is_pit_out_lap → is_pit_out_lap (text to boolean)
- s1_segments → s1_segments (text to jsonb)
- s2_segments → s2_segments (text to jsonb)
- s3_segments → s3_segments (text to jsonb)

Note: is_pit_in_lap and is_valid are derived later (after pit_stops upsert) and not included here.
"""

import os
import json
import logging
from typing import Dict, List, Optional
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
    except psycopg.Error as e:
        logger.error(f"Database connection failed: {e}")
        raise


def parse_timestamp(date_str: Optional[str]) -> Optional[datetime]:
    """
    Parse timestamp from TEXT to TIMESTAMPTZ.
    
    Args:
        date_str: Date string from bronze table
        
    Returns:
        Parsed datetime or None if invalid
    """
    if not date_str:
        return None
    
    try:
        # Try ISO format first (most common)
        return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
    except (ValueError, AttributeError):
        try:
            # Try other common formats
            for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%Y-%m-%dT%H:%M:%S']:
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue
        except Exception:
            pass
    
    logger.warning(f"Could not parse timestamp: {date_str}")
    return None


def parse_float(value: Optional[str]) -> Optional[float]:
    """Parse float value from string, returning None if invalid."""
    if not value or value.strip() == '':
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def parse_int(value: Optional[str]) -> Optional[int]:
    """Parse integer value from string, returning None if invalid."""
    if not value or value.strip() == '':
        return None
    try:
        return int(float(value))  # Convert float to int in case of "5.0" format
    except (ValueError, TypeError):
        return None


def parse_boolean(value: Optional[str]) -> Optional[bool]:
    """Parse boolean value from string."""
    if not value or value.strip() == '':
        return None
    
    value_lower = value.lower().strip()
    if value_lower in ('true', 't', '1', 'yes', 'y'):
        return True
    elif value_lower in ('false', 'f', '0', 'no', 'n'):
        return False
    
    return None


def parse_jsonb(value: Optional[str]) -> Optional[str]:
    """
    Parse PostgreSQL array format or JSON string to JSON string for JSONB storage.
    
    Handles PostgreSQL array format: {value1,value2,value3} or {NULL,value1,value2}
    Converts to JSON array format: ["value1","value2","value3"] or [null,"value1","value2"]
    """
    if not value or value.strip() == '':
        return None
    
    value = value.strip()
    
    # Check if it's PostgreSQL array format (starts with { and ends with })
    if value.startswith('{') and value.endswith('}'):
        try:
            # Remove outer braces
            inner = value[1:-1]
            if not inner:
                # Empty array
                return json.dumps([])
            
            # Simple split by comma (PostgreSQL arrays use comma as separator)
            # Handle NULL values (case-insensitive)
            parts = [p.strip() for p in inner.split(',')]
            
            # Convert parts to JSON array, handling NULL
            json_array = []
            for part in parts:
                if part.upper() == 'NULL' or part == '':
                    json_array.append(None)
                else:
                    # Try to parse as number, otherwise keep as string
                    try:
                        # Try integer first
                        json_array.append(int(part))
                    except ValueError:
                        try:
                            # Try float
                            json_array.append(float(part))
                        except ValueError:
                            # Keep as string
                            json_array.append(part)
            
            return json.dumps(json_array)
        except Exception as e:
            logger.debug(f"Could not parse PostgreSQL array format: {value[:50]}... Error: {e}")
            return None
    
    # Try to parse as JSON
    try:
        # Validate it's valid JSON first
        parsed = json.loads(value)
        return json.dumps(parsed)
    except (json.JSONDecodeError, TypeError):
        logger.debug(f"Could not parse as JSON: {value[:50]}...")
        return None


def convert_seconds_to_ms(seconds_str: Optional[str]) -> Optional[int]:
    """
    Convert seconds (as string) to milliseconds (as int).
    
    Args:
        seconds_str: Seconds as string
        
    Returns:
        Milliseconds as int or None if invalid
    """
    if not seconds_str or seconds_str.strip() == '':
        return None
    
    try:
        seconds = float(seconds_str)
        return int(seconds * 1000)
    except (ValueError, TypeError):
        return None


def get_laps_from_bronze(conn) -> List[Dict]:
    """
    Get lap records from bronze.laps_raw with resolved session_id and driver_id.
    
    Joins through sessions to get session_id and season, then through driver_numbers_by_season
    to get driver_id.
    
    Returns:
        List of lap dictionaries with resolved session_id and driver_id
    """
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT DISTINCT
                    lr.openf1_session_key,
                    lr.driver_number,
                    lr.lap_number,
                    lr.date_start,
                    lr.lap_duration_s,
                    lr.duration_s1_s,
                    lr.duration_s2_s,
                    lr.duration_s3_s,
                    lr.i1_speed_kph,
                    lr.i2_speed_kph,
                    lr.st_speed_kph,
                    lr.is_pit_out_lap,
                    lr.s1_segments,
                    lr.s2_segments,
                    lr.s3_segments,
                    s.session_id,
                    m.season,
                    dns.driver_id
                FROM bronze.laps_raw lr
                INNER JOIN silver.sessions s 
                    ON lr.openf1_session_key = s.openf1_session_key
                INNER JOIN silver.meetings m 
                    ON s.meeting_id = m.meeting_id
                INNER JOIN silver.driver_numbers_by_season dns 
                    ON CAST(lr.driver_number AS INT) = dns.driver_number
                    AND m.season = dns.season
                WHERE lr.openf1_session_key IS NOT NULL
                  AND lr.driver_number IS NOT NULL
                  AND lr.lap_number IS NOT NULL
                  AND lr.date_start IS NOT NULL
                ORDER BY lr.date_start
            """)
            
            laps = []
            for row in cur.fetchall():
                laps.append({
                    'openf1_session_key': row[0],
                    'driver_number': row[1],
                    'lap_number': row[2],
                    'date_start': row[3],
                    'lap_duration_s': row[4],
                    'duration_s1_s': row[5],
                    'duration_s2_s': row[6],
                    'duration_s3_s': row[7],
                    'i1_speed_kph': row[8],
                    'i2_speed_kph': row[9],
                    'st_speed_kph': row[10],
                    'is_pit_out_lap': row[11],
                    's1_segments': row[12],
                    's2_segments': row[13],
                    's3_segments': row[14],
                    'session_id': row[15],
                    'season': row[16],
                    'driver_id': row[17]
                })
            
            logger.info(f"Found {len(laps)} lap records in bronze.laps_raw with resolved session_id and driver_id")
            return laps
    except psycopg.Error as e:
        logger.error(f"Failed to fetch laps from bronze: {e}")
        raise


def upsert_laps(conn, laps: List[Dict]) -> int:
    """
    Upsert laps into silver.laps table.
    
    Args:
        conn: Database connection
        laps: List of lap records from bronze with resolved session_id and driver_id
        
    Returns:
        Number of records upserted
    """
    if not laps:
        logger.warning("No laps to upsert")
        return 0
    
    # Note: lap_id is auto-generated (bigserial), so we don't include it in the INSERT
    # Since there's no unique constraint on (session_id, driver_id, lap_number, date_start),
    # we'll check for existing records and update or insert accordingly
    check_sql = """
        SELECT lap_id 
        FROM silver.laps
        WHERE session_id = %s
          AND driver_id = %s
          AND lap_number = %s
          AND date_start = %s
        LIMIT 1
    """
    
    update_sql = """
        UPDATE silver.laps
        SET
            lap_duration_ms = %s,
            duration_s1_ms = %s,
            duration_s2_ms = %s,
            duration_s3_ms = %s,
            i1_speed_kph = %s,
            i2_speed_kph = %s,
            st_speed_kph = %s,
            is_pit_out_lap = %s,
            s1_segments = %s::jsonb,
            s2_segments = %s::jsonb,
            s3_segments = %s::jsonb
        WHERE lap_id = %s
    """
    
    insert_sql = """
        INSERT INTO silver.laps (
            session_id,
            driver_id,
            lap_number,
            date_start,
            lap_duration_ms,
            duration_s1_ms,
            duration_s2_ms,
            duration_s3_ms,
            i1_speed_kph,
            i2_speed_kph,
            st_speed_kph,
            is_pit_out_lap,
            s1_segments,
            s2_segments,
            s3_segments,
            is_pit_in_lap,
            is_valid
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb, FALSE, TRUE
        )
    """
    
    try:
        with conn.cursor() as cur:
            # Check if unique constraint exists, if not we'll need to handle duplicates differently
            upsert_records = []
            skipped = 0
            
            for lap in laps:
                # Validate required fields
                if not lap.get('session_id') or not lap.get('driver_id'):
                    logger.warning(f"Skipping lap due to missing session_id or driver_id")
                    skipped += 1
                    continue
                
                # Parse and convert values
                lap_number = parse_int(lap['lap_number'])
                if lap_number is None:
                    logger.warning(f"Skipping lap due to invalid lap_number: {lap.get('lap_number')}")
                    skipped += 1
                    continue
                
                date_start = parse_timestamp(lap['date_start'])
                if not date_start:
                    logger.warning(f"Skipping lap due to invalid date_start: {lap.get('date_start')}")
                    skipped += 1
                    continue
                
                # Convert durations from seconds to milliseconds
                lap_duration_ms = convert_seconds_to_ms(lap['lap_duration_s'])
                duration_s1_ms = convert_seconds_to_ms(lap['duration_s1_s'])
                duration_s2_ms = convert_seconds_to_ms(lap['duration_s2_s'])
                duration_s3_ms = convert_seconds_to_ms(lap['duration_s3_s'])
                
                # Parse speeds as numeric
                i1_speed_kph = parse_float(lap['i1_speed_kph'])
                i2_speed_kph = parse_float(lap['i2_speed_kph'])
                st_speed_kph = parse_float(lap['st_speed_kph'])
                
                # Parse boolean
                is_pit_out_lap = parse_boolean(lap['is_pit_out_lap'])
                
                # Parse JSON segments (returns JSON string already)
                s1_segments = parse_jsonb(lap['s1_segments'])
                s2_segments = parse_jsonb(lap['s2_segments'])
                s3_segments = parse_jsonb(lap['s3_segments'])
                
                upsert_records.append({
                    'session_id': lap['session_id'],
                    'driver_id': lap['driver_id'],
                    'lap_number': lap_number,
                    'date_start': date_start,
                    'lap_duration_ms': lap_duration_ms,
                    'duration_s1_ms': duration_s1_ms,
                    'duration_s2_ms': duration_s2_ms,
                    'duration_s3_ms': duration_s3_ms,
                    'i1_speed_kph': i1_speed_kph,
                    'i2_speed_kph': i2_speed_kph,
                    'st_speed_kph': st_speed_kph,
                    'is_pit_out_lap': is_pit_out_lap,
                    's1_segments': s1_segments,  # Already JSON string
                    's2_segments': s2_segments,  # Already JSON string
                    's3_segments': s3_segments,  # Already JSON string
                })
            
            if not upsert_records:
                logger.warning("No valid laps to upsert after validation")
                return 0
            
            # Use a more efficient approach: batch check existing, then batch insert/update
            # First, get all existing lap_ids in a single query using VALUES
            logger.info("Checking for existing laps...")
            existing_laps = {}
            batch_size = 10000
            
            for i in range(0, len(upsert_records), batch_size):
                batch = upsert_records[i:i + batch_size]
                # Build a VALUES clause for batch checking
                values_list = []
                params = []
                
                for record in batch:
                    values_list.append("(%s, %s, %s, %s)")
                    params.extend([
                        record['session_id'],
                        record['driver_id'],
                        record['lap_number'],
                        record['date_start']
                    ])
                
                if values_list:
                    batch_check_sql = f"""
                        SELECT l.session_id, l.driver_id, l.lap_number, l.date_start, l.lap_id
                        FROM silver.laps l
                        INNER JOIN (VALUES {','.join(values_list)}) AS v(session_id, driver_id, lap_number, date_start)
                            ON l.session_id = v.session_id
                            AND l.driver_id = v.driver_id
                            AND l.lap_number = v.lap_number
                            AND l.date_start = v.date_start
                    """
                    cur.execute(batch_check_sql, params)
                    for row in cur.fetchall():
                        key = (row[0], row[1], row[2], row[3])
                        existing_laps[key] = row[4]  # lap_id
            
            logger.info(f"Found {len(existing_laps)} existing laps out of {len(upsert_records)} total")
            
            # Separate records into inserts and updates
            records_to_insert = []
            records_to_update = []
            
            for record in upsert_records:
                key = (
                    record['session_id'],
                    record['driver_id'],
                    record['lap_number'],
                    record['date_start']
                )
                if key in existing_laps:
                    record['lap_id'] = existing_laps[key]
                    records_to_update.append(record)
                else:
                    records_to_insert.append(record)
            
            logger.info(f"Will insert {len(records_to_insert)} new laps and update {len(records_to_update)} existing laps")
            
            # Batch insert new records
            upserted_count = 0
            if records_to_insert:
                logger.info("Inserting new laps...")
                for i in range(0, len(records_to_insert), batch_size):
                    batch = records_to_insert[i:i + batch_size]
                    batch_params = []
                    for record in batch:
                        batch_params.append((
                            record['session_id'],
                            record['driver_id'],
                            record['lap_number'],
                            record['date_start'],
                            record['lap_duration_ms'],
                            record['duration_s1_ms'],
                            record['duration_s2_ms'],
                            record['duration_s3_ms'],
                            record['i1_speed_kph'],
                            record['i2_speed_kph'],
                            record['st_speed_kph'],
                            record['is_pit_out_lap'],
                            record['s1_segments'],
                            record['s2_segments'],
                            record['s3_segments']
                        ))
                    
                    try:
                        cur.executemany(insert_sql, batch_params)
                        upserted_count += len(batch)
                        conn.commit()
                        if (i + batch_size) % 50000 == 0:
                            logger.info(f"  Inserted {upserted_count} laps so far...")
                    except psycopg.Error as e:
                        logger.warning(f"Failed to insert batch: {e}")
                        conn.rollback()
            
            # Batch update existing records
            if records_to_update:
                logger.info("Updating existing laps...")
                for i in range(0, len(records_to_update), batch_size):
                    batch = records_to_update[i:i + batch_size]
                    batch_params = []
                    for record in batch:
                        batch_params.append((
                            record['lap_duration_ms'],
                            record['duration_s1_ms'],
                            record['duration_s2_ms'],
                            record['duration_s3_ms'],
                            record['i1_speed_kph'],
                            record['i2_speed_kph'],
                            record['st_speed_kph'],
                            record['is_pit_out_lap'],
                            record['s1_segments'],
                            record['s2_segments'],
                            record['s3_segments'],
                            record['lap_id']
                        ))
                    
                    try:
                        cur.executemany(update_sql, batch_params)
                        upserted_count += len(batch)
                        conn.commit()
                        if (i + batch_size) % 50000 == 0:
                            logger.info(f"  Updated {len(records_to_update) - (len(records_to_update) - i - len(batch))} laps so far...")
                    except psycopg.Error as e:
                        logger.warning(f"Failed to update batch: {e}")
                        conn.rollback()
            logger.info(f"Successfully upserted {upserted_count} laps into silver.laps")
            if skipped > 0:
                logger.warning(f"Skipped {skipped} laps due to validation issues")
            return upserted_count
            
    except psycopg.Error as e:
        conn.rollback()
        logger.error(f"Database upsert failed: {e}")
        raise


def main():
    """Main upsert function."""
    logger.info("Starting laps upsert from bronze.laps_raw to silver.laps")
    
    conn = get_db_connection()
    
    try:
        # Get laps from bronze with resolved session_id and driver_id
        logger.info("Fetching laps from bronze.laps_raw with resolved session_id and driver_id...")
        laps = get_laps_from_bronze(conn)
        
        if not laps:
            logger.warning("No laps found in bronze.laps_raw")
            return
        
        # Upsert laps
        logger.info("Upserting laps into silver.laps...")
        upserted = upsert_laps(conn, laps)
        
        logger.info("="*60)
        logger.info("LAPS UPSERT COMPLETE")
        logger.info("="*60)
        logger.info(f"Upserted: {upserted} laps")
        
        # Show summary
        logger.info("\nSummary:")
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) as total_laps
                FROM silver.laps
            """)
            total = cur.fetchone()[0]
            logger.info(f"  Total laps in silver.laps: {total}")
    
    finally:
        conn.close()


if __name__ == "__main__":
    main()

