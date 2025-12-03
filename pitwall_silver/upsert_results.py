#!/usr/bin/env python3
"""
Upsert results data from bronze.results_raw and bronze.starting_grid_raw into silver.results.

Resolves session_id and driver_id, derives status from dnf/dns/dsq, maps starting grid data
from qualifying sessions, and derives best_lap_ms and fastest_lap from laps table.
"""

import os
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime

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


def parse_int(value: Optional[str]) -> Optional[int]:
    """Parse string to int, return None if invalid."""
    if value is None or value.strip() == '':
        return None
    try:
        return int(value)
    except ValueError:
        return None


def parse_boolean(value: Optional[str]) -> bool:
    """Parse string to boolean, return False if invalid."""
    if value is None or value.strip() == '':
        return False
    value_lower = value.strip().lower()
    return value_lower in ('true', 't', '1', 'yes', 'y')


def convert_seconds_to_ms(seconds_str: Optional[str]) -> Optional[int]:
    """Convert seconds (as string) to milliseconds (as int)."""
    if not seconds_str or seconds_str.strip() == '':
        return None
    try:
        seconds = float(seconds_str)
        return int(seconds * 1000)
    except (ValueError, TypeError):
        return None


def derive_status(dnf: bool, dns: bool, dsq: bool) -> str:
    """
    Derive status enum from dnf, dns, dsq booleans.
    
    Mapping:
    - dnf=True → 'dnf'
    - dns=True → 'dns'
    - dsq=True → 'dsq'
    - none=True → 'finished'
    - multiple=True → 'nc'
    """
    true_count = sum([dnf, dns, dsq])
    
    if true_count > 1:
        return 'nc'  # Not classified - multiple flags
    elif dnf:
        return 'dnf'
    elif dns:
        return 'dns'
    elif dsq:
        return 'dsq'
    else:
        return 'finished'


