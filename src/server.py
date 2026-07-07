#!/usr/bin/env python3
"""
Wikipedia MCP Server
Provides: search, summary, random, did_you_know, dino_fact
Uses Wikipedia REST API — free, no API key required.

Hand-rolled JSON-RPC stdio MCP for maximum portability (no SDK dependency).
"""

import json
import random
import re
import sys
from typing import Optional

import requests

API_VERSION = "2025-06-18"
SERVER_NAME = "wikipedia-mcp"
SERVER_VERSION = "1.1.0"

# Wikipedia requires a descriptive User-Agent with contact info.
USER_AGENT = (
    f"{SERVER_NAME}/{SERVER_VERSION} "
    "(https://github.com/evanfoglia/wikipedia-mcp; evan@example.com)"
)
DEFAULT_TIMEOUT = 10
SUPPORTED_LANGS = ("en", "de", "es", "fr", "ja", "zh", "pt", "it", "ru", "nl")


def _base(lang: str = "en") -> str:
    lang = lang if lang in SUPPORTED_LANGS else "en"
    return f"https://{lang}.wikipedia.org/api/rest_v1"


def _wiki(lang: str = "en") -> str:
    lang = lang if lang in SUPPORTED_LANGS else "en"
    return f"https://{lang}.wikipedia.org/w/api.php"


def _get(url: str, params: Optional[dict] = None) -> requests.Response:
    return requests.get(
        url, params=params, headers={"User-Agent": USER_AGENT}, timeout=DEFAULT_TIMEOUT
    )


