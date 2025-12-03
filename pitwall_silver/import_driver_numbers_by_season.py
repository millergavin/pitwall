#!/usr/bin/env python3
"""
Import driver numbers by season from CSV and update driver_id to new format.

Reads driver numbers from CSV file and inserts them into silver.driver_numbers_by_season,
updating driver_id from old format to new format using the drivers export CSV.
"""

import os
import csv
import logging
from typing import Dict, List

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


def read_drivers_csv(csv_path: str) -> Dict[str, str]:
    """
    Read drivers from CSV file and create mapping from old driver_id to new format.
    
    Args:
        csv_path: Path to drivers export CSV file
        
    Returns:
        Dictionary mapping old_driver_id -> new_driver_id
    """
    driver_id_mapping = {}
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            # Skip empty lines and find the header row
            lines = [line.strip() for line in f.readlines() if line.strip()]
            if not lines:
                logger.error("CSV file is empty")
                return driver_id_mapping
            
            # Find header row (should contain 'driver_id')
            header_idx = 0
            for i, line in enumerate(lines):
                if 'driver_id' in line.lower() and 'first_name' in line.lower():
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
                old_driver_id = row.get('driver_id')
                first_name = row.get('first_name')
                last_name = row.get('last_name')
                
                if old_driver_id and first_name and last_name:
                    # Generate new driver_id format: drv:{firstname}-{lastname}
                    new_driver_id = generate_new_driver_id(first_name, last_name)
                    driver_id_mapping[old_driver_id] = new_driver_id
        
        logger.info(f"Created driver_id mapping for {len(driver_id_mapping)} drivers")
        return driver_id_mapping
    except Exception as e:
        logger.error(f"Failed to read drivers CSV file: {e}")
        raise


def generate_new_driver_id(first_name: str, last_name: str) -> str:
    """
    Generate new driver_id format: drv:{firstname}-{lastname}
    
    Args:
        first_name: Driver's first name
        last_name: Driver's last name
        
    Returns:
        New driver_id in format drv:{firstname}-{lastname}
    """
    # Sanitize names for use in ID (lowercase, replace spaces/special chars with hyphens)
    def sanitize(name: str) -> str:
        if not name:
            return ''
        name = name.lower().strip()
        # Replace spaces and special chars with hyphens
        name = name.replace(' ', '-').replace('/', '-').replace('\\', '-')
        # Remove any other problematic characters
        name = ''.join(c if c.isalnum() or c == '-' else '' for c in name)
        return name
    
    first_sanitized = sanitize(first_name)
    last_sanitized = sanitize(last_name)
    
    return f"drv:{first_sanitized}-{last_sanitized}"


def read_driver_numbers_csv(csv_path: str) -> List[Dict]:
    """
    Read driver numbers by season from CSV file.
    
    Args:
        csv_path: Path to driver numbers CSV file
        
    Returns:
        List of driver number dictionaries
    """
    records = []
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            # Skip empty lines and find the header row
            lines = [line.strip() for line in f.readlines() if line.strip()]
            if not lines:
                logger.error("CSV file is empty")
                return records
            
            # Find header row (should contain 'season')
            header_idx = 0
            for i, line in enumerate(lines):
                if 'season' in line.lower() and 'driver_id' in line.lower():
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
                season = row.get('season')
                driver_id = row.get('driver_id')
                number = row.get('number')
                
                if season and driver_id and number:
                    try:
                        records.append({
                            'season': int(season),
                            'driver_id': driver_id,
                            'driver_number': int(number)
                        })
                    except ValueError:
                        logger.warning(f"Invalid season or number: {row}")
                        continue
        
        logger.info(f"Read {len(records)} driver number records from CSV")
        return records
    except Exception as e:
        logger.error(f"Failed to read driver numbers CSV file: {e}")
        raise


