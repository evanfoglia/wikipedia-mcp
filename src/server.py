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
from datetime import datetime, timedelta, timezone
from html import unescape
from typing import Optional

import requests

API_VERSION = "2025-06-18"
SERVER_NAME = "wikipedia-mcp"
SERVER_VERSION = "1.1.6"

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
    try:
        limit = max(1, min(int(limit), 20))
    except (TypeError, ValueError):
        limit = 5  # fall back to default on garbage input
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


def article_extract(title: str, lang: str = "en") -> str:
    """Get a Wikipedia article's full plain-text extract by title (vs `summary`).

    Uses the MediaWiki Action API `prop=extracts` with `explaintext=1` to return
    the full article body as plain text — typically several paragraphs, much
    longer than `summary`'s short extract. Complements `summary`: use `summary`
    for the lead + thumbnail, `article_extract` when you want to read more
    without parsing HTML.
    """
    params = {
        "action": "query",
        "prop": "extracts",
        "explaintext": 1,
        "exsectionformat": "plain",
        "titles": title,
        "format": "json",
        "origin": "*",
    }
    resp = _get(_wiki(lang), params=params)
    if resp.status_code == 404:
        return f"Article '{title}' not found on Wikipedia."
    resp.raise_for_status()
    data = resp.json()
    pages = data.get("query", {}).get("pages", {})
    page = next(iter(pages.values()), {}) if pages else {}
    # MediaWiki Action API returns 200 OK with a "missing" marker for
    # non-existent pages rather than a 404 HTTP status. Detect that
    # explicitly so users see the same "not found" message as `summary`.
    if not page or "missing" in page:
        return f"Article '{title}' not found on Wikipedia."
    extract = (page.get("extract") or "").strip()
    title_out = (page.get("title") or title) if page else title
    if not extract:
        return f"No extract available for '{title_out}'."
    desktop_url = f"https://{lang}.wikipedia.org/wiki/{_slug(title_out)}"
    return f"## {title_out}\n\n{extract}\n\n[Read more →]({desktop_url})"


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


def on_this_day(lang: str = "en", count: int = 5) -> str:
    """Get historical events that happened on today's date from Wikipedia.

    Returns a random sample of events from Wikipedia's "On This Day" feed
    for the current UTC date. Pairs well with featured_article for daily
    content hooks — e.g. "today in history" newsletter intros.
    """
    try:
        count = max(1, min(int(count), 10))
    except (TypeError, ValueError):
        count = 5
    today_mm_dd = datetime.now(timezone.utc).strftime("%m/%d")
    resp = _get(f"{_base(lang)}/feed/onthisday/events/{today_mm_dd}")
    if resp.status_code == 404:
        return f"No 'on this day' events available for {lang}.wikipedia.org today."
    resp.raise_for_status()
    events = resp.json().get("events", [])
    if not events:
        return f"No historical events found for today on {lang}.wikipedia.org."

    sample = random.sample(events, min(count, len(events)))
    out = "**On this day:**\n\n"
    for ev in sample:
        year = ev.get("year", "?")
        text = _strip_html(ev.get("text", ""))
        out += f"- **{year}** — {text}\n"
        pages = ev.get("pages", [])
        if pages:
            page_title = pages[0].get("title", "")
            if page_title:
                out += (
                    f"  [Read on Wikipedia]"
                    f"(https://{lang}.wikipedia.org/wiki/{page_title})\n"
                )
    return out


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y/%m/%d")


def links(title: str, limit: int = 20, lang: str = "en") -> str:
    """List Wikipedia article links (outgoing internal links) from a page.

    Returns the first N article titles that an article links to (the
    "see also" network in raw form, no filtering by section). Useful
    for graph-style discovery — e.g. given "Tyrannosaurus", see which
    genera, paleontologists, formations, and anatomical terms it
    references. Complements `categories` (taxonomy) and `search`
    (text-based) — `links` shows what the article itself points to.
    Filters to main namespace (ns=0) so talk/user/etc. don't pollute
    the result.
    """
    try:
        limit = max(1, min(int(limit), 50))
    except (TypeError, ValueError):
        limit = 20
    params = {
        "action": "query",
        "prop": "links",
        "titles": title,
        "pllimit": limit,
        "plnamespace": 0,
        "format": "json",
        "origin": "*",
    }
    resp = _get(_wiki(lang), params=params)
    if resp.status_code == 404:
        return f"Article '{title}' not found on Wikipedia."
    resp.raise_for_status()
    data = resp.json()
    pages = data.get("query", {}).get("pages", {})
    if not pages:
        return f"No links found for '{title}'."

    page = next(iter(pages.values()))
    if page.get("missing") is not None:
        return f"Article '{title}' not found on Wikipedia."
    out_links = page.get("links", [])
    if not out_links:
        return f"No links found for '{page.get('title', title)}'."

    page_title = page.get("title", title)
    out = f"**Links from \"{page_title}\":**\n\n"
    for lnk in out_links:
        name = lnk.get("title", "").strip()
        if name:
            out += f"- {name}\n"
    out += (
        f"\n[View article]"
        f"(https://{lang}.wikipedia.org/wiki/{_slug(page_title)})"
    )
    return out


