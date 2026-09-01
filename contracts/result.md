# Result contract

The generated [result lifecycle cell](../docs/lifecycle.md#ticket-lifecycle)
names the committed launch these executor records may enter behind.

The executor files work into its ticket's one `## Report` section as it is
produced. There is no second heading to choose and no order to file in: what
belongs in a report is what a reader would need and cannot re-derive — the
exit code of every command as it was observed, what changed and why, what was
deliberately not done and why, and whatever the assignment asked to be
covered. Code tests are one possible kind of evidence, not a ticket-authored
criterion. Research, design, content, and specification work use the
artifact-appropriate evidence in
[verification.md](../rules/verification.md) §2. These records are append-only
after seal and do not change the semantic assignment digest. A write names its
`assignment_seal`, `dispatch_id`, and unique `record_id`. Every successful
write appends after what is already there and adds
exactly one canonical writer attribution,
`### Written by <writer>`, and returns that identity. The
required `--by` value must match both the dispatch attempt's recorded owner
and the currently claimed ticket; a reusable human-readable name alone grants
no filing authority. The command never changes lifecycle state.

The reserved outcome carries one non-empty closing note, appended to `Report`
like any other filing. Nothing compares it against what was already streamed:
no consumer parses this prose, so a repeated sentence is a reader's problem
rather than a refusal that loses the close.

The ticket section mutation and its dispatch-v1 committed record are
one atomic write. An exact retry of a committed `dispatch_id` plus `record_id`
returns the stored success without adding content, even after retirement,
replacement, or lease expiry. Changed operation content for that pair is an
`idempotency-conflict`; an unseen record on an ended attempt is stale. Every
refusal leaves the ticket byte-identical. A filed body may itself carry `## `
headings without being read as a second ticket section, and survives the round
trip byte for byte; how it is stored that way is
[`scripts/tickets_markdown.py`](../scripts/tickets_markdown.py)'s.
An unseen result requires the attempt's committed launch, and carries the
`(dispatch_id, assignment_seal, --by)` the attempt was opened under: that
triple is the writer's whole authority, on this write and on every other.

A read-only critique never rewrites the reviewed executor's Report. It is a
`judge` brick like any other now: its enumerated blockers are this same one
free-text `## Report`, and the repair answering it is a `do` brick the
calling workflow opens against them, sequenced by prose rather than a
mechanical selector. The `orchflows.review.v1` ledger -- `GatePlan`,
`CritiqueAdjudication`, `RepairOutcome`, and the `checked_by`/`review_stage`
fields and `tickets.py check` reader it carried -- retired with the door
that used to build it; see [work-item.md](work-item.md#review-stage-ledger).
`dispatch-join` writes no such chain and binds no findings array, accepted
subset, or fixed artifact identity of its own.

The join checks the returning name against the claim. The reserved durable
return and its lifecycle consumption belong to the
[dispatch contract](dispatch.md#outcome-and-join). Deterministic
repository-global gates run on the integrated tip. A path named in Details is
never an acceptance boundary.

A generic `dispatch-commit` record is not an executor report and does not
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

T0 supersession record sha256:36d63a5c339d9a7c987df1ad4725f6bc46d48490c57f664e59d9043a389b04a8:
an unseen executor result is admitted behind the attempt's committed packet
rather than behind a durable accepted receipt. The receipt is gone; the
`(dispatch_id, assignment_seal, --by)` triple every result already carried
is the writer's whole authority, and the first record a child files is its
acceptance.

T0 supersession record sha256:730ceeaa514de270f8094c987eccd06afa7244e99dc393774567a1eed6241cd2:
the record an unseen executor result enters behind is the attempt's
committed launch. The packet it used to name is gone, and the identities
this contract requires of every write are unchanged.

T0 supersession record sha256:f80f8c31a1a37649ee72f808d6fcec7a032eada1e542520ab208437f280f298b:
one filing channel. The executor's five sections collapse to `## Report`, and
`executor_result` loses `section` and `mode` with the flags that chose them --
`--section`, `--append`, `--replace` -- because one section admits one mode and
nothing downstream reads which heading a fact arrived under. Every write
appends. The closing outcome is one non-empty note appended here too, and the
delta law that refused a repeat is gone: no consumer parses this prose, so a
repeated sentence is a reader's problem rather than a refusal that loses the
close. Critique findings stop riding in `Result` or `Feedback`: the complete
array crosses the join as `--findings-file <path|->`, exactly as the accepted
subset crosses as `--accepted-file <path|->`, and both are bound in the review
ledger. The identities every write carries are unchanged.

<!-- BEGIN GENERATED T0 SHAPES -->
## Generated T0 shape

GENERATED BY tools/render_shapes.py from `contracts/shapes.json` for `contracts/result.md`. Rendered T0 shape; declaration drift is a validation error.

### `executor_result`

| field | required | declared values |
| --- | --- | --- |
| `assignment_seal` | yes | — |
| `body` | yes | — |
| `operation` | yes | `result` |
| `writer` | yes | — |

<!-- END GENERATED T0 SHAPES -->
