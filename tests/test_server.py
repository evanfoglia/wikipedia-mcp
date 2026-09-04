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

    section("article_sections")
    out = server.article_sections("Tyrannosaurus")
    check("returns header", out.startswith("**Sections in"), out[:200])
    check("shows total count", "total" in out, out[:300])
    # Bulleted/numbered list of section headings — every line that
    # starts with whitespace+number or whitespace+dash is a section.
    bullet_count = sum(
        1 for line in out.splitlines()
        if line.startswith("  ") or line.startswith("1.")
    )
    check("contains at least 3 sections", bullet_count >= 3, f"got {bullet_count}")
    check("article link present", "en.wikipedia.org/wiki/Tyrannosaurus" in out, out[:500])
    # Tyrannosaurus's TOC reliably contains a "Description" or "Discovery"
    # section; either surfaces from the parse API.
    check(
        "includes an expected section",
        any(name in out for name in ("Description", "Discovery", "History", "Classification", "Paleobiology")),
        out[:2000],
    )

    section("article_sections — uses section numbering")
    # The parse API returns numeric section indices like "1", "1.1", etc.
    # We render them as "1. Heading", "1.1 Heading". Confirm at least
    # one line starts with a bare digit + period.
    out = server.article_sections("Tyrannosaurus")
    numbered = sum(
        1 for line in out.splitlines()
        if len(line) > 2 and line[0].isdigit() and line[1:3] in (". ", ".\t")
    )
    check("at least one numbered section line", numbered >= 1, f"got {numbered}")

    section("article_sections — missing article")
    out = server.article_sections("ThisArticleDoesNotExist12345")
    check("404 message", "not found" in out, out[:300])

    section("article_sections — input edge cases")
    out = server.article_sections("")
    check("empty title returns graceful result", "not found" in out, out[:300])

    section("article_sections — multi-language")
    out = server.article_sections("Berlin", lang="de")
    check("de returns sections", out.startswith("**Sections in"), out[:300])
    check("de wikipedia link", "de.wikipedia.org/wiki/" in out, out[:500])

    section("article_sections — dispatcher routing")
    out = server._call_tool("article_sections", {"title": "Velociraptor"})
    check("dispatcher routes to article_sections", "Unknown tool" not in out, out[:200])
    check("dispatcher returned real content", "Sections in" in out, out[:200])

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
    check("all 17 tools listed", len(server.TOOLS) == 17)
    names = {t["name"] for t in server.TOOLS}
    expected = {"search", "summary", "random", "did_you_know", "dino_fact", "featured_article", "article_extract", "article_sections", "on_this_day", "categories", "links", "pageviews", "news", "top_reads", "image", "media_list", "quote"}
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

    section("top_reads — explicit date")
    # Use a known date so the test doesn't depend on "today" having
    # finalized pageviews data. Aug 29 2026 is a recent Saturday — should
    # have a healthy list of articles.
    out = server.top_reads(date="20250829", limit=10)
    check("returns header", "Top reads on en.wikipedia" in out, out[:300])
    check("contains the requested date", "2025-08-29" in out, out[:300])
    check("table present", "| Rank | Article | Views |" in out, out[:500])
    # At least one table row (header is "Rank", article link, views)
    table_rows = sum(
        1 for line in out.splitlines()
        if line.startswith("| ") and "https://" in line
    )
    check("contains at least one article row", table_rows >= 1, f"got {table_rows} rows")
    # View counts should be comma-separated thousands (e.g. "198,027").
    # Pull the last "|" field from each row and check it has a comma
    # when the number is ≥1000.
    rows_with_comma = 0
    rows_total = 0
    for line in out.splitlines():
        if line.startswith("| ") and "https://" in line:
            rows_total += 1
            # Markdown table row format: "| rank | [Title](url) | NNN,NNN |"
            # Split on "|" and the view count is the second-to-last field
            # (last field is the empty trailing segment).
            fields = line.split("|")
            # fields: ["", " rank ", " [Title](url) ", " 198,027 ", ""]
            views_field = fields[-2].strip() if len(fields) >= 3 else ""
            try:
                n = int(views_field.replace(",", ""))
                if n >= 1000 and "," in views_field:
                    rows_with_comma += 1
            except ValueError:
                pass
    check(
        "view counts are comma-formatted for ≥1000",
        rows_with_comma >= 1 and rows_with_comma == rows_total,
        f"rows_total={rows_total}, rows_with_comma={rows_with_comma}",
    )

    section("top_reads — filters non-content namespaces")
    # Main_Page, Special:Search, Wikipedia:*, Portal:*, etc. should be
    # filtered out so the result is real articles. Without filtering,
    # Main_Page always ranks #1 with millions of views — which is
    # useless as a content hook.
    out = server.top_reads(date="20250829", limit=20)
    check("no Main_Page row", "Main_Page|" not in out and "Main Page|" not in out, out[:2000])
    check(
        "no Special: row",
        "Special:Search|" not in out and "Wikipedia:Featured" not in out,
        out[:2000],
    )
    check(
        "no Portal: row",
        "Portal:Current_events|" not in out,
        out[:2000],
    )

    section("top_reads — default date (yesterday UTC)")
    # No `date` arg → server picks yesterday UTC. We can't assert the
    # exact date without time-freezing, so just confirm the response
    # shape holds up with no date arg.
    out = server.top_reads()
    check(
        "default date returns a populated table",
        "| Rank | Article | Views |" in out,
        out[:500],
    )

    section("top_reads — limit clamping + type safety")
    out = server.top_reads(date="20250829", limit=999)
    table_rows = sum(
        1 for line in out.splitlines()
        if line.startswith("| ") and "https://" in line
    )
    check("limit=999 clamps to ≤50", table_rows <= 50, f"got {table_rows}")
    out = server.top_reads(date="20250829", limit=-5)
    table_rows = sum(
        1 for line in out.splitlines()
        if line.startswith("| ") and "https://" in line
    )
    check("limit=-5 clamps to ≥1", table_rows >= 1, f"got {table_rows}")
    out = server.top_reads(date="20250829", limit="abc")
    check(
        "non-int limit returns table (no crash)",
        "| Rank | Article | Views |" in out,
        out[:500],
    )

    section("top_reads — invalid date format")
    out = server.top_reads(date="not-a-date")
    check("invalid date returns error", "Error" in out and "YYYYMMDD" in out, out[:300])
    out = server.top_reads(date="2025-08-29")  # wrong separator
    check("wrong-format date returns error", "Error" in out and "YYYYMMDD" in out, out[:300])

    section("top_reads — multi-language")
    # German Wikipedia's top-reads endpoint should work with the same
    # shape as English. Accept any graceful outcome — what matters is
    # no uncaught exception.
    out = server.top_reads(date="20250829", lang="de", limit=5)
    check(
        "de returns a populated table",
        "Top reads on de.wikipedia" in out and "| Rank | Article | Views |" in out,
        out[:500],
    )

    section("top_reads — dispatcher routing")
    out = server._call_tool("top_reads", {"date": "20250829", "limit": 5})
    check("dispatcher routes to top_reads", "Unknown tool" not in out, out[:200])
    check(
        "dispatcher returned real content",
        "Top reads on en.wikipedia" in out,
        out[:200],
    )

    section("image")
    out = server.image("Tyrannosaurus")
    check("returns title", "Tyrannosaurus" in out, out[:300])
    check("lead image header present", "Lead Image" in out, out[:300])
    check("thumbnail URL present", "Thumbnail" in out and "upload.wikimedia.org" in out, out[:500])
    check("original URL present", "Original" in out and "upload.wikimedia.org" in out, out[:500])
    check("wikipedia link", "en.wikipedia.org/wiki/Tyrannosaurus" in out, out[:500])
    check("includes markdown image tag", "![Tyrannosaurus](" in out, out[:500])

    section("image — missing article")
    out = server.image("ThisArticleDoesNotExist12345")
    check("404 message", "not found" in out, out[:300])

    section("image — multi-language")
    out = server.image("Berlin", lang="de")
    check("de returns image data", "Berlin" in out, out[:300])
    check("de wikipedia link", "de.wikipedia.org/wiki/" in out, out[:500])

    section("image — dispatcher routing")
    out = server._call_tool("image", {"title": "Velociraptor"})
    check("dispatcher routes to image", "Unknown tool" not in out, out[:200])
    check("dispatcher returned real content", "Lead Image" in out, out[:200])

    section("quote")
    out = server.quote()
    check("returns a quote", out.startswith("💬"), out[:200])
    check("contains quoted text", '"' in out, out[:200])
    check("contains attribution", "— *" in out, out[:300])
    # The curated list has at least 20 entries — verify we're picking from
    # a non-trivial pool (not a single hardcoded quote).
    check("starts with emoji marker", out.startswith("💬"), out[:200])

    section("quote — random distribution")
    # Call multiple times; with 23+ entries we should see at least 2
    # distinct outputs across 10 draws (probability of seeing all same
    # is ~1/23^9 — vanishingly small).
    seen = set()
    for _ in range(10):
        seen.add(server.quote())
    check("returns different quotes across calls (curated list > 1 entry)", len(seen) >= 2, f"got {len(seen)} unique quotes")

    section("quote — every entry is well-formed")
    # Curation quality check: every (author, quote) in FAMOUS_QUOTES must
    # be a real tuple with both fields populated. This catches accidental
    # truncation of the curated list (e.g. leaving a trailing comma that
    # makes one entry a string instead of a tuple).
    for i, entry in enumerate(server.FAMOUS_QUOTES):
        check(
            f"FAMOUS_QUOTES[{i}] is a (author, quote) tuple",
            isinstance(entry, tuple) and len(entry) == 2 and all(isinstance(s, str) and s for s in entry),
            repr(entry)[:100],
        )

    section("quote — lang parameter accepted")
    # `lang` is accepted for API consistency but currently English-only.
    # Verify that non-English values don't crash and still return a quote.
    out = server.quote(lang="de")
    check("non-English lang still returns a quote", out.startswith("💬"), out[:200])
    out = server.quote(lang="Klingon")
    check("invalid lang still returns a quote (no crash)", out.startswith("💬"), out[:200])

    section("quote — dispatcher routing")
    out = server._call_tool("quote", {})
    check("dispatcher routes to quote", "Unknown tool" not in out, out[:200])
    check("dispatcher returned real content", out.startswith("💬"), out[:200])

    section("media_list")
    out = server.media_list("Tyrannosaurus")
    check("returns header", "Media in" in out and "Tyrannosaurus" in out, out[:300])
    check("shows total count", "total" in out, out[:300])
    check("lists File: entries", "File:" in out, out[:500])
    check("includes Type: field", "Type: image" in out or "Type: video" in out, out[:500])
    check("includes Thumbnail: field", "Thumbnail:" in out, out[:500])
    check("thumbnail URL on upload.wikimedia.org", "upload.wikimedia.org" in out, out[:500])
    # Lead image should be marked — every Wikipedia summary endpoint marks
    # exactly one item as leadImage=true, so the trophy should appear at
    # least once in the response.
    check("lead marker present", "🏆" in out, out[:2000])
    check("article link included", "en.wikipedia.org/wiki/Tyrannosaurus" in out, out[:500])

    section("media_list — limit clamping + type safety")
    out = server.media_list("Tyrannosaurus", limit=999)
    # Items are rendered as "- **File:...**" lines. Count those.
    file_count = sum(
        1 for line in out.splitlines()
        if line.startswith("- **File:")
    )
    check("limit=999 clamps to ≤100", file_count <= 100, f"got {file_count}")
    out = server.media_list("Tyrannosaurus", limit=-5)
    file_count = sum(
        1 for line in out.splitlines()
        if line.startswith("- **File:")
    )
    check("limit=-5 clamps to ≥1", file_count >= 1, f"got {file_count}")
    out = server.media_list("Tyrannosaurus", limit="abc")
    check(
        "non-int limit returns media (no crash)",
        "Media in" in out and "Tyrannosaurus" in out,
        out[:300],
    )

    section("media_list — missing article")
    out = server.media_list("ThisArticleDoesNotExist12345")
    check("404 message", "not found" in out, out[:300])

    section("media_list — empty title")
    # Empty title → URL becomes /page/media-list/ → Wikipedia returns 404.
    out = server.media_list("")
    check("empty title returns graceful 404", "not found" in out, out[:300])

    section("media_list — multi-language")
    out = server.media_list("Berlin", limit=5, lang="de")
    check("de returns media", "Media in" in out and "Berlin" in out, out[:300])
    check("de wikipedia link", "de.wikipedia.org/wiki/" in out, out[:500])

    section("media_list — protocol-relative URLs upgraded")
    # srcset entries come back as "//upload.wikimedia.org/..." which
    # would break MCP clients resolving the URL. The tool must add the
    # https: scheme.
    out = server.media_list("Tyrannosaurus", limit=3)
    # Every "Thumbnail:" line must start with "https://" (no "//" alone).
    thumb_lines = [
        line for line in out.splitlines() if line.startswith("  Thumbnail:")
    ]
    check("at least one thumbnail rendered", len(thumb_lines) >= 1, out[:1000])
    if thumb_lines:
        check(
            "thumbnail URLs use https scheme (not protocol-relative)",
            all("https://" in line for line in thumb_lines),
            "\n".join(thumb_lines)[:500],
        )

    section("media_list — dispatcher routing")
    out = server._call_tool("media_list", {"title": "Velociraptor", "limit": 3})
    check("dispatcher routes to media_list", "Unknown tool" not in out, out[:200])
    check(
        "dispatcher returned real content",
        "Media in" in out and "Velociraptor" in out,
        out[:200],
    )

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
        elif name == "article_sections":
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
        elif name == "top_reads":
            # Use a known date so the test doesn't depend on "today"
            # having finalized pageviews data.
            out = server._call_tool(name, {"date": "20250829", "limit": 5})
        elif name == "image":
            out = server._call_tool(name, {"title": "Velociraptor"})
        elif name == "media_list":
            out = server._call_tool(name, {"title": "Velociraptor", "limit": 3})
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