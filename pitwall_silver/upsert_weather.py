#!/usr/bin/env python3
"""
Upsert weather data from bronze.weather_raw into silver.weather.

Resolves session_id by joining weather_raw.openf1_session_key to sessions.openf1_session_key.

Maps from bronze.weather_raw with conversions:
- date → date (text to timestamptz)
- air_temp_c → air_temp_c (text to numeric(6,3))
- track_temp_c → track_temp_c (text to numeric(6,3))
- humidity → humidity (text to int)
- rainfall → rainfall (text to int)
- pressure → pressure_mbar (text to numeric(6,3))
- wind_direction → wind_direction (text to int)
- wind_speed_mps → wind_speed_mps (text to numeric(6,3))
"""

import os
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


def parse_numeric(value: Optional[str]) -> Optional[float]:
    """Parse string to float for numeric fields, return None if invalid."""
    if value is None or value.strip() == '':
        return None
    try:
        return float(value)
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


def generate_weather_id(session_id: str, date: datetime) -> str:
    """
    Generate weather_id in format: weather:{session_id}-{date_iso}
    """
    # Format date as ISO string without microseconds and timezone
    date_str = date.strftime('%Y%m%dT%H%M%S')
    return f"weather:{session_id}-{date_str}"


def get_weather_from_bronze(conn) -> List[Dict]:
    """
    Get weather records from bronze.weather_raw with resolved session_id.
    """
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT DISTINCT
                    wr.openf1_session_key,
                    wr.date,
                    wr.air_temp_c,
                    wr.track_temp_c,
                    wr.humidity,
                    wr.rainfall,
                    wr.pressure,
                    wr.wind_direction,
                    wr.wind_speed_mps,
                    s.session_id
                FROM bronze.weather_raw wr
                INNER JOIN silver.sessions s 
                    ON wr.openf1_session_key = s.openf1_session_key
                WHERE wr.openf1_session_key IS NOT NULL
                  AND wr.date IS NOT NULL
                ORDER BY wr.date
            """)
            
            records = []
            for row in cur.fetchall():
                records.append({
                    'openf1_session_key': row[0],
                    'date': row[1],
                    'air_temp_c': row[2],
                    'track_temp_c': row[3],
                    'humidity': row[4],
                    'rainfall': row[5],
                    'pressure': row[6],
                    'wind_direction': row[7],
                    'wind_speed_mps': row[8],
                    'session_id': row[9]
                })
            
            logger.info(f"Found {len(records)} weather records in bronze.weather_raw with resolved session_id")
            return records
    except psycopg.Error as e:
        logger.error(f"Failed to fetch weather from bronze: {e}")
        raise


def upsert_weather(conn, records: List[Dict]) -> int:
    """
    Upsert weather records into silver.weather table with deduplication.
    """
    if not records:
        logger.warning("No weather records to upsert")
        return 0
    
    insert_sql = """
        INSERT INTO silver.weather (
            weather_id,
            session_id,
            date,
            air_temp_c,
            track_temp_c,
            humidity,
            rainfall,
            pressure_mbar,
            wind_direction,
            wind_speed_mps
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        ON CONFLICT (weather_id) DO UPDATE SET
            air_temp_c = EXCLUDED.air_temp_c,
            track_temp_c = EXCLUDED.track_temp_c,
            humidity = EXCLUDED.humidity,
            rainfall = EXCLUDED.rainfall,
            pressure_mbar = EXCLUDED.pressure_mbar,
            wind_direction = EXCLUDED.wind_direction,
            wind_speed_mps = EXCLUDED.wind_speed_mps
    """
    
    inserted_count = 0
    updated_count = 0
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
                
                # Generate weather_id
                weather_id = generate_weather_id(record['session_id'], date_parsed)
                
                # Parse numeric and int fields
                air_temp_c = parse_numeric(record['air_temp_c'])
                track_temp_c = parse_numeric(record['track_temp_c'])
                humidity = parse_int(record['humidity'])
                rainfall = parse_int(record['rainfall'])
                pressure_mbar = parse_numeric(record['pressure'])  # Map from 'pressure' to 'pressure_mbar'
                wind_direction = parse_int(record['wind_direction'])
                wind_speed_mps = parse_numeric(record['wind_speed_mps'])
                
                # Insert/update record
                inserts_data.append((
                    weather_id,
                    record['session_id'],
                    date_parsed,
                    air_temp_c,
                    track_temp_c,
                    humidity,
                    rainfall,
                    pressure_mbar,
                    wind_direction,
                    wind_speed_mps
                ))
            
            logger.info(f"Will upsert {len(inserts_data)} records")
            
            # Perform batch inserts/updates
            if inserts_data:
                logger.info("Upserting weather records...")
                for i in range(0, len(inserts_data), batch_size):
                    batch = inserts_data[i:i + batch_size]
                    cur.executemany(insert_sql, batch)
                    # Count rows affected (inserts + updates)
                    affected = cur.rowcount
                    # We can't distinguish inserts from updates with ON CONFLICT, so we'll estimate
                    # For now, just track total affected
                    inserted_count += affected
                conn.commit()
                logger.info(f"  Upserted {inserted_count} records")
            
            if skipped_count > 0:
                logger.warning(f"Skipped {skipped_count} records due to validation issues")
            return inserted_count
                    
    except psycopg.Error as e:
        conn.rollback()
        logger.error(f"Database upsert failed: {e}")
        raise


def main():
    """Main upsert function."""
    logger.info("Starting weather upsert from bronze.weather_raw to silver.weather")
    
    conn = get_db_connection()
    
    try:
        # Get weather records from bronze with resolved session_id
        logger.info("Fetching weather records from bronze.weather_raw with resolved session_id...")
        records = get_weather_from_bronze(conn)
        
        if not records:
            logger.warning("No weather records found in bronze.weather_raw")
            return
        
        # Upsert weather
        logger.info("Upserting weather records into silver.weather...")
        upserted = upsert_weather(conn, records)
        
        logger.info("="*60)
        logger.info("WEATHER UPSERT COMPLETE")
        logger.info("="*60)
        logger.info(f"Upserted: {upserted} records")
        
        # Show summary
        logger.info("\nSummary:")
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) as total_records,
                       COUNT(DISTINCT session_id) as unique_sessions,
                       COUNT(CASE WHEN air_temp_c IS NOT NULL THEN 1 END) as with_air_temp,
                       COUNT(CASE WHEN track_temp_c IS NOT NULL THEN 1 END) as with_track_temp,
                       COUNT(CASE WHEN rainfall > 0 THEN 1 END) as with_rainfall
                FROM silver.weather
            """)
            total, sessions, with_air_temp, with_track_temp, with_rainfall = cur.fetchone()
            logger.info(f"  Total records in silver.weather: {total}")
            logger.info(f"  Unique sessions: {sessions}")
            logger.info(f"  Records with air_temp_c: {with_air_temp}")
            logger.info(f"  Records with track_temp_c: {with_track_temp}")
            logger.info(f"  Records with rainfall > 0: {with_rainfall}")

        logger.info("\nSample Records:")
        with conn.cursor() as cur:
            cur.execute("""
                SELECT weather_id, session_id, date, air_temp_c, track_temp_c, rainfall
                FROM silver.weather
                ORDER BY date DESC
                LIMIT 5
            """)
            for row in cur.fetchall():
                logger.info(f"  {row[0]} | {row[1]} | {row[2]} | Air: {row[3]}°C | Track: {row[4]}°C | Rain: {row[5]}")
    
    finally:
        conn.close()


if __name__ == "__main__":
    main()


