"""
src/cron.py – OptiBot Daily Cron Scheduler
Runs main.py sync pipeline daily at 02:00 UTC (or local time).
Useful for deploying on platforms like Render or Railway.
"""

import schedule
import time
import subprocess
import sys
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] cron – %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("optibot.cron")


def run_sync():
    logger.info("Starting scheduled delta sync pipeline...")
    try:
        # Run main.py as a subprocess to keep environments isolated and clean
        result = subprocess.run(
            [sys.executable, "main.py"],
            capture_output=True,
            text=True,
            check=True
        )
        logger.info("Sync pipeline output:\n%s", result.stdout)
        logger.info("Delta sync pipeline completed successfully at %s", datetime.now().isoformat())
    except subprocess.CalledProcessError as err:
        logger.error("Sync pipeline failed with exit code %d", err.returncode)
        logger.error("Error output:\n%s", err.stderr)
    except Exception as exc:
        logger.error("An unexpected error occurred during sync: %s", exc)


def start_scheduler():
    logger.info("OptiBot Scheduler started. Sync job scheduled daily at 02:00 UTC.")
    
    # Schedule job daily at 02:00
    schedule.every().day.at("02:00").do(run_sync)
    
    # Run once immediately on startup to verify setup and fetch delta
    logger.info("Running initial delta sync on startup...")
    run_sync()

    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    start_scheduler()
