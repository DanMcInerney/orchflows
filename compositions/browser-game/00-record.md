---
id: 00-record
executor: orch-execute
pack: orch-content-pack
depends_on: []
bound: <= 80 tool calls
independence: checker
isolation: required
profile: orch-worker
---

<!-- BGW-TRACE[implementation:program-record|PJ-03,PJ-07] -->
<!-- BGW-TRACE[implementation:question-authority|PJ-06,PJ-09,PJ-10] -->
<!-- BGW-TRACE[implementation:decision-safety|PJ-22] -->

## Goal

One versioned browser-game program record in {{workspace}} for {{brief}},
conforming to the program-record schema and intake-authority policy named in
Context. It records every Q-01 through Q-12 atomic field independently, with
its disposition, authority kind, owner, rationale, evidence, and revision.
Every omitted material field has a stable open-question or decision identity;
settled decisions retain their revision and invalidation trigger. A missing
`kind: user-only` field returns the policy's complete question envelope with
the question verbatim for root relay. An unrelated user-only gap does not
block an independently schedulable empirical field.

## Context

- input: {"name":"brief","type":"literal","value":"{{brief}}"}
- input: {"name":"target-directory","type":"literal","value":"{{workspace}}"}
- input: {"name":"program-record-contract","type":"literal","value":"compositions/references/browser-game-program-record.schema.json"}
- input: {"name":"intake-authority-policy","type":"literal","value":"compositions/references/browser-game-intake-policy.json"}
- input: {"name":"instance-validator","type":"literal","value":"browser_game_validate.py; run it against the emitted program record before filing Result"}
- input: {"name":"audience","type":"literal","value":"browser-game product owners and delivery executors"}
- input: {"name":"voice-contract","type":"literal","value":"concise operational record; explicit identities, authority kinds, and open state"}
- input: {"name":"length-budget","type":"literal","value":"the smallest complete record; tables may carry repeated fields"}
- input: {"name":"citation-policy","type":"literal","value":"cite fixed evidence and governing AUTH, U, CR, EX, PJ, or D identities beside each decision"}

Exceptional constraints:

- invent a stack, cohort, support promise, budget, fallback, provider, license acceptance, or release policy
- settle a user-only field from evidence or paraphrase its question before root relay
- represent absence as agreement or silently overwrite a settled decision
- combine research, prose, code, and rendered outcomes into one artifact identity
- file a program record that the instance validator rejects

## Report
