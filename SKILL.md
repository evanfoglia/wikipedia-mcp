---
name: wikipedia
version: 1.1.10
description: Access Wikipedia via MCP — search articles, get summaries, random facts, dinosaur facts, today's featured article, today's historical events, article categories, outgoing links, view counts, current news, and most-read articles. Multi-language support (10 wikis). Great for research, content hooks, and general knowledge lookups.
---

# Wikipedia MCP

Access Wikipedia via Model Context Protocol (MCP). No API key required.

## Tools

| Tool | Description |
|------|-------------|
| `search` | Search Wikipedia for articles |
| `summary` | Get article summary + image by title |
| `random` | Random Wikipedia article |
| `did_you_know` | Random "Did You Know" fact |
| `dino_fact` | Dinosaur/prehistory fact (specific species or random) |
| `featured_article` | Today's Wikipedia Featured Article |
| `picture_of_the_day` | Wikimedia Commons' Picture of the Day — curated daily image (default today UTC, optional YYYYMMDD date) |
| `article_extract` | Full plain-text article extract by title (longer than `summary`) |
| `article_sections` | Table of contents (section headings) for an article — navigate before reading the full body |
| `on_this_day` | Historical events that happened on today's date |
| `deaths_on_this_day` | Notable deaths that happened on today's date — companion to `on_this_day` (events) |
| `categories` | List Wikipedia categories an article belongs to |
| `links` | List outgoing Wikipedia links from an article (graph-style discovery) |
| `backlinks` | List incoming Wikipedia links to an article — what links here (inverse of `links`) |
| `external_links` | List external (off-wiki) links from an article — citations, references, primary sources |
| `nearby` | Articles geographically near a location — anchor by article title or lat/lon, distances included |
| `translations` | All language versions of an article (langlinks) — discover what languages it exists in |
| `revisions` | Recent edit history of an article — who edited it, when, edit summaries, byte-size deltas, diff links |
| `pageviews` | Daily view counts for an article (popularity research, trending topics) |
| `news` | Current events from Wikipedia's Main Page "In the news" section |
| `top_reads` | Most-read articles on Wikipedia for a given date (trending discovery) |
| `image` | Lead image for an article — thumbnail + original URLs, no summary text |
| `media_list` | All media (images, videos, audio) in an article — full inventory with type, caption, and thumbnail |
| `quote` | Random notable quote from a curated list of famous authors |

All tools accept an optional `lang` parameter (default `en`; supported: `en`, `de`, `es`, `fr`, `ja`, `zh`, `pt`, `it`, `ru`, `nl`). Note: `quote` accepts the parameter for API consistency but is currently English-only (curated list).

## Installation

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

(Requires Python 3.10+ and `requests>=2.28.0`)

### 2. Find your install path

The MCP server lives at `<install-dir>/src/server.py`.

```bash
ls ~/.openclaw/workspace/skills/wikipedia/src/server.py
```

### 3. Add to mcporter

Add to `~/.openclaw/workspace/config/mcporter.json`:

```json
{
  "mcpServers": {
    "wikipedia": {
      "command": "python3",
      "args": ["<path-to>/src/server.py"]
    }
  }
}
```

Replace `<path-to>` with the actual install location from step 2.

### 4. Test

```bash
mcporter call wikipedia search --args '{"query": "velociraptor", "limit": 5}'
```

## Usage Examples

```
mcporter call wikipedia search --args '{"query": "velociraptor", "limit": 5}'
mcporter call wikipedia summary --args '{"title": "Tyrannosaurus"}'
mcporter call wikipedia dino_fact --args '{"species": "Spinosaurus"}'
mcporter call wikipedia dino_fact
mcporter call wikipedia did_you_know
mcporter call wikipedia featured_article
mcporter call wikipedia picture_of_the_day
mcporter call wikipedia picture_of_the_day --args '{"date": "20260901"}'
mcporter call wikipedia article_extract --args '{"title": "Tyrannosaurus"}'
mcporter call wikipedia article_sections --args '{"title": "Tyrannosaurus"}'
mcporter call wikipedia on_this_day
mcporter call wikipedia on_this_day --args '{"count": 8}'
mcporter call wikipedia deaths_on_this_day
mcporter call wikipedia deaths_on_this_day --args '{"count": 6}'
mcporter call wikipedia categories --args '{"title": "Tyrannosaurus"}'
mcporter call wikipedia categories --args '{"title": "Tyrannosaurus", "limit": 10}'
mcporter call wikipedia links --args '{"title": "Tyrannosaurus"}'
mcporter call wikipedia links --args '{"title": "Tyrannosaurus", "limit": 30}'
mcporter call wikipedia backlinks --args '{"title": "Velociraptor"}'
mcporter call wikipedia backlinks --args '{"title": "Velociraptor", "limit": 30}'
mcporter call wikipedia nearby --args '{"title": "Eiffel Tower"}'
mcporter call wikipedia nearby --args '{"lat": 40.7484, "lon": -73.9857, "radius": 2000}'
mcporter call wikipedia translations --args '{"title": "Tyrannosaurus"}'
mcporter call wikipedia translations --args '{"title": "Tyrannosaurus", "limit": 10}'
mcporter call wikipedia revisions --args '{"title": "Tyrannosaurus"}'
mcporter call wikipedia revisions --args '{"title": "Tyrannosaurus", "limit": 20}'
mcporter call wikipedia pageviews --args '{"title": "Tyrannosaurus"}'
mcporter call wikipedia pageviews --args '{"title": "Python_(programming_language)", "start": "20250101", "end": "20250107"}'
mcporter call wikipedia news
mcporter call wikipedia news --args '{"limit": 8}'
mcporter call wikipedia top_reads
mcporter call wikipedia top_reads --args '{"date": "20260101", "limit": 15}'
mcporter call wikipedia image --args '{"title": "Tyrannosaurus"}'
mcporter call wikipedia media_list --args '{"title": "Tyrannosaurus"}'
mcporter call wikipedia media_list --args '{"title": "Tyrannosaurus", "limit": 50}'
mcporter call wikipedia quote
mcporter call wikipedia summary --args '{"title": "Berlin", "lang": "de"}'
```

