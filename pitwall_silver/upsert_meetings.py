#!/usr/bin/env python3
"""
Upsert meetings data from bronze.meetings_raw into silver.meetings.

Maps from bronze.meetings_raw:
- openf1_meeting_key → openf1_meeting_key
- meeting_name → meeting_name
- season → season (converted to INT)
- meeting_official_name → meeting_official_name
- date_start → date_start (converted to TIMESTAMPTZ)

Generates meeting_id using format: mtg:{season}-{meeting_name}
Resolves circuit_id by joining to silver.circuits
Derives round_number from sequential order within season (only for "Grand Prix" meetings)
"""

import os
import logging
from typing import Dict, List, Optional
from datetime import datetime
from collections import defaultdict

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


def get_circuit_id_map(conn) -> Dict[str, str]:
    """
    Get a mapping of openf1_circuit_key to circuit_id.
    
    Returns:
        Dictionary mapping openf1_circuit_key -> circuit_id
    """
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT openf1_circuit_key, circuit_id 
                FROM silver.circuits
            """)
            return {str(row[0]): row[1] for row in cur.fetchall()}
    except psycopg.Error as e:
        logger.error(f"Failed to fetch circuit ID mapping: {e}")
        return {}


def generate_meeting_id(season: Optional[int], meeting_name: Optional[str]) -> Optional[str]:
    """
    Generate meeting_id using format: mtg:{season}-{meeting_name}
    
    Args:
        season: Season year
        meeting_name: Meeting name
        
    Returns:
        Generated meeting_id or None if required fields are missing
    """
    if season is None or not meeting_name:
        return None
    
    # Sanitize meeting_name for use in ID (replace spaces and special chars)
    sanitized_name = meeting_name.replace(' ', '-').replace('/', '-').replace('\\', '-')
    # Remove any other problematic characters
    sanitized_name = ''.join(c if c.isalnum() or c == '-' else '' for c in sanitized_name)
    
    return f"mtg:{season}-{sanitized_name}"


def parse_date_start(date_str: Optional[str]) -> Optional[datetime]:
    """
    Parse date_start from TEXT to TIMESTAMPTZ.
    
    Args:
        date_str: Date string from bronze table
        
    Returns:
        Parsed datetime or None if invalid
    """
    if not date_str:
        return None
    
    try:
        # Try ISO format first (most common)
        return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
    except (ValueError, AttributeError):
        try:
            # Try other common formats
            for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%Y-%m-%dT%H:%M:%S']:
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue
        except Exception:
            pass
    
    logger.warning(f"Could not parse date_start: {date_str}")
    return None


def get_meetings_from_bronze(conn) -> List[Dict]:
    """
    Get all meeting records from bronze.meetings_raw.
    
    Returns:
        List of meeting dictionaries
    """
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    openf1_meeting_key,
                    meeting_name,
                    season,
                    meeting_official_name,
                    date_start,
                    openf1_circuit_key
                FROM bronze.meetings_raw
                WHERE openf1_meeting_key IS NOT NULL
                  AND meeting_name IS NOT NULL
                  AND season IS NOT NULL
                  AND date_start IS NOT NULL
                ORDER BY season, date_start
            """)
            
            meetings = []
            for row in cur.fetchall():
                meetings.append({
                    'openf1_meeting_key': row[0],
                    'meeting_name': row[1],
                    'season': row[2],
                    'meeting_official_name': row[3],
                    'date_start': row[4],
                    'openf1_circuit_key': row[5]
                })
            
            logger.info(f"Found {len(meetings)} meetings in bronze.meetings_raw")
            return meetings
    except psycopg.Error as e:
        logger.error(f"Failed to fetch meetings from bronze: {e}")
        raise


def calculate_round_numbers(meetings: List[Dict]) -> Dict[str, int]:
    """
    Calculate round numbers for meetings.
    
    Only meetings with "Grand Prix" in the name are counted.
    Round numbers are sequential within each season, ordered by date_start.
    Count restarts each year.
    
    Args:
        meetings: List of meeting dictionaries
        
    Returns:
        Dictionary mapping meeting_id -> round_number
    """
    # Filter to only Grand Prix meetings
    gp_meetings = [
        m for m in meetings
        if m.get('meeting_name') and 'Grand Prix' in m['meeting_name']
    ]
    
    if not gp_meetings:
        logger.info("No Grand Prix meetings found for round number calculation")
        return {}
    
    # Group by season and sort by date_start
    by_season = defaultdict(list)
    
    for meeting in gp_meetings:
        try:
            season = int(meeting['season'])
            by_season[season].append(meeting)
        except (ValueError, TypeError):
            logger.warning(f"Invalid season for meeting: {meeting.get('meeting_name')}")
            continue
    
    # Sort meetings within each season by date_start
    for season in by_season:
        by_season[season].sort(key=lambda m: m.get('date_start', ''))
    
    # Assign round numbers
    round_map = {}
    for season in sorted(by_season.keys()):
        season_meetings = by_season[season]
        for round_num, meeting in enumerate(season_meetings, start=1):
            meeting_id = generate_meeting_id(
                int(meeting['season']),
                meeting['meeting_name']
            )
            if meeting_id:
                round_map[meeting_id] = round_num
    
    logger.info(f"Calculated round numbers for {len(round_map)} Grand Prix meetings")
    return round_map


