#!/usr/bin/env python3
"""
Calculate and assign championship points to drivers based on finishing position,
race completion, fastest lap achievements, and F1 safety car regulations.

This script processes points per session after all results rows have been upserted.
It reads from results, sessions, meetings, race_control, and points_system tables.
"""

import os
import logging
from typing import Dict, List, Optional, Tuple
from decimal import Decimal

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


def get_completion_band(completed_laps: int, scheduled_laps: Optional[int]) -> str:
    """
    Map completed-lap ratio to completion band.
    
    Returns:
        Completion band enum value: '0_to_25_PCT', '25_to_50_PCT', '50_to_75_PCT', or '100_PCT'
    """
    if scheduled_laps is None or scheduled_laps == 0:
        # Treat as fully completed
        return '100_PCT'
    
    ratio = completed_laps / scheduled_laps
    
    if ratio >= 0.75:
        return '100_PCT'
    elif ratio >= 0.50:
        return '50_to_75_PCT'
    elif ratio >= 0.25:
        return '25_to_50_PCT'
    else:
        return '0_to_25_PCT'


def has_minimum_race_laps(conn, session_id: str, completed_laps: int) -> bool:
    """
    Determine if session has minimum race laps (≥2 race laps) using heuristic.
    
    For completion_band = '0_to_25_PCT', FIA rules require at least 2 "race laps"
    (not entirely behind Safety Car / VSC). We approximate this using race_control messages.
    
    Returns:
        True if session has minimum race laps, False otherwise
    """
    # Default behavior
    if completed_laps >= 3:
        return True
    if completed_laps < 2:
        return False
    
    # Ambiguous case: completed_laps = 2
    # Check race_control for green flags and DRS enabled
    try:
        with conn.cursor() as cur:
            # Check for track green flag (not just pit exit)
            cur.execute("""
                SELECT COUNT(*) > 0
                FROM silver.race_control
                WHERE session_id = %s
                  AND category = 'Flag'
                  AND flag = 'GREEN'
                  AND scope = 'Track'
                  AND message NOT ILIKE '%PIT EXIT OPEN%'
            """, (session_id,))
            has_track_green_flag = cur.fetchone()[0]
            
            # Check for DRS enabled
            cur.execute("""
                SELECT COUNT(*) > 0
                FROM silver.race_control
                WHERE session_id = %s
                  AND category = 'Drs'
                  AND message ILIKE '%DRS ENABLED%'
            """, (session_id,))
            has_race_drs_enabled = cur.fetchone()[0]
            
            # If either condition is true, assume minimum race laps
            return has_track_green_flag or has_race_drs_enabled
            
    except psycopg.Error as e:
        logger.warning(f"Error checking minimum race laps for session {session_id}: {e}")
        # Conservative: assume minimum race laps if we can't determine
        return True


def get_session_context(conn, session_id: str) -> Optional[Dict]:
    """
    Get session-level context: season, points_awarding, completed_laps, completion_band, has_minimum_race_laps.
    
    Returns:
        Dictionary with session context, or None if session not found
    """
    try:
        with conn.cursor() as cur:
            # Get session and meeting info
            # Derive completed_laps from silver.laps (max lap_number) if results.laps_completed is NULL
            cur.execute("""
                SELECT 
                    s.points_awarding,
                    s.scheduled_laps,
                    m.season,
                    COALESCE(
                        MAX(r.laps_completed),
                        (SELECT MAX(lap_number) FROM silver.laps WHERE session_id = %s AND is_valid = TRUE),
                        0
                    ) as completed_laps
                FROM silver.sessions s
                INNER JOIN silver.meetings m ON s.meeting_id = m.meeting_id
                LEFT JOIN silver.results r ON s.session_id = r.session_id
                WHERE s.session_id = %s
                GROUP BY s.points_awarding, s.scheduled_laps, m.season
            """, (session_id, session_id))
            
            row = cur.fetchone()
            if not row:
                return None
            
            points_awarding = row[0]
            scheduled_laps = row[1]
            season = row[2]
            completed_laps = row[3] if row[3] is not None else 0
            
            # Determine completion band
            completion_band = get_completion_band(completed_laps, scheduled_laps)
            
            # Determine has_minimum_race_laps (only needed for 0-25% band, but calculate for all)
            has_min_race_laps = has_minimum_race_laps(conn, session_id, completed_laps)
            
            return {
                'season': season,
                'points_awarding': points_awarding,
                'completed_laps': completed_laps,
                'scheduled_laps': scheduled_laps,
                'completion_band': completion_band,
                'has_minimum_race_laps': has_min_race_laps
            }
            
    except psycopg.Error as e:
        logger.error(f"Failed to get session context for {session_id}: {e}")
        return None


