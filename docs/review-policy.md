# Delivery review policy

`review-delivery` owns ordinary delivery's review/repair/verification ending.
Its scope follows [composition](../rules/composition.md); callers supply
`context-file`, explicit `workspace-adapter`, and required `isolation` and
`repair-skill` along with the artifacts. A workspace path alone does not retain
a standard's adapter: a document directory inside Git still needs document-tree.
The parent chooses `--review-rounds 1`, positive finite N, or `until_pass`
when opening its frame. Precedence is explicit user choice, named workflow
setting, default one. A more discriminating standard changes strictness only.
One round consumes one substantive critique over fixed joined artifacts,
followed when needed by one repair wave and scoped verification. A pass stops
early. Further critique is allowed only by the selected repetition setting.

## Command carriers

For an unframed making ticket, create the review journal beneath that ticket
with `frame-open --parent <maker-ticket> --shape "judge > do > judge"` and a
goal file. It inherits the maker's owner and allowance; it is not a new
delivery.

`frame-open --review-rounds <setting>` seals `review_owner` and
`review_rounds`; root frames and making calls default to one. Descendant
frames and callables inherit that owner even across public workflow calls.
Nested `--review-rounds` refuses. An explicit new deliverable or independent
stage uses `frame-open --review-new-work <reason>` and may select its own
rounds; repair/verification subtrees cannot do this. The existing generated
`<ticket>.repair.<number>` ancestry also forbids owner resets and delivery
critique on descendants, including admission after resume. These completion
repairs need no invented critique reference; ordinary pre-review making continues. Opening another run for
the same delivery is not a legitimate reset.

An ordinary governed `judge` consumes `review_round`; its `review_phase` is
`critique`. `do --review-of <critique-ticket>` belongs to that round's repair
wave, including parallel workers. `judge --review-of <critique-ticket>` is
`verify`: its Goal must name the listed findings and affected seams. Both
seal the reference as `review_of`, inherit the owner, and preserve criteria.
The command validates reference ownership and pinned judge standards; it
cannot infer whether prose actually stayed in scope. The driver must inspect
that evidence. A failed launch still reserves its critique round: resume the
same ticket, never mint a replacement review to recover the allowance.

Parentless explicit judging remains standalone. Inside a delivery,
`judge --review-independent <reason>` explicitly declares independent research
judging or campaign comparison, never another default delivery review. It is
unavailable inside repair/verification. Named optimization campaigns keep
their own criteria and repetition; label their comparisons with this reason.
Policy cannot decide whether a claimed new scope is honest; its sealed reason
makes that decision visible. All policy fields are semantic sealed fields;
admission and resumed dispatch recheck inheritance, allowance and references.
Historical sealed tickets without policy are not rewritten.

## Installation and home migration

Do not install an older source tree over newer installed behavior. Create a
separate checkout at the receipt's source commit, apply the accepted review
commit there with `git cherry-pick`, resolve only its actual overlaps while
preserving that baseline's command evidence, seal validation, host bindings
and transactional installer, and run the gate on that resulting identity.
Install from that checkout with the verified interpreter and
`install.py --accepted-source <resulting-commit>`. Verify the receipt and
hashes of installed files; the reviewed source commit is not the combined
installation commit. Never change another task's worktree to do this.

Home packages are user-owned. Back up and edit only their closure paragraphs
and call carriers; do not copy gallery bodies wholesale. For
`3d-browser-game`, `browser-fps`, `orchflows-videos`, and `tiktok-video`:

1. Replace repeated broad judge/repair/re-judge endings with a call to
   `review-delivery`, supplying the same criteria, evidence, artifacts,
   workspace, context-file, explicit workspace-adapter, relevant isolation and
   repair-skill, and existing frame.
2. Forward the effective rounds to genuine independent stage owners through
   `--review-new-work <stage reason> --review-rounds <rounds>`.
   A local retry or production repair is not another stage.
3. Remove fallback instructions that open another repair batch after exhausted
   review. Preserve production probes, media/listening requirements and
   blocking dispositions. `verify` only proves listed repairs, not new overall
   acceptance. Run `orchflows check` on the edited home packages and exercise
   representative calls in a disposable project before resuming production.

The kernel judge and making contracts are reused unchanged in responsibility;
the common workflow has autorouting, checkpointed-build and delivery workflows
as callers. `tickets_review.py` owns only policy admission, not a workflow
interpreter, budget system, findings parser or progress scorer.