def get_driver_id_map(conn) -> Dict[Tuple[str, int], str]:
    """
    Get a mapping of (openf1_session_key, driver_number) -> driver_id from driver_id_by_session view.
    """
    driver_id_map = {}
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT openf1_session_key, driver_number, driver_id
                FROM silver.driver_id_by_session
            """)
            for row in cur.fetchall():
                key = (str(row[0]), row[1])
                driver_id_map[key] = row[2]
        logger.info(f"Loaded {len(driver_id_map)} driver_id mappings")
    except psycopg.Error as e:
        logger.error(f"Failed to fetch driver_id mappings: {e}")
        raise
    return driver_id_map


def get_qualifying_session_map(conn) -> Dict[str, str]:
    """
    Get a mapping of race/sprint session_id -> qualifying session openf1_session_key.
    
    For race sessions: finds most recent 'quali' session before the race.
    For sprint sessions: finds most recent 'sprint_quali' session before the sprint.
    
    Returns:
        Dictionary mapping (race/sprint session_id) -> (qualifying openf1_session_key)
    """
    quali_map = {}
    try:
        with conn.cursor() as cur:
            # For race sessions, find the most recent quali session before the race
            cur.execute("""
                SELECT 
                    race.session_id AS race_session_id,
                    quali.openf1_session_key AS quali_session_key
                FROM silver.sessions race
                INNER JOIN silver.meetings m ON race.meeting_id = m.meeting_id
                INNER JOIN silver.sessions quali ON m.meeting_id = quali.meeting_id
                WHERE race.session_type = 'race'
                  AND quali.session_type = 'quali'
                  AND quali.start_time < race.start_time
                ORDER BY race.start_time, quali.start_time DESC
            """)
            
            for row in cur.fetchall():
                race_session_id = row[0]
                quali_session_key = str(row[1])
                # Keep the most recent quali (last one wins due to ORDER BY)
                quali_map[race_session_id] = quali_session_key
            
            # For sprint sessions, find the most recent sprint_quali session before the sprint
            cur.execute("""
                SELECT 
                    sprint.session_id AS sprint_session_id,
                    sprint_quali.openf1_session_key AS sprint_quali_session_key
                FROM silver.sessions sprint
                INNER JOIN silver.meetings m ON sprint.meeting_id = m.meeting_id
                INNER JOIN silver.sessions sprint_quali ON m.meeting_id = sprint_quali.meeting_id
                WHERE sprint.session_type = 'sprint'
                  AND sprint_quali.session_type = 'sprint_quali'
                  AND sprint_quali.start_time < sprint.start_time
                ORDER BY sprint.start_time, sprint_quali.start_time DESC
            """)
            
            for row in cur.fetchall():
                sprint_session_id = row[0]
                sprint_quali_session_key = str(row[1])
                # Keep the most recent sprint_quali (last one wins due to ORDER BY)
                quali_map[sprint_session_id] = sprint_quali_session_key
            
        logger.info(f"Loaded {len(quali_map)} qualifying session mappings")
    except psycopg.Error as e:
        logger.error(f"Failed to fetch qualifying session mappings: {e}")
        raise
    return quali_map


def get_starting_grid_map(conn, quali_session_keys: List[str]) -> Dict[Tuple[str, int], Dict[str, Optional[int]]]:
    """
    Get starting grid data from bronze.starting_grid_raw for the given qualifying session keys.
    
    Returns:
        Dictionary mapping (openf1_session_key, driver_number) -> {grid_position, quali_lap_ms}
    """
    if not quali_session_keys:
        return {}
    
    starting_grid_map = {}
    try:
        with conn.cursor() as cur:
            # Use ANY for array matching
            placeholders = ','.join(['%s'] * len(quali_session_keys))
            cur.execute(f"""
                SELECT 
                    openf1_session_key,
                    driver_number,
                    position,
                    lap_duration_s
                FROM bronze.starting_grid_raw
                WHERE openf1_session_key IN ({placeholders})
                  AND driver_number IS NOT NULL
            """, quali_session_keys)
            
            for row in cur.fetchall():
                session_key = str(row[0])
                driver_number = parse_int(row[1])
                if driver_number is None:
                    continue
                
                grid_position = parse_int(row[2])
                quali_lap_ms = convert_seconds_to_ms(row[3])
                
                key = (session_key, driver_number)
                starting_grid_map[key] = {
                    'grid_position': grid_position,
                    'quali_lap_ms': quali_lap_ms
                }
            
        logger.info(f"Loaded {len(starting_grid_map)} starting grid records")
    except psycopg.Error as e:
        logger.error(f"Failed to fetch starting grid data: {e}")
        raise
    return starting_grid_map


def get_best_lap_map(conn) -> Dict[Tuple[str, str], Optional[int]]:
    """
    Get best lap time (in ms) for each (session_id, driver_id) combination.
    
    Returns:
        Dictionary mapping (session_id, driver_id) -> best_lap_ms
    """
    best_lap_map = {}
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    session_id,
                    driver_id,
                    MIN(lap_duration_ms) AS best_lap_ms
                FROM silver.laps
                WHERE lap_duration_ms IS NOT NULL
                  AND is_valid = TRUE
                GROUP BY session_id, driver_id
            """)
            
            for row in cur.fetchall():
                key = (row[0], row[1])
                best_lap_map[key] = row[2] if row[2] is not None else None
            
        logger.info(f"Loaded {len(best_lap_map)} best lap records")
    except psycopg.Error as e:
        logger.error(f"Failed to fetch best lap data: {e}")
        raise
    return best_lap_map


def get_fastest_lap_map(conn) -> Dict[str, Optional[int]]:
    """
    Get fastest lap time (in ms) for each session_id.
    
    Returns:
        Dictionary mapping session_id -> fastest_lap_ms
    """
    fastest_lap_map = {}
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    session_id,
                    MIN(lap_duration_ms) AS fastest_lap_ms
                FROM silver.laps
                WHERE lap_duration_ms IS NOT NULL
                  AND is_valid = TRUE
                GROUP BY session_id
            """)
            
            for row in cur.fetchall():
                fastest_lap_map[row[0]] = row[1] if row[1] is not None else None
            
        logger.info(f"Loaded {len(fastest_lap_map)} fastest lap records")
    except psycopg.Error as e:
        logger.error(f"Failed to fetch fastest lap data: {e}")
        raise
    return fastest_lap_map


def get_results_from_bronze(conn) -> List[Dict]:
    """
    Get results records from bronze.results_raw with resolved session_id.
    """
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT DISTINCT
                    rr.openf1_session_key,
                    rr.driver_number,
                    rr.position,
                    rr.gap_to_leader_s,
                    rr.duration_s,
                    rr.laps_completed,
                    rr.dnf,
                    rr.dns,
                    rr.dsq,
                    s.session_id
                FROM bronze.results_raw rr
                INNER JOIN silver.sessions s 
                    ON rr.openf1_session_key = s.openf1_session_key
                WHERE rr.openf1_session_key IS NOT NULL
                  AND rr.driver_number IS NOT NULL
                ORDER BY s.session_id, rr.position
            """)
            
            records = []
            for row in cur.fetchall():
                records.append({
                    'openf1_session_key': row[0],
                    'driver_number': row[1],
                    'position': row[2],
                    'gap_to_leader_s': row[3],
                    'duration_s': row[4],
                    'laps_completed': row[5],
                    'dnf': row[6],
                    'dns': row[7],
                    'dsq': row[8],
                    'session_id': row[9]
                })
            
            logger.info(f"Found {len(records)} results records in bronze.results_raw with resolved session_id")
            return records
    except psycopg.Error as e:
        logger.error(f"Failed to fetch results from bronze: {e}")
        raise


