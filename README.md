# 🤖 OptiBot – OptiSigns AI Support Assistant

OptiBot is an automated support assistant pipeline designed for **OptiSigns.com**. It scrapes customer support articles, processes them into clean Markdown, stores them using Gemini's native **File Search Store**, and provides a retrieval-augmented generation (RAG) assistant for support queries.

---

## ✨ Features

* **Automated Scraper**: Fetches all help center articles from OptiSigns Help Centre via Zendesk API.
* **Smart Delta Sync**: Computes MD5 hashes for each article to skip unchanged articles, saving API quota and processing time.
* **Gemini File Search Store**: Uses `google-genai` (2.x SDK) to upload documents and perform native RAG query searches.
* **Real-time Logging Scheduler**: Background cron scheduler (`src/cron.py`) that syncs daily at 02:00 UTC and streams logs instantly.
* **Multi-stage Docker Build**: Clean and secure Docker container configuration ready for deployment.
* **Full Unit Test Suite**: Comprehensive testing covering all helper utilities, core logic, and mocks.

---

## 🛠️ Setup

1. Copy `.env.sample` to `.env` and fill in your Gemini API key:
   ```bash
   cp .env.sample .env
   ```
2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

---

## 🚀 How to Run

### Run Locally

* **Full Delta Sync (Scrape + Upload)**:
  ```bash
  python main.py
  ```
* **Run Scraper Only**:
  ```bash
  python main.py --scrape
  ```
* **Run Uploader Only** (Uses existing `.md` files):
  ```bash
  python main.py --upload
  ```
* **Launch Interactive Chatbot**:
  ```bash
  python main.py --chat
  ```

### Run using Docker

1. Build the Docker image:
   ```bash
   docker build -t optibot .
   ```
2. Run the Docker container:
   ```bash
   docker run -e GEMINI_API_KEY="your_api_key_here" optibot
   ```

---

## 🧪 Testing

The codebase includes a comprehensive test suite of **79 unit tests** covering utilities, delta sync logic, mocking uploader/assistant SDK calls, CLI argument parsing, and integration-style runs.

To run the unit tests, install `pytest` and execute:
```bash
pip install pytest
python -m pytest tests/test_unit.py -v
```

---

## 📐 Chunking & Retrieval Strategy

* **Document Preprocessing**: Articles are fetched as HTML, stripped of scripts/styles, relative URLs are converted to absolute, and base64 payloads are removed to keep documents lightweight.
* **Automatic Chunking**: Gemini's File Search Store handles document parsing, chunking, and semantic embedding indexing automatically.
* **Delta Detection**: File hashes are tracked in a local `state.json` file. Unchanged files are skipped from scraper writes and uploader uploads to maintain optimal bandwidth and API consumption.
* **Response Constraints**: The assistant uses a system instruction to output concise responses (maximum of 5 bullet points) and cites up to 3 article sources at the end with the format `Article URL: <link>`.

---

## 📅 Daily Job Logs

* **Deployment Platform**: Deployed as a persistent service on **Railway** with a scheduled daily sync at `02:00 UTC`.
* **Persistent Storage**: Utilizes a Railway Persistent Volume mounted at `/data` to persist `state.json` and scraped articles across container restarts.
* **Live Job Logs**: [Railway Logs Link](https://railway.com/project/a14c0861-7dda-4742-804b-884758ac0838/service/33036b2d-9a6b-466e-a130-2e637687a9e7?environmentId=e9afd600-42da-47b9-a58c-f0af35b39e44&id=eb8bcf49-f836-4ed3-bee1-5c8a6d04fbd4#deploy)

---

## 📸 Screenshot

<img width="1412" height="905" alt="image" src="https://github.com/user-attachments/assets/bc8a47ff-fcd1-4a82-bfb8-42ecc0f8743c" />
