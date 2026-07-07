#!/usr/bin/env python3
"""
Smoke tests for wikipedia-mcp — exercises tools directly without spawning stdio.
Run: python3 tests/test_server.py
"""

import sys
from pathlib import Path

# Allow running from repo root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import server  # noqa: E402

PASS = 0
FAIL = 0


def check(label: str, condition: bool, detail: str = "") -> None:
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✅ {label}")
    else:
        FAIL += 1
        print(f"  ❌ {label}  {detail}")


def section(title: str) -> None:
    print(f"\n=== {title} ===")


def main() -> int:
    section("search_wikipedia")
    out = server.search_wikipedia("velociraptor", limit=3)
    check("returns markdown", "**Velociraptor**" in out, out[:200])
    check("respects limit", out.count("\n1. ") + out.count("\n2. ") + out.count("\n3. ") >= 3)

    section("search_wikipedia — no results")
    out = server.search_wikipedia("xyzzynonesuch", limit=3)
    check("graceful empty", "No results found" in out, out)

    section("get_summary")
    out = server.get_summary("Tyrannosaurus")
    check("title rendered", "## Tyrannosaurus" in out, out[:200])
    check("read more link", "Read more" in out)

    section("get_summary — 404")
    out = server.get_summary("ThisArticleDoesNotExist12345")
    check("404 message", "not found" in out, out)

    section("get_random")
    out = server.get_random()
    check("title rendered", out.startswith("## "), out[:200])

    section("did_you_know")
    out = server.did_you_know()
    check("Did you know prefix", "Did you know" in out, out[:200])

    section("dino_fact — specific species")
    out = server.dino_fact("Spinosaurus")
    check("species mentioned", "Spinosaurus" in out, out[:300])

    section("dino_fact — random")
    out = server.dino_fact("")
    check("returns a fact", "Did you know about" in out, out[:200])

    section("dino_fact — fallback when species not found")
    out = server.dino_fact("xyzzynonesuch")
    check("fallback message present", "Couldn't find" in out, out[:200])
    check("still returns a fact", "Did you know about" in out, out[:500])

    section("featured_article")
    out = server.featured_article()
    check("returns markdown", out.startswith("## "), out[:200])

    section("tool registry")
    check("all 6 tools listed", len(server.TOOLS) == 6)
    names = {t["name"] for t in server.TOOLS}
    expected = {"search", "summary", "random", "did_you_know", "dino_fact", "featured_article"}
    check("expected tool names", names == expected, f"got {names}")

    section("multi-language (de)")
    out = server.get_summary("Berlin", lang="de")
    check("returns German article", out.startswith("## "), out[:300])

    print(f"\n{PASS} passed, {FAIL} failed")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())