def upsert_results(conn, records: List[Dict], driver_id_map: Dict[Tuple[str, int], str],
                   quali_map: Dict[str, str], starting_grid_map: Dict[Tuple[str, int], Dict[str, Optional[int]]],
                   best_lap_map: Dict[Tuple[str, str], Optional[int]], fastest_lap_map: Dict[str, Optional[int]]) -> int:
    """
    Upsert results records into silver.results table.
    """
    if not records:
        logger.warning("No results records to upsert")
        return 0
    
    insert_sql = """
        INSERT INTO silver.results (
            session_id,
            driver_id,
            finish_position,
            gap_to_leader_ms,
            duration_ms,
            laps_completed,
            status,
            points,
            best_lap_ms,
            fastest_lap,
            grid_position,
            quali_lap_ms
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s::silver.status_enum, %s, %s, %s, %s, %s
        )
        ON CONFLICT (session_id, driver_id) DO UPDATE SET
            finish_position = EXCLUDED.finish_position,
            gap_to_leader_ms = EXCLUDED.gap_to_leader_ms,
            duration_ms = EXCLUDED.duration_ms,
            laps_completed = EXCLUDED.laps_completed,
            status = EXCLUDED.status,
            best_lap_ms = EXCLUDED.best_lap_ms,
            fastest_lap = EXCLUDED.fastest_lap,
            grid_position = EXCLUDED.grid_position,
            quali_lap_ms = EXCLUDED.quali_lap_ms
    """
    
    upserted_count = 0
    skipped_count = 0
    batch_size = 1000

    try:
        with conn.cursor() as cur:
            inserts_data = []
            
            for record in records:
                # Parse driver_number
                driver_number_parsed = parse_int(record['driver_number'])
                if driver_number_parsed is None:
                    logger.warning(f"Skipping record due to invalid driver_number: {record.get('driver_number')}")
                    skipped_count += 1
                    continue
                
                # Resolve driver_id
                driver_id_key = (record['openf1_session_key'], driver_number_parsed)
                driver_id = driver_id_map.get(driver_id_key)
                if not driver_id:
                    logger.debug(f"Skipping record due to unresolved driver_id for session {record.get('openf1_session_key')}, driver {driver_number_parsed}")
                    skipped_count += 1
                    continue
                
                # Parse and convert fields
                finish_position = parse_int(record['position'])
                gap_to_leader_ms = convert_seconds_to_ms(record['gap_to_leader_s'])
                duration_ms = convert_seconds_to_ms(record['duration_s'])
                laps_completed = parse_int(record['laps_completed'])
                
                # Derive status
                dnf = parse_boolean(record['dnf'])
                dns = parse_boolean(record['dns'])
                dsq = parse_boolean(record['dsq'])
                status = derive_status(dnf, dns, dsq)
                
                # Get best_lap_ms and fastest_lap
                best_lap_key = (record['session_id'], driver_id)
                best_lap_ms = best_lap_map.get(best_lap_key)
                
                fastest_lap_ms = fastest_lap_map.get(record['session_id'])
                fastest_lap = (best_lap_ms is not None and 
                               fastest_lap_ms is not None and 
                               best_lap_ms == fastest_lap_ms)
                
                # Get starting grid data (if applicable)
                grid_position = None
                quali_lap_ms = None
                
                # Check if this is a race or sprint session
                quali_session_key = quali_map.get(record['session_id'])
                if quali_session_key:
                    starting_grid_key = (quali_session_key, driver_number_parsed)
                    grid_data = starting_grid_map.get(starting_grid_key)
                    if grid_data:
                        grid_position = grid_data.get('grid_position')
                        quali_lap_ms = grid_data.get('quali_lap_ms')
                
                # Points will be set in a separate script, default to 0 for now
                points = 0.0
                
                # Insert/update record
                inserts_data.append((
                    record['session_id'],
                    driver_id,
                    finish_position,
                    gap_to_leader_ms,
                    duration_ms,
                    laps_completed,
                    status,
                    points,
                    best_lap_ms,
                    fastest_lap,
                    grid_position,
                    quali_lap_ms
                ))
            
            logger.info(f"Will upsert {len(inserts_data)} records")
            
            # Perform batch inserts/updates
            if inserts_data:
                logger.info("Upserting results records...")
                for i in range(0, len(inserts_data), batch_size):
                    batch = inserts_data[i:i + batch_size]
                    cur.executemany(insert_sql, batch)
                    upserted_count += len(batch)
                conn.commit()
                logger.info(f"  Upserted {upserted_count} records")
            
            if skipped_count > 0:
                logger.warning(f"Skipped {skipped_count} records due to validation issues")
            return upserted_count
                    
    except psycopg.Error as e:
        conn.rollback()
        logger.error(f"Database upsert failed: {e}")
        raise


