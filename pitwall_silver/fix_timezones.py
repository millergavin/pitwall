#!/usr/bin/env python3
"""
Fix incorrect timezones for specific circuits.
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

# Manual timezone corrections
TIMEZONE_FIXES = {
    'Sakhir': 'Asia/Bahrain',
    'Singapore': 'Asia/Singapore',
    'Shanghai': 'Asia/Shanghai',
    'Jeddah': 'Asia/Riyadh',
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


def fix_timezone(conn, circuit_short_name: str, timezone_tzid: str) -> bool:
    """
    Update timezone for a circuit.
    
    Args:
        conn: Database connection
        circuit_short_name: Circuit short name
        timezone_tzid: Correct IANA timezone ID
        
    Returns:
        True if update successful, False otherwise
    """
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE silver.circuits
                SET timezone_tzid = %s
                WHERE circuit_short_name = %s
            """, (timezone_tzid, circuit_short_name))
            conn.commit()
            return True
    except psycopg.Error as e:
        conn.rollback()
        logger.error(f"Failed to update timezone for {circuit_short_name}: {e}")
        return False


def main():
    """Main function."""
    logger.info("Fixing incorrect timezones")
    logger.info(f"Circuits to fix: {list(TIMEZONE_FIXES.keys())}")
    
    conn = get_db_connection()
    
    try:
        updated = 0
        failed = 0
        
        for circuit_name, correct_tzid in TIMEZONE_FIXES.items():
            logger.info(f"Updating {circuit_name} → {correct_tzid}")
            
            if fix_timezone(conn, circuit_name, correct_tzid):
                updated += 1
                logger.info(f"  ✓ Successfully updated {circuit_name}")
            else:
                failed += 1
                logger.error(f"  ✗ Failed to update {circuit_name}")
        
        logger.info("="*60)
        logger.info("TIMEZONE FIX COMPLETE")
        logger.info("="*60)
        logger.info(f"Updated: {updated}/{len(TIMEZONE_FIXES)}")
        if failed > 0:
            logger.warning(f"Failed: {failed}")
    
    finally:
        conn.close()


if __name__ == "__main__":
    main()