def categories(title: str, limit: int = 20, lang: str = "en") -> str:
    """List Wikipedia categories for an article.

    Returns the Wikipedia categories an article belongs to (e.g.
    "Late Cretaceous dinosaurs", "Articles containing Latin-language text").
    Useful for taxonomy-based discovery — finding related topics that
    don't show up in text search. Hidden/maintenance categories are
    filtered out so the result is high-signal.
    """
    try:
        limit = max(1, min(int(limit), 50))
    except (TypeError, ValueError):
        limit = 20
    params = {
        "action": "query",
        "prop": "categories",
        "titles": title,
        "cllimit": limit,
        "clshow": "!hidden",
        "clsort": "sortkey",
        "format": "json",
        "origin": "*",
    }
    resp = _get(_wiki(lang), params=params)
    if resp.status_code == 404:
        return f"Article '{title}' not found on Wikipedia."
    resp.raise_for_status()
    data = resp.json()
    pages = data.get("query", {}).get("pages", {})
    if not pages:
        return f"No categories found for '{title}'."

    # API returns pages as {pageid: {...}}; missing pages have id=-1
    page = next(iter(pages.values()))
    if page.get("missing") is not None or page.get("title", "") == "" and "categories" not in page:
        return f"Article '{title}' not found on Wikipedia."
    cats = page.get("categories", [])
    if not cats:
        return f"No categories found for '{page.get('title', title)}'."

    page_title = page.get("title", title)
    out = f"**Categories for \"{page_title}\":**\n\n"
    for cat in cats:
        # Strip "Category:" prefix for cleaner display
        name = cat.get("title", "").replace("Category:", "", 1)
        if name:
            out += f"- {name}\n"
    out += (
        f"\n[View article]"
        f"(https://{lang}.wikipedia.org/wiki/{_slug(page_title)})"
    )
    return out


