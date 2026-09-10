---
name: orchflows-contrib
version: 2026-09-02
requires: []
---

# orchflows-contrib

This repository's own bundle holds first-party ring items outside the
installed library. The former `skills/research-acquire/` moved into the
public `recent-search` workflow package. Its evidence-return option replaces
standalone acquisition; see that package's migration reference.

Nothing else belongs here. The library ships from `skills/`, `standards/`
and `example-workflows/` at the repository root; design notes, reviews and
run scratch live in `research/`.

A consumer imports this bundle with `orchflows add <git-url>@<tag-or-sha>`
and gets the items above, resolved through their own home ring. It requires
no other bundle.
