# Social Search

Optional library of three skills composing orchflows-light's two primitives.

```text
social-search
  choose sites → search-site per site with deferred gathering
    search-site → orch-work → worker: collect and hand off per research.search-site guidance
  gather every outcome, keep gaps
  rank-evidence → orch-review → ranked, cited assessment
```

Site knowledge: `guidance/research.search-site.md` plus one `research.search-site.<site>.md` per site; `search-site` accepts any domain. `search-site` and `rank-evidence` also work alone. The prompt supplies question, dates, sources, bounds and output location.

## Install

`scripts/orchflows.py setup --example social-search` (Python 3.11+) seeds `~/.orchflows/libraries/social-search` once; register the package with the host. Requires orchflows-light 0.6.0 or later and native child delegation. `setup --example research-acquire` adds the optional YouTube transcript reader. Setup preserves existing libraries; update old copies deliberately, replacing per-site skills with `search-site` and the relevant guidance.

Identities are `social-search:<skill>`. Dependencies and outputs: [library context](references/library-context.md). Trial: [request](trials/request.md), [acceptance](trials/expected-behavior.md). Origin: adapted from [orchflows recent-search](https://github.com/DanMcInerney/orchflows/tree/945546721732aa564a086ee9543803b38017e1c3/example-workflows/recent-search) under the retained [MIT license](LICENSE).
