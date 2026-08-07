# bad-late-qualification

HAZOP "late": the seal event ledger records identity minting before
qualification recording — the package's qualification verdicts cover
an identity minted after they were written. Every byte still
verifies: manifest recomputes, digests match, verdict entries are
complete. What is wrong is the order of operations the package's own
provenance attests, which is exactly the seal-ordering law: a verdict
recorded after the seal qualified nothing that the seal covers.
`late-operation` is a new deviation name, absent from the burn
census.

deviation: late-operation @ seal-ordering locus (qualification recorded after identity minting in the seal event ledger)