# ---------------------------------------------------------------------------
# Curated dinosaur list — Wikipedia's category pages change shape frequently,
# so we maintain a small high-quality list and let the API expand it.
# ---------------------------------------------------------------------------
DINOS = [
    "Tyrannosaurus", "Triceratops", "Velociraptor", "Spinosaurus",
    "Stegosaurus", "Ankylosaurus", "Brachiosaurus", "Parasaurolophus",
    "Pteranodon", "Mosasaurus", "Allosaurus", "Diplodocus",
    "Carnotaurus", "Giganotosaurus", "Carcharodontosaurus",
    "Acrocanthosaurus", "Argentinosaurus", "Therizinosaurus",
    "Utahraptor", "Oviraptor", "Troodon", "Deinonychus",
    "Dimorphodon", "Quetzalcoatlus", "Plateosaurus", "Coelophysis",
    "Mamenchisaurus", "Styracosaurus", "Protoceratops", "Pentaceratops",
    "Metriacanthosaurus", "Iguanodon", "Maiasaura", "Pachycephalosaurus",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(s: str) -> str:
    return _TAG_RE.sub("", s)


def _slug(title: str) -> str:
    return title.strip().replace(" ", "_")


def _summary_block(data: dict, fallback_title: str) -> str:
    """Render a Wikipedia summary response as Markdown text."""
    title = data.get("title", fallback_title)
    extract = data.get("extract", "No summary available.")
    desc = data.get("description", "")
    thumb = data.get("thumbnail", {}).get("source", "") if data.get("thumbnail") else ""
    desktop_url = (
        data.get("content_urls", {}).get("desktop", {}).get("page", "#")
    )

    out = f"## {title}\n\n{extract}\n\n"
    if desc:
        out += f"*({desc})*\n\n"
    out += f"[Read more →]({desktop_url})"
    if thumb:
        out += f"\n\n![{title}]({thumb})"
    return out


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------
def search_wikipedia(query: str, limit: int = 5, lang: str = "en") -> str:
    """Search Wikipedia for articles matching a query."""
    limit = max(1, min(int(limit), 20))
    params = {
        "action": "query",
        "list": "search",
        "srsearch": query,
        "srlimit": limit,
        "format": "json",
        "origin": "*",
    }
    resp = _get(_wiki(lang), params=params)
    resp.raise_for_status()
    data = resp.json()
    results = data.get("query", {}).get("search", [])
    if not results:
        return f"No results found for '{query}'."

    out = f"**Search results for '{query}':**\n\n"
    for i, page in enumerate(results, 1):
        title = page.get("title", "Unknown")
        snippet = _strip_html(page.get("snippet", ""))
        out += f"{i}. **{title}**\n"
        if snippet:
            out += f"   {snippet[:200]}...\n"
        out += (
            f"   https://{lang}.wikipedia.org/wiki/{_slug(title)}\n\n"
        )
    return out


def get_summary(title: str, lang: str = "en") -> str:
    """Get a Wikipedia article summary + thumbnail by title."""
    resp = _get(f"{_base(lang)}/page/summary/{_slug(title)}")
    if resp.status_code == 404:
        return f"Article '{title}' not found on Wikipedia."
    resp.raise_for_status()
    return _summary_block(resp.json(), fallback_title=title)


def get_random(lang: str = "en") -> str:
    """Get a random Wikipedia article summary."""
    resp = _get(f"{_base(lang)}/page/random/summary")
    resp.raise_for_status()
    return _summary_block(resp.json(), fallback_title="Random Article")


def did_you_know(lang: str = "en") -> str:
    """Get a random 'Did You Know' style fact from Wikipedia."""
    resp = _get(f"{_base(lang)}/page/random/summary")
    resp.raise_for_status()
    data = resp.json()
    fact = data.get("extract", "")
    title = data.get("title", "")
    if not fact:
        return f"Did you know? {title} is a fascinating topic on Wikipedia!"
    desktop_url = (
        data.get("content_urls", {}).get("desktop", {}).get("page", "#")
    )
    return (
        f"**Did you know?**\n\n{fact}\n\n"
        f"*Source: [Wikipedia — {title}]({desktop_url})*"
    )


def dino_fact(species: str = "", lang: str = "en") -> str:
    """
    Get a 'Did You Know' style fact about dinosaurs or prehistoric life.
    If species is provided, returns a fact about that specific dinosaur.
    Otherwise picks a random dinosaur from the curated list.
    """
    if not species:
        species = random.choice(DINOS)

    resp = _get(f"{_base(lang)}/page/summary/{_slug(species)}")
    if resp.status_code == 404:
        # Species not found — pick a random one rather than dumping a search.
        # The curated list gives reliable coverage.
        fallback = random.choice([d for d in DINOS if d.lower() != species.lower()])
        return (
            f"Couldn't find '{species}' on Wikipedia. "
            f"Here's a random dino instead:\n\n"
            f"{dino_fact(fallback, lang=lang)}"
        )
    resp.raise_for_status()
    data = resp.json()
    fact = data.get("extract", "")
    title = data.get("title", species)
    if not fact:
        return f"Not enough data on {title} yet. Try a different species!"
    desktop_url = (
        data.get("content_urls", {}).get("desktop", {}).get("page", "#")
    )
    return (
        f"**Did you know about {title}?**\n\n{fact}\n\n"
        f"*Source: [Wikipedia — {title}]({desktop_url})*"
    )


def featured_article(lang: str = "en") -> str:
    """Get today's Wikipedia Featured Article (great content hook)."""
    resp = _get(f"{_base(lang)}/feed/featured/{_today()}")
    if resp.status_code == 404:
        return f"No featured article available for {lang}.wikipedia.org today."
    resp.raise_for_status()
    payload = resp.json()
    # Feed wraps the article under "tfa" (today's featured article)
    data = payload.get("tfa") or payload
    return _summary_block(data, fallback_title=data.get("title", "Featured Article"))


def _today() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y/%m/%d")


# ---------------------------------------------------------------------------
# Tool registry — schemas declared in one place for clarity
# ---------------------------------------------------------------------------
TOOLS = [
    {
        "name": "search",
        "description": "Search Wikipedia for articles matching a query",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "limit": {
                    "type": "integer",
                    "description": "Max results (default 5, max 20)",
                    "default": 5,
                },
                "lang": {
                    "type": "string",
                    "description": "Wikipedia language code (default 'en')",
                    "default": "en",
                    "enum": list(SUPPORTED_LANGS),
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "summary",
        "description": "Get a Wikipedia article summary + thumbnail by title",
        "inputSchema": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Article title (e.g. 'Tyrannosaurus' or 'Albert_Einstein')",
                },
                "lang": {
                    "type": "string",
                    "description": "Wikipedia language code (default 'en')",
                    "default": "en",
                    "enum": list(SUPPORTED_LANGS),
                },
            },
            "required": ["title"],
        },
    },
    {
        "name": "random",
        "description": "Get a random Wikipedia article summary",
        "inputSchema": {
            "type": "object",
            "properties": {
                "lang": {
                    "type": "string",
                    "description": "Wikipedia language code (default 'en')",
                    "default": "en",
                    "enum": list(SUPPORTED_LANGS),
                },
            },
        },
    },
    {
        "name": "did_you_know",
        "description": "Get a random 'Did You Know' style fact from Wikipedia — great for hooks and general trivia",
        "inputSchema": {
            "type": "object",
            "properties": {
                "lang": {
                    "type": "string",
                    "description": "Wikipedia language code (default 'en')",
                    "default": "en",
                    "enum": list(SUPPORTED_LANGS),
                },
            },
        },
    },
    {
        "name": "dino_fact",
        "description": (
            "Get a 'Did You Know' style fact about dinosaurs or prehistoric life. "
            "Pass a specific species ('Tyrannosaurus', 'Spinosaurus') for a targeted fact, "
            "or call with no arguments for a random dino. Falls back to a random dino "
            "if the requested species isn't found on Wikipedia."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "species": {
                    "type": "string",
                    "description": "Specific dinosaur name (e.g. 'Tyrannosaurus'). Empty for random.",
                    "default": "",
                },
                "lang": {
                    "type": "string",
                    "description": "Wikipedia language code (default 'en')",
                    "default": "en",
                    "enum": list(SUPPORTED_LANGS),
                },
            },
        },
    },
    {
        "name": "featured_article",
        "description": "Get today's Wikipedia Featured Article — a curated long-form pick, perfect for content hooks",
        "inputSchema": {
            "type": "object",
            "properties": {
                "lang": {
                    "type": "string",
                    "description": "Wikipedia language code (default 'en')",
                    "default": "en",
                    "enum": list(SUPPORTED_LANGS),
                },
            },
        },
    },
]


