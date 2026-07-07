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

All tools accept an optional `lang` parameter (one of: `en`, `de`, `es`, `fr`, `ja`, `zh`, `pt`, `it`, `ru`, `nl`).

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

# Non-English Wikipedia
mcporter call wikipedia summary --args '{"title": "Berlin", "lang": "de"}'
```

## Requirements

- Python 3.10+
- `requests>=2.28.0`

## API

Uses Wikipedia's free REST API:
- Search: MediaWiki Action API (`/w/api.php`)
- Summary / Random / Featured: REST API v1 (`/api/rest_v1/...`)

No API key required. Respects Wikipedia's User-Agent policy.

## Development

Run the smoke tests:

```bash
python3 tests/test_server.py
```

## License

MIT