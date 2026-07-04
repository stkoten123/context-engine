"""
src/scraper.py – OptiBot Article Scraper
Fetches articles from the OptiSigns Zendesk Help Centre via the public
Help Center API, converts the HTML body to clean Markdown, and saves
each article as a .md file inside data/scraped_articles/.

Delta sync: articles already stored (by article_id + content hash) are
skipped, so re-runs only download new/updated content.
"""

from __future__ import annotations

import logging
import time
import os
from pathlib import Path
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md  # type: ignore
from tqdm import tqdm  # type: ignore

from .config import (
    STATE_FILE,
)
from .utils import clean_markdown, compute_md5, slugify, load_state, save_state

logger = logging.getLogger("optibot.scraper")

# ---------------------------------------------------------------------------
# Zendesk Help Center API helpers
# ---------------------------------------------------------------------------

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "OptiBot/1.0 (take-home-test)"})

NEW_PATHS_WRITTEN: list[Path] = []
SCRAPER_STATS = {
    "added": 0,
    "updated": 0,
    "skipped": 0,
    "errors": 0,
    "total": 0
}



def _api_get(url: str, params: dict | None = None) -> dict:
    """GET *url* with basic retry logic (3 attempts, exponential back-off)."""
    for attempt in range(1, 4):
        try:
            resp = SESSION.get(url, params=params, timeout=15)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as exc:
            logger.warning("Attempt %d failed for %s: %s", attempt, url, exc)
            if attempt < 3:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"Failed to fetch {url} after 3 attempts")


def fetch_all_articles() -> list[dict]:
    """
    Call Zendesk API with pagination (using next_page field) until at least 30 articles.
    Returns a list of article dicts containing: id, title, html_url, updated_at, body (HTML).
    """
    url = "https://support.optisigns.com/api/v2/help_center/en-us/articles.json?per_page=100"
    all_articles: list[dict] = []

    while url:
        try:
            data = _api_get(url)
        except Exception as exc:
            logger.error("Error fetching Zendesk articles: %s", exc)
            break

        articles = data.get("articles", [])
        for article in articles:
            # Each article must have: id, title, html_url, updated_at, body
            all_articles.append({
                "id": article.get("id"),
                "title": article.get("title", ""),
                "html_url": article.get("html_url", ""),
                "updated_at": article.get("updated_at", ""),
                "body": article.get("body") or "",
            })

        logger.info("Fetched page. Accumulated articles: %d", len(all_articles))
        
        # Paginate using next_page
        url = data.get("next_page")

    print(f"Fetched {len(all_articles)} articles")
    return all_articles


# ---------------------------------------------------------------------------
# HTML → Markdown conversion
# ---------------------------------------------------------------------------

def html_to_markdown(html: str, article_url: str) -> str:
    """
    Use BeautifulSoup to strip script, style, and nav elements.
    Convert relative links/images to absolute using article_url.
    Convert HTML to Markdown using markdownify, preserving headings, lists, code blocks, tables.
    """
    if not html:
        return ""

    soup = BeautifulSoup(html, "html.parser")

    # Strip script, style, nav elements
    for element in soup(["script", "style", "nav"]):
        element.decompose()

    # Convert relative links and image src to absolute, and strip base64 image data
    for a in soup.find_all("a", href=True):
        a["href"] = urljoin(article_url, a["href"])
    for img in soup.find_all("img", src=True):
        src = img["src"]
        if src.startswith("data:image/"):
            # Remove or replace base64 source with a placeholder to keep payload light
            img.decompose()
        else:
            img["src"] = urljoin(article_url, src)

    # Convert to Markdown
    raw_md = md(
        str(soup),
        heading_style="ATX",
        bullets="-",
    )
    return clean_markdown(raw_md)


# ---------------------------------------------------------------------------
# Save article helper
# ---------------------------------------------------------------------------

def save_article(article: dict, output_dir: str) -> tuple[str, str]:
    """
    Lưu markdown vào output_dir/<slug>.md.
    Return (slug, filepath).
    """
    title = article.get("title", "")
    slug = slugify(title)
    
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    
    filepath = out_path / f"{slug}.md"
    
    html_body = article.get("body") or ""
    markdown_body = html_to_markdown(html_body, article.get("html_url", ""))
    
    # Save with clean formatting, including h1 title
    full_content = f"# {title}\n\n{markdown_body}"
    filepath.write_text(full_content, encoding="utf-8")
    
    return slug, str(filepath)


