# bad-late-qualification

HAZOP "late": the build event ledger records the components frozen
after the qualification recorded against them — the package's
qualification verdicts cover components that did not yet exist when
they were written. Everything else holds: the manifest carries the
nine fields, every component locator resolves, verdict entries are
complete. What is wrong is the order of operations the package's own
provenance attests: a verdict recorded before its components qualified
nothing the package ships. `late-operation` is a new deviation name,
absent from the burn census.

deviation: late-operation @ event-ordering locus (components frozen after the qualification recorded against them)
