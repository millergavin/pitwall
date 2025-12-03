#!/usr/bin/env python3
"""
Upsert team_branding data from bronze.drivers_raw into silver.team_branding.

Maps from bronze.drivers_raw:
- team_name → team_name
- team_color_hex → color_hex

Resolves team_id by checking team_name against silver.team_alias.alias.
If team_name doesn't match any alias, the script fails and stops.

Derives season by joining:
drivers_raw.openf1_session_key → sessions.openf1_session_key → meetings.meeting_id → meetings.season

One entry per team_id per season (even if branding is the same across seasons).
"""

import os
import logging
from typing import Dict, List, Set, Tuple

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


def get_team_alias_map(conn) -> Dict[str, str]:
    """
    Get a mapping of team alias to team_id.
    
    Returns:
        Dictionary mapping alias -> team_id
    """
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT alias, team_id 
                FROM silver.team_alias
            """)
            return {row[0]: row[1] for row in cur.fetchall()}
    except psycopg.Error as e:
        logger.error(f"Failed to fetch team alias mapping: {e}")
        raise


def resolve_team_id(team_name: str, alias_map: Dict[str, str]) -> str:
    """
    Resolve team_id from team_name using team_alias lookup.
    
    Args:
        team_name: Team name from bronze.drivers_raw
        alias_map: Mapping of alias -> team_id
        
    Returns:
        Resolved team_id
        
    Raises:
        ValueError: If team_name doesn't match any alias
    """
    if not team_name:
        raise ValueError("team_name is required")
    
    team_id = alias_map.get(team_name)
    if not team_id:
        raise ValueError(
            f"Team name '{team_name}' does not match any alias in silver.team_alias. "
            f"Please add an alias for this team before running the upsert."
        )
    
    return team_id


def get_team_branding_from_bronze(conn) -> List[Dict]:
    """
    Get distinct team branding records from bronze.drivers_raw with season.
    
    Joins through sessions to meetings to get season.
    
    Returns:
        List of team branding dictionaries with team_name, color_hex, season
    """
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT DISTINCT
                    dr.team_name,
                    dr.team_color_hex,
                    m.season
                FROM bronze.drivers_raw dr
                INNER JOIN silver.sessions s 
                    ON dr.openf1_session_key = s.openf1_session_key
                INNER JOIN silver.meetings m 
                    ON s.meeting_id = m.meeting_id
                WHERE dr.team_name IS NOT NULL
                  AND dr.team_color_hex IS NOT NULL
                  AND m.season IS NOT NULL
                ORDER BY m.season, dr.team_name
            """)
            
            records = []
            for row in cur.fetchall():
                records.append({
                    'team_name': row[0],
                    'color_hex': row[1],
                    'season': row[2]
                })
            
            logger.info(f"Found {len(records)} distinct team branding records in bronze.drivers_raw")
            return records
    except psycopg.Error as e:
        logger.error(f"Failed to fetch team branding from bronze: {e}")
        raise


def validate_team_names(records: List[Dict], alias_map: Dict[str, str]) -> None:
    """
    Validate that all team names have matching aliases.
    
    Args:
        records: List of team branding records
        alias_map: Mapping of alias -> team_id
        
    Raises:
        ValueError: If any team_name doesn't match an alias
    """
    missing_aliases = set()
    
    for record in records:
        team_name = record['team_name']
        if team_name not in alias_map:
            missing_aliases.add(team_name)
    
    if missing_aliases:
        error_msg = (
            f"The following team names do not have matching aliases in silver.team_alias:\n"
            f"  {', '.join(sorted(missing_aliases))}\n\n"
            f"Please add aliases for these teams before running the upsert."
        )
        logger.error(error_msg)
        raise ValueError(error_msg)


def upsert_team_branding(conn, records: List[Dict], alias_map: Dict[str, str]) -> int:
    """
    Upsert team branding into silver.team_branding table.
    
    Args:
        conn: Database connection
        records: List of team branding records from bronze
        alias_map: Mapping of alias -> team_id
        
    Returns:
        Number of records upserted
    """
    if not records:
        logger.warning("No team branding records to upsert")
        return 0
    
    upsert_sql = """
        INSERT INTO silver.team_branding (
            team_id,
            team_name,
            season,
            color_hex
        ) VALUES (
            %(team_id)s,
            %(team_name)s,
            %(season)s,
            %(color_hex)s
        )
        ON CONFLICT (team_id, team_name, season) 
        DO UPDATE SET
            color_hex = EXCLUDED.color_hex
    """
    
    try:
        with conn.cursor() as cur:
            upsert_records = []
            
            for record in records:
                # Resolve team_id
                try:
                    team_id = resolve_team_id(record['team_name'], alias_map)
                except ValueError as e:
                    # This should have been caught in validation, but handle it anyway
                    logger.error(f"Failed to resolve team_id: {e}")
                    raise
                
                upsert_records.append({
                    'team_id': team_id,
                    'team_name': record['team_name'],
                    'season': record['season'],
                    'color_hex': record['color_hex']
                })
            
            if not upsert_records:
                logger.warning("No valid team branding records to upsert after validation")
                return 0
            
            cur.executemany(upsert_sql, upsert_records)
            conn.commit()
            upserted_count = len(upsert_records)
            logger.info(f"Successfully upserted {upserted_count} team branding records into silver.team_branding")
            return upserted_count
            
    except psycopg.Error as e:
        conn.rollback()
        logger.error(f"Database upsert failed: {e}")
        raise


def main():
    """Main upsert function."""
    logger.info("Starting team_branding upsert from bronze.drivers_raw to silver.team_branding")
    
    conn = get_db_connection()
    
    try:
        # Get team alias mapping
        logger.info("Loading team alias mapping...")
        alias_map = get_team_alias_map(conn)
        logger.info(f"Loaded {len(alias_map)} team aliases")
        
        if not alias_map:
            logger.error("No team aliases found in silver.team_alias. Please populate team aliases first.")
            return
        
        # Get team branding from bronze
        logger.info("Fetching team branding from bronze.drivers_raw...")
        records = get_team_branding_from_bronze(conn)
        
        if not records:
            logger.warning("No team branding records found in bronze.drivers_raw")
            return
        
        # Validate all team names have matching aliases
        logger.info("Validating team names against team aliases...")
        try:
            validate_team_names(records, alias_map)
            logger.info("✓ All team names have matching aliases")
        except ValueError as e:
            logger.error("Validation failed. Stopping upsert.")
            raise
        
        # Upsert team branding
        logger.info("Upserting team branding into silver.team_branding...")
        upserted = upsert_team_branding(conn, records, alias_map)
        
        logger.info("="*60)
        logger.info("TEAM BRANDING UPSERT COMPLETE")
        logger.info("="*60)
        logger.info(f"Upserted: {upserted} team branding records")
        
        # Show summary by season
        logger.info("\nSummary by season:")
        with conn.cursor() as cur:
            cur.execute("""
                SELECT season, COUNT(*) as team_count
                FROM silver.team_branding
                GROUP BY season
                ORDER BY season
            """)
            for row in cur.fetchall():
                logger.info(f"  {row[0]}: {row[1]} teams")
    
    finally:
        conn.close()


if __name__ == "__main__":
    main()


