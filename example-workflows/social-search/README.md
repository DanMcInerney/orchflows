# Social Search

Optional library of three skills composing orchflows-light's two primitives.

```text
social-search
  choose bounded source scopes → search-site per assignment with deferred gathering
    search-site → orch-work → worker: collect and hand off per research.search-site guidance
  gather every outcome, keep gaps
  rank-evidence → orch-review → ranked, cited assessment
```

Each assignment covers a named site, web discovery across chosen domains or the open web, or a supplied set of RSS/Atom feed URLs. `search-site` accepts these scopes and `rank-evidence` also works alone. N assignments use N workers and one reviewer; several feeds can share one worker. The prompt supplies question, dates, sources, bounds and output location.

Collection knowledge and the evidence handoff live in `guidance/research.search-site.md` and its dotted source specializations, including web, feeds and Lemmy. [Library context](references/library-context.md) owns their selection and optional readers.

## Install

`scripts/orchflows.py setup --example social-search` (Python 3.11+) seeds `~/.orchflows/libraries/social-search` once; register the package with the host. Requires orchflows-light 0.6.0 or later and native child delegation. Native public search and HTTP tools support collection; `setup --example research-acquire` adds optional web/feed acquisition and a YouTube transcript reader. Generic feeds require research-acquire 0.4.0 or later. Setup preserves existing libraries; update old copies deliberately, replacing per-site skills with `search-site` and the relevant guidance.

Identities are `social-search:<skill>`. Trials: [site collection](trials/request.md) and [acceptance](trials/expected-behavior.md); [web, feeds and Lemmy](trials/web-feeds-lemmy/request.md) and [acceptance](trials/web-feeds-lemmy/expected-behavior.md). Origin: adapted from [orchflows recent-search](https://github.com/DanMcInerney/orchflows/tree/945546721732aa564a086ee9543803b38017e1c3/example-workflows/recent-search) under the retained [MIT license](LICENSE).
