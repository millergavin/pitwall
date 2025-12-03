#!/usr/bin/env python3
"""
Enrich silver.circuits with lat/lon coordinates and timezone information.

Process:
1. Get circuits that need enrichment (where lat, lon, or timezone_tzid are NULL)
2. For each circuit:
   - Look up alpha2 country code from silver.countries using country_code
   - Geocode using Mapbox API: {location} + {alpha2}
   - Use timezonefinder to get IANA timezone ID from lat/lon
   - Update circuit with lat, lon, and timezone_tzid
"""

import os
import time
import logging
from typing import Dict, List, Optional, Tuple

import psycopg
import requests
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

# Configuration
MAPBOX_ACCESS_TOKEN = os.getenv('MAPBOX_ACCESS_TOKEN')
MAPBOX_GEOCODING_URL = "https://api.mapbox.com/geocoding/v5/mapbox.places"
GEOCODE_RATE_LIMIT_DELAY = 0.1  # seconds between geocode requests
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


def get_circuits_needing_enrichment(conn) -> List[Dict]:
    """
    Get circuits that need lat/lon/timezone enrichment.
    
    Returns:
        List of circuit dictionaries
    """
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    circuit_id,
                    openf1_circuit_key,
                    circuit_short_name,
                    country_code,
                    location
                FROM silver.circuits
                WHERE lat IS NULL 
                   OR lon IS NULL 
                   OR timezone_tzid IS NULL
                ORDER BY circuit_short_name
            """)
            
            circuits = []
            for row in cur.fetchall():
                circuits.append({
                    'circuit_id': row[0],
                    'openf1_circuit_key': row[1],
                    'circuit_short_name': row[2],
                    'country_code': row[3],
                    'location': row[4]
                })
            
            logger.info(f"Found {len(circuits)} circuits needing enrichment")
            return circuits
    except psycopg.Error as e:
        logger.error(f"Failed to fetch circuits: {e}")
        raise


def get_alpha2_from_country_code(conn, country_code: str) -> Optional[str]:
    """
    Get alpha2 country code from silver.countries using country_code.
    
    Args:
        conn: Database connection
        country_code: Alpha3 country code
        
    Returns:
        Alpha2 country code or None if not found
    """
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT alpha2 
                FROM silver.countries 
                WHERE country_code = %s
            """, (country_code,))
            row = cur.fetchone()
            if row:
                return row[0]
            return None
    except psycopg.Error as e:
        logger.error(f"Failed to fetch alpha2 for {country_code}: {e}")
        return None


def geocode_location(location: str, alpha2: Optional[str]) -> Optional[Tuple[float, float]]:
    """
    Geocode a location using Mapbox API.
    
    Args:
        location: Location name (e.g., "Melbourne")
        alpha2: Alpha2 country code (e.g., "AU")
        
    Returns:
        Tuple of (latitude, longitude) or None if geocoding fails
    """
    if not MAPBOX_ACCESS_TOKEN:
        logger.error("MAPBOX_ACCESS_TOKEN not set in environment variables")
        return None
    
    # Build query: location + country
    query = location
    if alpha2:
        query = f"{location}, {alpha2}"
    
    try:
        time.sleep(GEOCODE_RATE_LIMIT_DELAY)
        
        url = f"{MAPBOX_GEOCODING_URL}/{query}.json"
        params = {
            'access_token': MAPBOX_ACCESS_TOKEN,
            'limit': 1
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get('features') and len(data['features']) > 0:
            coordinates = data['features'][0]['geometry']['coordinates']
            lon, lat = coordinates[0], coordinates[1]
            logger.info(f"  ✓ Geocoded '{query}' → ({lat:.6f}, {lon:.6f})")
            return (lat, lon)
        else:
            logger.warning(f"  ✗ No results found for geocoding query: '{query}'")
            return None
            
    except requests.exceptions.HTTPError as e:
        logger.error(f"  ✗ HTTP error geocoding '{query}': {e}")
        if hasattr(e.response, 'text'):
            logger.error(f"    Response: {e.response.text[:200]}")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"  ✗ Request error geocoding '{query}': {e}")
        return None
    except Exception as e:
        logger.error(f"  ✗ Unexpected error geocoding '{query}': {e}")
        return None


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


