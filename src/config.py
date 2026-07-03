"""
src/config.py – OptiBot Configuration (google-genai 2.x)
Loads environment variables from .env and initialises the Google Gemini client.
"""

from __future__ import annotations

import os
import sys
import logging
from pathlib import Path

from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Load .env from the project root
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_PROJECT_ROOT / ".env", override=False)

# ---------------------------------------------------------------------------
# Logger
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s – %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("optibot.config")

# ---------------------------------------------------------------------------
# Required environment variables
# ---------------------------------------------------------------------------
GEMINI_API_KEY: str = os.environ.get("GEMINI_API_KEY", "")
if not GEMINI_API_KEY:
    logger.error(
        "GEMINI_API_KEY is not set. "
        "Copy .env.sample → .env and add your key from https://aistudio.google.com/"
    )
    sys.exit(1)

# Set standard environment variables
os.environ["API_KEY"] = GEMINI_API_KEY
os.environ["GEMINI_API_KEY"] = GEMINI_API_KEY

# ---------------------------------------------------------------------------
# Optional / defaulted variables
# ---------------------------------------------------------------------------
CORPUS_NAME: str = os.environ.get("CORPUS_NAME", "optisigns_support_corpus")

# OptiSigns Zendesk help-centre base URL
OPTISIGNS_HELP_BASE_URL: str = "https://support.optisigns.com"
ZENDESK_API_BASE: str = f"{OPTISIGNS_HELP_BASE_URL}/api/v2/help_center"

# Paths
DATA_DIR: Path = _PROJECT_ROOT / "data" / "scraped_articles"
STATE_FILE: Path = _PROJECT_ROOT / "state.json"

DATA_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Gemini / Google GenAI client (google-genai 2.x)
# ---------------------------------------------------------------------------
try:
    from google import genai  # type: ignore
    from google.genai import types as genai_types  # type: ignore

    GENAI_CLIENT = genai.Client(api_key=GEMINI_API_KEY)
    logger.info("Google GenAI client (google-genai 2.x) configured successfully.")
except ImportError as exc:  # pragma: no cover
    logger.error("google-genai not installed: %s", exc)
    GENAI_CLIENT = None  # type: ignore
    genai_types = None  # type: ignore

# Embedding and Generative models used
EMBEDDING_MODEL: str = "gemini-embedding-2"
GENERATIVE_MODEL: str = "gemini-2.5-flash"