# ---------------------------------------------------------------------------
# Main scrape function
# ---------------------------------------------------------------------------

def run_scraper(output_dir: str = "data/scraped_articles") -> list[dict]:
    """
    Orchestrate the scraping pipeline: fetch -> convert -> save.
    """
    global NEW_PATHS_WRITTEN, SCRAPER_STATS
    NEW_PATHS_WRITTEN = []
    
    state = load_state(str(STATE_FILE))
    scraped = state.get("scraped", {})

    articles = fetch_all_articles()
    
    # Handle MAX_ARTICLES limit if set
    max_articles_env = os.environ.get("MAX_ARTICLES")
    if max_articles_env:
        try:
            limit = int(max_articles_env)
            articles = articles[:limit]
            logger.info("Limiting scraper to %d articles due to MAX_ARTICLES=%d", limit, limit)
        except ValueError:
            pass

    SCRAPER_STATS = {
        "added": 0,
        "updated": 0,
        "skipped": 0,
        "errors": 0,
        "total": len(articles)
    }

    results = []
    saved_count = 0

    for article in tqdm(articles, desc="Processing articles", unit="art"):
        article_id = str(article.get("id", ""))
        title = article.get("title", "")
        url = article.get("html_url", "")
        updated_at = article.get("updated_at", "")
        body = article.get("body") or ""

        if not body:
            SCRAPER_STATS["skipped"] += 1
            continue

        content_hash = compute_md5(body)
        slug = slugify(title)
        filepath = Path(output_dir) / f"{slug}.md"

        # Check delta sync status
        if scraped.get(article_id) == content_hash and filepath.exists():
            SCRAPER_STATS["skipped"] += 1
            results.append({
                "article_id": article_id,
                "slug": slug,
                "filepath": str(filepath),
                "title": title,
                "url": url,
                "updated_at": updated_at,
                "content_hash": content_hash,
            })
            continue

        try:
            slug, filepath_str = save_article(article, output_dir)
            print(f"Saved: {slug}.md")
            
            # Determine if this is a new article or an update
            if article_id in scraped:
                SCRAPER_STATS["updated"] += 1
            else:
                SCRAPER_STATS["added"] += 1

            scraped[article_id] = content_hash
            saved_count += 1
            NEW_PATHS_WRITTEN.append(Path(filepath_str))

            results.append({
                "article_id": article_id,
                "slug": slug,
                "filepath": filepath_str,
                "title": title,
                "url": url,
                "updated_at": updated_at,
                "content_hash": content_hash,
            })
        except Exception as exc:
            logger.error("Failed to save article %s: %s", article_id, exc)
            SCRAPER_STATS["errors"] += 1

    # Save state
    state["scraped"] = scraped
    save_state(state, str(STATE_FILE))

    print(f"Total: {saved_count} articles saved")
    return results


def scrape_articles(force: bool = False) -> list[Path]:
    """
    Compatibility wrapper matching the original signature for main.py.
    """
    # If force is true, we can clear state or ignore it.
    if force:
        state = load_state(str(STATE_FILE))
        state["scraped"] = {}
        save_state(state, str(STATE_FILE))
        
    run_scraper()
    return NEW_PATHS_WRITTEN


if __name__ == "__main__":
    import sys
    # Initialize logging
    logging.basicConfig(level=logging.INFO)
    
    # Run scraper
    output_dir = "data/scraped_articles"
    articles = run_scraper(output_dir)
    
    # Validation info
    print("\n=== VALIDATION ===")
    print(f"Total articles fetched: {len(articles)}")
    
    # Get all .md files in output_dir
    md_files = sorted(Path(output_dir).glob("*.md"))
    print(f"Total .md files in output dir: {len(md_files)}")
    
    print("\nFirst 5 files and sizes:")
    for filepath in md_files[:5]:
        print(f" - {filepath.name} ({filepath.stat().st_size} bytes)")
        
    if md_files:
        preview_file = md_files[0]
        print(f"\nPreview (first 10 lines) of {preview_file.name}:")
        try:
            lines = preview_file.read_text(encoding="utf-8").splitlines()
            for line in lines[:10]:
                print(line)
        except Exception as exc:
            print(f"Error reading file: {exc}")

