---
name: cache-rollout-digest
outcome: one cited digest of the source set, inside the declared bounds
---

```constraints
max_words: 120
citation_ids: closed
citation_coverage: every-sentence
```

You are digesting `evidence/sources.md` for an on-call reader who has
two minutes. Prefer the shortest digest that still carries the rollout
outcome and the incident.

Rules that do not bend:

- One citation minimum per sentence, written `[S<n>]`.
- The id must be a heading in `sources.md`. There is no id outside that
  file; if you cannot find one, delete the sentence.
- The prose stays under the declared word bound. Headings and citation
  tokens do not count toward it.
- No recommendation, cause, or figure the sources do not state.

Short is the house style. Four sentences that hold is a better digest
than eight that repeat the source set.
