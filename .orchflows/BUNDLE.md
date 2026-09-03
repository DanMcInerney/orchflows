---
name: orchflows-contrib
version: 2026-09-02
requires: []
---

# orchflows-contrib

This repository's own bundle: the first-party ring items that are not part
of the installed library. `skills/research-acquire/` is one — an
acquisition skill with its own scripts and tests, shipped to whoever
imports this bundle rather than installed with the library.

Nothing else belongs here. The library ships from `skills/`, `packs/`,
`sheets/` and `example-workflows/` at the repository root; design notes,
reviews and run scratch live in `research/`.

A consumer imports this bundle with `orchflows add <git-url>@<tag-or-sha>`
and gets the items above, resolved through their own home ring. It requires
no other bundle.
