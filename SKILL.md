---
name: wikipedia
description: Access Wikipedia via MCP — search articles, get summaries, random facts, and dinosaur-specific facts. Great for research, hooks, and general knowledge lookups.
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

## Setup

```bash
# Install dependency
pip install requests

# Add to mcporter (in ~/.openclaw/workspace/config/mcporter.json)
{
  "mcpServers": {
    "wikipedia": {
      "command": "python3",
      "args": ["/path/to/projects/wikipedia-mcp/src/server.py"]
    }
  }
}
```

Restart mcporter (`openclaw gateway restart`) or reconnect the MCP connection.

## Usage

```
mcporter call wikipedia search --args '{"query": "velociraptor", "limit": 5}'
mcporter call wikipedia summary --args '{"title": "Tyrannosaurus"}'
mcporter call wikipedia dino_fact --args '{"species": "Spinosaurus"}'
mcporter call wikipedia dino_fact
mcporter call wikipedia did_you_know
```