def pageviews(title: str, start: str = "", end: str = "", lang: str = "en") -> str:
    """Get daily view counts for a Wikipedia article over a date range.

    Uses Wikimedia's pageviews REST API (per-article, all-access, daily
    granularity). Useful for popularity research, trending topics, and
    historical interest — e.g. "how is X trending this week?" or
    "what was the spike on date Y?".

    Returns a markdown table with daily views, total, and daily average.
    Default window is the last 7 days ending yesterday (UTC). The
    article must have measurable traffic — very new or very niche
    articles may return 404 from the pageviews API.
    """
    if not title or not title.strip():
        return "Error: title is required."

    # Validate lang (use SUPPORTED_LANGS so the URL is consistent and
    # falls back to "en" rather than producing a 404 for typos).
    lang = lang if lang in SUPPORTED_LANGS else "en"

    # Default dates: 7-day window ending yesterday UTC.
    if end == "":
        end_dt = datetime.now(timezone.utc) - timedelta(days=1)
        end = end_dt.strftime("%Y%m%d")
    if start == "":
        try:
            end_dt = datetime.strptime(end, "%Y%m%d")
        except ValueError:
            return f"Error: end date must be in YYYYMMDD format (got '{end}')"
        start = (end_dt - timedelta(days=6)).strftime("%Y%m%d")

    try:
        datetime.strptime(start, "%Y%m%d")
        datetime.strptime(end, "%Y%m%d")
    except ValueError:
        return f"Error: dates must be in YYYYMMDD format (got start='{start}', end='{end}')"

    if start > end:
        return f"Error: start date {start} is after end date {end}"

    encoded_title = _slug(title)
    # Pageviews API is a cross-wiki metric hosted centrally on wikimedia.org,
    # not on the per-language wiki. Use wikimedia.org as the base regardless
    # of `lang`; the language-specific project (e.g. "en.wikipedia") lives in
    # the URL path, not the host.
    url = (
        f"https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
        f"{lang}.wikipedia/all-access/user/{encoded_title}/daily/{start}00/{end}00"
    )

    try:
        resp = _get(url)
    except requests.RequestException as e:
        return f"Error fetching pageviews: {e}"

    if resp.status_code == 404:
        return (
            f"No pageviews data found for '{title}' in {lang}.wikipedia "
            f"between {start} and {end}. Article may not exist or have "
            f"insufficient history."
        )
    if resp.status_code != 200:
        return f"Error: pageviews API returned {resp.status_code} for '{title}'."

    data = resp.json()
    items = data.get("items", [])

    if not items:
        return f"No pageviews found for '{title}' in {lang} between {start} and {end}."

    total = sum(item["views"] for item in items)
    avg = total // len(items) if items else 0

    page_title = items[0].get("article", title).replace("_", " ")

    out = f'**Pageviews for "{page_title}"** ({lang}.wikipedia)\n\n'
    out += f"**Period:** {start} → {end} ({len(items)} days)  \n"
    out += f"**Total views:** {total:,}  |  **Daily average:** {avg:,}\n\n"
    out += "| Date | Views |\n"
    out += "|------|------:|\n"

    for item in items:
        ts = item["timestamp"]
        date_str = f"{ts[:4]}-{ts[4:6]}-{ts[6:8]}"
        out += f"| {date_str} | {item['views']:,} |\n"

    out += f"\n[View article](https://{lang}.wikipedia.org/wiki/{encoded_title})"
    return out


def news(lang: str = "en", limit: int = 5) -> str:
    """Get current events from Wikipedia's Main Page 'In the news' section.

    Returns today's curated list of recent notable events from the Main
    Page (Wikipedia's editorially-updated current-events feed). Pairs with
    `featured_article` (today's long-form pick) and `on_this_day`
    (historical) — `news` covers the present tense. The Main Page is
    rendered server-side, then the 'In the news' block is parsed out of
    the HTML so bold + linked article titles become Markdown.
    """
    try:
        limit = max(1, min(int(limit), 10))
    except (TypeError, ValueError):
        limit = 5

    params = {
        "action": "parse",
        "page": "Main_Page",
        "prop": "text",
        "format": "json",
        "origin": "*",
    }
    resp = _get(_wiki(lang), params=params)
    resp.raise_for_status()
    data = resp.json()

    if "error" in data:
        return f"Could not fetch news for {lang}.wikipedia.org today."

    html = data.get("parse", {}).get("text", {}).get("*", "")
    if not html:
        return f"No news available for {lang}.wikipedia.org today."

    # The Main Page renders "In the news" as a sibling <h2> + <div> block:
    # <h2 id="mp-itn-h2">In the news</h2>
    # <div id="mp-itn">...<ul><li>event text with links</li>...</ul></div>
    # Grab everything between that h2 and the next h2 in the page.
    m = re.search(
        r'<h2[^>]*id="mp-itn-h2"[^>]*>.*?</h2>(.*?)<h2',
        html,
        re.DOTALL,
    )
    if not m:
        return f"No 'In the news' section found on {lang}.wikipedia.org today."

    block = m.group(1)
    items = re.findall(r"<li>(.*?)</li>", block, re.DOTALL)
    if not items:
        return f"No news items found on {lang}.wikipedia.org today."

    sample = items[:limit]
    out = "**In the news:**\n\n"
    for item in sample:
        # Bold-linked article: <b><a href="/wiki/Title">Name</a></b>
        # Render as **[Name](url)** so the main subject stands out.
        md = re.sub(
            r'<b>\s*<a[^>]+href="/wiki/([^"#]+)"[^>]*>([^<]+)</a>\s*</b>',
            lambda mm: f'**[{mm.group(2)}](https://{lang}.wikipedia.org/wiki/{mm.group(1)})**',
            item,
        )
        # Plain wiki links: [Name](url)
        md = re.sub(
            r'<a[^>]+href="/wiki/([^"#]+)"[^>]*>([^<]+)</a>',
            lambda mm: f'[{mm.group(2)}](https://{lang}.wikipedia.org/wiki/{mm.group(1)})',
            md,
        )
        # Italics (e.g. "(pictured)") stay as *text*
        md = re.sub(r"<i>([^<]*)</i>", r"*\1*", md)
        # Strip any remaining tags
        md = re.sub(r"<[^>]+>", "", md)
        md = unescape(md)
        md = re.sub(r"\s+", " ", md).strip()
        if md:
            out += f"- {md}\n"

    out += f"\n[Wikipedia Main Page](https://{lang}.wikipedia.org/wiki/Main_Page)"
    return out


