# Scopes

Landing zones and oracles per scope. The scope law: a user-scope
install is the one resolver for both user- and project-scope custom
items' call edges, per its install receipt — project scope alone,
without a user-scope install, resolves nothing. A project additionally
carries a committable routing block, written by `install.py --project`,
so the item is discoverable in-repo. Canonical work happens in this
repository itself and needs no install.

| scope | skills land at | always-on rules land in | oracles |
| --- | --- | --- | --- |
| canonical | this repository's tiers, via PR | `rules/`, the host block template | validator, tests, library lens |
| user | `~/.orchflows/skills/<name>/SKILL.md` + host integrations | `~/.codex/AGENTS.md` and the user CLAUDE.md, outside managed blocks | library lens |
| project | `<repo>/.orchflows/skills/<name>/SKILL.md` + host integrations | the repo's `AGENTS.md`, outside managed blocks | library lens |

- User- and project-scope items are custom: outside library law,
  binding only at their scope, written to a skill's anatomy. What a
  custom item may be named is `orch-build`'s `Never:`.
- Host integrations match the installer's own: a Claude adapter stub
  at the scope's `.claude/skills/<name>/SKILL.md`, carrying the
  host-legal frontmatter (`name`, `description`, and for a role-bearing
  skill `context: fork` plus its matching `agent`) and an
  `@`-include of the item file — by absolute path at user scope, and by
  a path relative to the stub at project scope, because a project stub
  is committed and an absolute path in a committed file resolves on the
  machine that wrote it and nowhere else — never the orchflows-only
  `role`, which the item file itself keeps in full anatomy —
  and one routing line naming the item in the scope's AGENTS.md, which
  is the Codex surface.
- The scope's named oracle (library lens) is the only oracle for a
  custom item.
- Custom workflows instantiate from compositions: pick the nearest
  composition in `compositions/`, pin its open decisions (benchmark,
  bounds, defaults, schedule), and land the result at scope. A proven
  custom workflow may be proposed back as a composition — a
  canonical-scope build.