def get_points_system_map(conn) -> Dict[Tuple[int, str, str, Optional[int], Optional[str]], Decimal]:
    """
    Load all points_system rules into a map for quick lookup.
    
    Key: (season, race_type, completion_band, position, bonus)
    Value: points
    
    Returns:
        Dictionary mapping lookup key to points value
    """
    points_map = {}
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT season, race_type, completion_band, position, bonus, points
                FROM silver.points_system
            """)
            
            for row in cur.fetchall():
                key = (row[0], row[1], row[2], row[3], row[4])
                points_map[key] = Decimal(str(row[5]))
            
        logger.info(f"Loaded {len(points_map)} points system rules")
    except psycopg.Error as e:
        logger.error(f"Failed to load points system: {e}")
        raise
    return points_map


def get_session_results(conn, session_id: str) -> List[Dict]:
    """
    Get all results for a session, ordered by finish_position.
    
    Returns:
        List of result dictionaries
    """
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    session_id,
                    driver_id,
                    finish_position,
                    status,
                    fastest_lap,
                    points
                FROM silver.results
                WHERE session_id = %s
                ORDER BY finish_position NULLS LAST
            """, (session_id,))
            
            results = []
            for row in cur.fetchall():
                results.append({
                    'session_id': row[0],
                    'driver_id': row[1],
                    'finish_position': row[2],
                    'status': row[3],
                    'fastest_lap': row[4],
                    'points': float(row[5]) if row[5] is not None else 0.0
                })
            
            return results
    except psycopg.Error as e:
        logger.error(f"Failed to get results for session {session_id}: {e}")
        return []


def calculate_points_for_session(conn, session_id: str, context: Dict, points_map: Dict) -> Tuple[int, int]:
    """
    Calculate and assign points for all results in a session.
    
    Returns:
        Tuple of (updated_count, skipped_count)
    """
    # Check if points should be awarded for this session
    if context['points_awarding'] == 'none':
        # Set all points to 0 for this session
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE silver.results
                    SET points = 0.0
                    WHERE session_id = %s
                """, (session_id,))
                conn.commit()
                logger.debug(f"Session {session_id}: points_awarding = 'none', set all points to 0")
                return (cur.rowcount, 0)
        except psycopg.Error as e:
            conn.rollback()
            logger.error(f"Failed to update points for session {session_id}: {e}")
            return (0, 0)
    
    # Check minimum race laps gate for 0-25% completion band
    if (context['completion_band'] == '0_to_25_PCT' and 
        not context['has_minimum_race_laps']):
        # No points awarded for this session
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE silver.results
                    SET points = 0.0
                    WHERE session_id = %s
                """, (session_id,))
                conn.commit()
                logger.debug(f"Session {session_id}: 0-25% completion without minimum race laps, set all points to 0")
                return (cur.rowcount, 0)
        except psycopg.Error as e:
            conn.rollback()
            logger.error(f"Failed to update points for session {session_id}: {e}")
            return (0, 0)
    
    # Get results for this session
    results = get_session_results(conn, session_id)
    if not results:
        return (0, 0)
    
    # Prepare lookup keys
    season = context['season']
    race_type = context['points_awarding']
    completion_band = context['completion_band']
    
    # Check if fastest lap bonus exists for this season/race_type/completion_band
    fastest_lap_key = (season, race_type, completion_band, None, 'fastest_lap')
    fastest_lap_bonus = points_map.get(fastest_lap_key)
    
    updated_count = 0
    skipped_count = 0
    
    try:
        with conn.cursor() as cur:
            for result in results:
                # Step 1: Status check
                if result['status'] != 'finished':
                    # Set points to 0 for non-finished drivers
                    cur.execute("""
                        UPDATE silver.results
                        SET points = 0.0
                        WHERE session_id = %s AND driver_id = %s
                    """, (session_id, result['driver_id']))
                    updated_count += cur.rowcount
                    skipped_count += 1
                    continue
                
                # Step 2: Lookup base points from points_system
                finish_position = result['finish_position']
                base_points = Decimal('0.0')
                
                if finish_position is not None:
                    base_key = (season, race_type, completion_band, finish_position, None)
                    base_points = points_map.get(base_key, Decimal('0.0'))
                
                # Step 3: Apply fastest lap bonus
                bonus_points = Decimal('0.0')
                if (fastest_lap_bonus is not None and 
                    result['fastest_lap'] is True and 
                    finish_position is not None and 
                    finish_position <= 10):
                    # Driver qualifies for fastest lap bonus
                    bonus_points = fastest_lap_bonus
                
                total_points = float(base_points + bonus_points)
                
                # Update results.points
                cur.execute("""
                    UPDATE silver.results
                    SET points = %s
                    WHERE session_id = %s AND driver_id = %s
                """, (total_points, session_id, result['driver_id']))
                
                updated_count += cur.rowcount
                
                if total_points > 0:
                    logger.debug(f"  Driver {result['driver_id']}: Position {finish_position}, "
                               f"Base: {base_points}, Bonus: {bonus_points}, Total: {total_points}")
            
            conn.commit()
            
    except psycopg.Error as e:
        conn.rollback()
        logger.error(f"Failed to calculate points for session {session_id}: {e}")
        raise
    
    return (updated_count, skipped_count)


