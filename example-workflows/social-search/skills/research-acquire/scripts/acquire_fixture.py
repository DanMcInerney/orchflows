"""Executable offline admission: real archive/index/comment/page adapters, no socket.

The fixture's choices are authored semantic examples, never a production
selection heuristic. Timings are measured locally with canned responses; no
live-source speed or relevance generalization follows from them.
"""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import time

import acquire
from acquire_checkpoint import atomic_json, read_json
from super_research import transport


def fixture_plan():
    return {
        "version": 1, "plan_id": "representative", "question": "Compare conditional community and publisher cases.",
        "as_of": "2026-09-10T23:59:59Z", "window": {"start": "2026-09-08T00:00:00Z", "end": "2026-09-10T00:00:00Z"},
        "allowed_adapters": ["reddit_archive", "reddit_shreddit", "web_search", "open_page"],
        "limits": {"max_steps": 4, "max_requests": 4, "max_records": 12, "max_seconds": 30},
        "discovery": [
            {"step_id": "archive", "adapter_id": "reddit_archive", "query": "search:subreddit=BitcoinMarkets", "max_items": 4},
            {"step_id": "index", "adapter_id": "web_search", "query": "bing:conditional outlook", "max_items": 4}],
        "depth": [
            {"depth_id": "comments", "adapter_id": "reddit_shreddit", "operation": "comments", "from_steps": ["archive"], "max_items": 2, "max_targets": 1},
            {"depth_id": "pages", "adapter_id": "open_page", "operation": "", "from_steps": ["index"], "max_items": 2, "max_targets": 1}]
    }


def fixture_runtime(refuse=False):
    opened = []
    stamp = int(datetime(2026, 9, 9, 12, tzinfo=timezone.utc).timestamp())
    post = {"id": "abc", "title": "Daily discussion", "selftext": "General market discussion.",
            "author": "daily_host", "subreddit": "BitcoinMarkets", "created_utc": stamp,
            "permalink": "/r/BitcoinMarkets/comments/abc/daily/", "score": 3, "num_comments": 5}
    unrelated = dict(post, id="def", subreddit="CasualConversation", permalink="/r/CasualConversation/comments/def/daily/")
    old = dict(post, id="old", created_utc=stamp - 864000)
    archive = json.dumps({"data": [post, unrelated, old]})
    index = '''<rss><channel><item><title>Conditional publisher case</title>
        <link>https://example.net/outlook</link><description>A publisher weighs opposing cases.</description>
        <pubDate>Wed, 09 Sep 2026 12:00:00 GMT</pubDate></item></channel></rss>'''
    comments = '''<shreddit-comment-tree-stats total-comments="5" sort="TOP"></shreddit-comment-tree-stats>
        <shreddit-comment thingid="t1_comment" postid="t3_abc" author="reader" score="2" depth="0"
        created="2026-09-09T13:00:00+0000" permalink="/r/BitcoinMarkets/comments/abc/comment/comment/">
        <div id="t1_comment-post-rtjson-content"><p>A conditional case, not a prediction.</p></div></shreddit-comment>'''
    article = '''<html><head><title>Conditional publisher case</title>
        <meta property="article:published_time" content="2026-09-09T12:00:00Z"></head>
        <body><article><p>The outlook depends on a condition, with an opposing risk.</p></article></body></html>'''

    def opener(request):
        opened.append(request)
        if request.route_id == transport.ARCTIC_SHIFT_SEARCH_ROUTE:
            return 200, archive, "application/json"
        if request.route_id == "bing_rss":
            return 200, index, "application/rss+xml"
        if request.route_id == "reddit_shreddit_comments":
            return (403, "Forbidden", "text/html") if refuse else (200, comments, "text/html")
        if request.route_id == transport.WEB_PAGE_OPEN_ROUTE:
            return 200, article, "text/html"
        raise AssertionError("fixture has no route: " + request.route_id)

    # No repeated origin in this fixture, so pacing needs no fake wait.
    return {"opener": opener, "now": lambda: "2026-09-10T12:00:00Z"}, opened


def choose(output):
    batch = read_json(Path(output) / "candidates.json")
    daily = next(row for row in batch["candidates"] if row["community"] == "BitcoinMarkets")
    publisher = next(row for row in batch["candidates"] if row["adapter_id"] == "web_search")
    return {"candidate_id": batch["candidate_id"], "choices": [
        {"record_id": daily["record_id"], "depth_id": "comments",
         "reason": "The named market community makes this daily thread worth inspecting; no comment relevance is assumed."},
        {"record_id": publisher["record_id"], "depth_id": "pages",
         "reason": "The publisher's conditional argument needs full text to compare its caveats."}],
        "omission_reason": "The unrelated generic daily thread has no topic context; its title alone is insufficient."}


def admission(output):
    plan, (runtime, opened) = fixture_plan(), fixture_runtime()
    atomic_json(output / "plan.json", plan)
    start = time.monotonic()
    discovery = acquire.execute(plan, output, **runtime)
    selected = choose(output)
    atomic_json(output / "selected.json", selected)
    depth = acquire.execute(plan, output, selected, **runtime)
    packet = (output / "packet.json").read_bytes()
    resumed = acquire.execute(plan, output, selected, **runtime)
    if discovery["requests_this_invocation"] != 2 or depth["requests_this_invocation"] != 2:
        raise AssertionError("collection did not cross discovery and hydration seams")
    if resumed["requests_this_invocation"] or packet != (output / "packet.json").read_bytes():
        raise AssertionError("completed resume changed evidence or repeated reads")
    artifact = json.loads(packet)
    if len(artifact["edges"]) != 2 or not any(row["body"] == "A conditional case, not a prediction." for row in artifact["records"]):
        raise AssertionError("fixture did not retain linked comment and page evidence")
    result = {"kind": "offline_adapter_admission", "discovery": discovery, "hydration": depth,
              "resume": resumed, "actual_opener_attempts": len(opened),
              "total_wall_seconds": time.monotonic() - start,
              "limits": plan["limits"], "live_requests": 0,
              "limits_of_evidence": "Canned source responses and authored example choices; no live BTC benchmark, model selection, independent review or HTML rendering exercised."}
    atomic_json(output / "admission.json", result)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    if args.output:
        result = admission(args.output.resolve())
    else:
        with tempfile.TemporaryDirectory() as directory:
            result = admission(Path(directory))
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
