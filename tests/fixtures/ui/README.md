# Reader UI fixture corpus

Flat by run: `<run>/<id>.md`. `tests/test_ui.py` copies these into a
temporary `<tmp>/.orch/tickets/<run>/` at run time, so no `.orch/`
directory is tracked here and no test can mutate repository state. The
real ticket corpus is gitignored and uncommittable, so these are authored
to the shapes it exhibits rather than redacted from it.

| fixture | shape it carries |
|---|---|
| `run-alpha/A1.md` | conforming: every `contracts/work-item.md` floor key, plain body |
| `run-alpha/A2.md` | `## Goal` carrying `<script>alert(1)</script>` — untrusted data per `rules/visibility.md` §6 |
| `run-beta/B1.md` | degenerate: no `status`, no `executor`, no body section at all |
| `run-gamma/G1.md` | `## Verification` as a five-column verdict table, one row escaping a `\|` inside its evidence, one `FAIL` |
| `run-gamma/G2.md` | `## Verification` as numbered prose — the shape that must read `unparsed`, never zero rows |
| `run-gamma/G3.md` | `bound: one session` — a bound that is not a duration |
| `run-gamma/G4.md` | `bound: 90m` with a `claimed_at` — the only shape an elapsed meter may be drawn from |
| `run-gamma/G5.md` | `status: claimed` with no `claimed_at`, and only one body section |
| `run-gamma/G6.md` | `status: side<b>ways` — outside the contract's closed set, carrying markup |
| `run-gamma/G7.md` | a section name the contract does not fix, a present-but-empty section, and `## Handoff` inside a fence |
| `run-delta/D1.md`–`D5.md` | a cycle-free diamond: one root, two middle tickets, a join, a sink — four layers, and one edge that must cross a layer |
| `run-delta/D2.md`, `D3.md` | `depends_on` as a block list and inline, the two spellings `_parse_frontmatter` accepts |
| `run-delta/*` | every status terminal, so the run is the settled case the poll interval must read as idle |
| `run-epsilon/E1.md`–`E3.md` | a three-ticket `depends_on` cycle; `E1` is `ready`, so the run is also the live case for the poll interval |
| `run-epsilon/E4.md` | `depends_on` naming a ticket that is not in this run |
| `friction/2026-07.jsonl` | two well-formed entries, one carrying `<b>markup</b>` |
| `friction/2026-08.jsonl` | a line that is not JSON, an array that is JSON and not an entry, a blank line, and an entry with neither `category` nor `host` |
| `events/run-gamma.jsonl` | the deferred hooks seam: one line per `event` value, one carrying `<b>markup</b>`, one with every nullable key null, plus the same two unreadable shapes and a blank line. No other run has one, so the seam's silent half is a fixture too |
| `runs/run-gamma/run.json` | a live run's identity: `project.name` a POSIX path whose leaf is the folder, both terminal fields empty |
| `runs/run-delta/run.json` | finished `failed`; `project.name` a backslash path landing on the same `atlas-web` leaf as `run-gamma`, so one folder holds both a live and a finished run |
| `runs/run-epsilon/run.json` | finished `limited`, and the newest `terminal_at` in the corpus, so its folder leads any recency order |
| `runs/run-alpha/run.json` | a live run whose `project.name` is a bare leaf, not a path |

`runs/` carries the run identities `reader/scripts/ui_experience.py` reads for folder
and completion facts; `reader/web/src/smoke.spec.ts` copies the tree beside `tickets/`.
Every `project.root`, `origin` and `workspaces[].path` here is synthetic and
projection-forbidden: a body that carried one would be a privacy-wall defect,
which is why the smoke contract asserts none of them reaches the browser.
`run-beta` has no `run.json` at all — the unrecorded folder is a shape too.

Across both friction logs: five entries, two unreadable lines, and blank
lines that are not unreadable. Every log here is oldest-first on disk, the
order an append-only log is written in, so a feed that merely concatenated
them would be exactly backwards.

`claimed_at` values sit on 2026-01-01 so a test can pin `now` and assert an
exact elapsed figure.

A run directory with zero tickets is materialized by the test, since git
tracks no empty directory.
