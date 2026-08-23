---
name: wikipedia
version: 1.1.4
description: Access Wikipedia via MCP — search articles, get summaries, random facts, dinosaur facts, today's featured article, today's historical events, and article categories. Multi-language support (10 wikis). Great for research, content hooks, and general knowledge lookups.
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
| `on_this_day` | Historical events that happened on today's date |
| `categories` | List Wikipedia categories an article belongs to |

All tools accept an optional `lang` parameter (default `en`; supported: `en`, `de`, `es`, `fr`, `ja`, `zh`, `pt`, `it`, `ru`, `nl`).

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
mcporter call wikipedia on_this_day
mcporter call wikipedia on_this_day --args '{"count": 8}'
mcporter call wikipedia categories --args '{"title": "Tyrannosaurus"}'
mcporter call wikipedia categories --args '{"title": "Tyrannosaurus", "limit": 10}'
mcporter call wikipedia summary --args '{"title": "Berlin", "lang": "de"}'
```

## Data Source

Uses Wikipedia's free public REST API — no API key required.

- Search: MediaWiki Action API
- Summary / Random / Featured: REST API v1 (`/api/rest_v1/...`)

## Notes

- User-Agent is `wikipedia-mcp/1.1.4` per Wikipedia API etiquette
- All responses include links back to the source article
- `dino_fact` falls back to a random species if the requested one isn't found (instead of erroring)
- `featured_article` returns today's curated Featured Article — great for daily content hooks
- `on_this_day` returns historical events for today's UTC date from Wikipedia's "On This Day" feed — pairs with featured_article for daily "today in history" content hooks
- `categories` returns Wikipedia categories for an article (hidden/maintenance categories filtered) — useful for taxonomy-based discovery beyond text search
- Multi-language: pass `lang` to any tool to query de/es/fr/ja/zh/pt/it/ru/nl Wikipedia

## ClawHub

This skill is published on ClawHub as **Wikipedia** under the canonical slug `wikipedia` (1.6k+ downloads, 40 installs as of Aug 20 2026).

Do **NOT** publish to slug `wikipedia-mcp` — that is the abandoned duplicate skill (140 DL, 0 installs, lowercase "wikipedia" display name).

GitHub source: https://github.com/evanfoglia/wikipedia-mcp