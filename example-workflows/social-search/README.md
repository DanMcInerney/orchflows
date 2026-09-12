# Social Search

Optional library of three skills composing orchflows-light's two primitives.

```text
social-search
  assign distinct evidence and shared originals → search-site per assignment
    search-site → orch-work → collect and hand off evidence
  gather every outcome, keep gaps
  rank-evidence → orch-review → ranked, cited assessment
```

An assignment covers a named site, web scope, feed set or related sources. Group overlapping work; give shared originals one owner. N assignments use N workers and one reviewer, with no fixed source roster or worker count. The prompt supplies question, dates, sources, bounds and output location; a total time limit includes final review.

`search-site` and `rank-evidence` also work alone, sharing an [evidence contract](references/evidence.md). [Research guidance](guidance/research.search-site.md) adds collection and assessment preferences; site specializations contain only source differences. [Library context](references/library-context.md) selects guidance and resolves dependencies once.

## Install

`scripts/orchflows.py setup --example social-search` (Python 3.11+) seeds `~/.orchflows/libraries/social-search` once; register the package with the host. Requires orchflows-light 0.6.0 or later and native child delegation. Native public search and HTTP tools support collection; `setup --example research-acquire` adds optional public acquisition and a YouTube transcript reader. Its usage references own the supported routes; generic feeds require research-acquire 0.4.0 or later. Setup preserves existing libraries; update old copies deliberately.

Identities are `social-search:<skill>`. Trials: [site collection](trials/request.md), [web, feeds and Lemmy](trials/web-feeds-lemmy/request.md), and [papers, blogs and discussion](trials/papers-and-discussion/request.md), each with separate expected behavior. Origin: adapted from [orchflows recent-search](https://github.com/DanMcInerney/orchflows/tree/945546721732aa564a086ee9543803b38017e1c3/example-workflows/recent-search) under the retained [MIT license](LICENSE).
