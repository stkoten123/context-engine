"""
src/utils.py – OptiBot Utility Helpers
Provides hashing, safe file I/O, text chunking, and logging helpers.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from pathlib import Path
from typing import Generator

logger = logging.getLogger("optibot.utils")


# ---------------------------------------------------------------------------
# Hashing
# ---------------------------------------------------------------------------

def compute_md5(text: str) -> str:
    """Return the MD5 hex-digest of a UTF-8 encoded string."""
    return hashlib.md5(text.encode("utf-8")).hexdigest()


# Keep alias for compatibility
md5_of_text = compute_md5


def sha256_of_text(text: str) -> str:
    """Return the SHA-256 hex-digest of a UTF-8 encoded string."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# State / JSON helpers
# ---------------------------------------------------------------------------

def load_state(path: str) -> dict:
    """Load a state JSON file; return {} if missing or corrupt."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


# Keep alias for compatibility
load_json = lambda path: load_state(str(path))


def save_state(state: dict, path: str) -> None:
    """Save *state* to *path* as pretty-printed JSON with Windows retry logic."""
    import time
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    
    for attempt in range(5):
        try:
            with open(p, "w", encoding="utf-8") as fh:
                json.dump(state, fh, indent=2, ensure_ascii=False)
            logger.debug("State saved → %s", p)
            return
        except PermissionError:
            if attempt == 4:
                raise
            time.sleep(0.1 * (attempt + 1))




# Keep alias for compatibility
save_json = lambda data, path: save_state(data, str(path))


# ---------------------------------------------------------------------------
# Text / Markdown helpers
# ---------------------------------------------------------------------------

def slugify(title: str) -> str:
    """Convert *title* to a URL-safe slug (lowercase, hyphens)."""
    title = title.lower().strip()
    title = re.sub(r"[^\w\s-]", "", title)
    title = re.sub(r"[\s_]+", "-", title)
    title = re.sub(r"-+", "-", title)
    return title


def clean_markdown(md: str) -> str:
    """
    Light-touch cleanup of raw markdownify output:
    - Collapse 3+ consecutive blank lines to 2.
    - Strip trailing whitespace on each line.
    - Ensure single trailing newline.
    """
    lines = md.splitlines()
    cleaned: list[str] = []
    blank_run = 0
    for line in lines:
        stripped = line.rstrip()
        if stripped == "":
            blank_run += 1
            if blank_run <= 2:
                cleaned.append("")
        else:
            blank_run = 0
            cleaned.append(stripped)
    return "\n".join(cleaned).strip() + "\n"


def chunk_text(
    text: str,
    chunk_size: int = 1500,
    overlap: int = 200,
) -> Generator[str, None, None]:
    """
    Split *text* into overlapping chunks of at most *chunk_size* characters.
    Tries to split on paragraph boundaries first; falls back to hard split.
    """
    paragraphs = re.split(r"\n{2,}", text)
    current: list[str] = []
    current_len = 0

    for para in paragraphs:
        para_len = len(para)
        if current_len + para_len > chunk_size and current:
            yield "\n\n".join(current)
            # Keep last paragraph(s) for overlap
            overlap_text = "\n\n".join(current)[-overlap:]
            current = [overlap_text, para] if overlap_text else [para]
            current_len = len(overlap_text) + para_len + 2
        else:
            current.append(para)
            current_len += para_len + 2  # +2 for the "\n\n"

    if current:
        yield "\n\n".join(current)


# ---------------------------------------------------------------------------
# Logging setup helper (called from main.py if needed)
# ---------------------------------------------------------------------------

def setup_logging(level: int = logging.INFO) -> None:
    """Configure root logger with a standard format."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s – %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        force=True,
    )


# Keep alias for compatibility
configure_logging = setup_logging

