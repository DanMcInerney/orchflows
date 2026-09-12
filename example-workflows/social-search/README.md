# Social Search

Reference composition of orchflows-light's two primitives.

```text
social-search
  choose sites → search-site per site with deferred gathering
    search-site → orch-work → worker: collect and hand off per research.search-site guidance
  gather every outcome, keep gaps
  rank-evidence → orch-review → ranked, cited assessment
```

Site knowledge: `guidance/research.search-site.md` plus one `research.search-site.<site>.md` per site; `search-site` accepts any domain. `search-site` and `rank-evidence` also work alone. The prompt supplies question, dates, sources, bounds and output location.

## Install

`scripts/orchflows.py setup --example social-search` (Python 3.11+) seeds `~/.orchflows/libraries/social-search` once; register the package with the host. `setup --example research-acquire` adds the optional YouTube transcript reader.

Identities are `social-search:<skill>`. Dependencies and outputs: [library context](references/library-context.md). Trial: [request](trials/request.md), [acceptance](trials/expected-behavior.md). Origin: adapted from [orchflows recent-search](https://github.com/DanMcInerney/orchflows/tree/945546721732aa564a086ee9543803b38017e1c3/example-workflows/recent-search) under the retained [MIT license](LICENSE).
