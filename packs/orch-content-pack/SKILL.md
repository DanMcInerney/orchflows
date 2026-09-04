---
name: orch-content-pack
description: Domain pack for prose read by humans — document evidence and workspace. Stamp when the deliverable is a document.
adapter: document-tree
---

# orch-content-pack

## Making

The shape principles every domain shares are
[rules/token-economy.md](../../rules/token-economy.md) §10's.

## Vocabulary

- **hook** — the opening's specific promise that makes reading the
  next sentence rational.
- **throughline** — the one claim or question every section serves;
  what one document means mechanically.
- **voice contract** — the dimensions a judge scores: register (the
  formality and energy band of the prose), person, stance (the writer's
  relation to the claim), cadence (sentence rhythm) — and, where
  dimensions or budget can collide, which yields.
- **arc** — the sequence in which understanding is built; every genre
  has one (problem → stakes → turn → resolution; task → steps → proof).
- **section job** — the one thing a slot does for the throughline;
  two sections doing it is a slicing defect.
- **skim layer** — headings plus first sentences, read alone, carry
  the whole argument.
- **signpost** — a transition that carries the argument between
  sections, not mere adjacency.
- **landing** — the ending pays exactly what the hook promised.
- **cut log** — the record of what budget pressure removed.

## Workspace

document tree: identities are document revisions; integration compares
actual candidate changes and resolves section overlap.

## Spec fields

target directory; audience; voice contract; length budget; citation policy

## Lens

### root

#### What a frozen document root carries

- The audience, and the voice contract on every dimension a judge will score.
- A length budget stated as a number; weakest-first cutting has no meaning
  without one, and the cut log then measures against nothing.
- One throughline, phrased as a claim or a question, so a section job can be
  caught undone.

#### Worth asking at intake

- Who reads this, and what can they do afterwards that they cannot now?
- Which genre's arc is it — problem to resolution, or task to proof?
- Which assertions have to trace to supplied evidence, and where does that
  evidence sit?
- What citation policy applies, and does the reader see the citations?

#### Exemplar policy

Point at a document and say which dimensions to borrow: register, cadence,
skim layer. Subject matter is never borrowed, and a piece admired whole was
never an exemplar.

### cut

When one executor owns a complete artifact — one document, or a named set
edited together — issue one direct `orch-do` root for the whole of it.
Goal names the finished document; Context carries the voice contract,
citation policy, length bound, and fixed evidence.

One terminal assembly ticket names and assembles the decomposed sections in
one final editorial pass.

### doc

- Voice: does every section hold the spec's voice contract on every
  dimension it names, including the signposts the edit added?
- Structure: does the argument's arc arrive in the outline's order
  along one throughline — no section doing another's job or leaving
  its own undone — with the landing paying the hook?
- Skim layer: do the headings and first sentences alone carry the
  whole argument?
- Length: inside budget without cutting a criterion's coverage — check
  the cut log against acceptance.
- Claims: sampled claims trace to the spec's evidence; anything the
  evidence cannot support is marked, not smoothed over.
- Audience: the stated reader can act on this without knowledge the
  spec does not grant them.

Identify the document revision. Record applicable render and structure
observations, prose-lint output, claim-to-source support, reader fit against
the audience and voice facts, and uncovered claims.

Weigh in listed order.

- Concrete before abstract: an abstraction is earned by the instance
  beneath it, and a named instance or number beats a category word.
- The length budget is design pressure: cut weakest-first, into the
  cut log.

## Stages

- Draft from the fixed evidence and voice contract; every section has one
  section job and earns its place in the throughline.
- Edit only after the complete draft exists: preserve supported claims,
  add signposts, and cut weakest-first while recording the cut log.
- Assembly is terminal and deterministic: name every included section,
  resolve ordering and duplicate jobs, and emit one document identity.
- Re-read the skim layer and verify the landing against the opening hook.
- Hand off the revision number, length tally, citations, and recorded cuts.
