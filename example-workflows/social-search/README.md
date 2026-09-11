# Social Search

Reference composition of orchflows-light's two primitives. Source profiles add site knowledge to one site-search workflow; one reviewer assesses everything gathered.

```text
social-search
  choose profiles → each invokes search-site with deferred gathering
    search-site → orch-work → worker: collect, prepare-evidence
  gather every outcome, keep gaps
  rank-evidence → orch-review → ranked, cited assessment
```

N selected sources = N workers + 1 reviewer. No source reviews, no review-to-acquisition loop. Profiles: [source-workflows.md](skills/social-search/references/source-workflows.md). `search-site` and `rank-evidence` also work alone.

The prompt supplies question, dates, sources, bounds and output location; there is no default window. Workers use native tools plus resolved [source readers](references/source-readers.md); the optional `research-acquire` library supplies a YouTube transcript script that owns fetch, parse and fallback, and missing readers leave native search usable.

## Install

`scripts/orchflows.py setup --example social-search` (Python 3.11+) seeds `~/.orchflows/libraries/social-search` once. Register the package with the host and refresh after edits. `setup --example research-acquire` adds the readers; its README declares dependencies.

Identities are `social-search:<skill>`; `resolve social-search --skill <skill>` locates files. Dependency and output resolution: [library context](references/library-context.md). Origin: [provenance](references/provenance.md). Trial: [request](trials/request.md) and [acceptance](trials/expected-behavior.md).
