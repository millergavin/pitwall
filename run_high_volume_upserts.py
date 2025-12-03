#!/usr/bin/env python3
"""
Background runner for high-volume upsert scripts (car_telemetry and car_gps).

Runs both scripts in parallel to maximize throughput while allowing other
lighter scripts to run in the foreground.

Features:
- Runs under caffeinate to prevent system sleep during processing
- Logs output to separate files for each script
- Session-based processing (only processes new/incomplete sessions)
- COPY protocol for maximum insert speed
"""

import os
import subprocess
import logging
import signal
import sys
import platform
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Scripts to run
SCRIPTS = [
    'pitwall_silver/upsert_car_telemetry.py',
    'pitwall_silver/upsert_car_gps.py'
]

# Log directory
LOG_DIR = Path('logs')
LOG_DIR.mkdir(exist_ok=True)


def run_script_in_background(script_path: str, use_caffeinate: bool = True) -> subprocess.Popen:
    """
    Run a Python script in the background with logging to file.
    
    Args:
        script_path: Path to Python script
        use_caffeinate: Whether to wrap command in caffeinate (macOS only)
    
    Returns:
        subprocess.Popen object and log file path
    """
    script_name = Path(script_path).stem
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = LOG_DIR / f"{script_name}_{timestamp}.log"
    
    logger.info(f"Starting {script_path} in background")
    logger.info(f"  Log file: {log_file}")
    
    # Build command
    cmd = ['python3', script_path]
    
    # Wrap in caffeinate on macOS to prevent sleep
    if use_caffeinate and platform.system() == 'Darwin':
        cmd = ['caffeinate', '-i'] + cmd  # -i keeps system awake, display can sleep
        logger.info(f"  Using caffeinate to prevent system sleep")
    
    with open(log_file, 'w') as f:
        process = subprocess.Popen(
            cmd,
            stdout=f,
            stderr=subprocess.STDOUT,
            text=True
        )
    
    logger.info(f"  Process ID: {process.pid}")
    return process, log_file


def cleanup_processes(processes):
    """Clean up child processes on exit."""
    logger.info("\nCleaning up child processes...")
    for script, process, _ in processes:
        if process.poll() is None:  # Still running
            logger.info(f"  Terminating {script} (PID {process.pid})")
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning(f"  Force killing {script} (PID {process.pid})")
                process.kill()


def main():
    """Main function to run high-volume upserts in parallel."""
    logger.info("="*60)
    logger.info("HIGH-VOLUME UPSERTS - BACKGROUND EXECUTION")
    logger.info("="*60)
    
    # Check if on macOS for caffeinate
    is_macos = platform.system() == 'Darwin'
    if is_macos:
        logger.info("🚫💤 System sleep prevention: ENABLED (via caffeinate)")
    else:
        logger.info("⚠️  System sleep prevention: NOT AVAILABLE (macOS only)")
    
    logger.info(f"Running {len(SCRIPTS)} scripts in parallel")
    logger.info(f"Log directory: {LOG_DIR.absolute()}")
    logger.info("")
    
    processes = []
    log_files = []
    
    # Setup signal handler for clean exit
    def signal_handler(sig, frame):
        logger.info("\n\n⚠️  Received interrupt signal")
        cleanup_processes(processes)
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start all scripts in parallel
    for script in SCRIPTS:
        if not os.path.exists(script):
            logger.error(f"Script not found: {script}")
            continue
        
        process, log_file = run_script_in_background(script, use_caffeinate=is_macos)
        processes.append((script, process, log_file))
        log_files.append(log_file)
    
    if not processes:
        logger.error("No scripts to run")
        return
    
    logger.info("")
    logger.info("✅ All scripts started. They will run in the background.")
    logger.info("   Your computer will not sleep while these scripts are running.")
    logger.info("   You can continue working on other tasks.")
    logger.info("")
    logger.info("📊 To monitor progress, check the log files:")
    for script, _, log_file in processes:
        logger.info(f"     {script}: {log_file}")
    logger.info("")
    logger.info("     Or use: tail -f logs/*.log")
    logger.info("")
    logger.info("🔍 To check if processes are still running:")
    logger.info(f"     ps aux | grep -E 'upsert_car_(telemetry|gps)'")
    logger.info("")
    logger.info("ℹ️  Optimizations enabled:")
    logger.info("     • Session-based filtering (only processes new data)")
    logger.info("     • PostgreSQL COPY protocol (10-100x faster inserts)")
    logger.info("     • Parallel execution")
    logger.info("")
    logger.info("Scripts will continue running in the background.")
    logger.info("="*60)


if __name__ == "__main__":
    main()


