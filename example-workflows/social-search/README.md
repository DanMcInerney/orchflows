# Social Search

Research public sources in parallel, then independently rank the collected evidence.

```text
social-search
  assign distinct evidence and shared originals → search-site per assignment
    search-site → orch-work → collect and hand off evidence
  gather every outcome, keep gaps
  rank-evidence → orch-review → ranked, cited assessment
```

N collection assignments use N workers and one reviewer. Each assignment covers a site, web scope, feed set or related sources; shared originals have one owner. The prompt supplies question, dates, sources, bounds and output location. A total time limit includes review.

## Structure

| Owner | Responsibility |
| --- | --- |
| `skills/` | Composition, collection and assessment; either leaf also works alone |
| [Library context](references/library-context.md) | Shared dependencies, guidance selection and paths |
| [Evidence contract](references/evidence.md) | Collector-to-reviewer handoff |
| [Research guidance](guidance/research.search-site.md) | Collection and assessment criteria; site specializations add differences |
| `trials/` | Requests and expected behavior for [sites](trials/request.md), [web/feeds/Lemmy](trials/web-feeds-lemmy/request.md) and [papers/discussion](trials/papers-and-discussion/request.md) |

## Install

From a complete orchflows-light checkout, run `python scripts/orchflows.py setup --example social-search` (Python 3.11+). Setup preserves existing libraries. Core `docs/hosts.md` covers host registration and refresh. Invoke `social-search:<skill>`.

Requires orchflows-light 0.6.0+, native child delegation and public search/read tools. Optional `setup --example research-acquire` adds acquisition and a YouTube transcript reader; that package owns its dependencies and routes. Its generic feed support requires version 0.4.0+.

Adapted from [orchflows recent-search](https://github.com/DanMcInerney/orchflows/tree/945546721732aa564a086ee9543803b38017e1c3/example-workflows/recent-search) under the retained [MIT license](LICENSE).
