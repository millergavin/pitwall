#!/usr/bin/env python3
"""
Unified database update script for Pitwall.

Orchestrates the full ETL pipeline:
1. Bronze Ingestion - Fetch new data from OpenF1 API
2. Silver Upserts - Transform and load to silver layer
3. Gold Refresh - Refresh materialized views

Usage:
    python3 update_database.py                    # Run full pipeline
    python3 update_database.py --bronze-only      # Only run bronze ingestion
    python3 update_database.py --silver-only      # Only run silver upserts
    python3 update_database.py --gold-only        # Only refresh gold views
    python3 update_database.py --skip-high-volume # Skip GPS/telemetry (faster)
"""

import subprocess
import sys
import time
import logging
import argparse
import os
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Dict, Optional
import json

import psycopg
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

log_file = log_dir / f"update_database_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_file)
    ]
)
logger = logging.getLogger(__name__)

# =============================================================================
# SCRIPT DEFINITIONS
# =============================================================================

# Bronze ingestion scripts (in order)
BRONZE_SCRIPTS = [
    # Foundation (must run first)
    'pitwall_ingest/ingest_meetings.py',
    'pitwall_ingest/ingest_sessions.py',
    'pitwall_ingest/ingest_drivers.py',
    # Session data (can run after foundation)
    'pitwall_ingest/ingest_laps.py',
    'pitwall_ingest/ingest_results.py',
    'pitwall_ingest/ingest_race_control.py',
    'pitwall_ingest/ingest_starting_grid.py',
    'pitwall_ingest/ingest_pit_stops.py',
    'pitwall_ingest/ingest_stints.py',
    'pitwall_ingest/ingest_weather.py',
    'pitwall_ingest/ingest_overtakes.py',
    'pitwall_ingest/ingest_intervals.py',
    'pitwall_ingest/ingest_position.py',
]

# High-volume bronze scripts (optional, run separately)
BRONZE_HIGH_VOLUME_SCRIPTS = [
    'pitwall_ingest/ingest_car_telemetry.py',
    'pitwall_ingest/ingest_car_gps.py',
]

# Silver upsert scripts (in dependency order)
SILVER_SCRIPTS = [
    # Foundation tables
    'pitwall_silver/upsert_circuits.py',
    'pitwall_silver/upsert_meetings.py',
    'pitwall_silver/upsert_sessions.py',
    # Drivers and teams
    'pitwall_silver/upsert_drivers.py',
    'pitwall_silver/upsert_driver_numbers_by_season.py',
    'pitwall_silver/upsert_driver_teams_by_session.py',
    'pitwall_silver/upsert_team_branding.py',
    # Session data
    'pitwall_silver/upsert_laps.py',
    'pitwall_silver/upsert_results.py',
    'pitwall_silver/upsert_race_control.py',
    # Lap-dependent tables
    'pitwall_silver/upsert_stints.py',
    'pitwall_silver/upsert_pit_stops.py',
    # Other session data
    'pitwall_silver/upsert_weather.py',
    'pitwall_silver/upsert_overtakes.py',
    'pitwall_silver/upsert_intervals.py',
    'pitwall_silver/upsert_position.py',
    'pitwall_silver/upsert_points_awarding.py',
    # Post-processing
    'pitwall_silver/backfill_lap_validity.py',
]

# High-volume silver scripts (optional)
SILVER_HIGH_VOLUME_SCRIPTS = [
    'pitwall_silver/upsert_car_telemetry.py',
    'pitwall_silver/upsert_car_gps.py',
]

# Gold materialized views to refresh
GOLD_VIEWS = [
    'gold.dim_drivers',
    'gold.dim_teams',
    'gold.dim_circuits',
    'gold.dim_meetings',
    'gold.driver_session_results',
    'gold.session_classification',
    'gold.session_summary',
    'gold.lap_times',
    'gold.lap_intervals',
    'gold.driver_standings_progression',
    'gold.constructor_standings_progression',
    'gold.circuit_overtake_stats',
]


def get_db_connection():
    """Create and return a database connection."""
    return psycopg.connect(
        host=os.getenv('PGHOST', 'localhost'),
        port=os.getenv('PGPORT', '5433'),
        dbname=os.getenv('PGDATABASE', 'pitwall'),
        user=os.getenv('PGUSER', 'pitwall'),
        password=os.getenv('PGPASSWORD', 'pitwall')
    )


