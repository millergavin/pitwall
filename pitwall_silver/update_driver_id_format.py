#!/usr/bin/env python3
"""
One-time update to change driver_id format from:
  drv:{lastname}-{firstinitial}-{birth_year}
to:
  drv:{firstname}-{lastname}

Updates all tables that reference driver_id.
"""

import os
import logging
from typing import Dict, List, Tuple

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

# Tables that reference driver_id (in order of dependency)
# We'll update these before updating the drivers table itself
DRIVER_ID_REFERENCE_TABLES = [
    'driver_numbers_by_season',
    'driver_teams_by_session',
    'driver_alias',
    'race_control',
    'laps',
    'car_telemetry',
    'car_gps',
    'position',
    'intervals',
    'overtakes',  # Has overtaken_driver_id and overtaking_driver_id
    'pit_stops',
    'stints',
    'results',
]

# Tables with driver_id columns that need special handling
SPECIAL_DRIVER_ID_COLUMNS = {
    'circuits': 'fastest_lap_driver_id',  # Optional reference, not a foreign key
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


def get_all_drivers(conn) -> List[Dict]:
    """
    Get all drivers from silver.drivers.
    
    Returns:
        List of driver dictionaries with old driver_id, first_name, last_name
    """
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT driver_id, first_name, last_name
                FROM silver.drivers
                ORDER BY driver_id
            """)
            
            drivers = []
            for row in cur.fetchall():
                drivers.append({
                    'old_driver_id': row[0],
                    'first_name': row[1],
                    'last_name': row[2]
                })
            
            logger.info(f"Found {len(drivers)} drivers in silver.drivers")
            return drivers
    except psycopg.Error as e:
        logger.error(f"Failed to fetch drivers: {e}")
        raise


def create_driver_id_mapping(drivers: List[Dict]) -> Dict[str, str]:
    """
    Create mapping of old driver_id -> new driver_id.
    
    Args:
        drivers: List of driver dictionaries
        
    Returns:
        Dictionary mapping old_driver_id -> new_driver_id
    """
    mapping = {}
    duplicates = []
    
    for driver in drivers:
        new_id = generate_new_driver_id(driver['first_name'], driver['last_name'])
        old_id = driver['old_driver_id']
        
        if new_id in mapping.values():
            # Found duplicate - log warning
            duplicates.append((old_id, new_id))
            logger.warning(f"Duplicate new driver_id generated: {new_id} for driver {old_id}")
        else:
            mapping[old_id] = new_id
    
    if duplicates:
        logger.error(f"Found {len(duplicates)} duplicate new driver_ids. Cannot proceed.")
        raise ValueError(f"Duplicate driver_ids detected: {duplicates}")
    
    logger.info(f"Created driver_id mapping for {len(mapping)} drivers")
    return mapping


def update_driver_id_in_table(conn, table_name: str, column_name: str, 
                              driver_id_mapping: Dict[str, str]) -> int:
    """
    Update driver_id in a specific table column.
    
    Args:
        conn: Database connection
        table_name: Name of the table to update
        column_name: Name of the column containing driver_id
        driver_id_mapping: Mapping of old_driver_id -> new_driver_id
        
    Returns:
        Number of rows updated
    """
    if not driver_id_mapping:
        return 0
    
    try:
        with conn.cursor() as cur:
            # Build UPDATE statement with CASE WHEN for each mapping
            case_statements = []
            for old_id, new_id in driver_id_mapping.items():
                case_statements.append(f"WHEN '{old_id}' THEN '{new_id}'")
            
            update_sql = f"""
                UPDATE silver.{table_name}
                SET {column_name} = CASE {column_name}
                    {' '.join(case_statements)}
                    ELSE {column_name}
                END
                WHERE {column_name} IN ({','.join([f"'{old_id}'" for old_id in driver_id_mapping.keys()])})
            """
            
            cur.execute(update_sql)
            rows_updated = cur.rowcount
            conn.commit()
            
            if rows_updated > 0:
                logger.info(f"  Updated {rows_updated} rows in silver.{table_name}.{column_name}")
            
            return rows_updated
    except psycopg.Error as e:
        conn.rollback()
        logger.error(f"Failed to update silver.{table_name}.{column_name}: {e}")
        raise


def update_overtakes_table(conn, driver_id_mapping: Dict[str, str]) -> int:
    """
    Update overtakes table which has two driver_id columns.
    
    Args:
        conn: Database connection
        driver_id_mapping: Mapping of old_driver_id -> new_driver_id
        
    Returns:
        Total number of rows updated
    """
    if not driver_id_mapping:
        return 0
    
    try:
        with conn.cursor() as cur:
            # Build CASE statements for both columns
            case_statements = []
            for old_id, new_id in driver_id_mapping.items():
                case_statements.append(f"WHEN '{old_id}' THEN '{new_id}'")
            
            case_clause = ' '.join(case_statements)
            
            update_sql = f"""
                UPDATE silver.overtakes
                SET 
                    overtaken_driver_id = CASE overtaken_driver_id
                        {case_clause}
                        ELSE overtaken_driver_id
                    END,
                    overtaking_driver_id = CASE overtaking_driver_id
                        {case_clause}
                        ELSE overtaking_driver_id
                    END
                WHERE overtaken_driver_id IN ({','.join([f"'{old_id}'" for old_id in driver_id_mapping.keys()])})
                   OR overtaking_driver_id IN ({','.join([f"'{old_id}'" for old_id in driver_id_mapping.keys()])})
            """
            
            cur.execute(update_sql)
            rows_updated = cur.rowcount
            conn.commit()
            
            if rows_updated > 0:
                logger.info(f"  Updated {rows_updated} rows in silver.overtakes (both driver_id columns)")
            
            return rows_updated
    except psycopg.Error as e:
        conn.rollback()
        logger.error(f"Failed to update silver.overtakes: {e}")
        raise


def update_drivers_table(conn, driver_id_mapping: Dict[str, str]) -> int:
    """
    Update driver_id in silver.drivers table itself.
    
    Args:
        conn: Database connection
        driver_id_mapping: Mapping of old_driver_id -> new_driver_id
        
    Returns:
        Number of rows updated
    """
    if not driver_id_mapping:
        return 0
    
    try:
        with conn.cursor() as cur:
            # Build UPDATE statement with CASE WHEN for each mapping
            case_statements = []
            for old_id, new_id in driver_id_mapping.items():
                case_statements.append(f"WHEN '{old_id}' THEN '{new_id}'")
            
            update_sql = f"""
                UPDATE silver.drivers
                SET driver_id = CASE driver_id
                    {' '.join(case_statements)}
                    ELSE driver_id
                END
                WHERE driver_id IN ({','.join([f"'{old_id}'" for old_id in driver_id_mapping.keys()])})
            """
            
            cur.execute(update_sql)
            rows_updated = cur.rowcount
            conn.commit()
            
            logger.info(f"Updated {rows_updated} driver_ids in silver.drivers")
            return rows_updated
    except psycopg.Error as e:
        conn.rollback()
        logger.error(f"Failed to update silver.drivers: {e}")
        raise


def main():
    """Main update function."""
    logger.info("Starting driver_id format update")
    logger.info("Old format: drv:{lastname}-{firstinitial}-{birth_year}")
    logger.info("New format: drv:{firstname}-{lastname}")
    
    conn = get_db_connection()
    
    try:
        # Get all drivers
        logger.info("Fetching all drivers from silver.drivers...")
        drivers = get_all_drivers(conn)
        
        if not drivers:
            logger.warning("No drivers found in silver.drivers")
            return
        
        # Create driver_id mapping
        logger.info("Generating new driver_id format for all drivers...")
        driver_id_mapping = create_driver_id_mapping(drivers)
        
        # Show a few examples
        logger.info("Sample driver_id mappings:")
        for i, (old_id, new_id) in enumerate(list(driver_id_mapping.items())[:5]):
            logger.info(f"  {old_id} → {new_id}")
        
        # Confirm before proceeding
        logger.info(f"\nAbout to update {len(driver_id_mapping)} driver_ids across all tables...")
        
        # Update all reference tables first
        logger.info("\nUpdating driver_id in reference tables...")
        total_reference_updates = 0
        
        for table_name in DRIVER_ID_REFERENCE_TABLES:
            if table_name == 'overtakes':
                # Special handling for overtakes (has two driver_id columns)
                updated = update_overtakes_table(conn, driver_id_mapping)
                total_reference_updates += updated
            else:
                updated = update_driver_id_in_table(conn, table_name, 'driver_id', driver_id_mapping)
                total_reference_updates += updated
        
        # Update special driver_id columns (like fastest_lap_driver_id in circuits)
        for table_name, column_name in SPECIAL_DRIVER_ID_COLUMNS.items():
            logger.info(f"Updating {table_name}.{column_name}...")
            updated = update_driver_id_in_table(conn, table_name, column_name, driver_id_mapping)
            total_reference_updates += updated
        
        logger.info(f"Total reference table updates: {total_reference_updates} rows")
        
        # Finally, update the drivers table itself
        logger.info("\nUpdating driver_id in silver.drivers...")
        drivers_updated = update_drivers_table(conn, driver_id_mapping)
        
        logger.info("="*60)
        logger.info("DRIVER_ID FORMAT UPDATE COMPLETE")
        logger.info("="*60)
        logger.info(f"Updated {drivers_updated} drivers")
        logger.info(f"Updated {total_reference_updates} rows in reference tables")
        
        # Verify a few examples
        logger.info("\nVerifying updated driver_ids:")
        with conn.cursor() as cur:
            cur.execute("""
                SELECT driver_id, first_name, last_name
                FROM silver.drivers
                ORDER BY driver_id
                LIMIT 5
            """)
            for row in cur.fetchall():
                logger.info(f"  {row[0]} ({row[1]} {row[2]})")
    
    finally:
        conn.close()


if __name__ == "__main__":
    main()

