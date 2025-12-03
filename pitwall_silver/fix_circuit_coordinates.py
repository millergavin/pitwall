#!/usr/bin/env python3
"""
Fix circuit coordinates from CSV export and update timezones.

Reads lat/lon from CSV file and updates silver.circuits, then looks up
timezone using the corrected coordinates.
"""

import os
import csv
import logging
from typing import Dict, Optional

import psycopg
from timezonefinder import TimezoneFinder
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

tf = TimezoneFinder()


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


def read_circuits_csv(csv_path: str) -> Dict[str, Dict]:
    """
    Read circuits from CSV file.
    
    Args:
        csv_path: Path to CSV file
        
    Returns:
        Dictionary mapping openf1_circuit_key -> circuit data
    """
    circuits = {}
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                circuit_key = row.get('openf1_circuit_key')
                if circuit_key:
                    circuits[circuit_key] = {
                        'circuit_id': row.get('circuit_id'),
                        'circuit_short_name': row.get('circuit_short_name'),
                        'lat': row.get('lat'),
                        'lon': row.get('lon'),
                        'openf1_circuit_key': circuit_key
                    }
        
        logger.info(f"Read {len(circuits)} circuits from CSV")
        return circuits
    except Exception as e:
        logger.error(f"Failed to read CSV file: {e}")
        raise


def get_timezone_from_coords(lat: float, lon: float) -> Optional[str]:
    """
    Get IANA timezone ID from latitude and longitude using timezonefinder.
    
    Args:
        lat: Latitude
        lon: Longitude
        
    Returns:
        IANA timezone ID (e.g., "Australia/Melbourne") or None if not found
    """
    try:
        tzid = tf.timezone_at(lat=lat, lng=lon)
        if tzid:
            logger.debug(f"Timezone for ({lat}, {lon}): {tzid}")
            return tzid
        else:
            logger.warning(f"No timezone found for coordinates ({lat}, {lon})")
            return None
    except Exception as e:
        logger.error(f"Failed to get timezone for ({lat}, {lon}): {e}")
        return None


def update_circuit_coordinates(conn, circuit_key: str, lat: float, lon: float, timezone_tzid: Optional[str]) -> bool:
    """
    Update circuit with lat, lon, and timezone_tzid.
    
    Args:
        conn: Database connection
        circuit_key: OpenF1 circuit key
        lat: Latitude
        lon: Longitude
        timezone_tzid: IANA timezone ID (can be None)
        
    Returns:
        True if update successful, False otherwise
    """
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE silver.circuits
                SET lat = %s,
                    lon = %s,
                    timezone_tzid = %s
                WHERE openf1_circuit_key = %s
            """, (lat, lon, timezone_tzid, circuit_key))
            conn.commit()
            return True
    except psycopg.Error as e:
        conn.rollback()
        logger.error(f"Failed to update circuit {circuit_key}: {e}")
        return False


def get_circuit_info(conn, circuit_key: str) -> Optional[Dict]:
    """Get circuit info from database."""
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT circuit_id, circuit_short_name, country_code, location
                FROM silver.circuits
                WHERE openf1_circuit_key = %s
            """, (circuit_key,))
            row = cur.fetchone()
            if row:
                return {
                    'circuit_id': row[0],
                    'circuit_short_name': row[1],
                    'country_code': row[2],
                    'location': row[3]
                }
            return None
    except psycopg.Error as e:
        logger.error(f"Failed to fetch circuit info: {e}")
        return None


def main():
    """Main function."""
    csv_path = "/Users/gavinmiller/Programming/f1_dataviz/circuits_export.csv"
    
    logger.info("Starting circuit coordinate fix from CSV")
    logger.info(f"Reading CSV from: {csv_path}")
    
    # Read circuits from CSV
    csv_circuits = read_circuits_csv(csv_path)
    
    if not csv_circuits:
        logger.error("No circuits found in CSV file")
        return
    
    conn = get_db_connection()
    
    try:
        updated = 0
        failed = 0
        not_found = 0
        
        for circuit_key, csv_data in csv_circuits.items():
            logger.info(f"Processing circuit key: {circuit_key}")
            
            # Get circuit info from database
            db_circuit = get_circuit_info(conn, circuit_key)
            if not db_circuit:
                logger.warning(f"  ✗ Circuit with key {circuit_key} not found in database. Skipping.")
                not_found += 1
                continue
            
            circuit_name = db_circuit['circuit_short_name']
            logger.info(f"  Circuit: {circuit_name} ({db_circuit['circuit_id']})")
            
            # Get lat/lon from CSV
            lat_str = csv_data.get('lat')
            lon_str = csv_data.get('lon')
            
            if not lat_str or not lon_str:
                logger.warning(f"  ✗ Missing lat/lon in CSV for {circuit_name}. Skipping.")
                failed += 1
                continue
            
            try:
                lat = float(lat_str)
                lon = float(lon_str)
            except ValueError as e:
                logger.error(f"  ✗ Invalid lat/lon values in CSV for {circuit_name}: {lat_str}, {lon_str}")
                failed += 1
                continue
            
            logger.info(f"  CSV coordinates: lat={lat:.6f}, lon={lon:.6f}")
            
            # Get timezone from coordinates
            logger.info(f"  Looking up timezone for coordinates ({lat:.6f}, {lon:.6f})...")
            timezone_tzid = get_timezone_from_coords(lat, lon)
            
            if not timezone_tzid:
                logger.warning(f"  ⚠ Could not determine timezone for {circuit_name}. Updating lat/lon only.")
                if update_circuit_coordinates(conn, circuit_key, lat, lon, None):
                    updated += 1
                    logger.info(f"  ✓ Updated {circuit_name} with lat/lon (timezone missing)")
                else:
                    failed += 1
                continue
            
            logger.info(f"  Timezone: {timezone_tzid}")
            
            # Update circuit
            logger.info(f"  Updating circuit with lat={lat:.6f}, lon={lon:.6f}, tz={timezone_tzid}...")
            if update_circuit_coordinates(conn, circuit_key, lat, lon, timezone_tzid):
                updated += 1
                logger.info(f"  ✓ Successfully updated {circuit_name}")
            else:
                logger.error(f"  ✗ Failed to update {circuit_name} in database")
                failed += 1
            
            logger.info("")  # Blank line for readability
        
        logger.info("="*60)
        logger.info("COORDINATE FIX COMPLETE")
        logger.info("="*60)
        logger.info(f"Updated: {updated}/{len(csv_circuits)}")
        if not_found > 0:
            logger.warning(f"Not found in database: {not_found}")
        if failed > 0:
            logger.warning(f"Failed: {failed}")
    
    finally:
        conn.close()


if __name__ == "__main__":
    main()