def top_reads(date: str = "", limit: int = 10, lang: str = "en") -> str:
    """Get the most-read articles on Wikipedia for a given date.

    Uses Wikimedia's top-pageviews endpoint (all-access, daily) to
    return the top-N most-viewed articles on a language Wikipedia for a
    single day. Default date is yesterday UTC — today's data is
    typically not yet finalized, so defaulting to yesterday reliably
    returns a populated list.

    Filters out non-content namespaces (Main_Page, Special:Search,
    Portal:Current_events, Wikipedia:*, Talk:*, etc.) so the result is
    real articles only. Useful for "what's trending on Wikipedia"
    research and daily content hooks — pairs with `pageviews` (which is
    per-article over a range) for trending-vs-popular comparisons.

    Returns a markdown table: rank, article title (linked), and view
    count for the day.
    """
    lang = lang if lang in SUPPORTED_LANGS else "en"

    if date == "":
        date = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y%m%d")

    try:
        dt = datetime.strptime(date, "%Y%m%d")
    except ValueError:
        return f"Error: date must be in YYYYMMDD format (got '{date}')"

    # Pageviews API is cross-wiki; lang is in the path, not the host.
    url = (
        f"https://wikimedia.org/api/rest_v1/metrics/pageviews/top/"
        f"{lang}.wikipedia/all-access/{dt.year:04d}/{dt.month:02d}/{dt.day:02d}"
    )

    try:
        resp = _get(url)
    except requests.RequestException as e:
        return f"Error fetching top-reads: {e}"

    if resp.status_code == 404:
        return f"No top-reads data found for {lang}.wikipedia on {date}."
    if resp.status_code != 200:
        return f"Error: pageviews API returned {resp.status_code} for {date}."

    data = resp.json()
    items = data.get("items", [])
    if not items:
        return f"No top-reads found for {lang}.wikipedia on {date}."

    all_articles = items[0].get("articles", [])
    if not all_articles:
        return f"No top-reads found for {lang}.wikipedia on {date}."

    # Filter out non-content namespaces so users get real articles, not
    # Wikipedia infrastructure pages. The top-reads feed always ranks
    # Main_Page #1 (millions of daily views), Special:Search #2 (the
    # search bar), and Wikipedia:Featured_pictures high — these are
    # useful as raw telemetry but useless as content hooks.
    SKIP_PREFIXES = (
        "Main_Page", "Special:", "Wikipedia:", "Portal:", "Help:",
        "Talk:", "Template:", "Category:", "MediaWiki:", "User:",
        "File:", "Draft:", "Module:",
    )
    filtered = [
        a for a in all_articles
        if not any(a["article"].startswith(p) for p in SKIP_PREFIXES)
    ]

    try:
        limit = max(1, min(int(limit), 50))
    except (TypeError, ValueError):
        limit = 10

    sample = filtered[:limit]
    if not sample:
        return f"No top-reads articles found for {lang}.wikipedia on {date} (after filtering)."

    pretty_date = f"{date[:4]}-{date[4:6]}-{date[6:8]}"
    out = f"**Top reads on {lang}.wikipedia — {pretty_date}:**\n\n"
    out += "| Rank | Article | Views |\n"
    out += "|------|---------|------:|\n"

    for art in sample:
        title = art["article"].replace("_", " ")
        rank = art.get("rank", "?")
        views = art.get("views", 0)
        slug = art["article"]
        out += (
            f"| {rank} | [{title}]"
            f"(https://{lang}.wikipedia.org/wiki/{slug}) "
            f"| {views:,} |\n"
        )

    out += (
        f"\n[View full list]"
        f"(https://wikimedia.org/api/rest_v1/metrics/pageviews/top/"
        f"{lang}.wikipedia/all-access/{dt.year:04d}/{dt.month:02d}/{dt.day:02d})"
    )
    return out


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
        "name": "article_extract",
        "description": (
            "Get a Wikipedia article's full plain-text extract by title — "
            "much longer than `summary` (typically several paragraphs). "
            "Returns plain text (no HTML). Complements `summary`: use it "
            "when the summary is too brief and you want a fuller reading."
        ),
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
    {
        "name": "on_this_day",
        "description": (
            "Get historical events that happened on today's date (UTC) "
            "from Wikipedia's 'On This Day' feed. Returns a random sample "
            "of events with year + description + Wikipedia link — great "
            "daily content hook alongside featured_article."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "lang": {
                    "type": "string",
                    "description": "Wikipedia language code (default 'en')",
                    "default": "en",
                    "enum": list(SUPPORTED_LANGS),
                },
                "count": {
                    "type": "integer",
                    "description": "Number of events to return (default 5, max 10)",
                    "default": 5,
                },
            },
        },
    },
    {
        "name": "categories",
        "description": (
            "List Wikipedia categories an article belongs to. Useful for "
            "taxonomy-based discovery — finding related topics that don't "
            "appear in text search. Hidden/maintenance categories are filtered out."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Article title (e.g. 'Tyrannosaurus' or 'Albert_Einstein')",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max categories to return (default 20, max 50)",
                    "default": 20,
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
        "name": "links",
        "description": (
            "List outgoing Wikipedia links from an article (the article "
            "network in raw form). Useful for graph-style discovery — "
            "given 'Tyrannosaurus', see which genera, paleontologists, "
            "formations, and anatomical terms it references. Filters to "
            "main namespace so talk/user/etc. don't pollute the result."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Article title (e.g. 'Tyrannosaurus' or 'Albert_Einstein')",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max links to return (default 20, max 50)",
                    "default": 20,
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
        "name": "pageviews",
        "description": (
            "Get daily view counts for a Wikipedia article over a date range "
            "(popularity research, trending topics, historical interest). "
            "Uses Wikimedia's pageviews REST API. Default window is the "
            "last 7 days ending yesterday UTC. Returns total + daily average "
            "+ markdown table of daily views."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Article title (e.g. 'Tyrannosaurus' or 'Albert_Einstein')",
                },
                "start": {
                    "type": "string",
                    "description": "Start date in YYYYMMDD (default: 7 days before end)",
                },
                "end": {
                    "type": "string",
                    "description": "End date in YYYYMMDD (default: yesterday UTC)",
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
        "name": "news",
        "description": (
            "Get current events from Wikipedia's Main Page 'In the news' "
            "section — the editorially-curated list of recent notable "
            "events. Pairs with featured_article (today's long-form pick) "
            "and on_this_day (historical) — news covers the present tense. "
            "Bold-linked article titles become Markdown so the main "
            "subject of each event stands out."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "lang": {
                    "type": "string",
                    "description": "Wikipedia language code (default 'en')",
                    "default": "en",
                    "enum": list(SUPPORTED_LANGS),
                },
                "limit": {
                    "type": "integer",
                    "description": "Max events to return (default 5, max 10)",
                    "default": 5,
                },
            },
        },
    },
    {
        "name": "top_reads",
        "description": (
            "Get the most-read articles on Wikipedia for a given date. "
            "Uses Wikimedia's top-pageviews endpoint (all-access, daily). "
            "Default date is yesterday UTC (today's data is typically "
            "not yet finalized). Filters out non-content namespaces "
            "(Main_Page, Special:Search, Portal:Current_events, "
            "Wikipedia:*, etc.) so the result is real articles only. "
            "Pairs with `pageviews` (per-article over a range) for "
            "trending-vs-popular comparisons — top_reads answers "
            "'what is everyone reading right now' while pageviews "
            "answers 'how is this specific article trending'."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "date": {
                    "type": "string",
                    "description": "Date in YYYYMMDD (default: yesterday UTC)",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max articles to return (default 10, max 50)",
                    "default": 10,
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
    if name == "article_extract":
        return article_extract(**args)
    if name == "on_this_day":
        return on_this_day(**args)
    if name == "categories":
        return categories(**args)
    if name == "links":
        return links(**args)
    if name == "pageviews":
        return pageviews(**args)
    if name == "news":
        return news(**args)
    if name == "top_reads":
        return top_reads(**args)
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