def _call_tool(name: str, args: dict) -> str:
    if name == "search":
        return search_wikipedia(**args)
    if name == "summary":
        return get_summary(**args)
    if name == "random":
        return get_random(**args)
    if name == "did_you_know":
        return did_you_know(**args)
    if name == "dino_fact":
        return dino_fact(**args)
    if name == "featured_article":
        return featured_article(**args)
    return f"Unknown tool: {name}"


# ---------------------------------------------------------------------------
# JSON-RPC stdio loop
# ---------------------------------------------------------------------------
def _reply(msg_id, result):
    print(json.dumps({"jsonrpc": "2.0", "id": msg_id, "result": result}))
    sys.stdout.flush()


def _reply_error(msg_id, code: int, message: str):
    print(
        json.dumps(
            {"jsonrpc": "2.0", "id": msg_id, "error": {"code": code, "message": message}}
        )
    )
    sys.stdout.flush()


def _handle_request(request: dict) -> None:
    method = request.get("method", "")
    msg_id = request.get("id")

    if method == "initialize":
        _reply(
            msg_id,
            {
                "protocolVersion": API_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
            },
        )
        return

    if method == "notifications/initialized":
        # Client signals init complete; nothing to do.
        return

    if method == "tools/list":
        _reply(msg_id, {"tools": TOOLS})
        return

    if method == "tools/call":
        params = request.get("params", {})
        name = params.get("name")
        args = params.get("arguments", {}) or {}
        if not name:
            _reply_error(msg_id, -32602, "Missing tool name")
            return
        try:
            result = _call_tool(name, args)
            _reply(msg_id, {"content": [{"type": "text", "text": str(result)}]})
        except Exception as e:
            _reply_error(msg_id, -32603, f"{type(e).__name__}: {e}")
        return

    # Notifications (no id) — ignore unknown
    if msg_id is None:
        return
    _reply_error(msg_id, -32601, f"Method not found: {method}")


def main() -> int:
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break
            line = line.strip()
            if not line:
                continue
            _handle_request(json.loads(line))
        except json.JSONDecodeError as e:
            print(f"# JSON decode error: {e}", file=sys.stderr)
            sys.stderr.flush()
        except Exception as e:
            print(f"# Loop error: {type(e).__name__}: {e}", file=sys.stderr)
            sys.stderr.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())