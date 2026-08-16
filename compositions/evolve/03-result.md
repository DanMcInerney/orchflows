---
id: 03-result
executor: orch-verify
pack: orch-code-pack
depends_on: [02-campaign]
write_scope: []
bound: <= 30 tool calls
excluded_actions:
  - closing on a score card that cites no admitted evidence
  - expose protected evidence
  - add a closing wrapper
independence: checker
isolation: none
---

## Objective

The campaign's verdict over {{target}}: one final score card naming the
final incumbent and the admitted result/evidence behind it.

## Fixed inputs

- 02-campaign's `## Result` — the final incumbent identity, its score
  cards, and the promotion/kill log, by identity.
- 00-eval's `## Result`, or {{evaluation}} where that is not `none` —
  the frozen evaluation identity, mode, promotion rule and margin.
- 01-eligibility's `## Result` — the evaluation identity {{incumbent}}
  was admitted under.

## Completion test

- the final score card cites the final incumbent — promoted, or {{incumbent}} kept where 02-campaign closed `limited` — and the admitted result/evidence behind it | oracle: the card against 02-campaign's Result and status | oracle_class: deterministic | provenance: pre-existing
- the evaluation identity behind the final card is the one 01-eligibility admitted {{incumbent}} under | oracle: the two identities compared | oracle_class: deterministic | provenance: pre-existing

## Return fields

status; result — the final incumbent identity; verification — the final
score card and admission verdicts, with the frozen evaluation identity
and mode, generation count, promotion/kill log and bounds spent;
feedback; risks

## Result

## Verification

## Feedback

[]

## Risks

[]
