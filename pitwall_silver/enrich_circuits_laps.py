#!/usr/bin/env python3
"""
Enrich circuits with lap length, race laps, and sprint laps from CSV.

Reads lap_length_km, race_laps, and sprint_laps from CSV file and updates
silver.circuits table.
"""

import os
import csv
import logging
from typing import Dict, Optional

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


def read_circuits_csv(csv_path: str) -> Dict[str, Dict]:
    """
    Read circuits from CSV file.
    
    Args:
        csv_path: Path to CSV file
        
    Returns:
        Dictionary mapping circuit_id -> circuit data
    """
    circuits = {}
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            # Skip empty lines and find the header row
            lines = [line.strip() for line in f.readlines() if line.strip()]
            if not lines:
                logger.error("CSV file is empty")
                return circuits
            
            # Find header row (should contain 'circuit_id')
            header_idx = 0
            for i, line in enumerate(lines):
                if 'circuit_id' in line.lower():
                    header_idx = i
                    break
            
            # Parse header
            header = [col.strip() for col in lines[header_idx].split(',')]
            
            # Parse data rows
            for line in lines[header_idx + 1:]:
                if not line.strip():
                    continue
                values = [val.strip() for val in line.split(',')]
                if len(values) < len(header):
                    continue
                
                row = dict(zip(header, values))
                circuit_id = row.get('circuit_id')
                if circuit_id and circuit_id.strip():
                    circuits[circuit_id] = {
                        'circuit_id': circuit_id,
                        'circuit_short_name': row.get('circuit_short_name'),
                        'lap_length_km': row.get('lap_length_km'),
                        'race_laps': row.get('race_laps'),
                        'sprint_laps': row.get('sprint_laps')
                    }
        
        logger.info(f"Read {len(circuits)} circuits from CSV")
        return circuits
    except Exception as e:
        logger.error(f"Failed to read CSV file: {e}")
        raise


def parse_numeric(value: Optional[str]) -> Optional[float]:
    """Parse numeric value from string, returning None if invalid."""
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


def update_circuit_laps(conn, circuit_id: str, lap_length_km: Optional[float], 
                       race_laps: Optional[int], sprint_laps: Optional[int]) -> bool:
    """
    Update circuit with lap length, race laps, and sprint laps.
    
    Args:
        conn: Database connection
        circuit_id: Circuit ID
        lap_length_km: Lap length in kilometers
        race_laps: Number of race laps
        sprint_laps: Number of sprint laps
        
    Returns:
        True if update successful, False otherwise
    """
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE silver.circuits
                SET lap_length_km = %s,
                    race_laps = %s,
                    sprint_laps = %s
                WHERE circuit_id = %s
            """, (lap_length_km, race_laps, sprint_laps, circuit_id))
            conn.commit()
            return True
    except psycopg.Error as e:
        conn.rollback()
        logger.error(f"Failed to update circuit {circuit_id}: {e}")
        return False


def get_circuit_info(conn, circuit_id: str) -> Optional[Dict]:
    """Get circuit info from database."""
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT circuit_id, circuit_short_name
                FROM silver.circuits
                WHERE circuit_id = %s
            """, (circuit_id,))
            row = cur.fetchone()
            if row:
                return {
                    'circuit_id': row[0],
                    'circuit_short_name': row[1]
                }
            return None
    except psycopg.Error as e:
        logger.error(f"Failed to fetch circuit info: {e}")
        return None


def main():
    """Main function."""
    csv_path = "/Users/gavinmiller/Programming/pitwall/seed/agent_enrich/enriched/circuits_laps_enriched.csv"
    
    logger.info("Starting circuit laps enrichment from CSV")
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
        
        for circuit_id, csv_data in csv_circuits.items():
            logger.info(f"Processing circuit: {circuit_id}")
            
            # Get circuit info from database
            db_circuit = get_circuit_info(conn, circuit_id)
            if not db_circuit:
                logger.warning(f"  ✗ Circuit {circuit_id} not found in database. Skipping.")
                not_found += 1
                continue
            
            circuit_name = db_circuit['circuit_short_name']
            logger.info(f"  Circuit: {circuit_name}")
            
            # Parse values from CSV
            lap_length_km = parse_numeric(csv_data.get('lap_length_km'))
            race_laps = parse_int(csv_data.get('race_laps'))
            sprint_laps = parse_int(csv_data.get('sprint_laps'))
            
            logger.info(f"  CSV values: lap_length_km={lap_length_km}, race_laps={race_laps}, sprint_laps={sprint_laps}")
            
            # Update circuit
            if update_circuit_laps(conn, circuit_id, lap_length_km, race_laps, sprint_laps):
                updated += 1
                logger.info(f"  ✓ Successfully updated {circuit_name}")
            else:
                logger.error(f"  ✗ Failed to update {circuit_name} in database")
                failed += 1
            
            logger.info("")  # Blank line for readability
        
        logger.info("="*60)
        logger.info("CIRCUIT LAPS ENRICHMENT COMPLETE")
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

