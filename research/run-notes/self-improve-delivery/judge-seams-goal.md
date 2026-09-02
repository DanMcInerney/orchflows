Judge the SEAMS of the self-improve delivery (run 20260901T132749Z) at
the merged tip of branch `claude/self-improve-workflow-design-c2009b`
in C:\Users\danhm\tools\orchflows-public\.claude\worktrees\self-improve-workflow-design-c2009b.
Design doc `research/self-improve-design-2026-09-01.md` is the
normative spec. Three workers landed independently (B1.1 harvest door,
B1.2 event stream, B1.3 workflow body + law repoints) plus one repair
commit; per-child oracles already ran at each land — do NOT re-run
them. Your job is composition: do the parts fit, and did any worker's
green go vacuous at the merged tip?

Seams to read, in priority order:

1. Reader/writer schema seam (flagged by B1.1's own report): B1.1's
   `scripts/harvest.py` was written ASSUMING event field names while
   B1.2's `scripts/tickets_result.py`/`tickets_frame.py`/
   `tickets_land.py` defined the writer independently. Compare, field
   by field, what harvest reads from `events/*.jsonl` (event kinds,
   `workflow`, `goal_head`, ts format, provenance names) against what
   the landed writer emits. A silent mismatch (harvest degrades to
   null/no-match) is a BLOCKER finding: `--list-runs` and `--workflow`
   selection would ship dead.
2. Prose/CLI seam: every command and flag
   `example-workflows/self-improve/SKILL.md` names must exist with that
   exact spelling in the shipped `harvest.py` and `tickets.py`
   surfaces (`--list-runs`, `--on`, `--since`, `frame-open`, `do`,
   `judge`, `improvement --proposal`/`--covered`). Also check the
   SKILL.md against the design doc's Move 3 semantics after the repair
   reword: the seam-judge close rule, the unjudged single-child rule,
   and every Never: item must still carry the design's meaning.
3. Law seam: `rules/improvement.md` §6 (as re-pointed) must not
   contradict §§4–5, the SKILL.md body, or `rules/visibility.md` §6's
   new events sentence; the design doc's covered-line fields
   (cluster_key, matcher, watermark) must be what the digest actually
   emits (`harvest.py`/`harvest_cluster.py`).
4. Vacuous-green check: confirm B1.1's tests still anchor real
   behavior at the tip (e.g. its list-runs test would fail if the
   event field names changed), and that the repair's reword did not
   detach any test anchor B1.3's validator pass relied on.
5. Weigh the reported deviations for blocker-vs-successor: the
   deliver-only path opening no frame (repair child's flag); the
   missing Return: paragraph the draft lacked (B1.3 added one);
   harvest.py at 537 lines and tickets_frame.py at 571 (warn-only).

Return findings as your pack's Lens directs: each finding with
severity (blocker / should-fix / successor), the exact files and
lines, and the evidence you read. Blockers are only defects that make
a shipped surface lie or a seam silently dead. Do not edit anything;
you are read-only.
