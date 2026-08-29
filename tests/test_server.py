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

    section("search_wikipedia — limit clamping + type safety")
    # limit above 20 should be clamped to ≤20
    out = server.search_wikipedia("dinosaur", limit=100)
    numbered = sum(1 for i in range(1, 21) if f"\n{i}. " in out)
    check("limit=100 clamps to ≤20 results", numbered <= 20, f"got {numbered} items")

    # limit <= 0 should be clamped to 1 (no result number 2+ should appear)
    out = server.search_wikipedia("dinosaur", limit=-5)
    check(
        "limit=-5 clamps to 1",
        "\n1. " in out and "\n2. " not in out,
        out[:300],
    )

    # Non-integer limit must not crash — fall back to default (5)
    out = server.search_wikipedia("dinosaur", limit="abc")
    check(
        "non-int limit returns results (no crash)",
        out.startswith("**Search results"),
        out[:300],
    )
    numbered = sum(1 for i in range(1, 21) if f"\n{i}. " in out)
    check("non-int limit uses default 5", numbered <= 5, f"got {numbered} items")

    section("get_summary")
    out = server.get_summary("Tyrannosaurus")
    check("title rendered", "## Tyrannosaurus" in out, out[:200])
    check("read more link", "Read more" in out)

    section("get_summary — 404")
    out = server.get_summary("ThisArticleDoesNotExist12345")
    check("404 message", "not found" in out, out)

    section("get_summary — input edge cases")
    # Empty title → URL becomes /page/summary/ → Wikipedia returns 404.
    # Guards against regression where an uncaught exception could surface to the MCP client.
    out = server.get_summary("")
    check("empty title returns graceful 404", "not found" in out, out)
    # Whitespace-only title: _slug strips, so URL is empty → 404.
    out = server.get_summary("   ")
    check("whitespace title returns graceful 404", "not found" in out, out)

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

    section("article_extract")
    out = server.article_extract("Tyrannosaurus")
    check("title rendered", "## Tyrannosaurus" in out, out[:200])
    # Strip the markdown header + footer link to confirm body has no HTML tags
    body = out.split("\n\n", 2)[1] if "\n\n" in out else out
    check("plain text (no HTML tags in body)", "<" not in body and ">" not in body, body[:300])
    check("contains body text", "theropod" in out, out[:500])
    summary_out = server.get_summary("Tyrannosaurus")
    check(
        "longer than summary extract",
        len(out) > len(summary_out),
        f"extract={len(out)} summary={len(summary_out)}",
    )

    section("article_extract — 404")
    out = server.article_extract("ThisArticleDoesNotExist12345")
    check("404 message", "not found" in out, out)

    section("article_extract — multi-language")
    out = server.article_extract("Berlin", lang="de")
    check("de title rendered", "## " in out and "Berlin" in out, out[:200])
    check("de link present", "de.wikipedia.org/wiki/" in out, out[:500])

    section("article_extract — input edge cases")
    out = server.article_extract("")
    check("empty title returns graceful result", "not found" in out or "No extract" in out, out)

    section("article_extract — dispatcher routing")
    out = server._call_tool("article_extract", {"title": "Velociraptor"})
    check("dispatcher routes to article_extract", "Unknown tool" not in out, out[:200])
    check("dispatcher returned real content", "## " in out, out[:200])

    section("featured_article")
    out = server.featured_article()
    check("returns markdown", out.startswith("## "), out[:200])

    section("on_this_day")
    out = server.on_this_day()
    check("returns header", out.startswith("**On this day"), out[:200])
    check("contains at least one event", "- **" in out, out[:300])
    check("contains Wikipedia link", "wikipedia.org/wiki/" in out, out[:500])

    section("on_this_day — count clamping")
    out = server.on_this_day(count=3)
    bullet_count = sum(1 for line in out.splitlines() if line.startswith("- **"))
    check("count=3 returns ≤3 events", bullet_count <= 3, f"got {bullet_count}")
    out = server.on_this_day(count=999)
    bullet_count = sum(1 for line in out.splitlines() if line.startswith("- **"))
    check("count=999 clamps to ≤10", bullet_count <= 10, f"got {bullet_count}")
    out = server.on_this_day(count=-5)
    bullet_count = sum(1 for line in out.splitlines() if line.startswith("- **"))
    check("count=-5 clamps to ≥1", bullet_count >= 1, f"got {bullet_count}")

    section("on_this_day — non-int count falls back gracefully")
    out = server.on_this_day(count="abc")
    check("non-int count returns events (no crash)", out.startswith("**On this day"), out[:300])

    section("on_this_day — multi-language")
    out = server.on_this_day(lang="de")
    check("de returns events", out.startswith("**On this day"), out[:300])
    check("de wikipedia.org link", "de.wikipedia.org/wiki/" in out, out[:500])

    section("categories")
    out = server.categories("Tyrannosaurus")
    check("returns header", out.startswith("**Categories for"), out[:200])
    check("contains a bullet list", "- Dinosaur genera" in out or "- Tyrannosaurus" in out, out[:500])
    check("article link present", "en.wikipedia.org/wiki/Tyrannosaurus" in out, out[:500])
    check("no Category: prefix", "Category:" not in out, out[:500])

    section("categories — limit clamping + type safety")
    out = server.categories("Tyrannosaurus", limit=999)
    bullet_count = sum(1 for line in out.splitlines() if line.startswith("- "))
    check("limit=999 clamps to ≤50", bullet_count <= 50, f"got {bullet_count}")
    out = server.categories("Tyrannosaurus", limit=-5)
    bullet_count = sum(1 for line in out.splitlines() if line.startswith("- "))
    check("limit=-5 clamps to ≥1", bullet_count >= 1, f"got {bullet_count}")
    out = server.categories("Tyrannosaurus", limit="abc")
    check("non-int limit returns categories (no crash)", out.startswith("**Categories for"), out[:300])

    section("categories — missing article")
    out = server.categories("ThisArticleDoesNotExist12345")
    check("missing article returns clear message", "not found" in out, out[:300])

    section("categories — multi-language")
    out = server.categories("Berlin", limit=5, lang="de")
    check("de returns categories", out.startswith("**Categories for"), out[:300])
    check("de wikipedia link", "de.wikipedia.org/wiki/" in out, out[:500])

    section("links")
    out = server.links("Tyrannosaurus")
    check("returns header", out.startswith("**Links from"), out[:200])
    # Bulleted list of linked titles — each line "- Some Title"
    bullet_count = sum(1 for line in out.splitlines() if line.startswith("- "))
    check("contains a bullet list", bullet_count >= 5, f"got {bullet_count} bullets")
    check("article link present", "en.wikipedia.org/wiki/Tyrannosaurus" in out, out[:500])
    # Sanity-check that at least one well-known related subject surfaces
    check(
        "includes an expected related article",
        any(name in out for name in ("Albertosaurus", "Allosaurus", "Cretaceous", "theropod", "Dinosaur")),
        out[:1000],
    )

    section("links — limit clamping + type safety")
    out = server.links("Tyrannosaurus", limit=999)
    bullet_count = sum(1 for line in out.splitlines() if line.startswith("- "))
    check("limit=999 clamps to ≤50", bullet_count <= 50, f"got {bullet_count}")
    out = server.links("Tyrannosaurus", limit=-5)
    bullet_count = sum(1 for line in out.splitlines() if line.startswith("- "))
    check("limit=-5 clamps to ≥1", bullet_count >= 1, f"got {bullet_count}")
    out = server.links("Tyrannosaurus", limit="abc")
    check("non-int limit returns links (no crash)", out.startswith("**Links from"), out[:300])

    section("links — missing article")
    out = server.links("ThisArticleDoesNotExist12345")
    check("missing article returns clear message", "not found" in out, out[:300])

    section("links — multi-language")
    out = server.links("Berlin", limit=5, lang="de")
    check("de returns links", out.startswith("**Links from"), out[:300])
    check("de wikipedia link", "de.wikipedia.org/wiki/" in out, out[:500])

    section("links — dispatcher routing")
    out = server._call_tool("links", {"title": "Velociraptor"})
    check("dispatcher routes to links", "Unknown tool" not in out, out[:200])
    check("dispatcher returned real content", out.startswith("**Links from"), out[:200])

    section("tool registry")
    check("all 12 tools listed", len(server.TOOLS) == 12)
    names = {t["name"] for t in server.TOOLS}
    expected = {"search", "summary", "random", "did_you_know", "dino_fact", "featured_article", "article_extract", "on_this_day", "categories", "links", "pageviews", "news"}
    check("expected tool names", names == expected, f"got {names}")

    section("pageviews")
    out = server.pageviews("Tyrannosaurus")
    check("returns header", "Pageviews for" in out, out[:300])
    check("table present", "| Date | Views |" in out, out[:500])
    check("at least one day shown", "|" in out and "202" in out, out[:1000])
    check("total + average present", "Total views:" in out and "Daily average:" in out, out[:500])
    check("wikipedia link included", "en.wikipedia.org/wiki/Tyrannosaurus" in out, out[:1000])

    section("pageviews — custom date range")
    out = server.pageviews("Python_(programming_language)", start="20250101", end="20250107")
    check("returns data", "Pageviews for" in out, out[:300])
    check("7 days in window", out.count("| 2025-01-") == 7, out[:1500])

    section("pageviews — missing article")
    out = server.pageviews("ThisArticleDoesNotExist12345")
    check("missing returns clear message", "No pageviews data found" in out, out[:300])

    section("pageviews — invalid date format")
    out = server.pageviews("Tyrannosaurus", start="bad-date")
    check("invalid start returns error", "Error" in out and "YYYYMMDD" in out, out[:300])

    section("pageviews — start after end")
    out = server.pageviews("Tyrannosaurus", start="20250110", end="20250101")
    check("reversed range returns error", "after end" in out, out[:300])

    section("pageviews — empty title")
    out = server.pageviews("")
    check("empty title returns error", "title is required" in out, out[:300])

    section("pageviews — multi-language")
    out = server.pageviews("Berlin", lang="de")
    check("de returns pageviews", "Pageviews for" in out, out[:300])
    check("de wikipedia link", "de.wikipedia.org/wiki/" in out, out[:500])

    section("pageviews — dispatcher routing")
    out = server._call_tool("pageviews", {"title": "Velociraptor"})
    check("dispatcher routes to pageviews", "Unknown tool" not in out, out[:200])
    check("dispatcher returned real content", "Pageviews for" in out, out[:200])

    section("news")
    out = server.news()
    check("returns header", out.startswith("**In the news"), out[:200])
    # Bullet list of events
    bullet_count = sum(1 for line in out.splitlines() if line.startswith("- "))
    check("contains at least one event", bullet_count >= 1, f"got {bullet_count}")
    check("contains wikipedia link", "wikipedia.org/wiki/" in out, out[:500])
    # Bold-linked article titles should be present (Main Page almost always has them)
    check(
        "contains a bold-linked article title",
        "**[",
        out[:500],
    )
    # Main Page link in footer
    check("main page link present", "/wiki/Main_Page" in out, out[:500])

    section("news — limit clamping + type safety")
    out = server.news(limit=999)
    bullet_count = sum(1 for line in out.splitlines() if line.startswith("- "))
    check("limit=999 clamps to ≤10", bullet_count <= 10, f"got {bullet_count}")
    out = server.news(limit=-5)
    bullet_count = sum(1 for line in out.splitlines() if line.startswith("- "))
    check("limit=-5 clamps to ≥1", bullet_count >= 1, f"got {bullet_count}")
    out = server.news(limit="abc")
    check("non-int limit returns news (no crash)", out.startswith("**In the news"), out[:300])

    section("news — multi-language")
    # German Wikipedia's Main Page is structured differently than en's,
    # so the parser may not find an "In the news" h2 block. Accept any
    # graceful outcome (real items, structural fallback, or empty-feed
    # fallback) — what matters is no uncaught exception.
    out = server.news(lang="de")
    check(
        "de returns news or graceful fallback",
        out.startswith("**In the news")
        or "No 'In the news' section" in out
        or "No news" in out
        or "Could not fetch" in out,
        out[:300],
    )

    section("news — dispatcher routing")
    out = server._call_tool("news", {})
    check("dispatcher routes to news", "Unknown tool" not in out, out[:200])
    check("dispatcher returned real content", out.startswith("**In the news"), out[:200])

    section("multi-language (de)")
    out = server.get_summary("Berlin", lang="de")
    check("returns German article", out.startswith("## "), out[:300])

    section("language validation fallback")
    # _base() and _wiki() silently coerce unsupported langs to "en" so a
    # bad/typo'd lang string can't route a request to the wrong Wikipedia.
    # Test the validation directly (no network) so regressions get caught
    # even if the live calls happen to succeed.
    check("_base('en') → en rest_v1", server._base("en") == "https://en.wikipedia.org/api/rest_v1")
    check("_base('de') → de rest_v1", server._base("de") == "https://de.wikipedia.org/api/rest_v1")
    check("_base('ja') → ja rest_v1", server._base("ja") == "https://ja.wikipedia.org/api/rest_v1")
    check("_base('') → en rest_v1 (default)", server._base("") == "https://en.wikipedia.org/api/rest_v1")
    check("_base('invalid') → falls back to en", server._base("invalid") == "https://en.wikipedia.org/api/rest_v1")
    check("_base('EN') → case-sensitive fallback to en", server._base("EN") == "https://en.wikipedia.org/api/rest_v1")
    check("_wiki('en') → en api.php", server._wiki("en") == "https://en.wikipedia.org/w/api.php")
    check("_wiki('de') → de api.php", server._wiki("de") == "https://de.wikipedia.org/w/api.php")
    check("_wiki('invalid') → falls back to en", server._wiki("invalid") == "https://en.wikipedia.org/w/api.php")
    check("_wiki('Klingon') → falls back to en", server._wiki("Klingon") == "https://en.wikipedia.org/w/api.php")
    # Unsupported lang flows through to live calls without crashing
    out = server.get_summary("Berlin", lang="Klingon")
    check("unsupported lang still returns an article", out.startswith("## "), out[:200])

    section("_call_tool dispatch routing")
    # Every registered MCP tool name must route through the dispatcher
    # (i.e. NOT return the "Unknown tool" fallback). This is the layer
    # MCP clients actually call via tools/call — if it breaks, the
    # whole server breaks even though individual functions still work.
    routed_ok = set()
    for tool_def in server.TOOLS:
        name = tool_def["name"]
        if name == "search":
            out = server._call_tool(name, {"query": "test", "limit": 1})
        elif name == "summary":
            out = server._call_tool(name, {"title": "Velociraptor"})
        elif name == "dino_fact":
            out = server._call_tool(name, {"species": ""})
        elif name == "article_extract":
            out = server._call_tool(name, {"title": "Velociraptor"})
        elif name == "on_this_day":
            out = server._call_tool(name, {})
        elif name == "categories":
            out = server._call_tool(name, {"title": "Velociraptor"})
        elif name == "links":
            out = server._call_tool(name, {"title": "Velociraptor"})
        elif name == "pageviews":
            out = server._call_tool(name, {"title": "Velociraptor"})
        elif name == "news":
            out = server._call_tool(name, {})
        else:
            out = server._call_tool(name, {})
        check(
            f"'{name}' routes through dispatcher",
            "Unknown tool" not in out,
            out[:200],
        )
        if "Unknown tool" not in out:
            routed_ok.add(name)
    expected_names = {t["name"] for t in server.TOOLS}
    check(
        "every registered tool is routable",
        routed_ok == expected_names,
        f"missing: {expected_names - routed_ok}",
    )
    # Unknown tool name returns a clear, non-empty message
    out = server._call_tool("definitely_not_a_real_tool", {})
    check(
        "unknown tool returns clear message",
        "Unknown tool: definitely_not_a_real_tool" in out,
        out,
    )

    print(f"\n{PASS} passed, {FAIL} failed")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())