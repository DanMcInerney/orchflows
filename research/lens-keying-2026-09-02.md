# Lens keyed by artifact kind

Design outline, 2026-09-02. Frozen root for the run that delivers it; each
unit below cites this document by path and revision in its Context.

## The idea

Make and judge are the same craft section read in opposite directions. A
craft already states what a well-formed frozen root carries (`## Outline`),
how a spec cuts (`## Slicing`), and what a finished deliverable must satisfy
(`## Lens`, `## Evidence`). The making side reads those forward; the judging
side today has criteria only for the finished deliverable, because
`orch-judge` reads `## Lens` alone and the judge command accepts only the
adapter's artifact kinds. So a workflow that reviews its outline or its
slices has no craft-owned criteria and no way to name the artifact.

The generalization is not more review prose. It is one key: the artifact
kind. Every craft's `## Lens` carries one entry per artifact kind the domain
produces; `do` makes toward the entry and `judge` checks against it. Fidelity
is unchanged because each entry is the same domain-specific text that exists
today, moved under its kind and written once.

## Artifact kinds

Two kinds are library-owned and appear in every pack, because the ticket
machinery already defines and identifies them:

- `root` — a frozen goal. Identity: the ticket's `root_generation` value,
  already spelled `root:<id>:<n>:sha256:<digest>`.
- `cut` — a set of work items under a root. Identity: the ticket's
  `cut_generation` value, already spelled `cut:<id>:<n>:sha256:<digest>`.

The remaining kinds are domain-owned and fixed by the pack's adapter
(`scripts/tickets_adapters.py` `artifact_kind`): `git` for code and design
(git-plus-render), `doc` for content, `evidence` for research and data.

A new kind earns a Lens entry only when a workflow judges that artifact in
its own call. A packet versus a synthesis, or a draft versus an edit, stay
stages inside one child until then.

## The craft signature after this change

Mandatory sections: `## Vocabulary`, `## Workspace`, `## Spec fields`,
`## Lens`. Optional: `## Stages` (narrative behind the `stages` cell; the
verification-scope bullet the launch prompt quotes stays here) and
`## Shape` is retired into the deliverable's Lens entry.

`## Lens` carries exactly these `###` entries, in this order:

    ### root
    ### cut
    ### <one per adapter artifact kind: git | doc | evidence>

Each entry states, in prose or bullets: what a well-formed artifact of the
kind carries (today's Outline, Slicing, or Lens bullets), what proves it
(today's Evidence, for the deliverable kind), and which findings are
`blocking: true`. Domain taste beyond the shared shape principles (today's
`## Shape`) lives in the deliverable entry.

Migration map, every pack:

| today | after |
| --- | --- |
| `## Outline` (three `###` subsections) | `## Lens` › `### root`, subsections kept as bullets or `####` |
| `## Slicing` | `## Lens` › `### cut` |
| `## Lens` + `## Evidence` + `## Shape` | `## Lens` › `### <adapter kind>` |
| `## Vocabulary`, `## Workspace`, `## Spec fields`, `## Stages` | unchanged |

`## Spec fields` stays its own section because `tickets_grade` reads it
mechanically as the root's intake checklist.

## The one rule the callables state

`orch-do`: the artifact kind names the Lens entry you make toward. A making
`do` makes the adapter's kind; a planning `do` makes `root` or `cut` and says
which. `orch-judge`: the kind on each typed artifact line names the Lens
entry you check against. Neither body lists sections any more, and neither
resolves the craft itself: the launch prompt hands the craft path and names
the kind.

## Units

Independent seams; each is one `do` under `orch-code-pack`, isolation
required, on branch `claude/orchestrator-subagent-analysis-758331` from
revision 8e643085 or later.

**U1 — judge accepts `root:` and `cut:`.** `scripts/tickets_mint.py`
`_artifact_lines` admits the two library kinds beside `ARTIFACT_KINDS`; the
identity after the prefix must match a `root_generation` or `cut_generation`
value carried by a ticket in the same run, else a structured refusal naming
the run's known values. Tests beside the existing judge tests.

**U2 — contract, validator, scaffold, exemplar craft.**
`contracts/pack-signature.md` craft-section table and prose (a T0 change:
re-pin through `tools/validate.py --pin`); `tools/validate_support/names.py`
`validate_craft_sections` checks the four mandatory headings and that
`## Lens` carries `### root`, `### cut`, and one `###` per adapter kind of
the pack's adapter cell, nothing else; `scripts/orchflows_scaffold.py`
`_CRAFT_SECTIONS`; `docs/pack-authoring.md` step order;
`packs/orch-code-pack/references/craft.md` migrated per the map as the
exemplar. `tests/test_verification_model.py`'s per-pack `## Evidence`
anchor test moves to the deliverable Lens entry. `CRAFT_BUDGET` may rise
by the added `###` lines only.

**U3 — the other four crafts.** `packs/orch-content-pack`,
`orch-data-pack`, `orch-design-pack`, `orch-research-pack`
`references/craft.md` migrated per the map, text moved not rewritten,
every existing anchor phrase preserved (the Evidence anchors
`test_verification_model.py` pins: content "audience","lint"; design
"interaction","accessibility"; research "sources","uncertainty"). Runs in
parallel with U2 against this document's heading spec; the join's gate is
the integration check.

**U4 — the callables and the vocabulary.** `skills/kernel/orch-do/SKILL.md`
and `skills/kernel/orch-judge/SKILL.md` state the one rule above, drop the
`packs.py cells <digest>` sentence (the prompt hands the craft path; two
owners of one fact), keep every property `tests/test_verification_model.py`
pins by meaning, updating a spelling pin only where the sentence it pinned
is the one being changed. `docs/vocabulary.md` craft-section entry
rewritten to the keyed form. Body budgets per `rules/composition.md` §5.

**U5 — the launch prompt names the kind.**
`scripts/tickets_dispatch_launch.py` `_craft_lines` adds one sentence after
the craft path: for a `do`, "You make a `<kind>`: the craft's `## Lens`
entry `### <kind>` is what your artifact must satisfy"; for a `judge`, "You
judge `<kind>` artifacts: that same entry is your criteria". The kind comes
from the assignment: a judge's from its artifact lines (one kind per judge;
mixed kinds refuse at mint), a `do`'s from the adapter unless the new
`do --makes root|cut` flag names a planning kind. `tickets_assignment.py`
carries `lens_key`; `tickets_mint.py`/`tickets_commands.py` carry the flag.
Tests in `tests/test_dispatch_launch.py`.

Out of scope: retiring `packs.py cells` itself; new artifact kinds beyond
root and cut; any change to `tickets_grade`'s Spec fields read; workflow
bodies under `example-workflows/`.

## Acceptance for the whole

`python tools/run_required.py --no-cache` green at the joined tip; a
`judge` minted with `--artifacts root:<a live root_generation>` is
accepted and its launch prompt names `### root`; every pack's craft passes
`validate_craft_sections` with the four headings and its Lens keys.