def insert_driver_numbers(conn, records: List[Dict], driver_id_mapping: Dict[str, str]) -> int:
    """
    Insert driver numbers into silver.driver_numbers_by_season table.
    
    Args:
        conn: Database connection
        records: List of driver number records from CSV
        driver_id_mapping: Mapping of old_driver_id -> new_driver_id
        
    Returns:
        Number of records inserted
    """
    if not records:
        logger.warning("No driver number records to insert")
        return 0
    
    insert_sql = """
        INSERT INTO silver.driver_numbers_by_season (driver_id, season, driver_number)
        VALUES (%(driver_id)s, %(season)s, %(driver_number)s)
        ON CONFLICT (driver_id, season) 
        DO UPDATE SET driver_number = EXCLUDED.driver_number
    """
    
    try:
        with conn.cursor() as cur:
            insert_records = []
            skipped = 0
            unmapped = 0
            
            for record in records:
                old_driver_id = record['driver_id']
                new_driver_id = driver_id_mapping.get(old_driver_id)
                
                if not new_driver_id:
                    logger.warning(
                        f"Driver_id '{old_driver_id}' not found in mapping. "
                        f"Skipping season {record['season']}, number {record['driver_number']}"
                    )
                    unmapped += 1
                    skipped += 1
                    continue
                
                # Verify driver_id exists in silver.drivers
                cur.execute("""
                    SELECT 1 FROM silver.drivers WHERE driver_id = %s
                """, (new_driver_id,))
                
                if not cur.fetchone():
                    logger.warning(
                        f"Driver_id '{new_driver_id}' not found in silver.drivers. "
                        f"Skipping season {record['season']}, number {record['driver_number']}"
                    )
                    skipped += 1
                    continue
                
                insert_records.append({
                    'driver_id': new_driver_id,
                    'season': record['season'],
                    'driver_number': record['driver_number']
                })
            
            if not insert_records:
                logger.warning("No valid driver number records to insert after validation")
                return 0
            
            cur.executemany(insert_sql, insert_records)
            conn.commit()
            inserted_count = len(insert_records)
            logger.info(f"Successfully inserted/updated {inserted_count} driver number records")
            if skipped > 0:
                logger.warning(f"Skipped {skipped} records ({unmapped} unmapped driver_ids)")
            return inserted_count
            
    except psycopg.Error as e:
        conn.rollback()
        logger.error(f"Database insert failed: {e}")
        raise


def main():
    """Main function."""
    drivers_csv_path = "/Users/gavinmiller/Programming/pitwall/seed/f1db_export/drivers_export.csv"
    numbers_csv_path = "/Users/gavinmiller/Programming/pitwall/seed/f1db_export/driver_numbers_by_season_export.csv"
    
    logger.info("Starting driver numbers by season import from CSV")
    logger.info(f"Reading drivers mapping from: {drivers_csv_path}")
    logger.info(f"Reading driver numbers from: {numbers_csv_path}")
    
    # Read driver_id mapping from drivers CSV
    logger.info("Creating driver_id mapping from old to new format...")
    driver_id_mapping = read_drivers_csv(drivers_csv_path)
    
    if not driver_id_mapping:
        logger.error("No driver_id mappings found")
        return
    
    # Show a few examples
    logger.info("Sample driver_id mappings:")
    for i, (old_id, new_id) in enumerate(list(driver_id_mapping.items())[:5]):
        logger.info(f"  {old_id} → {new_id}")
    
    # Read driver numbers from CSV
    logger.info(f"\nReading driver numbers from CSV...")
    records = read_driver_numbers_csv(numbers_csv_path)
    
    if not records:
        logger.error("No driver number records found in CSV file")
        return
    
    conn = get_db_connection()
    
    try:
        logger.info(f"Processing {len(records)} driver number records...")
        
        # Insert driver numbers
        logger.info("Inserting driver numbers into silver.driver_numbers_by_season...")
        inserted = insert_driver_numbers(conn, records, driver_id_mapping)
        
        logger.info("="*60)
        logger.info("DRIVER NUMBERS BY SEASON IMPORT COMPLETE")
        logger.info("="*60)
        logger.info(f"Inserted/updated: {inserted}/{len(records)}")
        
        # Verify by season
        logger.info("\nSummary by season:")
        with conn.cursor() as cur:
            cur.execute("""
                SELECT season, COUNT(*) as driver_count
                FROM silver.driver_numbers_by_season
                GROUP BY season
                ORDER BY season
            """)
            for row in cur.fetchall():
                logger.info(f"  {row[0]}: {row[1]} drivers")
    
    finally:
        conn.close()


if __name__ == "__main__":
    main()


