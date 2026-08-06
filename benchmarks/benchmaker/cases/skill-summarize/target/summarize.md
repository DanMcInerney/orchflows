---
name: cache-rollout-digest
outcome: one cited digest of the source set, inside the declared bounds
---

```constraints
max_words: 120
citation_ids: closed
citation_coverage: every-sentence
```

Read every source in `evidence/sources.md`. Write one digest of the set.

Cite with `[S<n>]` naming the source the sentence rests on. The set is
closed: cite only ids that appear as a heading in `sources.md`. When no
source supports a sentence, cut the sentence — never reach for an id
that is not in the set.

Every sentence carries at least one citation. A sentence with none is a
claim with no owner, whatever its content.

Stay within the word bound. Counting excludes heading lines and citation
tokens, so the bound is a bound on prose. Cut the least load-bearing
sentence rather than compressing every sentence into an unreadable one.

Cover what the set carries: the rollout outcome and the incident. Never
add a recommendation, a cause, or a number no source states.
