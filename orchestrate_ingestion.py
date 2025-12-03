#!/usr/bin/env python3
"""
Orchestrate ingestion scripts - wait for high-volume scripts to complete,
then run remaining scripts in a coordinated manner.
"""

import subprocess
import time
import logging
import os
from datetime import datetime
from typing import List, Tuple, Dict
from pathlib import Path

# Set up logging to both console and file
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

log_file = log_dir / f"orchestration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

# Create formatters
detailed_formatter = logging.Formatter(
    '%(asctime)s - %(levelname)s - [%(name)s] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(detailed_formatter)

# File handler
file_handler = logging.FileHandler(log_file)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(detailed_formatter)

# Root logger
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
logger.addHandler(console_handler)
logger.addHandler(file_handler)

logger.info(f"Logging to file: {log_file}")

# High-volume scripts that must complete first
HIGH_VOLUME_SCRIPTS = [
    'pitwall_ingest/ingest_car_telemetry.py',
    'pitwall_ingest/ingest_car_gps.py'
]

# Remaining scripts to run after high-volume ones complete
REMAINING_SCRIPTS = [
    'pitwall_ingest/ingest_pit_stops.py',
    'pitwall_ingest/ingest_stints.py',
    'pitwall_ingest/ingest_weather.py',
    'pitwall_ingest/ingest_overtakes.py',
    'pitwall_ingest/ingest_intervals.py',
    'pitwall_ingest/ingest_position.py'
]

# Scripts that can run in parallel (lower volume, different endpoints)
# Group them to avoid overwhelming the API
PARALLEL_GROUPS = [
    # Group 1: Lower volume, can run together
    [
        'pitwall_ingest/ingest_pit_stops.py',
        'pitwall_ingest/ingest_stints.py',
    ],
    # Group 2: Can run together
    [
        'pitwall_ingest/ingest_overtakes.py',
        'pitwall_ingest/ingest_position.py',
    ],
    # Group 3: Intervals (might be higher volume, run alone)
    [
        'pitwall_ingest/ingest_intervals.py',
    ],
    # Group 4: Weather (run alone to be safe)
    [
        'pitwall_ingest/ingest_weather.py',
    ],
]


def is_process_running(script_name: str) -> bool:
    """Check if a script process is currently running."""
    try:
        result = subprocess.run(
            ['pgrep', '-f', script_name],
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    except Exception as e:
        logger.error(f"Error checking process: {e}")
        return False


def wait_for_scripts(scripts: List[str], check_interval: int = 30) -> Dict[str, float]:
    """Wait for all specified scripts to complete. Returns start times for each script."""
    logger.info("="*80)
    logger.info(f"PHASE 1: MONITORING HIGH-VOLUME SCRIPTS")
    logger.info("="*80)
    logger.info(f"Waiting for {len(scripts)} high-volume scripts to complete...")
    logger.info(f"Scripts being monitored:")
    for script in scripts:
        logger.info(f"  - {script}")
    logger.info(f"Check interval: {check_interval} seconds")
    logger.info("")
    
    start_times = {}
    check_count = 0
    
    while True:
        check_count += 1
        running = []
        completed = []
        
        for script in scripts:
            if is_process_running(script):
                running.append(script)
                if script not in start_times:
                    start_times[script] = time.time()
                    logger.info(f"[Check #{check_count}] Detected running: {script.split('/')[-1]}")
            else:
                if script not in start_times:
                    # Script already completed before we started monitoring
                    logger.info(f"[Check #{check_count}] {script.split('/')[-1]} already completed")
                elif script not in completed:
                    duration = time.time() - start_times[script]
                    logger.info(f"[Check #{check_count}] ✓ {script.split('/')[-1]} completed (duration: {duration/60:.1f} minutes)")
                    completed.append(script)
        
        if not running:
            logger.info("")
            logger.info("="*80)
            logger.info("✓ ALL HIGH-VOLUME SCRIPTS HAVE COMPLETED!")
            logger.info("="*80)
            return start_times
        
        elapsed = time.time() - min(start_times.values()) if start_times else 0
        logger.info(f"[Check #{check_count}] Status: {len(running)} still running, {len(completed)} completed")
        logger.info(f"  Running: {', '.join([s.split('/')[-1] for s in running])}")
        if elapsed > 0:
            logger.info(f"  Elapsed time: {elapsed/60:.1f} minutes")
        logger.info(f"  Next check in {check_interval} seconds...")
        logger.info("")
        time.sleep(check_interval)


def run_script(script: str) -> Tuple[bool, str, float]:
    """Run a single script and return success status, output, and duration."""
    script_name = script.split('/')[-1]
    logger.info(f"  → Starting: {script_name}")
    start_time = time.time()
    
    try:
        result = subprocess.run(
            ['python3', script],
            capture_output=True,
            text=True,
            timeout=3600  # 1 hour timeout per script
        )
        
        duration = time.time() - start_time
        
        if result.returncode == 0:
            logger.info(f"  ✓ Completed: {script_name} (duration: {duration/60:.1f} minutes)")
            # Log last few lines of output for context
            output_lines = result.stdout.strip().split('\n')
            if output_lines:
                logger.debug(f"  Last output lines from {script_name}:")
                for line in output_lines[-5:]:
                    logger.debug(f"    {line}")
            return True, result.stdout, duration
        else:
            logger.error(f"  ✗ Failed: {script_name} (duration: {duration/60:.1f} minutes)")
            logger.error(f"  Exit code: {result.returncode}")
            logger.error(f"  Error output (last 20 lines):")
            error_lines = result.stderr.strip().split('\n')
            for line in error_lines[-20:]:
                logger.error(f"    {line}")
            return False, result.stderr, duration
            
    except subprocess.TimeoutExpired:
        duration = time.time() - start_time
        logger.error(f"  ✗ Timeout: {script_name} (after {duration/60:.1f} minutes)")
        return False, "Script timed out after 1 hour", duration
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"  ✗ Exception running {script_name}: {e} (duration: {duration/60:.1f} minutes)")
        return False, str(e), duration


def run_scripts_parallel(scripts: List[str]) -> List[Tuple[str, bool, float]]:
    """Run multiple scripts in parallel. Returns list of (script, success, duration)."""
    script_names = [s.split('/')[-1] for s in scripts]
    logger.info(f"Running {len(scripts)} scripts in parallel: {', '.join(script_names)}")
    
    processes = []
    script_to_process = {}
    start_times = {}
    
    # Start all scripts
    for script in scripts:
        script_name = script.split('/')[-1]
        logger.info(f"  → Starting: {script_name}")
        start_times[script] = time.time()
        proc = subprocess.Popen(
            ['python3', script],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        processes.append(proc)
        script_to_process[proc] = script
    
    logger.info(f"  All {len(scripts)} scripts started. Waiting for completion...")
    
    # Wait for all to complete
    results = []
    for proc in processes:
        script = script_to_process[proc]
        script_name = script.split('/')[-1]
        stdout, stderr = proc.communicate()
        duration = time.time() - start_times[script]
        
        if proc.returncode == 0:
            logger.info(f"  ✓ Completed: {script_name} (duration: {duration/60:.1f} minutes)")
            # Log last few lines of output for context
            output_lines = stdout.strip().split('\n')
            if output_lines:
                logger.debug(f"  Last output lines from {script_name}:")
                for line in output_lines[-5:]:
                    logger.debug(f"    {line}")
            results.append((script, True, duration))
        else:
            logger.error(f"  ✗ Failed: {script_name} (duration: {duration/60:.1f} minutes)")
            logger.error(f"  Exit code: {proc.returncode}")
            logger.error(f"  Error output (last 20 lines):")
            error_lines = stderr.strip().split('\n')
            for line in error_lines[-20:]:
                logger.error(f"    {line}")
            results.append((script, False, duration))
    
    return results


def main():
    """Main orchestration function."""
    orchestration_start = time.time()
    start_datetime = datetime.now()
    
    logger.info("="*80)
    logger.info("INGESTION ORCHESTRATION STARTED")
    logger.info("="*80)
    logger.info(f"Start time: {start_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Log file: {log_file}")
    logger.info("")
    
    # Step 1: Wait for high-volume scripts
    high_volume_start_times = wait_for_scripts(HIGH_VOLUME_SCRIPTS, check_interval=30)
    
    # Step 2: Run remaining scripts in coordinated groups
    logger.info("")
    logger.info("="*80)
    logger.info("PHASE 2: RUNNING REMAINING SCRIPTS")
    logger.info("="*80)
    logger.info(f"Total groups to process: {len(PARALLEL_GROUPS)}")
    logger.info("")
    
    all_results = []
    group_start_times = {}
    
    for group_idx, group in enumerate(PARALLEL_GROUPS, 1):
        group_start = time.time()
        group_start_times[group_idx] = group_start
        script_names = [s.split('/')[-1] for s in group]
        
        logger.info("-"*80)
        logger.info(f"GROUP {group_idx}/{len(PARALLEL_GROUPS)}: {', '.join(script_names)}")
        logger.info("-"*80)
        logger.info(f"Group start time: {datetime.now().strftime('%H:%M:%S')}")
        logger.info("")
        
        if len(group) == 1:
            # Run sequentially for single script
            script = group[0]
            success, output, duration = run_script(script)
            all_results.append((script, success, duration))
        else:
            # Run in parallel for multiple scripts
            results = run_scripts_parallel(group)
            all_results.extend(results)
        
        group_duration = time.time() - group_start
        logger.info("")
        logger.info(f"Group {group_idx} completed in {group_duration/60:.1f} minutes")
        
        # Small delay between groups to be safe
        if group_idx < len(PARALLEL_GROUPS):
            logger.info("Waiting 5 seconds before next group...")
            logger.info("")
            time.sleep(5)
    
    # Final Summary
    orchestration_duration = time.time() - orchestration_start
    end_datetime = datetime.now()
    
    logger.info("")
    logger.info("="*80)
    logger.info("ORCHESTRATION COMPLETE - FINAL SUMMARY")
    logger.info("="*80)
    logger.info(f"End time: {end_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Total orchestration duration: {orchestration_duration/60:.1f} minutes ({orchestration_duration/3600:.2f} hours)")
    logger.info("")
    
    # Process results
    successful = [(r[0], r[2]) for r in all_results if r[1]]
    failed = [(r[0], r[2]) for r in all_results if not r[1]]
    
    logger.info("="*80)
    logger.info("RESULTS SUMMARY")
    logger.info("="*80)
    logger.info(f"Total scripts run: {len(all_results)}")
    logger.info(f"Successful: {len(successful)}/{len(all_results)} ({len(successful)/len(all_results)*100:.1f}%)")
    logger.info(f"Failed: {len(failed)}/{len(all_results)} ({len(failed)/len(all_results)*100:.1f}%)")
    logger.info("")
    
    if successful:
        logger.info("SUCCESSFUL SCRIPTS:")
        total_success_duration = 0
        for script, duration in successful:
            script_name = script.split('/')[-1]
            total_success_duration += duration
            logger.info(f"  ✓ {script_name:40s} ({duration/60:6.1f} minutes)")
        logger.info(f"  Total time for successful scripts: {total_success_duration/60:.1f} minutes")
        logger.info("")
    
    if failed:
        logger.warning("FAILED SCRIPTS:")
        total_failed_duration = 0
        for script, duration in failed:
            script_name = script.split('/')[-1]
            total_failed_duration += duration
            logger.warning(f"  ✗ {script_name:40s} ({duration/60:6.1f} minutes)")
        logger.warning(f"  Total time for failed scripts: {total_failed_duration/60:.1f} minutes")
        logger.info("")
    
    # High-volume script summary
    if high_volume_start_times:
        logger.info("="*80)
        logger.info("HIGH-VOLUME SCRIPTS (monitored)")
        logger.info("="*80)
        for script, start_time in high_volume_start_times.items():
            script_name = script.split('/')[-1]
            logger.info(f"  • {script_name}")
        logger.info("")
    
    logger.info("="*80)
    logger.info(f"Full log available at: {log_file}")
    logger.info("="*80)


if __name__ == "__main__":
    main()

