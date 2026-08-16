# Vocabulary authoring

The order of work when a namespace — this library, a domain pack, or a
project — earns a vocabulary. Definition law lives with its owners: one
meaning everywhere in [vocabulary.md](vocabulary.md)'s preamble; the
mandated consumer test and craft budget in
[contracts/pack-signature.md](../contracts/pack-signature.md)'s craft
cell; lexical stability in [documentation.md](documentation.md) law 2;
one name per concept in
[rules/token-economy.md](../rules/token-economy.md) §10. This file only
orders the work; its budget is 40 lines.

1. Namespace first. A term belongs to the smallest namespace all its
   consumers share: the library's own words in `docs/vocabulary.md`, a
   domain's in its pack's craft, a project's in `<repo>/docs/vocabulary.md`.
   A term with one consumer is defined inline where it is used and
   earns no entry.
2. Collision second. Grep the term against every namespace above it
   and every T0 field name; a match with a different meaning is
   refused — the new thing needs a new word.
3. Entry third: one sentence naming the thing and what it excludes;
   any law about it by link to its owner, never restated; no undefined
   term inside a definition; a synonym is never introduced.
4. Consumer test fourth — the oracle: for each entry, one consumer
   outside the vocabulary file, by grep. Zero consumers → delete. Run
   it before every review.
5. Group by the reader's question — what is the structure, the unit of
   work, how done is decided — never alphabetically; a metered reader
   loads one section, not the file.
6. Rename only as a breaking change landing with every use in one
   change set; a fork of a spelling is a defect.

Grow on evidence: an entry is added when two contexts used one word
differently (a friction cluster), removed when its last consumer goes.
