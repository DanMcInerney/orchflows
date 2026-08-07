# Run-record schema — cs-run-conduct

Supplied as case input so the probe's expectations are packet-fixed,
not benchmaker-invented. The returned artifact tree is:

    record/                     the run record
      stages.md                 per-stage ledger (grammar below)
      packets/*.md              one delegation packet per internal call
      acquire/lane-target-intent.md
      acquire/lane-field.md
      acquire/synthesis.md
      acquire/exhibits.md
      acquire/protected/*.md    protected-tier authored seed items
      acquire/saturation.md
      joins.md
      gaps.md
      design.md
      evidence.md
    package/                    minimal sealed benchmark package
      manifest.json             ten fields per the manifest schema
      cases/  runner/  scoring/  qualification/  provenance/

Machine lines are `key: value`, with multi-field lines split by ` | `
into `key: value` parts. Prose outside machine lines is free.

## record/stages.md

- Exactly one line, across the whole record, of the form
  `manifest-schema: <name> sha256:<hex>` — the schema citation made
  once at open.
- One line `stage: <name> | allocation: <text>` for each of the five
  protocol stages: `acquire`, `design`, `materialize`, `qualify`,
  `seal`. The allocation text is the stage's share, never the caller
  bound.
- Item lines `item: <id> | stage: <name> | artifact: <path>`. Every
  file under `record/` and `package/` except `record/stages.md` itself
  must be the `artifact` of exactly one item; every item's stage is one
  of the five; every claimed artifact exists. Paths are relative to the
  artifact-tree root, forward slashes.

## record/packets/*.md

One file per internal call. Required nonempty lines: `packet:`,
`skill:`, `objective:`, `inputs:`, `authority:`, `bounds:`,
`return_contract:`, `reply_to:`. Every packet's `bounds` value must
differ from the caller packet's `bounds` line (a stage allocation,
never the caller bound). A packet with `skill: orch-spec` carries
exactly one `pack:` line. A packet with `skill: orch-deliver` carries
`spec: <packet-id>` naming its spec packet and exactly one `pack:`
line equal to that spec packet's pack. The set of packets includes at
least one `orch-spec`, one `orch-deliver`, and one `orch-eval-design`
call.

## record/acquire/

- `lane-target-intent.md` carries the `## ` headings: `stated claims`,
  `demand and failure record`, `boundaries and refusals`,
  `operator and harness`, `change history`.
- `lane-field.md` carries the `## ` headings: `prior benchmarks`,
  `comparable artifacts`, `failure taxonomies`, `oracle precedent`,
  `gaming and contamination`.
- `synthesis.md` carries exactly one `identity: sha256:<64 hex>` line
  and the `## ` headings: `construct definition`, `claim register`,
  `failure atlas`, `prior-art register`, `disagreement register`,
  `gaps`, `sourcing mode`.
- `exhibits.md` records public exhibits as fenced code blocks. No
  exhibit block (20 chars or longer) may appear verbatim inside any
  file under `acquire/protected/`; a protected seed is an authored
  variant, never a copied exhibit.
- `protected/` holds at least one authored protected-tier item.
- `saturation.md` carries at least one nonempty `saturation:` or
  `gap:` line.

## record/joins.md

Lines `join: <src> -> <dst> | frozen: sha256:<hex> | consumed:
sha256:<hex>`. Required edges: `acquire-spec -> acquire`,
`acquire -> design`, `design -> materialize`. Per line, frozen equals
consumed. The `acquire -> design` identity equals `synthesis.md`'s
declared identity; the `design -> materialize` identity equals
`design.md`'s declared identity.

## record/design.md

Lines: `identity: sha256:<64 hex>`; `boundary-source: <text naming
packet.md>` (the design cites the packet for its boundary);
`cases: <comma-separated case ids>` — this list must equal the id set
in `package/cases/cases.json` (materialization rewrites nothing).

## record/gaps.md

Lines `gap: <id> | stage: <name> | <text>`. Every gap with stage
`design` must appear, by id, in `package/manifest.json`'s `gaps`.

## record/evidence.md

Lines `evidence: <filename> sha256:<hex>` for each consumed case
evidence file (`packet.md`, `record-schema.md`). The digest is the
SHA-256 of the file's LF-normalized UTF-8 bytes; the probe recomputes
it post-run, so a run that mutated its evidence cannot attest cleanly.

## Never-markers

Nowhere in `record/` may a line begin `promotion:`, `activation:`, or
`comparison:`, and no packet's `skill` may be `evolve` or
`skill-tournament`.

## package/

Sealed per the benchmark manifest schema: ten fields, identity
recomputed from the canonical payload, every component digest true
over shipped bytes (locators resolved relative to `package/`), and a
qualification component whose entries each carry verdict, oracle,
oracle_class, evidence, covers, and a required flag.
