# Held-back evaluation streams — policy

A second class of evaluation streams exists for this target and is
held back from every builder and candidate context. This file declares
the policy; it never names a member.

- Members: stream files `stream-*.json`, each an object with `id`
  (string), `items` (list of strings), `seed` (integer) and `k`
  (integer). They live only in the protected store, outside every
  sealed public tree.
- Identity: the held-back set is fixed by a sha256 identity over the
  store's stream files, minted by the qualifying context (Q2) when it
  authors the store. At materialization the store does not yet exist,
  so the manifest records the identity as null with this policy cited
  as the binder; Q2's seal supersedes it.
- Visibility: qualification and scoring contexts only. Release policy:
  never to candidate or builder contexts.
- Access mechanism: probes and scoring read the environment variable
  `BENCH_PROTECTED_DIR` when it is set and degrade to public-subset
  checks when it is unset. Validator behavior is unchanged by this
  policy.
- No exhibited file — package, seeds, evidence, expected criteria —
  may contain a held-back stream constant.
