"""
src/uploader.py – OptiBot Corpus Uploader (google-genai 2.x)
Reads Markdown files from data/scraped_articles/ and uploads each file to a
Gemini File Search Store. Tracks uploaded file hashes for delta sync.
"""

from __future__ import annotations

import logging
import time
import io
from pathlib import Path
from typing import Optional

from tqdm import tqdm  # type: ignore

from .config import (
    CORPUS_NAME,
    DATA_DIR,
    STATE_FILE,
    GENAI_CLIENT,
)
from .utils import load_state, compute_md5, save_state

logger = logging.getLogger("optibot.uploader")


# ---------------------------------------------------------------------------
# File Search Store (Corpus) management
# ---------------------------------------------------------------------------

def get_or_create_store(display_name: str = CORPUS_NAME) -> str:
    """
    Return the resource name of an existing File Search Store, or create one.
    """
    if not GENAI_CLIENT:
        raise RuntimeError("Gemini client not initialised – check GEMINI_API_KEY.")

    state = load_state(str(STATE_FILE))
    store_name: str = state.get("store_name", "")

    if store_name:
        logger.info("Using existing File Search Store: %s", store_name)
        return store_name

    # Check for existing store with same display name
    try:
        for store in GENAI_CLIENT.file_search_stores.list():
            if getattr(store, "display_name", "") == display_name:
                store_name = store.name
                logger.info("Found existing store '%s' -> %s", display_name, store_name)
                break
    except Exception as exc:
        logger.warning("Could not list stores: %s", exc)

    if not store_name:
        logger.info("Creating new File Search Store '%s'...", display_name)
        store = GENAI_CLIENT.file_search_stores.create(
            config={"display_name": display_name}
        )
        store_name = store.name
        logger.info("Store created: %s", store_name)

    state["store_name"] = store_name
    save_state(state, str(STATE_FILE))
    return store_name


# ---------------------------------------------------------------------------
# Upload helpers
# ---------------------------------------------------------------------------

def _upload_file_to_store(store_name: str, md_path: Path) -> bool:
    """
    Upload a single Markdown file to the File Search Store.
    """
    try:
        content = md_path.read_bytes()
        file_obj = io.BytesIO(content)

        GENAI_CLIENT.file_search_stores.upload_to_file_search_store(
            file_search_store_name=store_name,
            file=file_obj,
            config={
                "mime_type": "text/plain",
                "display_name": md_path.name,
            },
        )
        logger.debug("Uploaded: %s", md_path.name)
        return True
    except Exception as exc:
        logger.error("Failed to upload %s: %s", md_path.name, exc)
        return False


def upload_markdown_files(
    paths: Optional[list[Path]] = None,
    force: bool = False,
) -> int:
    """
    Upload Markdown files to the Gemini File Search Store.
    """
    if not GENAI_CLIENT:
        raise RuntimeError("Gemini client not initialised – check GEMINI_API_KEY.")

    store_name = get_or_create_store()
    state = load_state(str(STATE_FILE))
    uploaded: dict = state.get("uploaded", {})

    if paths is None:
        paths = sorted(DATA_DIR.glob("*.md"))

    if not paths:
        logger.warning("No Markdown files found in %s", DATA_DIR)
        return 0

    total_uploaded = 0
    total_failed = 0

    for md_path in tqdm(paths, desc="Uploading to Gemini Store", unit="file"):
        text = md_path.read_text(encoding="utf-8")
        file_hash = compute_md5(text)
        doc_id = md_path.name

        if not force and uploaded.get(doc_id) == file_hash:
            logger.debug("Skipping unchanged file %s", md_path.name)
            continue

        success = _upload_file_to_store(store_name, md_path)

        if success:
            total_uploaded += 1
            uploaded[doc_id] = file_hash
            # Save state incrementally
            state["uploaded"] = uploaded
            save_state(state, str(STATE_FILE))
        else:
            total_failed += 1

        time.sleep(0.3)  # Rate limit protection

    logger.info(
        "Upload complete – %d uploaded, %d failed, store: %s",
        total_uploaded, total_failed, store_name
    )
    return total_uploaded
