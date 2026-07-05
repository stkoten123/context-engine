"""
tests/test_unit.py – OptiBot Unit Test Suite
============================================
Covers: utils, scraper (pure logic), uploader (mock), assistant (mock), main pipeline.
Run with:
    python -m pytest tests/test_unit.py -v
    python -m pytest tests/test_unit.py -v --tb=short
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch, mock_open, call
import pytest

# ── Ensure project root is on path ─────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# ===========================================================================
# 1. src/utils.py
# ===========================================================================

class TestComputeMd5:
    def test_known_hash(self):
        from src.utils import compute_md5
        result = compute_md5("hello")
        assert result == hashlib.md5(b"hello").hexdigest()

    def test_empty_string(self):
        from src.utils import compute_md5
        result = compute_md5("")
        assert result == hashlib.md5(b"").hexdigest()

    def test_different_inputs_produce_different_hashes(self):
        from src.utils import compute_md5
        assert compute_md5("abc") != compute_md5("xyz")

    def test_same_input_deterministic(self):
        from src.utils import compute_md5
        assert compute_md5("test") == compute_md5("test")

    def test_unicode_encoded_correctly(self):
        from src.utils import compute_md5
        text = "Thêm video YouTube"
        result = compute_md5(text)
        expected = hashlib.md5(text.encode("utf-8")).hexdigest()
        assert result == expected


class TestSha256OfText:
    def test_known_hash(self):
        from src.utils import sha256_of_text
        result = sha256_of_text("hello")
        assert result == hashlib.sha256(b"hello").hexdigest()

    def test_empty_string(self):
        from src.utils import sha256_of_text
        assert sha256_of_text("") == hashlib.sha256(b"").hexdigest()


class TestSlugify:
    def test_basic(self):
        from src.utils import slugify
        assert slugify("Hello World") == "hello-world"

    def test_special_characters_removed(self):
        from src.utils import slugify
        assert slugify("How do I add a YouTube video?") == "how-do-i-add-a-youtube-video"

    def test_multiple_spaces_become_one_hyphen(self):
        from src.utils import slugify
        assert slugify("a   b") == "a-b"

    def test_leading_trailing_spaces(self):
        from src.utils import slugify
        assert slugify("  hello  ") == "hello"

    def test_consecutive_hyphens_collapsed(self):
        from src.utils import slugify
        result = slugify("hello--world")
        assert result == "hello-world"

    def test_already_lowercase(self):
        from src.utils import slugify
        assert slugify("test") == "test"

    def test_mixed_case(self):
        from src.utils import slugify
        assert slugify("OptiSigns Digital Signage") == "optisigns-digital-signage"

    def test_numbers_preserved(self):
        from src.utils import slugify
        assert slugify("Step 1 Setup") == "step-1-setup"

    def test_empty_string(self):
        from src.utils import slugify
        assert slugify("") == ""


class TestCleanMarkdown:
    def test_trailing_whitespace_stripped(self):
        from src.utils import clean_markdown
        result = clean_markdown("line1   \nline2  ")
        lines = result.splitlines()
        assert all(not line.endswith(" ") for line in lines)

    def test_single_trailing_newline(self):
        from src.utils import clean_markdown
        result = clean_markdown("text")
        assert result.endswith("\n")

    def test_collapses_excess_blank_lines(self):
        from src.utils import clean_markdown
        result = clean_markdown("a\n\n\n\n\nb")
        # Should not have 3+ consecutive blank lines
        assert "\n\n\n\n" not in result

    def test_preserves_double_blank_line(self):
        from src.utils import clean_markdown
        result = clean_markdown("a\n\n\nb")
        # At most 2 blank lines allowed
        assert "\n\n\n\n" not in result

    def test_empty_string_returns_newline(self):
        from src.utils import clean_markdown
        result = clean_markdown("")
        assert result == "\n"


class TestLoadState:
    def test_returns_empty_dict_if_file_missing(self, tmp_path):
        from src.utils import load_state
        result = load_state(str(tmp_path / "nonexistent.json"))
        assert result == {}

    def test_loads_valid_json(self, tmp_path):
        from src.utils import load_state
        state_file = tmp_path / "state.json"
        state_file.write_text(json.dumps({"key": "value"}), encoding="utf-8")
        result = load_state(str(state_file))
        assert result == {"key": "value"}

    def test_returns_empty_dict_on_corrupt_json(self, tmp_path):
        from src.utils import load_state
        state_file = tmp_path / "state.json"
        state_file.write_text("not valid json{{{{", encoding="utf-8")
        result = load_state(str(state_file))
        assert result == {}

    def test_preserves_nested_structure(self, tmp_path):
        from src.utils import load_state
        data = {"scraped": {"123": "abc"}, "uploaded": {"file.md": "def"}}
        state_file = tmp_path / "state.json"
        state_file.write_text(json.dumps(data), encoding="utf-8")
        assert load_state(str(state_file)) == data


class TestSaveState:
    def test_creates_file(self, tmp_path):
        from src.utils import save_state
        state_file = tmp_path / "state.json"
        save_state({"key": "value"}, str(state_file))
        assert state_file.exists()

    def test_written_content_is_valid_json(self, tmp_path):
        from src.utils import save_state
        state_file = tmp_path / "state.json"
        save_state({"scraped": {"id1": "hash1"}}, str(state_file))
        content = json.loads(state_file.read_text(encoding="utf-8"))
        assert content == {"scraped": {"id1": "hash1"}}

    def test_creates_parent_dirs(self, tmp_path):
        from src.utils import save_state
        nested = tmp_path / "a" / "b" / "state.json"
        save_state({}, str(nested))
        assert nested.exists()

    def test_roundtrip_load_save(self, tmp_path):
        from src.utils import load_state, save_state
        state_file = tmp_path / "state.json"
        original = {"scraped": {"1": "a"}, "uploaded": {"x.md": "b"}}
        save_state(original, str(state_file))
        loaded = load_state(str(state_file))
        assert loaded == original


class TestChunkText:
    def test_short_text_single_chunk(self):
        from src.utils import chunk_text
        chunks = list(chunk_text("Hello world", chunk_size=1500))
        assert len(chunks) == 1
        assert "Hello world" in chunks[0]

    def test_long_text_multiple_chunks(self):
        from src.utils import chunk_text
        text = "paragraph\n\n" * 200  # very long
        chunks = list(chunk_text(text, chunk_size=100))
        assert len(chunks) > 1

    def test_chunks_cover_all_content(self):
        from src.utils import chunk_text
        # Each paragraph should appear in at least one chunk
        text = "alpha\n\nbeta\n\ngamma"
        chunks = list(chunk_text(text, chunk_size=20, overlap=5))
        combined = " ".join(chunks)
        assert "alpha" in combined
        assert "beta" in combined
        assert "gamma" in combined

    def test_empty_string_yields_empty(self):
        from src.utils import chunk_text
        chunks = list(chunk_text(""))
        # Empty or single empty chunk
        assert chunks == [] or chunks == [""]


# ===========================================================================
# 2. src/scraper.py  (pure logic – no HTTP calls)
# ===========================================================================

class TestHtmlToMarkdown:
    def test_basic_conversion(self):
        from src.scraper import html_to_markdown
        result = html_to_markdown("<p>Hello <b>world</b></p>", "https://example.com/")
        assert "Hello" in result
        assert "world" in result

    def test_empty_html_returns_empty(self):
        from src.scraper import html_to_markdown
        assert html_to_markdown("", "https://example.com/") == ""

    def test_script_tags_stripped(self):
        from src.scraper import html_to_markdown
        html = "<p>text</p><script>alert('xss')</script>"
        result = html_to_markdown(html, "https://example.com/")
        assert "alert" not in result

    def test_style_tags_stripped(self):
        from src.scraper import html_to_markdown
        html = "<p>text</p><style>body { color: red; }</style>"
        result = html_to_markdown(html, "https://example.com/")
        assert "color" not in result

    def test_relative_links_made_absolute(self):
        from src.scraper import html_to_markdown
        html = '<a href="/hc/en-us/articles/123">Link</a>'
        result = html_to_markdown(html, "https://support.optisigns.com/")
        assert "https://support.optisigns.com/hc/en-us/articles/123" in result

    def test_base64_images_removed(self):
        from src.scraper import html_to_markdown
        html = '<img src="data:image/png;base64,AAAA"><p>text</p>'
        result = html_to_markdown(html, "https://example.com/")
        assert "base64" not in result
        assert "data:image" not in result

    def test_absolute_images_preserved(self):
        from src.scraper import html_to_markdown
        html = '<img src="https://cdn.example.com/img.png"><p>text</p>'
        result = html_to_markdown(html, "https://example.com/")
        assert "https://cdn.example.com/img.png" in result

    def test_heading_conversion(self):
        from src.scraper import html_to_markdown
        html = "<h1>Title</h1><h2>Subtitle</h2>"
        result = html_to_markdown(html, "https://example.com/")
        assert "# Title" in result
        assert "## Subtitle" in result

    def test_list_conversion(self):
        from src.scraper import html_to_markdown
        html = "<ul><li>Item 1</li><li>Item 2</li></ul>"
        result = html_to_markdown(html, "https://example.com/")
        assert "Item 1" in result
        assert "Item 2" in result


class TestSaveArticle:
    def test_creates_md_file(self, tmp_path):
        from src.scraper import save_article
        article = {
            "title": "How to Add YouTube",
            "body": "<p>Follow these steps.</p>",
            "html_url": "https://support.optisigns.com/hc/123",
        }
        slug, filepath = save_article(article, str(tmp_path))
        assert Path(filepath).exists()
        assert filepath.endswith(".md")

    def test_slug_is_correct(self, tmp_path):
        from src.scraper import save_article
        article = {
            "title": "How to Add YouTube",
            "body": "<p>Steps.</p>",
            "html_url": "https://example.com/",
        }
        slug, _ = save_article(article, str(tmp_path))
        assert slug == "how-to-add-youtube"

    def test_file_contains_title_as_h1(self, tmp_path):
        from src.scraper import save_article
        article = {
            "title": "My Article",
            "body": "<p>Content here.</p>",
            "html_url": "https://example.com/",
        }
        _, filepath = save_article(article, str(tmp_path))
        content = Path(filepath).read_text(encoding="utf-8")
        assert "# My Article" in content

    def test_file_contains_body_content(self, tmp_path):
        from src.scraper import save_article
        article = {
            "title": "Test",
            "body": "<p>Unique content abc123</p>",
            "html_url": "https://example.com/",
        }
        _, filepath = save_article(article, str(tmp_path))
        content = Path(filepath).read_text(encoding="utf-8")
        assert "Unique content abc123" in content

    def test_creates_output_dir_if_missing(self, tmp_path):
        from src.scraper import save_article
        subdir = tmp_path / "new_subdir"
        article = {
            "title": "Test",
            "body": "<p>Body</p>",
            "html_url": "https://example.com/",
        }
        save_article(article, str(subdir))
        assert subdir.exists()

    def test_empty_body_creates_file_with_h1(self, tmp_path):
        from src.scraper import save_article
        article = {
            "title": "Empty Body Article",
            "body": "",
            "html_url": "https://example.com/",
        }
        slug, filepath = save_article(article, str(tmp_path))
        content = Path(filepath).read_text(encoding="utf-8")
        assert "# Empty Body Article" in content


class TestRunScraperDeltaLogic:
    """Test run_scraper() delta-sync using mocked fetch_all_articles."""

    def _make_article(self, article_id: int, title: str, body: str = "<p>Body</p>") -> dict:
        return {
            "id": article_id,
            "title": title,
            "html_url": f"https://support.optisigns.com/hc/{article_id}",
            "updated_at": "2026-01-01T00:00:00Z",
            "body": body,
        }

    @patch("src.scraper.fetch_all_articles")
    @patch("src.scraper.save_state")
    @patch("src.scraper.load_state")
    def test_new_articles_are_saved(self, mock_load, mock_save, mock_fetch, tmp_path):
        import src.scraper as scraper_module
        mock_load.return_value = {"scraped": {}}
        mock_fetch.return_value = [self._make_article(1, "Article One")]

        results = scraper_module.run_scraper(str(tmp_path))

        assert len(results) == 1
        assert scraper_module.SCRAPER_STATS["added"] == 1
        assert scraper_module.SCRAPER_STATS["skipped"] == 0

    @patch("src.scraper.fetch_all_articles")
    @patch("src.scraper.save_state")
    @patch("src.scraper.load_state")
    def test_unchanged_article_is_skipped(self, mock_load, mock_save, mock_fetch, tmp_path):
        import src.scraper as scraper_module
        from src.utils import compute_md5

        body = "<p>Body content</p>"
        content_hash = compute_md5(body)
        article = self._make_article(42, "Same Article", body)

        # Simulate file already exists
        from src.utils import slugify
        slug = slugify("Same Article")
        (tmp_path / f"{slug}.md").write_text("# Same Article\n\nBody content\n", encoding="utf-8")

        mock_load.return_value = {"scraped": {"42": content_hash}}
        mock_fetch.return_value = [article]

        scraper_module.run_scraper(str(tmp_path))

        assert scraper_module.SCRAPER_STATS["skipped"] == 1
        assert scraper_module.SCRAPER_STATS["added"] == 0

    @patch("src.scraper.fetch_all_articles")
    @patch("src.scraper.save_state")
    @patch("src.scraper.load_state")
    def test_updated_article_increments_updated_stat(self, mock_load, mock_save, mock_fetch, tmp_path):
        import src.scraper as scraper_module
        from src.utils import compute_md5

        old_body = "<p>Old body</p>"
        new_body = "<p>New body changed</p>"
        article = self._make_article(99, "Updated Article", new_body)

        # Previous hash differs → updated
        mock_load.return_value = {"scraped": {"99": compute_md5(old_body)}}
        mock_fetch.return_value = [article]

        scraper_module.run_scraper(str(tmp_path))

        assert scraper_module.SCRAPER_STATS["updated"] == 1
        assert scraper_module.SCRAPER_STATS["added"] == 0

    @patch("src.scraper.fetch_all_articles")
    @patch("src.scraper.save_state")
    @patch("src.scraper.load_state")
    def test_article_with_no_body_is_skipped(self, mock_load, mock_save, mock_fetch, tmp_path):
        import src.scraper as scraper_module
        mock_load.return_value = {"scraped": {}}
        mock_fetch.return_value = [
            {"id": 1, "title": "No Body", "html_url": "https://example.com/", "updated_at": "", "body": ""},
        ]

        scraper_module.run_scraper(str(tmp_path))

        assert scraper_module.SCRAPER_STATS["skipped"] == 1

    @patch.dict(os.environ, {"SCRAPER_MAX_ARTICLES": "2"})
    @patch("src.scraper.fetch_all_articles")
    @patch("src.scraper.save_state")
    @patch("src.scraper.load_state")
    def test_max_articles_env_limits_results(self, mock_load, mock_save, mock_fetch, tmp_path):
        import src.scraper as scraper_module
        mock_load.return_value = {"scraped": {}}
        mock_fetch.return_value = [
            self._make_article(i, f"Article {i}") for i in range(10)
        ]

        results = scraper_module.run_scraper(str(tmp_path))

        # Should process only 2 articles
        assert len(results) <= 2

    @patch("src.scraper.fetch_all_articles")
    @patch("src.scraper.save_state")
    @patch("src.scraper.load_state")
    def test_multiple_articles_stats_correct(self, mock_load, mock_save, mock_fetch, tmp_path):
        import src.scraper as scraper_module
        from src.utils import compute_md5, slugify

        old_hash = compute_md5("<p>old</p>")

        # Article 1: new (not in state)
        # Article 2: unchanged (same hash + file exists)
        # Article 3: updated (different hash)
        articles = [
            self._make_article(1, "New Article"),
            self._make_article(2, "Unchanged Article", "<p>same</p>"),
            self._make_article(3, "Updated Article", "<p>new content</p>"),
        ]

        # Create file for article 2 (unchanged)
        slug2 = slugify("Unchanged Article")
        (tmp_path / f"{slug2}.md").write_text("# Unchanged Article\n", encoding="utf-8")

        mock_load.return_value = {
            "scraped": {
                "2": compute_md5("<p>same</p>"),   # unchanged
                "3": compute_md5("<p>old content</p>"),  # different → updated
            }
        }
        mock_fetch.return_value = articles

        scraper_module.run_scraper(str(tmp_path))

        assert scraper_module.SCRAPER_STATS["added"] == 1    # article 1
        assert scraper_module.SCRAPER_STATS["skipped"] == 1  # article 2
        assert scraper_module.SCRAPER_STATS["updated"] == 1  # article 3


# ===========================================================================
# 3. src/uploader.py (mocked Gemini client)
# ===========================================================================

class TestUploadMarkdownFiles:

    def _write_md_files(self, directory: Path, names: list[str]) -> list[Path]:
        """Helper: write dummy .md files, return list of paths."""
        paths = []
        for name in names:
            p = directory / name
            p.write_text(f"# {name}\n\nContent of {name}\n", encoding="utf-8")
            paths.append(p)
        return paths

    @patch("src.uploader.GENAI_CLIENT")
    @patch("src.uploader.get_or_create_store")
    @patch("src.uploader.load_state")
    @patch("src.uploader.save_state")
    def test_uploads_new_files(self, mock_save, mock_load, mock_store, mock_client, tmp_path):
        from src.uploader import upload_markdown_files

        paths = self._write_md_files(tmp_path, ["a.md", "b.md"])
        mock_store.return_value = "fileSearchStores/test-store"
        mock_load.return_value = {"uploaded": {}, "store_name": "fileSearchStores/test-store"}
        mock_client.file_search_stores.upload_to_file_search_store = MagicMock(return_value=True)

        result = upload_markdown_files(paths=paths)
        assert result == 2

    @patch("src.uploader.GENAI_CLIENT")
    @patch("src.uploader.get_or_create_store")
    @patch("src.uploader.load_state")
    @patch("src.uploader.save_state")
    def test_skips_unchanged_files(self, mock_save, mock_load, mock_store, mock_client, tmp_path):
        from src.uploader import upload_markdown_files
        from src.utils import compute_md5

        content = "# File\n\nContent of file.md\n"
        p = tmp_path / "file.md"
        p.write_text(content, encoding="utf-8")
        existing_hash = compute_md5(content)

        mock_store.return_value = "fileSearchStores/test-store"
        mock_load.return_value = {"uploaded": {"file.md": existing_hash}}
        mock_client.file_search_stores.upload_to_file_search_store = MagicMock()

        result = upload_markdown_files(paths=[p])

        # Should skip, not upload
        assert result == 0
        mock_client.file_search_stores.upload_to_file_search_store.assert_not_called()

    @patch("src.uploader.GENAI_CLIENT")
    @patch("src.uploader.get_or_create_store")
    @patch("src.uploader.load_state")
    @patch("src.uploader.save_state")
    def test_force_uploads_even_if_unchanged(self, mock_save, mock_load, mock_store, mock_client, tmp_path):
        from src.uploader import upload_markdown_files
        from src.utils import compute_md5

        content = "# File\n\nContent of file.md\n"
        p = tmp_path / "file.md"
        p.write_text(content, encoding="utf-8")
        existing_hash = compute_md5(content)

        mock_store.return_value = "fileSearchStores/test-store"
        mock_load.return_value = {"uploaded": {"file.md": existing_hash}}
        mock_client.file_search_stores.upload_to_file_search_store = MagicMock(return_value=True)

        result = upload_markdown_files(paths=[p], force=True)
        assert result == 1

    @patch("src.uploader.GENAI_CLIENT")
    @patch("src.uploader.get_or_create_store")
    @patch("src.uploader.load_state")
    @patch("src.uploader.save_state")
    def test_returns_zero_for_empty_paths(self, mock_save, mock_load, mock_store, mock_client):
        from src.uploader import upload_markdown_files

        mock_store.return_value = "fileSearchStores/test-store"
        mock_load.return_value = {"uploaded": {}}

        result = upload_markdown_files(paths=[])
        assert result == 0

    @patch("src.uploader.GENAI_CLIENT")
    @patch("src.uploader.get_or_create_store")
    @patch("src.uploader.load_state")
    @patch("src.uploader.save_state")
    def test_none_paths_reads_from_data_dir(self, mock_save, mock_load, mock_store, mock_client, tmp_path):
        from src.uploader import upload_markdown_files
        import src.uploader as uploader_module

        # Write 2 md files in tmp DATA_DIR
        (tmp_path / "x.md").write_text("# X\ncontent", encoding="utf-8")
        (tmp_path / "y.md").write_text("# Y\ncontent", encoding="utf-8")

        original_data_dir = uploader_module.DATA_DIR
        uploader_module.DATA_DIR = tmp_path

        mock_store.return_value = "fileSearchStores/test-store"
        mock_load.return_value = {"uploaded": {}}
        mock_client.file_search_stores.upload_to_file_search_store = MagicMock(return_value=True)

        try:
            result = upload_markdown_files(paths=None)
            assert result == 2
        finally:
            uploader_module.DATA_DIR = original_data_dir


# ===========================================================================
# 4. src/assistant.py (mocked Gemini client)
# ===========================================================================

class TestAskOptibot:

    def _make_mock_response(self, text: str, urls: list[str] = None):
        """Build a fake Gemini response object."""
        response = MagicMock()
        response.text = text
        candidate = MagicMock()
        grounding = MagicMock()

        if urls:
            chunks = []
            for url in urls:
                chunk = MagicMock()
                web = MagicMock()
                web.uri = url
                chunk.web = web
                chunk.retrieved_context = None
                chunks.append(chunk)
            grounding.grounding_chunks = chunks
        else:
            grounding.grounding_chunks = []

        candidate.grounding_metadata = grounding
        response.candidates = [candidate]
        return response

    @patch("src.assistant.load_state")
    @patch("src.assistant.GENAI_CLIENT")
    def test_returns_answer_text(self, mock_client, mock_load_state):
        from src.assistant import ask_optibot

        mock_load_state.return_value = {"store_name": "fileSearchStores/test-store"}
        mock_client.models.generate_content.return_value = self._make_mock_response("Here is the answer.")

        result = ask_optibot("How do I add a YouTube video?")
        assert "Here is the answer." in result

    @patch("src.assistant.load_state")
    @patch("src.assistant.GENAI_CLIENT")
    def test_appends_citation_urls(self, mock_client, mock_load_state):
        from src.assistant import ask_optibot

        mock_load_state.return_value = {"store_name": "fileSearchStores/test-store"}
        url = "https://support.optisigns.com/hc/en-us/articles/123"
        mock_client.models.generate_content.return_value = self._make_mock_response(
            "Answer text", urls=[url]
        )

        result = ask_optibot("test question")
        assert f"Article URL: {url}" in result

    @patch("src.assistant.load_state")
    @patch("src.assistant.GENAI_CLIENT")
    def test_deduplicates_urls(self, mock_client, mock_load_state):
        from src.assistant import ask_optibot

        mock_load_state.return_value = {"store_name": "fileSearchStores/test-store"}
        url = "https://support.optisigns.com/hc/en-us/articles/123"
        mock_client.models.generate_content.return_value = self._make_mock_response(
            "Answer", urls=[url, url, url]
        )

        result = ask_optibot("test")
        assert result.count(f"Article URL: {url}") == 1

    @patch("src.assistant.load_state")
    @patch("src.assistant.GENAI_CLIENT")
    def test_max_3_citation_urls(self, mock_client, mock_load_state):
        from src.assistant import ask_optibot

        mock_load_state.return_value = {"store_name": "fileSearchStores/test-store"}
        urls = [f"https://example.com/article/{i}" for i in range(10)]
        mock_client.models.generate_content.return_value = self._make_mock_response(
            "Answer", urls=urls
        )

        result = ask_optibot("test")
        count = result.count("Article URL:")
        assert count <= 3

    @patch("src.assistant.load_state")
    @patch("src.assistant.GENAI_CLIENT")
    def test_no_urls_when_no_grounding(self, mock_client, mock_load_state):
        from src.assistant import ask_optibot

        mock_load_state.return_value = {"store_name": "fileSearchStores/test-store"}
        mock_client.models.generate_content.return_value = self._make_mock_response("Just text", urls=[])

        result = ask_optibot("test")
        assert "Article URL:" not in result

    @patch("src.assistant.load_state")
    def test_raises_without_store_name(self, mock_load_state):
        from src.assistant import ask_optibot

        mock_load_state.return_value = {}  # No store_name

        with pytest.raises(RuntimeError, match="File Search Store name not found"):
            ask_optibot("test")

    @patch("src.assistant.load_state")
    @patch("src.assistant.GENAI_CLIENT")
    def test_returns_error_string_on_exception(self, mock_client, mock_load_state):
        from src.assistant import ask_optibot

        mock_load_state.return_value = {"store_name": "fileSearchStores/test-store"}
        mock_client.models.generate_content.side_effect = Exception("API Error")

        result = ask_optibot("test")
        assert "error" in result.lower()


# ===========================================================================
# 5. System Instruction Validation
# ===========================================================================

class TestSystemInstruction:
    def test_contains_all_four_rules(self):
        from src.assistant import SYSTEM_INSTRUCTION
        assert "OptiBot" in SYSTEM_INSTRUCTION
        assert "helpful, factual, concise" in SYSTEM_INSTRUCTION
        assert "uploaded docs" in SYSTEM_INSTRUCTION
        assert "5 bullet" in SYSTEM_INSTRUCTION
        assert "Article URL:" in SYSTEM_INSTRUCTION

    def test_contains_ui_navigation_hint(self):
        from src.assistant import SYSTEM_INSTRUCTION
        assert "Files/Assets" in SYSTEM_INSTRUCTION or "Create" in SYSTEM_INSTRUCTION

    def test_contains_assign_to_screen_reminder(self):
        from src.assistant import SYSTEM_INSTRUCTION
        lower = SYSTEM_INSTRUCTION.lower()
        assert "screen" in lower or "playlist" in lower


# ===========================================================================
# 6. main.py pipeline logic
# ===========================================================================

class TestMainPipelineArgs:
    """Test the argument parsing and pipeline flow of main.py without real I/O."""

    @patch("src.scraper.scrape_articles", return_value=[])
    @patch("src.uploader.upload_markdown_files", return_value=0)
    @patch("sys.argv", ["optibot"])
    def test_default_run_calls_scrape_and_upload(self, mock_upload, mock_scrape):
        from main import main
        result = main()
        assert result == 0
        mock_scrape.assert_called_once()
        mock_upload.assert_called_once()

    @patch("src.scraper.scrape_articles", return_value=[])
    @patch("src.uploader.upload_markdown_files", return_value=0)
    @patch("sys.argv", ["optibot", "--scrape"])
    def test_scrape_only_flag_skips_upload(self, mock_upload, mock_scrape):
        from main import main
        result = main()
        assert result == 0
        mock_scrape.assert_called_once()
        mock_upload.assert_not_called()

    @patch("src.scraper.scrape_articles", return_value=[])
    @patch("src.uploader.upload_markdown_files", return_value=0)
    @patch("sys.argv", ["optibot", "--upload"])
    def test_upload_only_flag_skips_scrape(self, mock_upload, mock_scrape):
        from main import main
        result = main()
        assert result == 0
        mock_scrape.assert_not_called()
        mock_upload.assert_called_once()

    @patch("src.scraper.scrape_articles", return_value=[])
    @patch("src.uploader.upload_markdown_files", return_value=0)
    @patch("sys.argv", ["optibot", "--force"])
    def test_force_flag_passes_to_scraper(self, mock_upload, mock_scrape):
        from main import main
        main()
        mock_scrape.assert_called_once_with(force=True)

    @patch("src.assistant.interactive_loop")
    @patch("src.scraper.scrape_articles", return_value=[])
    @patch("src.uploader.upload_markdown_files", return_value=0)
    @patch("sys.argv", ["optibot", "--chat"])
    def test_chat_flag_launches_assistant(self, mock_upload, mock_scrape, mock_chat):
        from main import main
        main()
        mock_chat.assert_called_once()

    @patch("src.scraper.scrape_articles", return_value=[])
    @patch("src.uploader.upload_markdown_files", return_value=5)
    @patch("sys.argv", ["optibot"])
    def test_main_returns_zero_on_success(self, mock_upload, mock_scrape):
        from main import main
        assert main() == 0


class TestParseArgs:
    def test_no_args_all_false(self):
        from main import parse_args
        with patch("sys.argv", ["optibot"]):
            args = parse_args()
        assert args.force is False
        assert args.scrape is False
        assert args.upload is False
        assert args.chat is False

    def test_force_arg(self):
        from main import parse_args
        with patch("sys.argv", ["optibot", "--force"]):
            args = parse_args()
        assert args.force is True

    def test_chat_arg(self):
        from main import parse_args
        with patch("sys.argv", ["optibot", "--chat"]):
            args = parse_args()
        assert args.chat is True


# ===========================================================================
# 7. Integration-style: Delta sync end-to-end (file system only)
# ===========================================================================

class TestDeltaSyncEndToEnd:
    """End-to-end delta sync test using temp directory and mocked HTTP."""

    @patch("src.scraper.fetch_all_articles")
    @patch("src.scraper.load_state")
    @patch("src.scraper.save_state")
    def test_full_cycle_new_then_skip(self, mock_save, mock_load, mock_fetch, tmp_path):
        """First run: saves article. Second run with same content: skips it."""
        import src.scraper as scraper_module
        from src.utils import compute_md5, slugify

        body = "<p>How to add YouTube video to OptiSigns.</p>"
        article = {
            "id": 7777,
            "title": "How to Add YouTube",
            "html_url": "https://support.optisigns.com/hc/en-us/articles/7777",
            "updated_at": "2026-01-01T00:00:00Z",
            "body": body,
        }

        # ── First run: empty state ──────────────────────────────────────────
        mock_load.return_value = {"scraped": {}}
        mock_fetch.return_value = [article]
        scraper_module.run_scraper(str(tmp_path))

        assert scraper_module.SCRAPER_STATS["added"] == 1
        assert scraper_module.SCRAPER_STATS["skipped"] == 0

        # Simulate state being saved after first run
        slug = slugify("How to Add YouTube")
        saved_state = {"scraped": {"7777": compute_md5(body)}}

        # ── Second run: same content, state reflects previous run ──────────
        file_path = tmp_path / f"{slug}.md"
        assert file_path.exists()  # File was created in first run

        mock_load.return_value = saved_state
        scraper_module.run_scraper(str(tmp_path))

        assert scraper_module.SCRAPER_STATS["skipped"] == 1
        assert scraper_module.SCRAPER_STATS["added"] == 0
