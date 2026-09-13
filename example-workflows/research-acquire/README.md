# Research Acquire

Collect bounded public evidence inside the current worker; launch no agents. The caller judges the evidence.

```text
discovery → worker selects candidates → selected depth → evidence + receipts
```

## Structure

| Owner | Responsibility |
| --- | --- |
| [Skill](skills/research-acquire/SKILL.md) | Invocation and handoff |
| [Acquisition method](skills/research-acquire/references/acquisition.md) | Plan, select and resume |
| [Source operations](skills/research-acquire/references/selection-routes.md) | Supported routes and limits |
| [Protocol](skills/research-acquire/references/protocol.md) | Direct API and manifest contract |
| `skills/research-acquire/scripts/` | Acquisition mechanics |
| `skills/research-acquire/tests/` | Offline checks |

## Install and dependencies

From a complete orchflows checkout, run `python scripts/orchflows.py setup --example research-acquire` (Python 3.11+). Core `docs/hosts.md` covers host registration and refresh. Invoke `research-acquire:research-acquire`.

The acquisition tools require Python 3.9+ and use the standard library. The optional [YouTube transcript reader](skills/research-acquire/references/source-inspection.md) requires `yt-dlp` in the same interpreter (`python -m pip install yt-dlp`). Setup installs no library dependencies.

From the skill directory with `PYTHONPATH` set to its absolute `scripts/`, run `python -m unittest discover -s tests -t .`. `python scripts/acquire_fixture.py --output <scratch>` exercises parsing, selected depth and resume offline. Neither establishes live access or research quality.

Backend from [orchflows recent-search](https://github.com/DanMcInerney/orchflows/tree/945546721732aa564a086ee9543803b38017e1c3/example-workflows/recent-search), under its [MIT license](LICENSE).
