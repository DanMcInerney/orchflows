# Source readers

Readers fetch known material inside the source worker; they launch no agents. Resolve an installed reader through the home CLI:

```text
<runtime-python> <core-cli> resolve research-acquire --resource skills/research-acquire/scripts/inspect_source.py --home <home>
```

For YouTube transcripts, prefer the resolved reader over ad-hoc caption scraping:

```text
<runtime-python> <reader> youtube-transcript --url <video-url> --output <evidence.json> --timeout-seconds 45 --max-chars 8000
```

The example bounds are illustrative; choose timeout and excerpt limits from the assignment. Forward `YYYY-MM-DD` dates with `--start-date` and `--end-date` for inclusive UTC days, or offset-qualified ISO instants with `--window-start` and `--window-end` for a half-open window. The reader does not enforce request-count or network-byte quotas.

Its deterministic caption attempts return support, provenance and gaps for prepare-evidence. A transcript supports speech, not audience sentiment; its retrieval time does not date the video or its comments. Preserve uncertain dates and truncated text.

If the reader or its dependencies are unavailable, use available native tools and retain that gap. Other bounded acquisition can use `research-acquire:research-acquire`. Installation and dependencies belong to that library's resolved README.
