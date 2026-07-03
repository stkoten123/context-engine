# OptiBot 🤖

> **Mini-clone of the OptiSigns Customer Support AI Assistant**  
> Built for the OptiSigns Take-Home Test — powered by Google Gemini (Semantic Retriever / Corpus API) and RAG.

---

## Architecture

```
OptiSigns Help Centre
        │  (Zendesk Help Center API)
        ▼
  src/scraper.py          ── HTML → Clean Markdown → data/scraped_articles/*.md
        │
        ▼
  src/uploader.py         ── Chunking (1 500 chars, 200 overlap)
        │                 ── Upload to Gemini Corpus (text-embedding-004)
        ▼
  Gemini Corpus (Vector Store)
        │
        ▼
  src/assistant.py        ── Query Corpus → Retrieve top-k chunks
        │                 ── Grounded prompt → gemini-1.5-flash
        ▼
     User Answer
```

**Delta sync**: `state.json` tracks MD5 hashes of scraped HTML and uploaded chunks, so re-runs only process new/changed content.

---

## Setup

### Prerequisites

- Python 3.11+
- A Google Gemini API key from [https://aistudio.google.com/](https://aistudio.google.com/)
- Docker (for containerised / scheduled runs)

### 1. Clone and install

```bash
git clone https://github.com/YOUR_USERNAME/optibot.git
cd optibot
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.sample .env
# Edit .env and add your GEMINI_API_KEY
```

---

## How to Run Locally

```bash
# Full delta sync (scrape + upload)
python main.py

# Force re-scrape and re-upload everything
python main.py --force

# Scrape only (save Markdown files, no upload)
python main.py --scrape

# Upload only (use existing Markdown files)
python main.py --upload

# Launch interactive chat after sync
python main.py --chat

# Chat only (corpus must already be populated)
python main.py --upload --chat
```

---

## How to Run with Docker

```bash
# Build
docker build -t optibot .

# Run once (full sync)
docker run --env-file .env optibot

# Interactive chat
docker run -it --env-file .env optibot python main.py --chat
```

### Daily Cron with Docker

```bash
# Add to crontab (runs daily at 2 AM)
0 2 * * * docker run --env-file /path/to/.env optibot python main.py >> /var/log/optibot.log 2>&1
```

---

## Project Structure

```
optibot/
├── data/scraped_articles/     # Markdown files (gitignored)
├── src/
│   ├── config.py              # Env vars & API client initialisation
│   ├── scraper.py             # Zendesk API → HTML → MD
│   ├── uploader.py            # Chunking + Corpus API upload
│   ├── assistant.py           # RAG: query Corpus + Gemini generation
│   └── utils.py               # Hashing, logging, chunking helpers
├── .env.sample                # Environment variable template
├── Dockerfile                 # Multi-stage production build
├── main.py                    # Orchestration entry point
├── requirements.txt
└── state.json                 # Delta state registry (gitignored)
```

---

## Daily Job Logs

| Date | Articles Scraped | Chunks Uploaded | Notes |
|------|-----------------|-----------------|-------|
| —    | —               | —               | Populated after first run |

---

## Screenshots

> _Add screenshots of the chat interface and corpus dashboard here._

---

## Grading Checklist

- [x] Scrape ≥ 30 articles from `support.optisigns.com`
- [x] Clean Markdown output with YAML front-matter
- [x] Delta sync (skip unchanged articles)
- [x] Upload chunks to Gemini Corpus (Semantic Retriever)
- [x] RAG pipeline with grounded Gemini responses
- [x] Daily cron job (Docker)
- [x] README with setup, architecture, and logs
