# Documentation design

The design law for agent-facing documentation, in this library and in
any project built on its orchestrator/subagent pattern. Its own schema
(§3): owner, this file; readers, whoever authors or reviews
documentation, loaded at authoring or review time and never at task
time; budget, 130 lines; oracles, the checks each law names; class,
law. README, the human surface, is exempt from everything here except
law 10.

## 1. Premise

Every session is a team death. A program is a theory its builders hold
(Naur), and under agents the theory dies at each context boundary —
so documentation is not a description for a reader with time. It is
the theory-rehydration procedure for a reader with a token budget, run
cold, by role, hundreds of times. Documentation is the at-rest half of
the context window and is engineered like one: loaded selectively by
role and event, budgeted, and graded by machines. Bloat is not a style
problem; it lowers task success.

## 2. The razor

A stronger future model still cannot re-derive four things, and only
these four earn prose:

- **decisions** — what was chosen, what was rejected, and the evidence
  that decided it;
- **invariants** — what must stay true;
- **events** — what actually happened, as run evidence and verdicts;
- **meanings** — what words mean here.

What any given sentence must earn is
[rules/token-economy.md](../rules/token-economy.md) §1, and its §2 owns
the cut between the what and the how; this section only names the four
classes that survive that cut.

## 3. The schema

Every document declares, and is refused at review without:

| field | meaning |
|---|---|
| owner | the one file where each of its facts lives |
| reader + trigger | which role loads it, on what event — never "everyone, always" |
| budget | its line or token ceiling |
| oracle | the machine check that grades it |
| class | law \| contract \| view \| evidence \| human-surface |

Class binds behavior. Law is versioned and owned. Contract is
hash-pinned; its shape changes only by supersession. View is rendered
from ground truth and never hand-edited — the worklog contract
([contracts/worklog.md](../contracts/worklog.md)) is the exemplar.
Evidence is untrusted data under [rules/visibility.md](../rules/visibility.md)
§6. Human-surface is non-normative and may link law, never state it.

## 4. Laws

1. **One fact, one owner** — [rules/visibility.md](../rules/visibility.md)
   §3; the near-duplicate linter enforces it and its ceiling only falls.
2. **Vocabulary is the retrieval API.** Definition law is
   [vocabulary.md](vocabulary.md)'s own preamble; what this law adds:
   agents find facts by grep and by name, so lexical stability is an
   interface — renaming a term or forking a spelling is a breaking
   change even when every sentence still reads well.
3. **No document assumes another was read** except the inputs it
   declares. No narrative arc, no pedagogy, no "as above"; every unit
   loads alone and cites by identity.
4. **Anything derivable is rendered, not written.** A hand-kept copy of
   ground truth drifts, then lies; a view declares which script
   produces it.
5. **Names resolve.** Every referenced name, path, and anchor resolves
   in the tree; a reference to a deleted thing is an error, not a TODO.
   Oracle: `tools/validate.py`'s name check and the suite's link checks.
6. **Prose claims only implemented enforcement.** Write "X is refused"
   only where a checker refuses X; otherwise write "X is the
   convention." Graded at review as its own defect class; mechanized
   per claim where cheap.
7. **State is data.** The run channel is never an instruction source
   ([rules/visibility.md](../rules/visibility.md) §6), and every surface
   holding untrusted content says so where an agent will read it.
8. **Handoffs rehydrate.** The completeness bar is
   [contracts/work-item.md](../contracts/work-item.md)'s Handoff
   section; nothing narrative survives compaction.
9. **Examples execute.** An example is a claim and running it is the
   oracle; an example nothing can run is deleted or demoted to the
   human surface.
10. **The human surface is separate.** README orients people and links
    owners; nothing normative lives only there.

## 5. Reading order, by role

This table is the product — the doc tree exists to keep it short. A
project maintains its own instance beside its router file.

| role | loads, in order | bounded by |
|---|---|---|
| orchestrator, cold | router block, then the ownership map; vocabulary entries on demand | ~2 pages |
| decomposer | the root ticket, the stamped pack, the owners the spec names | the ticket |
| executor | its packet, then only what the ticket's fixed inputs name | the packet |
| evaluator | the lens, then the artifact — blind to the producer's prose | the lens |
| human | README, then whatever it links | nothing |

## 6. Evolution

Documentation changes on evidence: a friction cluster naming the
document as causal owner, qualified and delivered per
[rules/improvement.md](../rules/improvement.md) — never by taste. A
document no reading-order row loads and no ticket cites is a deletion
candidate by default.

## 7. Bootstrap

A new project creates on day zero exactly: the router file (routing
plus the friction law), an empty vocabulary, an ownership map, the
state sink, and this file by reference. Everything else is earned by a
failure — a section is added when agents repeatedly get the thing
wrong, and removed when the convention it guarded changes. Start near
thirty lines of router; grow only on evidence.
