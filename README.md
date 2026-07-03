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

## Chunking Strategy
Files uploaded to Gemini File Search Store as plain Markdown.
Gemini handles internal chunking automatically.
Delta detection: MD5 hash per file stored in state.json.
Log format: "added X, updated Y, skipped Z"

## Daily Job Logs
- Railway Cron Job: [https://railway.app/](https://railway.app/) (Runs daily at `0 2 * * *` UTC)
- Job Logs: [https://railway.app/](https://railway.app/) (Replace with your actual Railway job logs URL after connecting your repository)

## Screenshot
Below is the CLI chat transcript demonstration of OptiBot answering the question with the required source URL citation:

```
🤖  OptiBot – OptiSigns AI Support Assistant (File Search Store)
    Type 'exit' or Ctrl-C to quit.

You: How do I add a YouTube video?

OptiBot is thinking...

OptiBot: To add a YouTube video to OptiSigns, follow these steps:

*   Log in to the OptiSigns portal at http://app.optisigns.com/.
*   Navigate to "Files/Assets" and click on "App".
*   Select "YouTube" (or "YouTube Live").
*   Enter a name for your video and paste the actual YouTube video URL into the "URL" field.
*   For YouTube Shorts, change /shorts/ in the URL to /embed/ (e.g., https://youtube.com/shorts/BUXczOFByAU becomes https://youtube.com/embed/BUXczOFByAU).
*   Click "Save".

Article URL: https://support.optisigns.com/hc/en-us/articles/360051014713-How-to-use-YouTube-with-OptiSigns
```
