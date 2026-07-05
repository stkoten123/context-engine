# OptiBot – OptiSigns Support AI Assistant

## Setup
cp .env.sample .env   # Fill in GEMINI_API_KEY
pip install -r requirements.txt

## How to Run Locally
# Full delta sync (scrape + upload):
python main.py

# Upload only (skip scrape):
python main.py --upload

# Chat with assistant:
python main.py --chat

# Docker:
docker build -t optibot .
docker run -e GEMINI_API_KEY=AIza... optibot

## How to Run Unit Tests
python -m pytest tests/test_unit.py -v

## Chunking Strategy
Files uploaded to Gemini File Search Store as plain Markdown.
Gemini handles internal chunking automatically.
Delta detection: MD5 hash per file stored in state.json.
Log format: "added X, updated Y, skipped Z"

## Daily Job Logs
- Railway Cron Job: [https://railway.app/](https://railway.app/) (Runs daily at `0 2 * * *` UTC)
- Job Logs: https://railway.com/project/a14c0861-7dda-4742-804b-884758ac0838/service/33036b2d-9a6b-466e-a130-2e637687a9e7?environmentId=e9afd600-42da-47b9-a58c-f0af35b39e44&id=eb8bcf49-f836-4ed3-bee1-5c8a6d04fbd4#deploy

## Screenshot
<img width="1412" height="905" alt="image" src="https://github.com/user-attachments/assets/bc8a47ff-fcd1-4a82-bfb8-42ecc0f8743c" />
