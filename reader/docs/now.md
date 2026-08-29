# Now

Now is the read-only execution home. Its dominant hierarchy is one vertical
scan: **Current work** first and **Recent history** below. Current runs remain
ordered with attention before active execution. Completed runs are visually
subordinate without losing their canonical identity, lifecycle counts, last
meaningful activity, or repository metadata. Client identity is never inferred.

Every run row gives the plain-language objective and state before secondary
metadata. Its compact semantic flow is derived from canonical dependency depth;
Brief, Plan, Work, Review, and Verify are presentation labels, not lifecycle
law. The visible flow is noninteractive orientation and has an ordered
nonvisual equivalent that names every step, state, and represented ticket
count. Now does not render a second detailed execution graph.

Current and Next lists identify the exact tickets that canonical status marks
as executing, attention-worthy, or ready. Waiting work is not described as
next. The run objective and each current or next ticket are descriptive native
links built by `reader/web/src/shared/routes/executionRoutes.ts`; the run link opens
the full execution graph and ticket links open canonical ticket detail. Now
does not import another feature's view.

Empty current work, a filter with no matches, unreadable canonical data,
unknown ticket progress, paused polling, and absent recent history each have an
explicit state. Unknown data remains visible and is never guessed. Pause live
freezes visual replacement for inspection; it does not stop or mutate a run,
and the active filter survives pause and resume. At compact width, Current and
Next stack while the current-before-history hierarchy remains unchanged.

The toolbar is a filter group: `All runs` and `Needs attention` operate on the
same hierarchy and do not imply a text-search field. Reduced motion removes
nonessential animation, and forced colors retain state words, glyphs, and
borders.

The view consumes only closed same-origin projections. It never displays or
requests prompts, tool inputs or outputs, command output, file contents,
transcript text, or subagent conversation content.
