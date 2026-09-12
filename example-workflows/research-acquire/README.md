# Research Acquire

Optional scripts for research workers: bounded keyless acquisition with receipts and resume, and a direct YouTube transcript reader. Both run inside an existing worker; neither launches agents or reviews.

Install with `scripts/orchflows.py setup --example research-acquire` from a checkout. Locate with `resolve research-acquire --skill research-acquire` or `--resource skills/research-acquire/scripts/inspect_source.py`. Needs Python 3.9+. For transcripts, use an existing Python environment with pip, install `yt-dlp` with `python -m pip install yt-dlp`, then run the reader with that same interpreter. Setup does not install dependencies.

- Transcript: `inspect_source.py youtube-transcript --url <url> --output <file.json>` runs yt-dlp once and saves the caption track, the video's metadata and a receipt. Flags, statuses, dates and tests: [source inspection](skills/research-acquire/references/source-inspection.md).
- Acquisition: [entrypoint](skills/research-acquire/SKILL.md); plan, semantic selection, resumed depth. Enforcement is per plan; the caller splits bounds across plans.

Offline checks from the skill directory with `PYTHONPATH` set to its absolute `scripts/`: `python -m unittest discover -s tests -t .` runs the full suite; `python scripts/acquire_fixture.py --output <scratch>` exercises parsing, selection, depth and resume. Neither tests live access or judgment.

Backend from [orchflows recent-search](https://github.com/DanMcInerney/orchflows/tree/945546721732aa564a086ee9543803b38017e1c3/example-workflows/recent-search) under its [MIT license](LICENSE).
