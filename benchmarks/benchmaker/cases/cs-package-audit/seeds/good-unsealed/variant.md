# good-unsealed

A lawful package that was edited after it was assembled: one component's
bytes — `provenance/provenance.json`, case `pc-4` — differ from the
reference target's, and nothing in the manifest records a digest that
would have to move with them. The manifest carries the nine schema
fields and addresses every component by locator alone.

A benchmark's version is the git revision it sits at, so revising one
produces a new revision rather than a forgery, and the audit reads what
the package ships instead of what a recorded digest claims it shipped.
The probe must pass it.
