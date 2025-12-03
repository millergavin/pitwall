#!/usr/bin/env python3
"""
Deduplicate car_telemetry and car_gps tables, then add unique constraints.

Removes duplicate records based on (session_id, driver_id, date) composite key,
keeping the record with the smallest primary key ID (oldest insert).
"""

import os
import logging
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


def check_duplicates(conn, table_name: str, id_column: str) -> int:
    """Check for duplicate records in a table."""
    logger.info(f"\nChecking for duplicates in silver.{table_name}...")
    
    try:
        with conn.cursor() as cur:
            cur.execute(f"""
                SELECT COUNT(*) as duplicate_count
                FROM (
                    SELECT session_id, driver_id, date, COUNT(*) as cnt
                    FROM silver.{table_name}
                    GROUP BY session_id, driver_id, date
                    HAVING COUNT(*) > 1
                ) dupes
            """)
            duplicate_groups = cur.fetchone()[0]
            
            if duplicate_groups == 0:
                logger.info(f"  ✅ No duplicates found in silver.{table_name}")
                return 0
            
            # Get total duplicate records
            cur.execute(f"""
                WITH duplicate_groups AS (
                    SELECT session_id, driver_id, date, COUNT(*) as cnt
                    FROM silver.{table_name}
                    GROUP BY session_id, driver_id, date
                    HAVING COUNT(*) > 1
                )
                SELECT SUM(cnt) FROM duplicate_groups
            """)
            total_duplicates = cur.fetchone()[0]
            
            logger.warning(f"  ⚠️  Found {duplicate_groups:,} duplicate groups with {total_duplicates:,} total records")
            logger.info(f"     Will keep {duplicate_groups:,} records (oldest by {id_column})")
            logger.info(f"     Will delete {total_duplicates - duplicate_groups:,} duplicate records")
            
            return total_duplicates - duplicate_groups
            
    except psycopg.Error as e:
        logger.error(f"Failed to check duplicates: {e}")
        raise


def deduplicate_table(conn, table_name: str, id_column: str) -> int:
    """
    Remove duplicate records from a table, keeping the oldest by primary key.
    
    Returns:
        Number of records deleted
    """
    logger.info(f"\nDeduplicating silver.{table_name}...")
    
    try:
        with conn.cursor() as cur:
            # Delete duplicates, keeping the record with the smallest ID (oldest)
            cur.execute(f"""
                WITH duplicates AS (
                    SELECT 
                        {id_column},
                        ROW_NUMBER() OVER (
                            PARTITION BY session_id, driver_id, date 
                            ORDER BY {id_column}
                        ) as rn
                    FROM silver.{table_name}
                )
                DELETE FROM silver.{table_name}
                WHERE {id_column} IN (
                    SELECT {id_column}
                    FROM duplicates
                    WHERE rn > 1
                )
            """)
            
            deleted_count = cur.rowcount
            conn.commit()
            
            logger.info(f"  ✅ Deleted {deleted_count:,} duplicate records from silver.{table_name}")
            return deleted_count
            
    except psycopg.Error as e:
        conn.rollback()
        logger.error(f"Failed to deduplicate {table_name}: {e}")
        raise


def add_unique_constraint(conn, table_name: str, constraint_name: str) -> bool:
    """
    Add unique constraint to a table.
    
    Returns:
        True if constraint was added, False if it already exists
    """
    logger.info(f"\nAdding unique constraint to silver.{table_name}...")
    
    try:
        with conn.cursor() as cur:
            # Check if constraint already exists
            cur.execute("""
                SELECT COUNT(*)
                FROM pg_constraint
                WHERE conname = %s
            """, (constraint_name,))
            
            if cur.fetchone()[0] > 0:
                logger.info(f"  ℹ️  Constraint {constraint_name} already exists")
                return False
            
            # Add unique constraint
            cur.execute(f"""
                ALTER TABLE silver.{table_name}
                ADD CONSTRAINT {constraint_name}
                UNIQUE (session_id, driver_id, date)
            """)
            
            conn.commit()
            logger.info(f"  ✅ Added unique constraint: {constraint_name}")
            return True
            
    except psycopg.Error as e:
        conn.rollback()
        logger.error(f"Failed to add constraint: {e}")
        raise


