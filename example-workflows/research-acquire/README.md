# Research Acquire

Optional tools for bounded public research: discovery → semantic selection → selected depth → evidence and receipts. They run inside the current worker and launch no agents. Source operations and their limits live in [route guidance](skills/research-acquire/references/selection-routes.md); the [skill](skills/research-acquire/SKILL.md) owns invocation. This library collects evidence; the caller judges its value.

Install from an Orchflows checkout with `python scripts/orchflows.py setup --example research-acquire`; locate with `resolve research-acquire --skill research-acquire`. Requires Python 3.9+. Acquisition uses the standard library. The optional [YouTube transcript reader](skills/research-acquire/references/source-inspection.md) requires `yt-dlp` installed in the same interpreter (`python -m pip install yt-dlp`). Setup installs no dependencies.

From the skill directory with `PYTHONPATH` set to its absolute `scripts/`, run `python -m unittest discover -s tests -t .`. `python scripts/acquire_fixture.py --output <scratch>` exercises parsing, selected depth and resume offline. Neither establishes live access or research quality.

Backend from [orchflows recent-search](https://github.com/DanMcInerney/orchflows/tree/945546721732aa564a086ee9543803b38017e1c3/example-workflows/recent-search), under its [MIT license](LICENSE).
