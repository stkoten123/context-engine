"""
main.py – OptiBot Entry Point
Orchestrates the full pipeline:
  1. Scrape new/updated articles from OptiSigns Help Centre.
  2. Upload changed Markdown files to the Gemini Corpus.
  3. (Optional) Launch interactive assistant for testing.

Usage:
    python main.py              # full delta sync
    python main.py --force      # force re-scrape + re-upload everything
    python main.py --chat       # interactive assistant (after sync)
    python main.py --scrape     # scrape only
    python main.py --upload     # upload only (use existing .md files)
"""

from __future__ import annotations

import argparse
import logging
import sys

from src.utils import configure_logging

configure_logging()
logger = logging.getLogger("optibot.main")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="optibot",
        description="OptiBot – OptiSigns AI Support Assistant Pipeline",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-scrape and re-upload all articles, ignoring delta state.",
    )
    parser.add_argument(
        "--scrape",
        action="store_true",
        help="Run scraper only (skip upload).",
    )
    parser.add_argument(
        "--upload",
        action="store_true",
        help="Run uploader only on existing Markdown files (skip scrape).",
    )
    parser.add_argument(
        "--chat",
        action="store_true",
        help="Launch interactive chat assistant after sync.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    run_scrape = not args.upload   # scrape unless --upload-only
    run_upload = not args.scrape   # upload unless --scrape-only

    new_files = []

    # ---- STEP 1: Scrape ---------------------------------------------------
    if run_scrape:
        logger.info("=== STEP 1: Scraping articles ===")
        from src.scraper import scrape_articles

        new_files = scrape_articles(force=args.force)
        logger.info("Scraper finished – %d new/updated files", len(new_files))
    else:
        logger.info("Skipping scrape (--upload flag set)")

    # ---- STEP 2: Upload ---------------------------------------------------
    if run_upload:
        logger.info("=== STEP 2: Uploading to Gemini Corpus ===")
        from src.uploader import upload_markdown_files

        # If we only ran the uploader (--upload), pass None → pick up all .md files
        paths = new_files if run_scrape else None
        chunks_uploaded = upload_markdown_files(paths=paths, force=args.force)
        logger.info("Uploader finished – %d files uploaded", chunks_uploaded)
    else:
        logger.info("Skipping upload (--scrape flag set)")

    # ---- Delta Summary ----------------------------------------------------
    if run_scrape:
        from src.scraper import SCRAPER_STATS
        logger.info(
            "Delta summary: added=%d, updated=%d, skipped=%d, errors=%d",
            SCRAPER_STATS["added"],
            SCRAPER_STATS["updated"],
            SCRAPER_STATS["skipped"],
            SCRAPER_STATS["errors"]
        )

    # ---- STEP 3: Chat (optional) ------------------------------------------
    if args.chat:
        logger.info("=== STEP 3: Launching interactive assistant ===")
        from src.assistant import interactive_loop

        interactive_loop()

    logger.info("OptiBot pipeline complete. ✅")
    return 0


if __name__ == "__main__":
    sys.exit(main())
