# Wikipedia MCP

A Model Context Protocol (MCP) server that provides access to Wikipedia via the free REST API. No API key required.

## Tools

| Tool | Description |
|------|-------------|
| `search` | Search Wikipedia for articles matching a query |
| `summary` | Get a Wikipedia article summary + thumbnail by title |
| `random` | Get a random Wikipedia article summary |
| `did_you_know` | Get a random "Did You Know" style fact |
| `dino_fact` | Get a dino/prehistory-specific fact (specific species or random) |
| `featured_article` | Get today's Wikipedia Featured Article |
| `article_extract` | Get a full plain-text extract of an article (longer than `summary`) |
| `article_sections` | Get the table of contents (section headings) for an article — useful for navigating long articles before reading the full body |
| `on_this_day` | Get historical events that happened on today's date |
| `categories` | List Wikipedia categories an article belongs to |
| `links` | List outgoing Wikipedia links from an article (the article's reference network) |
| `pageviews` | Get daily view counts for an article (popularity, trending, historical interest) |
| `news` | Get current events from Wikipedia's Main Page "In the news" section |
| `top_reads` | Get the most-read articles on Wikipedia for a given date |
| `image` | Get just the lead image (thumbnail + original URLs) for an article, no summary text |
| `media_list` | List all media (images, videos, audio) used in an article — full inventory with type, caption, and thumbnail |
| `quote` | Get a random notable quote from a curated list of famous authors |

All tools accept an optional `lang` parameter (one of: `en`, `de`, `es`, `fr`, `ja`, `zh`, `pt`, `it`, `ru`, `nl`). Note: `quote` accepts the parameter for API consistency but is currently English-only (curated list).

## Setup

### 1. Register with mcporter

Add to your `~/.openclaw/workspace/config/mcporter.json`:

```json
{
  "mcpServers": {
    "wikipedia": {
      "command": "python3",
      "args": ["/path/to/wikipedia-mcp/src/server.py"]
    }
  }
}
```

### 2. Restart mcporter

```bash
openclaw gateway restart
```

## Usage

```bash
# Search
mcporter call wikipedia search --args '{"query": "velociraptor", "limit": 5}'

# Article summary
mcporter call wikipedia summary --args '{"title": "Tyrannosaurus"}'

# Random article
mcporter call wikipedia random

# Random dino fact
mcporter call wikipedia dino_fact

# Specific species
mcporter call wikipedia dino_fact --args '{"species": "Spinosaurus"}'

# Today's featured article
mcporter call wikipedia featured_article

# Full plain-text article extract (vs summary)
mcporter call wikipedia article_extract --args '{"title": "Tyrannosaurus"}'

# Article table of contents — section headings (navigate before reading full body)
mcporter call wikipedia article_sections --args '{"title": "Tyrannosaurus"}'

# On this day (historical events for today)
mcporter call wikipedia on_this_day
mcporter call wikipedia on_this_day --args '{"count": 8}'

# Categories for an article (taxonomy-based discovery)
mcporter call wikipedia categories --args '{"title": "Tyrannosaurus"}'
mcporter call wikipedia categories --args '{"title": "Tyrannosaurus", "limit": 10}'

# Outgoing links from an article (graph-style discovery)
mcporter call wikipedia links --args '{"title": "Tyrannosaurus"}'
mcporter call wikipedia links --args '{"title": "Tyrannosaurus", "limit": 30}'

# Daily view counts (popularity research, trending topics)
mcporter call wikipedia pageviews --args '{"title": "Tyrannosaurus"}'
mcporter call wikipedia pageviews --args '{"title": "Python_(programming_language)", "start": "20250101", "end": "20250107"}'

# Current events from Wikipedia's Main Page (today's "In the news")
mcporter call wikipedia news
mcporter call wikipedia news --args '{"limit": 8}'

# Top reads — most-viewed articles on a given date
mcporter call wikipedia top_reads
mcporter call wikipedia top_reads --args '{"date": "20260101", "limit": 15}'

# Lead image — thumbnail + original URLs for an article (no text)
mcporter call wikipedia image --args '{"title": "Tyrannosaurus"}'
mcporter call wikipedia image --args '{"title": "Tyrannosaurus", "lang": "de"}'

# Media inventory — all images/videos/audio in an article (full list, not just lead)
mcporter call wikipedia media_list --args '{"title": "Tyrannosaurus"}'
mcporter call wikipedia media_list --args '{"title": "Tyrannosaurus", "limit": 50}'
mcporter call wikipedia media_list --args '{"title": "Berlin", "lang": "de"}'

# Random notable quote (curated list of famous authors)
mcporter call wikipedia quote
mcporter call wikipedia quote --args '{"lang": "de"}'  # lang accepted, currently English-only

# Non-English Wikipedia
mcporter call wikipedia summary --args '{"title": "Berlin", "lang": "de"}'
```

## Requirements

- Python 3.10+
- `requests>=2.28.0`

## API

Uses Wikipedia's free REST API:
- Search: MediaWiki Action API (`/w/api.php`)
- Summary / Random / Featured / Media-list: REST API v1 (`/api/rest_v1/...`)
- Pageviews / Top reads: Wikimedia cross-wiki metrics API (`https://wikimedia.org/api/rest_v1/metrics/pageviews/...`)

No API key required. Respects Wikipedia's User-Agent policy.

## Development

Run the smoke tests:

```bash
python3 tests/test_server.py
```

## License

MIT