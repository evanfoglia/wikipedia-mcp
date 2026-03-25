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
# or restart openclaw
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
```

## Requirements

- Python 3.8+
- `requests` library (`pip install requests`)
- mcporter (for MCP integration)

## API

Uses the free Wikipedia REST API:
- `https://en.wikipedia.org/api/rest_v1/page/summary/{title}`
- `https://en.wikipedia.org/w/api.php`

No API key required. Respects Wikipedia's User-Agent policy.

## License

MIT
