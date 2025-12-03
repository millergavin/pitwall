#!/usr/bin/env python3
"""
Upsert sessions data from bronze.sessions_raw into silver.sessions.

Maps from bronze.sessions_raw:
- openf1_session_key → openf1_session_key
- date_start → start_time (converted to TIMESTAMPTZ)
- date_end → end_time (converted to TIMESTAMPTZ)
- session_name → session_name

Resolves meeting_id by joining to silver.meetings
Generates session_id using format: ses:{circuit_short_name}-{season}-{session_type}-{openf1_session_key}
Derives session_type and points_awarding from session_name
Derives scheduled_laps from circuits (race_laps or sprint_laps)
Derives duration_min from start_time and end_time
"""

import os
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta

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

# Session name to session_type mapping
SESSION_TYPE_MAP = {
    'Practice 1': 'p1',
    'Practice 2': 'p2',
    'Practice 3': 'p3',
    'Qualifying': 'quali',
    'Sprint Qualifying': 'sprint_quali',
    'Sprint Shootout': 'sprint_quali',
    'Sprint': 'sprint',
    'Race': 'race',
}

# Session type to points_awarding mapping
POINTS_AWARDING_MAP = {
    'p1': 'none',
    'p2': 'none',
    'p3': 'none',
    'quali': 'none',
    'sprint_quali': 'none',
    'sprint': 'sprint',
    'race': 'race',
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


def get_meeting_info_map(conn) -> Dict[str, Dict]:
    """
    Get a mapping of openf1_meeting_key to meeting info.
    
    Returns:
        Dictionary mapping openf1_meeting_key -> {meeting_id, season, circuit_id}
    """
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    m.openf1_meeting_key,
                    m.meeting_id,
                    m.season,
                    m.circuit_id
                FROM silver.meetings m
            """)
            result = {}
            for row in cur.fetchall():
                result[str(row[0])] = {
                    'meeting_id': row[1],
                    'season': row[2],
                    'circuit_id': row[3]
                }
            return result
    except psycopg.Error as e:
        logger.error(f"Failed to fetch meeting info mapping: {e}")
        return {}


def get_circuit_info_map(conn) -> Dict[str, Dict]:
    """
    Get a mapping of circuit_id to circuit info.
    
    Returns:
        Dictionary mapping circuit_id -> {circuit_short_name, race_laps, sprint_laps}
    """
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    circuit_id,
                    circuit_short_name,
                    race_laps,
                    sprint_laps
                FROM silver.circuits
            """)
            result = {}
            for row in cur.fetchall():
                result[row[0]] = {
                    'circuit_short_name': row[1],
                    'race_laps': row[2],
                    'sprint_laps': row[3]
                }
            return result
    except psycopg.Error as e:
        logger.error(f"Failed to fetch circuit info mapping: {e}")
        return {}


def derive_session_type(session_name: Optional[str]) -> Optional[str]:
    """
    Derive session_type from session_name.
    
    Args:
        session_name: Session name from bronze table
        
    Returns:
        Session type enum value or None if not found
    """
    if not session_name:
        return None
    
    # Try exact match first
    if session_name in SESSION_TYPE_MAP:
        return SESSION_TYPE_MAP[session_name]
    
    # Try case-insensitive match
    session_name_lower = session_name.lower()
    for key, value in SESSION_TYPE_MAP.items():
        if key.lower() == session_name_lower:
            return value
    
    # Try partial match (e.g., "Practice 1" in "Practice 1 - FP1")
    for key, value in SESSION_TYPE_MAP.items():
        if key.lower() in session_name_lower:
            return value
    
    logger.warning(f"Could not derive session_type from session_name: {session_name}")
    return None


def derive_points_awarding(session_type: Optional[str]) -> str:
    """
    Derive points_awarding from session_type.
    
    Args:
        session_type: Session type enum value
        
    Returns:
        Points awarding enum value (defaults to 'none')
    """
    if not session_type:
        return 'none'
    
    return POINTS_AWARDING_MAP.get(session_type, 'none')


def generate_session_id(circuit_short_name: Optional[str], season: Optional[int], 
                        session_type: Optional[str], openf1_session_key: Optional[str]) -> Optional[str]:
    """
    Generate session_id using format: ses:{circuit_short_name}-{season}-{session_type}-{openf1_session_key}
    
    Args:
        circuit_short_name: Circuit short name
        season: Season year
        session_type: Session type enum value
        openf1_session_key: OpenF1 session key
        
    Returns:
        Generated session_id or None if required fields are missing
    """
    if not circuit_short_name or season is None or not session_type or not openf1_session_key:
        return None
    
    # Sanitize circuit_short_name for use in ID
    sanitized_circuit = circuit_short_name.replace(' ', '-').replace('/', '-').replace('\\', '-')
    sanitized_circuit = ''.join(c if c.isalnum() or c == '-' else '' for c in sanitized_circuit)
    
    return f"ses:{sanitized_circuit}-{season}-{session_type}-{openf1_session_key}"


