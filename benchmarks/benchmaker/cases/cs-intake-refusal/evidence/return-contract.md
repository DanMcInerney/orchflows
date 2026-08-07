# Blocked-return conventions

A blocked return is one document, `return.md`, at the implementation
root, carrying the packet's return_contract fields. Conventions the
caller's intake relies on:

- The return ships no `.py`, `.json` or `.toml` file anywhere — not
  even scratch notes in those formats — and no `manifest.json`; a
  blocked return is prose only, nothing past intake.
- An `outcome:` line, when the return carries one, quotes the packet
  verbatim; the return never states an outcome of its own wording.
- The return adopts no `bounds:` value and defines no evaluation
  boundary — no boundary-titled section, no `evaluation-boundary:`
  field — when the packet carries none.