def upsert_meetings(conn, meetings: List[Dict], circuit_id_map: Dict[str, str], round_map: Dict[str, int]) -> int:
    """
    Upsert meetings into silver.meetings table.
    
    Args:
        conn: Database connection
        meetings: List of meeting records from bronze
        circuit_id_map: Mapping of openf1_circuit_key -> circuit_id
        round_map: Mapping of meeting_id -> round_number
        
    Returns:
        Number of records upserted
    """
    if not meetings:
        logger.warning("No meetings to upsert")
        return 0
    
    # Note: COALESCE for openf1_meeting_key ensures that:
    # - If a future meeting exists with NULL openf1_meeting_key, the incoming value fills it in
    # - If an existing meeting already has openf1_meeting_key, we keep it (don't overwrite with NULL)
    upsert_sql = """
        INSERT INTO silver.meetings (
            meeting_id,
            openf1_meeting_key,
            circuit_id,
            meeting_name,
            season,
            meeting_official_name,
            date_start,
            round_number
        ) VALUES (
            %(meeting_id)s,
            %(openf1_meeting_key)s,
            %(circuit_id)s,
            %(meeting_name)s,
            %(season)s,
            %(meeting_official_name)s,
            %(date_start)s,
            %(round_number)s
        )
        ON CONFLICT (meeting_id) 
        DO UPDATE SET
            openf1_meeting_key = COALESCE(EXCLUDED.openf1_meeting_key, silver.meetings.openf1_meeting_key),
            circuit_id = EXCLUDED.circuit_id,
            meeting_name = EXCLUDED.meeting_name,
            season = EXCLUDED.season,
            meeting_official_name = EXCLUDED.meeting_official_name,
            date_start = EXCLUDED.date_start,
            round_number = EXCLUDED.round_number
    """
    
    try:
        with conn.cursor() as cur:
            upsert_records = []
            skipped = 0
            
            for meeting in meetings:
                # Parse season
                try:
                    season = int(meeting['season'])
                except (ValueError, TypeError):
                    logger.warning(f"Invalid season for meeting: {meeting.get('meeting_name')}")
                    skipped += 1
                    continue
                
                # Generate meeting_id
                meeting_id = generate_meeting_id(season, meeting['meeting_name'])
                if not meeting_id:
                    logger.warning(f"Skipping meeting due to missing required fields: {meeting.get('meeting_name')}")
                    skipped += 1
                    continue
                
                # Resolve circuit_id
                circuit_key = str(meeting['openf1_circuit_key']) if meeting.get('openf1_circuit_key') else None
                circuit_id = circuit_id_map.get(circuit_key) if circuit_key else None
                
                if not circuit_id:
                    logger.warning(
                        f"Circuit ID not found for openf1_circuit_key '{circuit_key}'. "
                        f"Skipping meeting {meeting_id}"
                    )
                    skipped += 1
                    continue
                
                # Parse date_start
                date_start = parse_date_start(meeting['date_start'])
                if not date_start:
                    logger.warning(f"Could not parse date_start for meeting {meeting_id}. Skipping.")
                    skipped += 1
                    continue
                
                # Get round_number (may be None for non-GP meetings)
                round_number = round_map.get(meeting_id)
                
                upsert_records.append({
                    'meeting_id': meeting_id,
                    'openf1_meeting_key': meeting['openf1_meeting_key'],
                    'circuit_id': circuit_id,
                    'meeting_name': meeting['meeting_name'],
                    'season': season,
                    'meeting_official_name': meeting.get('meeting_official_name'),
                    'date_start': date_start,
                    'round_number': round_number
                })
            
            if not upsert_records:
                logger.warning("No valid meetings to upsert after validation")
                return 0
            
            cur.executemany(upsert_sql, upsert_records)
            conn.commit()
            upserted_count = len(upsert_records)
            logger.info(f"Successfully upserted {upserted_count} meetings into silver.meetings")
            if skipped > 0:
                logger.warning(f"Skipped {skipped} meetings due to validation issues")
            return upserted_count
            
    except psycopg.Error as e:
        conn.rollback()
        logger.error(f"Database upsert failed: {e}")
        raise


def main():
    """Main upsert function."""
    logger.info("Starting meetings upsert from bronze.meetings_raw to silver.meetings")
    
    conn = get_db_connection()
    
    try:
        # Get circuit ID mapping
        logger.info("Loading circuit ID mapping...")
        circuit_id_map = get_circuit_id_map(conn)
        logger.info(f"Loaded {len(circuit_id_map)} circuit mappings")
        
        if not circuit_id_map:
            logger.error("No circuits found in silver.circuits. Please run upsert_circuits.py first.")
            return
        
        # Get meetings from bronze
        logger.info("Fetching meetings from bronze.meetings_raw...")
        meetings = get_meetings_from_bronze(conn)
        
        if not meetings:
            logger.warning("No meetings found in bronze.meetings_raw")
            return
        
        # Calculate round numbers
        logger.info("Calculating round numbers for Grand Prix meetings...")
        round_map = calculate_round_numbers(meetings)
        
        # Upsert meetings
        logger.info("Upserting meetings into silver.meetings...")
        upserted = upsert_meetings(conn, meetings, circuit_id_map, round_map)
        
        logger.info(f"Upsert complete: {upserted} meetings upserted")
    
    finally:
        conn.close()


if __name__ == "__main__":
    main()