def parse_timestamp(date_str: Optional[str]) -> Optional[datetime]:
    """
    Parse timestamp from TEXT to TIMESTAMPTZ.
    
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
    
    logger.warning(f"Could not parse timestamp: {date_str}")
    return None


def calculate_duration_min(start_time: Optional[datetime], end_time: Optional[datetime]) -> Optional[int]:
    """
    Calculate duration in minutes from start_time and end_time.
    
    Args:
        start_time: Session start time
        end_time: Session end time
        
    Returns:
        Duration in minutes or None if invalid
    """
    if not start_time or not end_time:
        return None
    
    if end_time < start_time:
        logger.warning(f"End time {end_time} is before start time {start_time}")
        return None
    
    delta = end_time - start_time
    return int(delta.total_seconds() / 60)


def get_scheduled_laps(session_type: Optional[str], circuit_info: Optional[Dict]) -> Optional[int]:
    """
    Get scheduled laps from circuit info based on session_type.
    
    Args:
        session_type: Session type enum value
        circuit_info: Circuit info dictionary with race_laps and sprint_laps
        
    Returns:
        Scheduled laps or None if not applicable
    """
    if not session_type or not circuit_info:
        return None
    
    if session_type == 'race':
        return circuit_info.get('race_laps')
    elif session_type == 'sprint':
        return circuit_info.get('sprint_laps')
    else:
        return None


def get_sessions_from_bronze(conn) -> List[Dict]:
    """
    Get all session records from bronze.sessions_raw.
    
    Returns:
        List of session dictionaries
    """
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    openf1_session_key,
                    openf1_meeting_key,
                    date_start,
                    date_end,
                    session_name
                FROM bronze.sessions_raw
                WHERE openf1_session_key IS NOT NULL
                  AND openf1_meeting_key IS NOT NULL
                  AND date_start IS NOT NULL
                  AND date_end IS NOT NULL
                  AND session_name IS NOT NULL
                ORDER BY date_start
            """)
            
            sessions = []
            for row in cur.fetchall():
                sessions.append({
                    'openf1_session_key': row[0],
                    'openf1_meeting_key': row[1],
                    'date_start': row[2],
                    'date_end': row[3],
                    'session_name': row[4]
                })
            
            logger.info(f"Found {len(sessions)} sessions in bronze.sessions_raw")
            return sessions
    except psycopg.Error as e:
        logger.error(f"Failed to fetch sessions from bronze: {e}")
        raise


