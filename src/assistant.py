"""
src/assistant.py – OptiBot RAG Assistant (google-genai 2.x)
Implements RAG query using native Gemini File Search tool.
"""

from __future__ import annotations

import logging
import sys

from .config import (
    GENAI_CLIENT,
    GENERATIVE_MODEL,
    STATE_FILE,
)
from .utils import load_state

logger = logging.getLogger("optibot.assistant")

# Verbatim System Prompt/Instruction
# ---------------------------------------------------------------------------
SYSTEM_INSTRUCTION = (
    "You are OptiBot, the customer-support bot for OptiSigns.com.\n"
    "- Tone: helpful, factual, concise.\n"
    "- Only answer using the uploaded docs.\n"
    "- Max 5 bullet points; else link to the doc.\n"
    '- Cite up to 3 "Article URL:" lines per reply.\n'
    "- UI navigation: Files/Assets → green '+' Create button → Apps → choose app.\n"
    "- Always include the final step: after saving, assign the asset to a "
    "Screen or Playlist (Edit Screen → Content, or add to a Playlist)."
)


def ask_optibot(query: str) -> str:
    """
    RAG pipeline using the Google GenAI SDK's native File Search tool.
    """
    if not GENAI_CLIENT:
        raise RuntimeError("Gemini client not initialised – check GEMINI_API_KEY.")

    state = load_state(str(STATE_FILE))
    store_name = state.get("store_name", "")

    if not store_name:
        raise RuntimeError(
            "File Search Store name not found in state.json. "
            "Please run the uploader or define store_name in state.json."
        )

    try:
        from google.genai import types

        logger.info("Querying Gemini File Search Store: %s", store_name)
        response = GENAI_CLIENT.models.generate_content(
            model=GENERATIVE_MODEL,
            contents=query,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                tools=[
                    types.Tool(
                        file_search=types.FileSearch(
                            file_search_store_names=[store_name]
                        )
                    )
                ]
            )
        )
        
        answer = response.text or ""
        
        # Check for citation source URLs inside grounding metadata
        source_urls = []
        candidate = response.candidates[0] if response.candidates else None
        if candidate and candidate.grounding_metadata:
            metadata = candidate.grounding_metadata
            if metadata.grounding_chunks:
                for chunk in metadata.grounding_chunks:
                    if hasattr(chunk, 'web') and chunk.web and chunk.web.uri:
                        source_urls.append(chunk.web.uri)
                    elif hasattr(chunk, 'retrieved_context') and chunk.retrieved_context:
                        # Fallback try retrieving the title/doc name as reference
                        uri = getattr(chunk.retrieved_context, 'uri', '')
                        if uri:
                            source_urls.append(uri)

        # Unique & format
        if source_urls:
            unique_urls = sorted(list(set(source_urls)))[:3]
            citation_text = "\n\n" + "\n".join(f"Article URL: {url}" for url in unique_urls)
            if "Article URL:" not in answer:
                answer += citation_text
                
        return answer.strip()
    except Exception as exc:
        logger.error("Failed to generate content: %s", exc)
        return f"Sorry, an error occurred while generating the answer: {exc}"


def ask(query: str) -> str:
    return ask_optibot(query)


def run_interactive_cli() -> None:
    """Start an interactive Q&A session in the terminal."""
    print("\n🤖  OptiBot – OptiSigns AI Support Assistant (File Search Store)")
    print("    Type 'exit' or Ctrl-C to quit.\n")
    while True:
        try:
            query = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            break
        if query.lower() in {"exit", "quit", "q"}:
            print("Goodbye!")
            break
        if not query:
            continue
        
        print("\nOptiBot is thinking...")
        answer = ask_optibot(query)
        print(f"\nOptiBot: {answer}\n")


def interactive_loop() -> None:
    run_interactive_cli()


if __name__ == "__main__":
    from src.utils import setup_logging
    setup_logging()
    run_interactive_cli()
