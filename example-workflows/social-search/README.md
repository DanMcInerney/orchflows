# Social Search

Optional library of three skills composing orchflows-light's two primitives.

```text
social-search
  choose bounded source scopes → search-site per assignment with deferred gathering
    search-site → orch-work → worker: collect and hand off per research.search-site guidance
  gather every outcome, keep gaps
  rank-evidence → orch-review → ranked, cited assessment
```

An assignment covers a named site, web scope, feed set or closely related sources. Choose scopes for their likely contribution to the question; related sources can share a worker to reduce overhead. `search-site` and `rank-evidence` also work alone. N assignments use N workers and one reviewer. The prompt supplies question, dates, sources, bounds and output location.

The [shared source guidance](guidance/research.search-site.md) owns the inspectable evidence handoff and final Review criteria, keeping evidence strength separate from measured reach. Dotted specializations add source knowledge. [Library context](references/library-context.md) owns their selection and resolves optional readers once.

## Install

`scripts/orchflows.py setup --example social-search` (Python 3.11+) seeds `~/.orchflows/libraries/social-search` once; register the package with the host. Requires orchflows-light 0.6.0 or later and native child delegation. Native public search and HTTP tools support collection; `setup --example research-acquire` adds optional public acquisition and a YouTube transcript reader. Its usage references own the supported routes; generic feeds require research-acquire 0.4.0 or later. Setup preserves existing libraries; update old copies deliberately.

Identities are `social-search:<skill>`. Trials: [site collection](trials/request.md), [web, feeds and Lemmy](trials/web-feeds-lemmy/request.md), and [papers, blogs and discussion](trials/papers-and-discussion/request.md), each with separate expected behavior. Origin: adapted from [orchflows recent-search](https://github.com/DanMcInerney/orchflows/tree/945546721732aa564a086ee9543803b38017e1c3/example-workflows/recent-search) under the retained [MIT license](LICENSE).