def get_all_sessions_with_results(conn) -> List[str]:
    """
    Get all unique session_ids that have results.
    
    Returns:
        List of session_id strings
    """
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT DISTINCT session_id
                FROM silver.results
                ORDER BY session_id
            """)
            
            return [row[0] for row in cur.fetchall()]
    except psycopg.Error as e:
        logger.error(f"Failed to get sessions with results: {e}")
        return []


def main():
    """Main points awarding function."""
    logger.info("Starting points awarding calculation")
    
    conn = get_db_connection()
    
    try:
        # Load points system rules
        logger.info("Loading points system rules...")
        points_map = get_points_system_map(conn)
        
        if not points_map:
            logger.warning("No points system rules found. Exiting.")
            return
        
        # Get all sessions with results
        logger.info("Getting sessions with results...")
        session_ids = get_all_sessions_with_results(conn)
        logger.info(f"Found {len(session_ids)} sessions with results")
        
        total_updated = 0
        total_skipped = 0
        sessions_processed = 0
        sessions_with_points = 0
        
        # Process each session
        for session_id in session_ids:
            # Get session context
            context = get_session_context(conn, session_id)
            if not context:
                logger.warning(f"Could not get context for session {session_id}, skipping")
                continue
            
            logger.info(f"Processing session {session_id}: "
                       f"season={context['season']}, "
                       f"points_awarding={context['points_awarding']}, "
                       f"completion_band={context['completion_band']}, "
                       f"completed_laps={context['completed_laps']}")
            
            # Calculate points for this session
            updated, skipped = calculate_points_for_session(conn, session_id, context, points_map)
            
            total_updated += updated
            total_skipped += skipped
            sessions_processed += 1
            
            # Check if any points were awarded
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT COUNT(*) FROM silver.results
                    WHERE session_id = %s AND points > 0
                """, (session_id,))
                if cur.fetchone()[0] > 0:
                    sessions_with_points += 1
        
        logger.info("="*60)
        logger.info("POINTS AWARDING COMPLETE")
        logger.info("="*60)
        logger.info(f"Sessions processed: {sessions_processed}")
        logger.info(f"Sessions with points awarded: {sessions_with_points}")
        logger.info(f"Total results updated: {total_updated}")
        logger.info(f"Total results skipped (non-finished): {total_skipped}")
        
        # Show summary statistics
        logger.info("\nSummary Statistics:")
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    COUNT(*) as total_results,
                    COUNT(CASE WHEN points > 0 THEN 1 END) as with_points,
                    COUNT(CASE WHEN status = 'finished' THEN 1 END) as finished,
                    SUM(points) as total_points_awarded,
                    MAX(points) as max_points
                FROM silver.results
            """)
            total, with_points, finished, total_points, max_points = cur.fetchone()
            logger.info(f"  Total results: {total}")
            logger.info(f"  Results with points > 0: {with_points}")
            logger.info(f"  Finished results: {finished}")
            logger.info(f"  Total points awarded: {total_points}")
            logger.info(f"  Maximum points in single result: {max_points}")
        
        logger.info("\nTop 10 Results by Points:")
        with conn.cursor() as cur:
            cur.execute("""
                SELECT r.session_id, r.driver_id, r.finish_position, r.points, r.status, r.fastest_lap
                FROM silver.results r
                ORDER BY r.points DESC, r.finish_position
                LIMIT 10
            """)
            for row in cur.fetchall():
                logger.info(f"  {row[0]} | {row[1]} | Position: {row[2]} | Points: {row[3]} | "
                          f"Status: {row[4]} | Fastest: {row[5]}")
    
    finally:
        conn.close()


if __name__ == "__main__":
    main()