def run_script(script_path: str, timeout: int = 1800) -> Tuple[bool, str, float]:
    """
    Run a Python script and return results.
    
    Args:
        script_path: Path to the script
        timeout: Maximum time in seconds (default 30 minutes)
        
    Returns:
        Tuple of (success, output, duration_seconds)
    """
    script_name = Path(script_path).name
    start_time = time.time()
    
    try:
        result = subprocess.run(
            ['python3', script_path],
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        duration = time.time() - start_time
        
        if result.returncode == 0:
            return True, result.stdout, duration
        else:
            return False, result.stderr or result.stdout, duration
            
    except subprocess.TimeoutExpired:
        duration = time.time() - start_time
        return False, f"Script timed out after {timeout} seconds", duration
    except Exception as e:
        duration = time.time() - start_time
        return False, str(e), duration


def run_bronze_ingestion(include_high_volume: bool = False) -> Dict:
    """
    Run all bronze ingestion scripts.
    
    Returns:
        Dict with results summary
    """
    logger.info("=" * 60)
    logger.info("PHASE 1: BRONZE INGESTION")
    logger.info("=" * 60)
    
    scripts = BRONZE_SCRIPTS.copy()
    if include_high_volume:
        scripts.extend(BRONZE_HIGH_VOLUME_SCRIPTS)
    
    results = {"success": 0, "failed": 0, "skipped": 0, "details": []}
    
    for idx, script in enumerate(scripts, 1):
        script_name = Path(script).name
        logger.info(f"[{idx}/{len(scripts)}] Running {script_name}...")
        
        if not Path(script).exists():
            logger.warning(f"  Script not found: {script}")
            results["skipped"] += 1
            continue
        
        success, output, duration = run_script(script)
        
        if success:
            logger.info(f"  ✓ Completed in {duration:.1f}s")
            results["success"] += 1
            # Extract key info from output
            for line in output.split('\n')[-5:]:
                if 'inserted' in line.lower() or 'new' in line.lower():
                    logger.info(f"    {line.strip()}")
        else:
            logger.error(f"  ✗ Failed after {duration:.1f}s")
            logger.error(f"    Error: {output[-500:]}")
            results["failed"] += 1
        
        results["details"].append({
            "script": script_name,
            "success": success,
            "duration": duration
        })
    
    return results


def run_silver_upserts(include_high_volume: bool = False) -> Dict:
    """
    Run all silver upsert scripts.
    
    Returns:
        Dict with results summary
    """
    logger.info("=" * 60)
    logger.info("PHASE 2: SILVER UPSERTS")
    logger.info("=" * 60)
    
    scripts = SILVER_SCRIPTS.copy()
    if include_high_volume:
        scripts.extend(SILVER_HIGH_VOLUME_SCRIPTS)
    
    results = {"success": 0, "failed": 0, "skipped": 0, "details": []}
    
    for idx, script in enumerate(scripts, 1):
        script_name = Path(script).name
        logger.info(f"[{idx}/{len(scripts)}] Running {script_name}...")
        
        if not Path(script).exists():
            logger.warning(f"  Script not found: {script}")
            results["skipped"] += 1
            continue
        
        success, output, duration = run_script(script)
        
        if success:
            logger.info(f"  ✓ Completed in {duration:.1f}s")
            results["success"] += 1
            # Extract key info from output
            for line in output.split('\n')[-5:]:
                if 'upsert' in line.lower() or 'complete' in line.lower():
                    logger.info(f"    {line.strip()}")
        else:
            logger.error(f"  ✗ Failed after {duration:.1f}s")
            logger.error(f"    Error: {output[-500:]}")
            results["failed"] += 1
        
        results["details"].append({
            "script": script_name,
            "success": success,
            "duration": duration
        })
    
    return results


def refresh_gold_views() -> Dict:
    """
    Refresh all gold materialized views.
    
    Returns:
        Dict with results summary
    """
    logger.info("=" * 60)
    logger.info("PHASE 3: GOLD VIEW REFRESH")
    logger.info("=" * 60)
    
    results = {"success": 0, "failed": 0, "details": []}
    
    try:
        conn = get_db_connection()
        
        for idx, view in enumerate(GOLD_VIEWS, 1):
            view_name = view.split('.')[-1]
            logger.info(f"[{idx}/{len(GOLD_VIEWS)}] Refreshing {view_name}...")
            
            start_time = time.time()
            try:
                with conn.cursor() as cur:
                    cur.execute(f"REFRESH MATERIALIZED VIEW {view}")
                    conn.commit()
                
                duration = time.time() - start_time
                logger.info(f"  ✓ Refreshed in {duration:.1f}s")
                results["success"] += 1
                results["details"].append({
                    "view": view_name,
                    "success": True,
                    "duration": duration
                })
                
            except Exception as e:
                duration = time.time() - start_time
                logger.error(f"  ✗ Failed: {e}")
                results["failed"] += 1
                results["details"].append({
                    "view": view_name,
                    "success": False,
                    "duration": duration,
                    "error": str(e)
                })
        
        conn.close()
        
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        results["failed"] = len(GOLD_VIEWS)
    
    return results


def get_database_stats() -> Dict:
    """Get current database statistics."""
    try:
        conn = get_db_connection()
        stats = {}
        
        with conn.cursor() as cur:
            # Bronze counts
            cur.execute("SELECT COUNT(*) FROM bronze.meetings_raw")
            stats["bronze_meetings"] = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM bronze.sessions_raw")
            stats["bronze_sessions"] = cur.fetchone()[0]
            
            # Silver counts
            cur.execute("SELECT COUNT(*) FROM silver.meetings")
            stats["silver_meetings"] = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM silver.sessions")
            stats["silver_sessions"] = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM silver.laps")
            stats["silver_laps"] = cur.fetchone()[0]
            
            # Latest data
            cur.execute("SELECT MAX(season), MAX(date_start) FROM silver.meetings")
            row = cur.fetchone()
            stats["latest_season"] = row[0]
            stats["latest_meeting_date"] = str(row[1]) if row[1] else None
        
        conn.close()
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get database stats: {e}")
        return {}


def run_full_pipeline(include_high_volume: bool = False) -> Dict:
    """
    Run the complete ETL pipeline.
    
    Args:
        include_high_volume: Whether to include GPS/telemetry data
        
    Returns:
        Dict with complete results
    """
    start_time = time.time()
    start_datetime = datetime.now()
    
    logger.info("=" * 60)
    logger.info("PITWALL DATABASE UPDATE")
    logger.info("=" * 60)
    logger.info(f"Start time: {start_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Include high-volume data: {include_high_volume}")
    logger.info(f"Log file: {log_file}")
    logger.info("")
    
    # Get initial stats
    initial_stats = get_database_stats()
    logger.info(f"Initial state: {initial_stats.get('silver_meetings', 0)} meetings, "
                f"{initial_stats.get('silver_sessions', 0)} sessions, "
                f"{initial_stats.get('silver_laps', 0)} laps")
    logger.info("")
    
    results = {
        "start_time": start_datetime.isoformat(),
        "include_high_volume": include_high_volume,
        "phases": {}
    }
    
    # Phase 1: Bronze
    bronze_results = run_bronze_ingestion(include_high_volume)
    results["phases"]["bronze"] = bronze_results
    logger.info(f"Bronze: {bronze_results['success']} succeeded, {bronze_results['failed']} failed")
    logger.info("")
    
    # Phase 2: Silver
    silver_results = run_silver_upserts(include_high_volume)
    results["phases"]["silver"] = silver_results
    logger.info(f"Silver: {silver_results['success']} succeeded, {silver_results['failed']} failed")
    logger.info("")
    
    # Phase 3: Gold
    gold_results = refresh_gold_views()
    results["phases"]["gold"] = gold_results
    logger.info(f"Gold: {gold_results['success']} succeeded, {gold_results['failed']} failed")
    logger.info("")
    
    # Final stats
    final_stats = get_database_stats()
    
    total_duration = time.time() - start_time
    end_datetime = datetime.now()
    
    results["end_time"] = end_datetime.isoformat()
    results["duration_seconds"] = total_duration
    results["initial_stats"] = initial_stats
    results["final_stats"] = final_stats
    results["success"] = (
        bronze_results["failed"] == 0 and
        silver_results["failed"] == 0 and
        gold_results["failed"] == 0
    )
    
    # Summary
    logger.info("=" * 60)
    logger.info("UPDATE COMPLETE")
    logger.info("=" * 60)
    logger.info(f"Total duration: {total_duration/60:.1f} minutes")
    logger.info(f"Final state: {final_stats.get('silver_meetings', 0)} meetings, "
                f"{final_stats.get('silver_sessions', 0)} sessions, "
                f"{final_stats.get('silver_laps', 0)} laps")
    logger.info(f"Log file: {log_file}")
    
    if results["success"]:
        logger.info("✓ All phases completed successfully!")
    else:
        logger.warning("⚠ Some phases had failures - check logs for details")
    
    return results


def main():
    """Main entry point with argument parsing."""
    parser = argparse.ArgumentParser(
        description="Update Pitwall database with latest F1 data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 update_database.py                    # Full pipeline
  python3 update_database.py --skip-high-volume # Skip GPS/telemetry
  python3 update_database.py --bronze-only      # Only bronze ingestion
  python3 update_database.py --gold-only        # Only refresh gold views
        """
    )
    
    parser.add_argument(
        '--bronze-only',
        action='store_true',
        help='Only run bronze ingestion'
    )
    parser.add_argument(
        '--silver-only',
        action='store_true',
        help='Only run silver upserts'
    )
    parser.add_argument(
        '--gold-only',
        action='store_true',
        help='Only refresh gold views'
    )
    parser.add_argument(
        '--skip-high-volume',
        action='store_true',
        help='Skip GPS and telemetry data (faster)'
    )
    parser.add_argument(
        '--include-high-volume',
        action='store_true',
        help='Include GPS and telemetry data (slower)'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output results as JSON'
    )
    
    args = parser.parse_args()
    
    include_high_volume = args.include_high_volume and not args.skip_high_volume
    
    if args.bronze_only:
        results = {"phases": {"bronze": run_bronze_ingestion(include_high_volume)}}
    elif args.silver_only:
        results = {"phases": {"silver": run_silver_upserts(include_high_volume)}}
    elif args.gold_only:
        results = {"phases": {"gold": refresh_gold_views()}}
    else:
        results = run_full_pipeline(include_high_volume)
    
    if args.json:
        print(json.dumps(results, indent=2, default=str))
    
    # Exit with appropriate code
    if results.get("success", True):
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()

