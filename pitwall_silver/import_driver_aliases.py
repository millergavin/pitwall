#!/usr/bin/env python3
"""
Import driver aliases from CSV and update driver_id to new format.

Reads aliases from CSV file and inserts them into silver.driver_alias,
updating driver_id from old format to new format.
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

# Mapping of old driver_id format to new format
# For this specific case: drv:antonelli-k-2006 -> drv:kimi-antonelli
DRIVER_ID_MAPPING = {
    'drv:antonelli-k-2006': 'drv:kimi-antonelli'
}


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


def read_driver_aliases_csv(csv_path: str) -> List[Dict]:
    """
    Read driver aliases from CSV file.
    
    Args:
        csv_path: Path to CSV file
        
    Returns:
        List of alias dictionaries
    """
    aliases = []
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            # Skip empty lines and find the header row
            lines = [line.strip() for line in f.readlines() if line.strip()]
            if not lines:
                logger.error("CSV file is empty")
                return aliases
            
            # Find header row (should contain 'alias')
            header_idx = 0
            for i, line in enumerate(lines):
                if 'alias' in line.lower() and 'driver_id' in line.lower():
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
                alias = row.get('alias')
                driver_id = row.get('driver_id')
                
                if alias and driver_id and alias.strip() and driver_id.strip():
                    aliases.append({
                        'alias': alias,
                        'driver_id': driver_id,
                        'alias_type': row.get('alias_type'),
                        'created_at': row.get('created_at')
                    })
        
        logger.info(f"Read {len(aliases)} aliases from CSV")
        return aliases
    except Exception as e:
        logger.error(f"Failed to read CSV file: {e}")
        raise


def update_driver_id(old_driver_id: str) -> str:
    """
    Update driver_id from old format to new format.
    
    Args:
        old_driver_id: Old format driver_id
        
    Returns:
        New format driver_id
    """
    return DRIVER_ID_MAPPING.get(old_driver_id, old_driver_id)


def insert_driver_aliases(conn, aliases: List[Dict]) -> int:
    """
    Insert driver aliases into silver.driver_alias table.
    
    Args:
        conn: Database connection
        aliases: List of alias dictionaries
        
    Returns:
        Number of aliases inserted
    """
    if not aliases:
        logger.warning("No aliases to insert")
        return 0
    
    insert_sql = """
        INSERT INTO silver.driver_alias (alias, driver_id)
        VALUES (%(alias)s, %(driver_id)s)
        ON CONFLICT (alias) 
        DO UPDATE SET driver_id = EXCLUDED.driver_id
    """
    
    try:
        with conn.cursor() as cur:
            insert_records = []
            skipped = 0
            
            for alias_data in aliases:
                old_driver_id = alias_data['driver_id']
                new_driver_id = update_driver_id(old_driver_id)
                
                if new_driver_id != old_driver_id:
                    logger.debug(f"Updating driver_id: {old_driver_id} → {new_driver_id}")
                
                # Verify driver_id exists in silver.drivers
                cur.execute("""
                    SELECT 1 FROM silver.drivers WHERE driver_id = %s
                """, (new_driver_id,))
                
                if not cur.fetchone():
                    logger.warning(
                        f"Driver_id '{new_driver_id}' not found in silver.drivers. "
                        f"Skipping alias '{alias_data['alias']}'"
                    )
                    skipped += 1
                    continue
                
                insert_records.append({
                    'alias': alias_data['alias'],
                    'driver_id': new_driver_id
                })
            
            if not insert_records:
                logger.warning("No valid aliases to insert after validation")
                return 0
            
            cur.executemany(insert_sql, insert_records)
            conn.commit()
            inserted_count = len(insert_records)
            logger.info(f"Successfully inserted/updated {inserted_count} aliases into silver.driver_alias")
            if skipped > 0:
                logger.warning(f"Skipped {skipped} aliases due to validation issues")
            return inserted_count
            
    except psycopg.Error as e:
        conn.rollback()
        logger.error(f"Database insert failed: {e}")
        raise


def main():
    """Main function."""
    csv_path = "/Users/gavinmiller/Programming/pitwall/seed/f1db_export/driver_alias_export.csv"
    
    logger.info("Starting driver alias import from CSV")
    logger.info(f"Reading CSV from: {csv_path}")
    
    # Read aliases from CSV
    aliases = read_driver_aliases_csv(csv_path)
    
    if not aliases:
        logger.error("No aliases found in CSV file")
        return
    
    conn = get_db_connection()
    
    try:
        logger.info(f"Processing {len(aliases)} aliases...")
        
        # Show sample mappings
        logger.info("Sample driver_id mappings:")
        for alias_data in aliases[:3]:
            old_id = alias_data['driver_id']
            new_id = update_driver_id(old_id)
            if old_id != new_id:
                logger.info(f"  {old_id} → {new_id}")
        
        # Insert aliases
        logger.info("\nInserting aliases into silver.driver_alias...")
        inserted = insert_driver_aliases(conn, aliases)
        
        logger.info("="*60)
        logger.info("DRIVER ALIAS IMPORT COMPLETE")
        logger.info("="*60)
        logger.info(f"Inserted/updated: {inserted}/{len(aliases)}")
        
        # Verify a few examples
        logger.info("\nVerifying inserted aliases:")
        with conn.cursor() as cur:
            cur.execute("""
                SELECT alias, driver_id
                FROM silver.driver_alias
                WHERE driver_id = 'drv:kimi-antonelli'
                ORDER BY alias
                LIMIT 5
            """)
            for row in cur.fetchall():
                logger.info(f"  {row[0]} → {row[1]}")
    
    finally:
        conn.close()


if __name__ == "__main__":
    main()


