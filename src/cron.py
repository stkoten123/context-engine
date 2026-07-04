"""
src/cron.py – OptiBot Daily Cron Scheduler
Runs the sync pipeline daily at 02:00 UTC.
Calls main() directly (no subprocess) so every log line streams
in real-time to Railway / Render log collectors.
"""

import schedule
import time
import logging
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Logging – force unbuffered stdout so Railway sees every line immediately
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s – %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    force=True,
)
logger = logging.getLogger("optibot.cron")


def run_sync() -> None:
    """
    Execute the full delta-sync pipeline in-process.
    Calling main() directly (instead of subprocess) means every INFO/ERROR
    line is written to stdout immediately – exactly what Railway captures.
    """
    start = datetime.now(timezone.utc)
    logger.info("=" * 55)
    logger.info("OptiBot delta sync started at %s", start.isoformat())
    logger.info("=" * 55)

    try:
        # Import here so cron.py can be imported without triggering pipeline
        from main import main as pipeline

        exit_code = pipeline()

        elapsed = (datetime.now(timezone.utc) - start).total_seconds()
        if exit_code == 0:
            logger.info("Delta sync COMPLETED successfully in %.1fs ✅", elapsed)
        else:
            logger.error("Delta sync exited with code %d after %.1fs ❌", exit_code, elapsed)

    except Exception as exc:
        elapsed = (datetime.now(timezone.utc) - start).total_seconds()
        logger.exception("Delta sync FAILED after %.1fs: %s ❌", elapsed, exc)


def start_scheduler() -> None:
    logger.info("OptiBot Scheduler started – daily job at 02:00 UTC.")

    # Run once immediately on boot so the first Railway log shows real output
    logger.info("Running initial sync on startup …")
    run_sync()

    # Schedule subsequent daily runs
    schedule.every().day.at("02:00").do(run_sync)
    logger.info("Next run scheduled for 02:00 UTC. Entering wait loop …")

    while True:
        schedule.run_pending()
        time.sleep(60)   # check every minute; very low CPU overhead


if __name__ == "__main__":
    start_scheduler()