def main():
    """Main upsert function."""
    logger.info("Starting results upsert from bronze.results_raw to silver.results")
    
    conn = get_db_connection()
    
    try:
        # Load driver_id mappings
        logger.info("Loading driver_id mappings...")
        driver_id_map = get_driver_id_map(conn)
        
        # Load qualifying session mappings
        logger.info("Loading qualifying session mappings...")
        quali_map = get_qualifying_session_map(conn)
        
        # Get unique qualifying session keys for starting grid lookup
        quali_session_keys = list(set(quali_map.values()))
        logger.info(f"Found {len(quali_session_keys)} unique qualifying sessions")
        
        # Load starting grid data
        logger.info("Loading starting grid data...")
        starting_grid_map = get_starting_grid_map(conn, quali_session_keys)
        
        # Load best lap and fastest lap data
        logger.info("Loading best lap and fastest lap data...")
        best_lap_map = get_best_lap_map(conn)
        fastest_lap_map = get_fastest_lap_map(conn)
        
        # Get results records from bronze with resolved session_id
        logger.info("Fetching results records from bronze.results_raw with resolved session_id...")
        records = get_results_from_bronze(conn)
        
        if not records:
            logger.warning("No results records found in bronze.results_raw")
            return
        
        # Upsert results
        logger.info("Upserting results records into silver.results...")
        upserted = upsert_results(conn, records, driver_id_map, quali_map, starting_grid_map,
                                  best_lap_map, fastest_lap_map)
        
        logger.info("="*60)
        logger.info("RESULTS UPSERT COMPLETE")
        logger.info("="*60)
        logger.info(f"Upserted: {upserted} records")
        
        # Show summary
        logger.info("\nSummary:")
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) as total_records,
                       COUNT(DISTINCT session_id) as unique_sessions,
                       COUNT(DISTINCT driver_id) as unique_drivers,
                       COUNT(CASE WHEN status = 'finished' THEN 1 END) as finished,
                       COUNT(CASE WHEN fastest_lap = TRUE THEN 1 END) as fastest_lap_count,
                       COUNT(CASE WHEN grid_position IS NOT NULL THEN 1 END) as with_grid_position
                FROM silver.results
            """)
            total, sessions, drivers, finished, fastest_lap_count, with_grid = cur.fetchone()
            logger.info(f"  Total records in silver.results: {total}")
            logger.info(f"  Unique sessions: {sessions}")
            logger.info(f"  Unique drivers: {drivers}")
            logger.info(f"  Finished: {finished}")
            logger.info(f"  Fastest lap records: {fastest_lap_count}")
            logger.info(f"  Records with grid position: {with_grid}")

        logger.info("\nSample Records:")
        with conn.cursor() as cur:
            cur.execute("""
                SELECT session_id, driver_id, finish_position, status, fastest_lap, grid_position
                FROM silver.results
                ORDER BY session_id, finish_position
                LIMIT 5
            """)
            for row in cur.fetchall():
                logger.info(f"  {row[0]} | {row[1]} | Position: {row[2]} | Status: {row[3]} | Fastest: {row[4]} | Grid: {row[5]}")
    
    finally:
        conn.close()


if __name__ == "__main__":
    main()