def verify_no_duplicates(conn, table_name: str) -> bool:
    """Verify that no duplicates remain after deduplication."""
    logger.info(f"\nVerifying silver.{table_name} has no duplicates...")
    
    try:
        with conn.cursor() as cur:
            cur.execute(f"""
                SELECT COUNT(*) as duplicate_count
                FROM (
                    SELECT session_id, driver_id, date, COUNT(*) as cnt
                    FROM silver.{table_name}
                    GROUP BY session_id, driver_id, date
                    HAVING COUNT(*) > 1
                ) dupes
            """)
            duplicate_count = cur.fetchone()[0]
            
            if duplicate_count == 0:
                logger.info(f"  ✅ Verified: No duplicates in silver.{table_name}")
                return True
            else:
                logger.error(f"  ❌ Found {duplicate_count} duplicate groups still remaining!")
                return False
                
    except psycopg.Error as e:
        logger.error(f"Failed to verify: {e}")
        raise


def get_table_stats(conn, table_name: str):
    """Get and display table statistics."""
    try:
        with conn.cursor() as cur:
            cur.execute(f"""
                SELECT 
                    COUNT(*) as total_records,
                    COUNT(DISTINCT session_id) as unique_sessions,
                    COUNT(DISTINCT driver_id) as unique_drivers,
                    MIN(date) as earliest_date,
                    MAX(date) as latest_date
                FROM silver.{table_name}
            """)
            stats = cur.fetchone()
            
            logger.info(f"\n  Final stats for silver.{table_name}:")
            logger.info(f"    Total records: {stats[0]:,}")
            logger.info(f"    Unique sessions: {stats[1]}")
            logger.info(f"    Unique drivers: {stats[2]}")
            logger.info(f"    Date range: {stats[3]} to {stats[4]}")
            
    except psycopg.Error as e:
        logger.error(f"Failed to get stats: {e}")


def main():
    """Main function to deduplicate and add constraints."""
    logger.info("="*70)
    logger.info("DEDUPLICATION AND CONSTRAINT ADDITION")
    logger.info("="*70)
    logger.info("Tables: silver.car_telemetry, silver.car_gps")
    logger.info("Constraint: UNIQUE (session_id, driver_id, date)")
    logger.info("="*70)
    
    conn = get_db_connection()
    
    try:
        # Process car_telemetry
        logger.info("\n" + "="*70)
        logger.info("PROCESSING: silver.car_telemetry")
        logger.info("="*70)
        
        dupes_to_delete = check_duplicates(conn, 'car_telemetry', 'car_telemetry_id')
        
        if dupes_to_delete > 0:
            deleted = deduplicate_table(conn, 'car_telemetry', 'car_telemetry_id')
            if not verify_no_duplicates(conn, 'car_telemetry'):
                raise Exception("Deduplication failed for car_telemetry!")
        
        add_unique_constraint(conn, 'car_telemetry', 'car_telemetry_unique_session_driver_date')
        get_table_stats(conn, 'car_telemetry')
        
        # Process car_gps
        logger.info("\n" + "="*70)
        logger.info("PROCESSING: silver.car_gps")
        logger.info("="*70)
        
        dupes_to_delete = check_duplicates(conn, 'car_gps', 'car_gps_id')
        
        if dupes_to_delete > 0:
            deleted = deduplicate_table(conn, 'car_gps', 'car_gps_id')
            if not verify_no_duplicates(conn, 'car_gps'):
                raise Exception("Deduplication failed for car_gps!")
        
        add_unique_constraint(conn, 'car_gps', 'car_gps_unique_session_driver_date')
        get_table_stats(conn, 'car_gps')
        
        # Final summary
        logger.info("\n" + "="*70)
        logger.info("✅ DEDUPLICATION AND CONSTRAINT ADDITION COMPLETE")
        logger.info("="*70)
        logger.info("Next steps:")
        logger.info("  • Future inserts will automatically prevent duplicates")
        logger.info("  • Upsert scripts will use ON CONFLICT to handle existing records")
        logger.info("="*70)
        
    finally:
        conn.close()


if __name__ == "__main__":
    main()

