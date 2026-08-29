# Result contract

The generated [result lifecycle cell](../docs/lifecycle.md#ticket-lifecycle)
names the receipt required before this contract's executor records may enter.

The executor files work into its ticket's `## Result`, `## Verification`,
`## Feedback`, `## Risks`, and optional `## Handoff` sections as it is
produced. `Result` identifies the delivered artifact. `Verification` records
the methods the executor chose, their observations, the Goal portions they
cover, contradictions, and gaps. Code tests are one possible method, not a
ticket-authored criterion. Research, design, content, and specification work
use the artifact-appropriate evidence in
[verification.md](../rules/verification.md) §2. These records are append-only
after seal and do not change the semantic assignment digest. A write names its
`assignment_seal`, `dispatch_id`, and unique `record_id`. Every successful
section write adds exactly one canonical writer attribution,
`### Written by <writer>`, and returns that identity. The required `--by`
value must match both the dispatch attempt's recorded owner and the currently
claimed ticket; a reusable human-readable name alone grants no filing
authority. The command never changes lifecycle state.

The reserved outcome carries only the non-empty closing delta that has not
already entered these sections through result records. Repeating an attributed
item is refused before mutation; outcome import therefore materializes every
evidence item once rather than treating the close as a second snapshot.

The ticket section mutation and its dispatch-v1 committed-record receipt are
one atomic write. An exact retry of a committed `dispatch_id` plus `record_id`
returns the stored success without adding content, even after retirement,
replacement, or lease expiry. Changed operation content for that pair is an
`idempotency-conflict`; an unseen record on an ended attempt is stale. Every
refusal leaves the ticket byte-identical.
An unseen result requires the attempt's durable `dispatch-receipt`, proving the
established receiver accepted the exact committed packet before execution.

A read-only critique never rewrites the reviewed executor's Result or
Verification. A verifier records its independent verdict and evidence in
`## Verification`.
Gate and ordinary-checker critique findings are streamed in either `Result` or `Feedback` as one JSON array. Each finding object has exactly `blocking` (boolean), `class`, `goal_impact`, `id`, `repair`, `summary` (non-empty strings), and `evidence` (a non-empty array of non-empty strings). Finding ids are unique in the array. The join accepts any valid JSON encoding of the findings and accepted arrays, normalizes both, and binds the complete findings and exact accepted subset in the review ledger.

The join reads the fixed candidate identity and its actual diff, checks the
returning name against the claim, and adjudicates only material blockers
against Goal and Context. The reserved durable return and its lifecycle
consumption belong to the [dispatch contract](dispatch.md#outcome-and-join).
Deterministic repository-global gates run on the integrated tip. Suggested
files are never an acceptance boundary.

A generic `dispatch-commit` record is not an executor Result and does not
replace this section's writer. The `result` operation uses the same committed
record precedence while atomically writing the attributed section. Neither
makes an exactly-once external-side-effect claim.

T0 supersession record sha256:9c4a109ca9158a60109f756f02e28673270cc741d8ad2e6a2fa06529841d5fdd: result section writes now require and return their current claim writer.

T0 supersession record sha256:3d86568240f6cd4fd87483b1be39e415f496d588601935a5e67d72bcf2b1dc58: executor-record writes are dispatch-v1 operations fenced by
assignment, attempt, record, and recorded writer identity; the old
claim-name-only writer is not a compatibility path.

T0 supersession record sha256:0654e413997c54fcbe12f4aa4e8ebb27bae7c36ac2c6c7dc0798917a48414524: `dispatch-join`
atomically binds a lifecycle disposition to one committed executor result and
the attempt that produced it.

T0 supersession record sha256:47f6855da46fd692a6dd8e42408ef721e719400d655f5e74e85dcdb50f924dd3: the
distinguished outcome envelope is the sole durable return consumed by join.

T0 supersession record sha256:734f7558400198917ee42aa9f0c06052bacdec2e0d9dd9304976e937e88b9873:
closing outcome evidence is the nonduplicating delta after streamed result
records, and an unseen executor result is admitted only after the dispatch
contract's durable accepted receiver receipt.

T0 supersession record sha256:80252b67dd8b7010630831f233be12ba8fe32c31ba98bfccbe277328b9a458eb:
critique Feedback result records are canonical JSON arrays whose complete value
and accepted subset are carried by the immutable review adjudication.

T0 supersession record sha256:ecac1cfcd4758e3389a36eb1da88d6856f0499ad34e5943fbdb23d321f6ce2fc:
critique finding records may use Result or Feedback, and join normalizes valid
JSON encodings before it compares and binds the accepted subset.

T0 supersession record sha256:7265fd61589c2e180d7aca87161ea02946868b001896cdbebb4d67024729ab59:
the T0 shape is declared in contracts/shapes.json and renders this contract
section and its validator consumer.

T0 supersession record sha256:731cb4b8fa47a72a1a890f6bb3a1c488214fb1c5456be0e99994b7ee93c45026:
the generated section wording is kept distinct from lifecycle prose while
remaining a deterministic declaration-to-consumer gate.

T0 supersession record sha256:cdc9c619f5843f308755e4ba841a4617957adca850afc2769f1a2017c6ef3301:
the generated T0 section now uses declaration-specific wording.

<!-- BEGIN GENERATED T0 SHAPES -->
## Generated T0 shape

GENERATED BY tools/render_shapes.py from `contracts/shapes.json` for `contracts/result.md`. Rendered T0 shape; declaration drift is a validation error.

### `executor_result`

| field | required | declared values |
| --- | --- | --- |
| `assignment_seal` | yes | — |
| `body` | yes | — |
| `mode` | yes | `write`, `append`, `replace` |
| `operation` | yes | `result` |
| `section` | yes | — |
| `writer` | yes | — |

<!-- END GENERATED T0 SHAPES -->
