#!/usr/bin/env python3
"""
Upsert circuits data from bronze.meetings_raw into silver.circuits.

Maps from bronze.meetings_raw:
- openf1_circuit_key → openf1_circuit_key
- circuit_short_name → circuit_short_name
- location → location
- country_code → country_code (with alias lookup)

Generates circuit_id using format: circuit:{circuit_short_name}-{openf1_circuit_key}
"""

import os
import logging
from typing import Dict, List, Optional

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


def get_country_code_alias_map(conn) -> Dict[str, str]:
    """
    Get a mapping of country code aliases to actual country codes.
    
    Returns:
        Dictionary mapping alias -> country_code
    """
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT alias, country_code 
                FROM silver.country_code_alias
            """)
            return {row[0]: row[1] for row in cur.fetchall()}
    except psycopg.Error as e:
        logger.error(f"Failed to fetch country code aliases: {e}")
        return {}


def resolve_country_code(country_code: Optional[str], alias_map: Dict[str, str]) -> Optional[str]:
    """
    Resolve country code using alias lookup if needed.
    
    Args:
        country_code: Country code from bronze.meetings_raw
        alias_map: Mapping of aliases to country codes
        
    Returns:
        Resolved country code
    """
    if not country_code:
        return None
    
    # Check if the country_code is an alias
    if country_code in alias_map:
        resolved = alias_map[country_code]
        logger.debug(f"Resolved country code alias '{country_code}' to '{resolved}'")
        return resolved
    
    # Return as-is if not found in alias map
    return country_code


def generate_circuit_id(circuit_short_name: Optional[str], openf1_circuit_key: Optional[str]) -> Optional[str]:
    """
    Generate circuit_id using format: circuit:{circuit_short_name}-{openf1_circuit_key}
    
    Args:
        circuit_short_name: Circuit short name
        openf1_circuit_key: OpenF1 circuit key
        
    Returns:
        Generated circuit_id or None if required fields are missing
    """
    if not circuit_short_name or not openf1_circuit_key:
        return None
    
    return f"circuit:{circuit_short_name}-{openf1_circuit_key}"


def get_distinct_circuits_from_bronze(conn) -> List[Dict]:
    """
    Get distinct circuit records from bronze.meetings_raw.
    
    Returns:
        List of circuit dictionaries with openf1_circuit_key, circuit_short_name, location, country_code
    """
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT DISTINCT 
                    openf1_circuit_key,
                    circuit_short_name,
                    location,
                    country_code
                FROM bronze.meetings_raw
                WHERE openf1_circuit_key IS NOT NULL
                  AND circuit_short_name IS NOT NULL
                ORDER BY openf1_circuit_key
            """)
            
            circuits = []
            for row in cur.fetchall():
                circuits.append({
                    'openf1_circuit_key': row[0],
                    'circuit_short_name': row[1],
                    'location': row[2],
                    'country_code': row[3]
                })
            
            logger.info(f"Found {len(circuits)} distinct circuits in bronze.meetings_raw")
            return circuits
    except psycopg.Error as e:
        logger.error(f"Failed to fetch circuits from bronze: {e}")
        raise


def upsert_circuits(conn, circuits: List[Dict], alias_map: Dict[str, str]) -> int:
    """
    Upsert circuits into silver.circuits table.
    
    Args:
        conn: Database connection
        circuits: List of circuit records from bronze
        alias_map: Country code alias mapping
        
    Returns:
        Number of records upserted
    """
    if not circuits:
        logger.warning("No circuits to upsert")
        return 0
    
    upsert_sql = """
        INSERT INTO silver.circuits (
            circuit_id,
            openf1_circuit_key,
            circuit_short_name,
            country_code,
            location
        ) VALUES (
            %(circuit_id)s,
            %(openf1_circuit_key)s,
            %(circuit_short_name)s,
            %(country_code)s,
            %(location)s
        )
        ON CONFLICT (circuit_id) 
        DO UPDATE SET
            openf1_circuit_key = EXCLUDED.openf1_circuit_key,
            circuit_short_name = EXCLUDED.circuit_short_name,
            country_code = EXCLUDED.country_code,
            location = EXCLUDED.location
    """
    
    try:
        with conn.cursor() as cur:
            upsert_records = []
            skipped = 0
            
            for circuit in circuits:
                # Generate circuit_id
                circuit_id = generate_circuit_id(
                    circuit['circuit_short_name'],
                    circuit['openf1_circuit_key']
                )
                
                if not circuit_id:
                    logger.warning(f"Skipping circuit due to missing required fields: {circuit}")
                    skipped += 1
                    continue
                
                # Resolve country code
                resolved_country_code = resolve_country_code(
                    circuit['country_code'],
                    alias_map
                )
                
                # Validate country code exists in countries table
                if resolved_country_code:
                    cur.execute("""
                        SELECT 1 FROM silver.countries 
                        WHERE country_code = %s
                    """, (resolved_country_code,))
                    if not cur.fetchone():
                        logger.warning(
                            f"Country code '{resolved_country_code}' not found in silver.countries. "
                            f"Skipping circuit {circuit_id}"
                        )
                        skipped += 1
                        continue
                
                upsert_records.append({
                    'circuit_id': circuit_id,
                    'openf1_circuit_key': circuit['openf1_circuit_key'],
                    'circuit_short_name': circuit['circuit_short_name'],
                    'country_code': resolved_country_code,
                    'location': circuit['location']
                })
            
            if not upsert_records:
                logger.warning("No valid circuits to upsert after validation")
                return 0
            
            cur.executemany(upsert_sql, upsert_records)
            conn.commit()
            upserted_count = len(upsert_records)
            logger.info(f"Successfully upserted {upserted_count} circuits into silver.circuits")
            if skipped > 0:
                logger.warning(f"Skipped {skipped} circuits due to validation issues")
            return upserted_count
            
    except psycopg.Error as e:
        conn.rollback()
        logger.error(f"Database upsert failed: {e}")
        raise


def main():
    """Main upsert function."""
    logger.info("Starting circuits upsert from bronze.meetings_raw to silver.circuits")
    
    conn = get_db_connection()
    
    try:
        # Get country code alias mapping
        logger.info("Loading country code alias mapping...")
        alias_map = get_country_code_alias_map(conn)
        logger.info(f"Loaded {len(alias_map)} country code aliases")
        
        # Get distinct circuits from bronze
        logger.info("Fetching distinct circuits from bronze.meetings_raw...")
        circuits = get_distinct_circuits_from_bronze(conn)
        
        if not circuits:
            logger.warning("No circuits found in bronze.meetings_raw")
            return
        
        # Upsert circuits
        logger.info("Upserting circuits into silver.circuits...")
        upserted = upsert_circuits(conn, circuits, alias_map)
        
        logger.info(f"Upsert complete: {upserted} circuits upserted")
    
    finally:
        conn.close()


if __name__ == "__main__":
    main()


