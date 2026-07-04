"""
test_phase3.py – Validates Phase 3: delta sync, docker readiness, README
Run: python test_phase3.py
"""
import sys, json, warnings, subprocess
from pathlib import Path

warnings.filterwarnings("ignore")
sys.path.insert(0, ".")

PASS = "[PASS]"
FAIL = "[FAIL]"
WARN = "[WARN]"

results = []

def check(label, ok, detail=""):
    tag = PASS if ok else FAIL
    msg = f"  {tag} {label}"
    if detail:
        msg += f"\n         {detail}"
    print(msg)
    results.append((label, ok))

print("=" * 62)
print("PHASE 3 VALIDATION")
print("=" * 62)

# ── 1. SCRAPER_STATS exists and is accurate ──────────────────
print("\n[A] Delta Sync – SCRAPER_STATS")
try:
    from src.scraper import SCRAPER_STATS
    check("SCRAPER_STATS importable", True, str(SCRAPER_STATS))
except Exception as e:
    check("SCRAPER_STATS importable", False, str(e))

# ── 2. main.py imports SCRAPER_STATS correctly ───────────────
print("\n[B] main.py – Delta summary log")
mp = Path("main.py").read_text(encoding="utf-8")
has_stats = "SCRAPER_STATS" in mp
has_summary = "Delta summary" in mp
check("main.py imports SCRAPER_STATS", has_stats)
check("main.py logs Delta summary", has_summary)

# ── 3. Simulate 2nd run → all skipped ────────────────────────
print("\n[C] Second run of scraper → all skipped")
try:
    from src.scraper import run_scraper, SCRAPER_STATS as before
    results_list = run_scraper("data/scraped_articles")
    from src.scraper import SCRAPER_STATS as after
    skipped = after["skipped"]
    added   = after["added"]
    updated = after["updated"]
    check("2nd run: added = 0", added == 0, f"added={added}")
    check("2nd run: skipped > 0", skipped > 0, f"skipped={skipped}")
    check("2nd run: updated = 0", updated == 0, f"updated={updated}")
except Exception as e:
    check("2nd run scraper", False, str(e))

# ── 4. Upload pipeline works ─────────────────────────────────
print("\n[D] Uploader pipeline")
try:
    from src.uploader import get_or_create_store, upload_markdown_files
    store = get_or_create_store()
    check("get_or_create_store() OK", bool(store), f"store={store}")
except Exception as e:
    check("get_or_create_store()", False, str(e))

state = json.loads(Path("state.json").read_text(encoding="utf-8"))
uploaded_count = len(state.get("uploaded", {}))
check("uploaded > 0 in state.json", uploaded_count > 0,
      f"{uploaded_count} files tracked as uploaded")

# ── 5. Dockerfile checks ─────────────────────────────────────
print("\n[E] Dockerfile")
df = Path("Dockerfile").read_text(encoding="utf-8")
check("FROM python:3.11", "python:3.11" in df)
check("COPY requirements.txt", "requirements.txt" in df)
check("pip install", "pip install" in df)
check("CMD python main.py", 'CMD ["python", "main.py"]' in df)
check("PYTHONUNBUFFERED=1", "PYTHONUNBUFFERED" in df)

# ── 6. .gitignore critical entries ───────────────────────────
print("\n[F] .gitignore")
gi = Path(".gitignore").read_text(encoding="utf-8")
check(".env ignored", ".env" in gi)
check("state.json ignored", "state.json" in gi)
check("data/ ignored", "data/" in gi)

# ── 7. .env.sample OK ────────────────────────────────────────
print("\n[G] .env.sample")
es = Path(".env.sample").read_text(encoding="utf-8")
check("GEMINI_API_KEY placeholder", "GEMINI_API_KEY" in es)
check("No real key in .env.sample", "AIza" not in es and "AQ." not in es)

# ── 8. README completeness ───────────────────────────────────
print("\n[H] README.md")
rm = Path("README.md").read_text(encoding="utf-8")
check("## Setup section", "## Setup" in rm)
check("## How to Run", "## How to Run" in rm)
check("## Daily Job", "## Daily Job" in rm)
check("## Screenshot", "## Screenshot" in rm)
check("python main.py mentioned", "python main.py" in rm)
check("docker run mentioned", "docker run" in rm)
check("Article URL in screenshot", "Article URL:" in rm)
check("Chunking strategy explained", "Chunking" in rm or "chunk" in rm.lower())
# Check if daily job URL is still placeholder
is_placeholder = "Replace with your actual" in rm or "railway.app/" in rm and "logs" not in rm
check("Daily job URL (not placeholder)", not is_placeholder,
      "⚠ Still has placeholder URL – update after deploy" if is_placeholder else "")

# ── 9. No hardcoded API key in source ────────────────────────
print("\n[I] Security – no hardcoded keys")
for f in ["src/config.py", "src/scraper.py", "src/uploader.py",
          "src/assistant.py", "main.py"]:
    content = Path(f).read_text(encoding="utf-8")
    no_key = "AIza" not in content and "AQ." not in content
    check(f"No hardcoded key in {f}", no_key)

# ── SUMMARY ──────────────────────────────────────────────────
print("\n" + "=" * 62)
passed = sum(1 for _, ok in results if ok)
total  = len(results)
failed_items = [label for label, ok in results if not ok]
print(f"RESULT: {passed}/{total} checks passed")
if failed_items:
    print("NEED FIX:")
    for item in failed_items:
        print(f"  - {item}")
else:
    print("ALL CHECKS PASSED ✅")
print("=" * 62)