## Data Source

Uses Wikipedia's free public REST API — no API key required.

- Search: MediaWiki Action API
- External links: MediaWiki Action API (`prop=extlinks`)
- Summary / Random / Featured / Picture of the Day: REST API v1 (`/api/rest_v1/...`)

## Notes

- User-Agent is `wikipedia-mcp/1.1.13` per Wikipedia API etiquette
- All responses include links back to the source article
- `dino_fact` falls back to a random species if the requested one isn't found (instead of erroring)
- `featured_article` returns today's curated Featured Article — great for daily content hooks
- `picture_of_the_day` returns Wikimedia Commons' Picture of the Day from Wikipedia's featured feed — the visual counterpart to `featured_article`. Accepts an optional `date` (YYYYMMDD, default today UTC) to browse past pictures. Returns the embedded thumbnail preview, file name, photographer/artist, license, description, and links to the full-size image + Commons file page. `image`/`media_list` cover article-specific media; this covers the editorially curated daily pick.
- `article_extract` returns the full plain-text article (vs `summary`'s short extract + thumbnail) — use when you need more than a summary
- `article_sections` returns the article's table of contents — section number, heading text, and nesting level — so callers can navigate long articles (50KB+ body) by picking the section they want before committing to `article_extract`. Pairs with `summary` (lead), `article_sections` (structure), `article_extract` (full body).
- `on_this_day` returns historical events for today's UTC date from Wikipedia's "On This Day" feed — pairs with featured_article for daily "today in history" content hooks
- `deaths_on_this_day` returns notable deaths for today's UTC date — the deaths-only companion to `on_this_day`. Pairs with `on_this_day` (events) and `featured_article` (today's long-form) for a full "today in Wikipedia" daily digest. Useful for "in memoriam" content hooks and obituary-style social posts.
- `categories` returns Wikipedia categories for an article (hidden/maintenance categories filtered) — useful for taxonomy-based discovery beyond text search
- `links` returns the article's outgoing Wikipedia links (main namespace only) — graph-style discovery showing which genera, people, and concepts an article references
- `backlinks` returns the article's incoming Wikipedia links (what links here) — the inverse of `links`. Shows which other articles reference this one (cultural mentions, scientific citations, comparative anatomy pages, etc.). Same main-namespace filtering.
- `nearby` returns Wikipedia articles geographically near a location, with distances — location-based discovery. Anchor by article title (e.g. 'Eiffel Tower', uses that article's coordinates so no geocoding service is needed) or by explicit lat/lon. Radius in meters (default 1000, max 10000), main-namespace only. Useful for travel research and "what's notable around here" questions.
- `translations` returns all language editions of an article (langlinks) — the other-language titles that Wikipedia knows about. Complements the one-way `lang` parameter used by other tools: every tool can query a single language, but only `translations` reveals the article's full language coverage so callers can pick a target language to fetch next. Useful for translation research (full coverage vs. stub languages), cross-language content sourcing, and language-coverage analysis.
- `pageviews` returns daily view counts for an article over a date range (default last 7 days) — popularity research, trending topics, historical interest spikes. Uses Wikimedia's pageviews REST API.
- `news` returns today's editorially-curated current events from Wikipedia's Main Page "In the news" block — pairs with featured_article (today's long-form) and on_this_day (historical) for a full "today in Wikipedia" content hook
- `top_reads` returns the most-viewed articles on Wikipedia for a given date (default yesterday UTC) — answers "what is everyone reading right now" while `pageviews` answers "how is this specific article trending". Filters out Main_Page, Special:Search, Portal:Current_events, etc. so the result is real articles only.
- `image` returns the article's lead image as URLs (300px thumbnail + full-size original) without summary prose — useful for embedding the image elsewhere (cards, slide decks, Telegram hero images). `summary` embeds the thumbnail inline; `image` exposes both URLs separately.
- `media_list` returns every media item (images, videos, audio) the article uses — not just the lead thumbnail. Each entry has file title, type, caption, and thumbnail URL; lead media is marked with 🏆 so callers can skip it when they already have it via `image`. Uses Wikipedia's REST `/page/media-list` endpoint (structured JSON, no HTML parsing). Pairs with `image` (lead only) — use `image` for the headline thumbnail, `media_list` for the full inventory (gallery generation, fact-checking, slide decks, audits).
- Multi-language: pass `lang` to any tool to query de/es/fr/ja/zh/pt/it/ru/nl Wikipedia

## ClawHub

This skill is published on ClawHub as **Wikipedia** under the canonical slug `wikipedia` (1.6k+ downloads, 40 installs as of Aug 20 2026).

Do **NOT** publish to slug `wikipedia-mcp` — that is the abandoned duplicate skill (140 DL, 0 installs, lowercase "wikipedia" display name).

GitHub source: https://github.com/evanfoglia/wikipedia-mcp