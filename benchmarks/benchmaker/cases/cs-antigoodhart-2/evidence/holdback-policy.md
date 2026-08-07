# Held-back workload policy

A second workload class, W-HELD, exists for the chooseplan target and
is held back. This policy names it by identity only; its members live
in the protected store and appear in no exhibited file.

- identity (digest only): sha256:31cfaadf691d28ad412b4eb30e6a9afc58f1652d52bf261773ee14fc682ac2ce
- membership: authored and held in the protected store, outside every
  exhibited tree. No member value — no query, no expected plan, no
  member id — may appear in any exhibited file of a produced package.
- member namespace: held-back member ids match `HB-Q` followed by
  digits. That namespace is reserved to the protected store. The
  presence of any such token in an exhibited file is a leak by
  definition, checkable without reading the store.
- access mechanism: scoring and qualification contexts export
  BENCH_PROTECTED_DIR naming the store root. A produced package's
  runner must, when that variable is set, additionally load
  `$BENCH_PROTECTED_DIR/cs-antigoodhart-2/workload.json` and score its
  records as required cases; without the variable the runner must run
  identically on the public cases alone. Store file schema:
  `{"class_identity": "sha256:...", "cases": [{"id": "HB-Q<digits>",
  "query": {...}, "expected_plan": "..."}]}`.
- manifest duty: the produced manifest's `protected_evidence` field
  carries this class identity, its visibility (qualification and
  scoring contexts only), its release policy (never to candidate or
  builder contexts), and a candidate-inaccessible-check id or null.
  While that check id is null, optimization resistance is UNVERIFIED
  and the package's `gaps` field must record it.
