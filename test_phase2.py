"""
test_phase2.py - Validates Phase 2: uploader + assistant
Run: python test_phase2.py
"""
import sys
import warnings
import json
from pathlib import Path

warnings.filterwarnings("ignore")
sys.path.insert(0, ".")

print("=" * 60)
print("PHASE 2 VALIDATION TEST")
print("=" * 60)

# ── 1. Config & Client ──────────────────────────────────────────
print("\n[1] Config & GENAI_CLIENT")
from src.config import GENAI_CLIENT, GENERATIVE_MODEL, CORPUS_NAME
print(f"    GENAI_CLIENT : {type(GENAI_CLIENT).__name__}")
print(f"    GENERATIVE_MODEL : {GENERATIVE_MODEL}")
print(f"    CORPUS_NAME  : {CORPUS_NAME}")

# ── 2. State ──────────────────────────────────────────────────
print("\n[2] state.json")
state = json.loads(Path("state.json").read_text(encoding="utf-8"))
store_name = state.get("store_name", "")
uploaded   = state.get("uploaded", {})
print(f"    store_name   : {store_name!r}")
print(f"    uploaded files tracked : {len(uploaded)}")

# ── 3. Uploader imports ──────────────────────────────────────
print("\n[3] uploader.py imports")
try:
    from src.uploader import get_or_create_store, upload_markdown_files
    print("    OK")
except Exception as e:
    print(f"    FAIL: {e}")
    sys.exit(1)

# ── 4. Assistant imports ─────────────────────────────────────
print("\n[4] assistant.py imports")
try:
    from src.assistant import ask_optibot, ask, SYSTEM_INSTRUCTION
    print("    OK")
    print(f"    SYSTEM_INSTRUCTION (first 60 chars): {SYSTEM_INSTRUCTION[:60]!r}")
except Exception as e:
    print(f"    FAIL: {e}")
    sys.exit(1)

# ── 5. List stores ────────────────────────────────────────────
print("\n[5] Listing File Search Stores via GENAI_CLIENT")
try:
    stores = list(GENAI_CLIENT.file_search_stores.list())
    print(f"    Found {len(stores)} store(s)")
    for s in stores:
        dn = getattr(s, "display_name", "")
        print(f"    -> name={s.name!r}, display_name={dn!r}")
except Exception as e:
    print(f"    ERROR: {type(e).__name__}: {e}")

# ── 6. Uploader: get_or_create_store ─────────────────────────
print("\n[6] get_or_create_store()")
try:
    sn = get_or_create_store()
    print(f"    store_name = {sn!r}")
except Exception as e:
    print(f"    ERROR: {type(e).__name__}: {e}")

# ── 7. Real RAG query (sanity check) ─────────────────────────
print("\n[7] RAG Query: 'How do I add a YouTube video?'")
if not store_name:
    print("    SKIP: no store_name in state.json. Run uploader first.")
else:
    try:
        answer = ask_optibot("How do I add a YouTube video?")
        print("    --- ANSWER ---")
        for line in answer.splitlines():
            print("   ", line)
        print("    --- END ---")
        has_url = "Article URL:" in answer or "http" in answer
        print(f"    Contains citation/URL: {'YES' if has_url else 'NO (check grounding_metadata)'}")
    except Exception as e:
        print(f"    ERROR: {type(e).__name__}: {e}")

print("\n" + "=" * 60)
print("DONE")