def upsert_sessions(conn, sessions: List[Dict], meeting_info_map: Dict[str, Dict], 
                   circuit_info_map: Dict[str, Dict]) -> int:
    """
    Upsert sessions into silver.sessions table.
    
    Args:
        conn: Database connection
        sessions: List of session records from bronze
        meeting_info_map: Mapping of openf1_meeting_key -> meeting info
        circuit_info_map: Mapping of circuit_id -> circuit info
        
    Returns:
        Number of records upserted
    """
    if not sessions:
        logger.warning("No sessions to upsert")
        return 0
    
    upsert_sql = """
        INSERT INTO silver.sessions (
            session_id,
            meeting_id,
            openf1_session_key,
            start_time,
            end_time,
            session_name,
            session_type,
            scheduled_laps,
            points_awarding,
            duration_min
        ) VALUES (
            %(session_id)s,
            %(meeting_id)s,
            %(openf1_session_key)s,
            %(start_time)s,
            %(end_time)s,
            %(session_name)s,
            %(session_type)s::silver.session_type_enum,
            %(scheduled_laps)s,
            %(points_awarding)s::silver.points_awarding_enum,
            %(duration_min)s
        )
        ON CONFLICT (session_id) 
        DO UPDATE SET
            meeting_id = EXCLUDED.meeting_id,
            openf1_session_key = EXCLUDED.openf1_session_key,
            start_time = EXCLUDED.start_time,
            end_time = EXCLUDED.end_time,
            session_name = EXCLUDED.session_name,
            session_type = EXCLUDED.session_type,
            scheduled_laps = EXCLUDED.scheduled_laps,
            points_awarding = EXCLUDED.points_awarding,
            duration_min = EXCLUDED.duration_min
    """
    
    try:
        with conn.cursor() as cur:
            upsert_records = []
            skipped = 0
            
            for session in sessions:
                # Resolve meeting info
                meeting_key = str(session['openf1_meeting_key'])
                meeting_info = meeting_info_map.get(meeting_key)
                
                if not meeting_info:
                    logger.warning(
                        f"Meeting not found for openf1_meeting_key '{meeting_key}'. "
                        f"Skipping session {session.get('openf1_session_key')}"
                    )
                    skipped += 1
                    continue
                
                meeting_id = meeting_info['meeting_id']
                season = meeting_info['season']
                circuit_id = meeting_info['circuit_id']
                
                # Get circuit info
                circuit_info = circuit_info_map.get(circuit_id)
                if not circuit_info:
                    logger.warning(
                        f"Circuit info not found for circuit_id '{circuit_id}'. "
                        f"Skipping session {session.get('openf1_session_key')}"
                    )
                    skipped += 1
                    continue
                
                circuit_short_name = circuit_info['circuit_short_name']
                
                # Derive session_type
                session_type = derive_session_type(session['session_name'])
                if not session_type:
                    logger.warning(
                        f"Could not derive session_type for session {session.get('openf1_session_key')}. "
                        f"Skipping."
                    )
                    skipped += 1
                    continue
                
                # Derive points_awarding
                points_awarding = derive_points_awarding(session_type)
                
                # Generate session_id
                session_id = generate_session_id(
                    circuit_short_name,
                    season,
                    session_type,
                    session['openf1_session_key']
                )
                
                if not session_id:
                    logger.warning(f"Skipping session due to missing required fields: {session.get('openf1_session_key')}")
                    skipped += 1
                    continue
                
                # Parse timestamps
                start_time = parse_timestamp(session['date_start'])
                end_time = parse_timestamp(session['date_end'])
                
                if not start_time or not end_time:
                    logger.warning(f"Could not parse timestamps for session {session_id}. Skipping.")
                    skipped += 1
                    continue
                
                # Calculate duration
                duration_min = calculate_duration_min(start_time, end_time)
                
                # Get scheduled_laps
                scheduled_laps = get_scheduled_laps(session_type, circuit_info)
                
                upsert_records.append({
                    'session_id': session_id,
                    'meeting_id': meeting_id,
                    'openf1_session_key': session['openf1_session_key'],
                    'start_time': start_time,
                    'end_time': end_time,
                    'session_name': session['session_name'],
                    'session_type': session_type,
                    'scheduled_laps': scheduled_laps,
                    'points_awarding': points_awarding,
                    'duration_min': duration_min
                })
            
            if not upsert_records:
                logger.warning("No valid sessions to upsert after validation")
                return 0
            
            cur.executemany(upsert_sql, upsert_records)
            conn.commit()
            upserted_count = len(upsert_records)
            logger.info(f"Successfully upserted {upserted_count} sessions into silver.sessions")
            if skipped > 0:
                logger.warning(f"Skipped {skipped} sessions due to validation issues")
            return upserted_count
            
    except psycopg.Error as e:
        conn.rollback()
        logger.error(f"Database upsert failed: {e}")
        raise


def main():
    """Main upsert function."""
    logger.info("Starting sessions upsert from bronze.sessions_raw to silver.sessions")
    
    conn = get_db_connection()
    
    try:
        # Get meeting info mapping
        logger.info("Loading meeting info mapping...")
        meeting_info_map = get_meeting_info_map(conn)
        logger.info(f"Loaded {len(meeting_info_map)} meeting mappings")
        
        if not meeting_info_map:
            logger.error("No meetings found in silver.meetings. Please run upsert_meetings.py first.")
            return
        
        # Get circuit info mapping
        logger.info("Loading circuit info mapping...")
        circuit_info_map = get_circuit_info_map(conn)
        logger.info(f"Loaded {len(circuit_info_map)} circuit mappings")
        
        if not circuit_info_map:
            logger.error("No circuits found in silver.circuits. Please run upsert_circuits.py first.")
            return
        
        # Get sessions from bronze
        logger.info("Fetching sessions from bronze.sessions_raw...")
        sessions = get_sessions_from_bronze(conn)
        
        if not sessions:
            logger.warning("No sessions found in bronze.sessions_raw")
            return
        
        # Upsert sessions
        logger.info("Upserting sessions into silver.sessions...")
        upserted = upsert_sessions(conn, sessions, meeting_info_map, circuit_info_map)
        
        logger.info(f"Upsert complete: {upserted} sessions upserted")
    
    finally:
        conn.close()


if __name__ == "__main__":
    main()