def update_circuit_enrichment(conn, circuit_id: str, lat: float, lon: float, timezone_tzid: Optional[str]) -> bool:
    """
    Update circuit with lat, lon, and timezone_tzid.
    
    Args:
        conn: Database connection
        circuit_id: Circuit ID
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
                WHERE circuit_id = %s
            """, (lat, lon, timezone_tzid, circuit_id))
            conn.commit()
            return True
    except psycopg.Error as e:
        conn.rollback()
        logger.error(f"Failed to update circuit {circuit_id}: {e}")
        return False


def main():
    """Main enrichment function."""
    logger.info("Starting circuit enrichment (lat/lon/timezone)")
    
    if not MAPBOX_ACCESS_TOKEN:
        logger.error("MAPBOX_ACCESS_TOKEN environment variable is required")
        logger.error("Please set it in your .env file or environment")
        return
    
    conn = get_db_connection()
    
    try:
        # Get circuits needing enrichment
        circuits = get_circuits_needing_enrichment(conn)
        
        if not circuits:
            logger.info("No circuits need enrichment")
            return
        
        updated = 0
        failed = 0
        
        for idx, circuit in enumerate(circuits, 1):
            circuit_id = circuit['circuit_id']
            circuit_name = circuit['circuit_short_name']
            location = circuit['location']
            country_code = circuit['country_code']
            
            logger.info(f"Processing {idx}/{len(circuits)}: {circuit_name} ({circuit_id})")
            logger.info(f"  Location: {location}, Country: {country_code}")
            
            # Get alpha2 country code
            alpha2 = None
            if country_code:
                alpha2 = get_alpha2_from_country_code(conn, country_code)
                if alpha2:
                    logger.info(f"  Country code {country_code} → alpha2: {alpha2}")
                else:
                    logger.warning(f"  ⚠ Could not find alpha2 for country_code '{country_code}'. Proceeding without country code.")
            else:
                logger.warning(f"  ⚠ No country_code for circuit. Proceeding without country code.")
            
            # Geocode location
            if not location:
                logger.warning(f"  ✗ No location for circuit {circuit_id}. Skipping.")
                failed += 1
                continue
            
            logger.info(f"  Geocoding: '{location}'" + (f" in {alpha2}" if alpha2 else ""))
            coords = geocode_location(location, alpha2)
            if not coords:
                logger.warning(f"  ✗ Geocoding failed for {circuit_name}. Skipping.")
                failed += 1
                continue
            
            lat, lon = coords
            
            # Get timezone
            logger.info(f"  Looking up timezone for coordinates ({lat:.6f}, {lon:.6f})...")
            timezone_tzid = get_timezone_from_coords(lat, lon)
            if not timezone_tzid:
                logger.warning(f"  ⚠ Could not determine timezone for {circuit_name}. Updating lat/lon only.")
                # Update with lat/lon even if timezone is missing
                if update_circuit_enrichment(conn, circuit_id, lat, lon, None):
                    updated += 1
                    logger.info(f"  ✓ Updated {circuit_name} with lat/lon (timezone missing)")
                else:
                    failed += 1
                continue
            
            # Update circuit
            logger.info(f"  Updating circuit with lat={lat:.6f}, lon={lon:.6f}, tz={timezone_tzid}...")
            if update_circuit_enrichment(conn, circuit_id, lat, lon, timezone_tzid):
                updated += 1
                logger.info(f"  ✓ Successfully enriched {circuit_name}")
            else:
                logger.error(f"  ✗ Failed to update {circuit_name} in database")
                failed += 1
            
            logger.info("")  # Blank line for readability
        
        logger.info("="*60)
        logger.info("ENRICHMENT COMPLETE")
        logger.info("="*60)
        logger.info(f"Updated: {updated}/{len(circuits)}")
        if failed > 0:
            logger.warning(f"Failed: {failed}/{len(circuits)}")
    
    finally:
        conn.close()


if __name__ == "__main__":
    main()

