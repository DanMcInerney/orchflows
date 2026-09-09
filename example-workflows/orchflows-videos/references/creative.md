# Direction Git handoff

Direction fixes an original Markdown script, static illustrated panels/contact
sheet and editable layout source in the video's Git repository before final-video
rendering. Its isolated maker and independent judge stamp
orchflows-marketing-videos, expanding exactly orch-code, short-videos,
orchflows-marketing-videos in the public owner's scope. Production consumes the
accepted commit, not a mutable path or an unreviewed repair.

Goal carries the complete brief; Context preserves research identities, dated
observations/gaps, renderer pins, voice/citation requirements, permissions,
authoring-owner pointer and bound. The direction contains the timed beat plan,
claim/source and asset/rights ledgers, research-to-choice rationale and unresolved
production questions. List repository-relative paths for the illustrated assets,
editable source and restoration/render instructions in the direction document.
Commit them with the plan so the reviewed Git identity fixes the complete handoff;
uncommitted illustrations or missing source leave direction incomplete. Build
panels from reusable layout components compatible with the pinned renderer, so
production animates the reviewed type, cards and connectors instead of redrawing
them. The brief determines hooks, examples, scene count and duration.
Its acceptance says nothing about future playback or hearing.

Before closing, inspect the actual independent review ticket: it must review the
exact direction commit with the maker's ordered pins and no blocking findings.
Confirm the judge inspected the listed panels/contact sheet at target display
size and checked the editable source, brief and canonical subject relationships.
Record inspected paths, scale and coverage in that review. Missing illustrated
assets/source or unavailable visual inspection cannot yield accepted direction.
Freeze a JSON snapshot with artifact (git:<full commit>), standards (ordered
objects with name and digest), blockers (empty for accepted direction), and
review_identity (the actual review ticket/findings locator). Record its SHA256.
This is a local integrity carrier, not a substitute for independent judgment.
The snapshot must faithfully preserve that review; absent or unresolved review
means no accepted direction.

Run the package's [direction verifier](../scripts/verify_direction.py) outside
children with the fixed commit, repository-relative Markdown path, committed blob
SHA256, review snapshot/hash and the three exact maker standard digests:

    <resolved-interpreter> <package>/scripts/verify_direction.py --project <workspace> --commit <full-commit> --path <direction.md> --sha256 <blob-sha256> --review <snapshot.json> --review-sha256 <snapshot-sha256> --digests <orch-code-digest> <short-videos-digest> <marketing-digest>

The probe binds the document bytes and review snapshot to the commit; it does not
inspect linked assets, readability, approval or the truth of review claims.
The semantic checks above remain required before freezing the snapshot.

Retain absent/corrupt and actual readings. It checks committed bytes and review
binding; changed direction or pins require a fresh independent review. Pass the
accepted Git identity, actual findings/review identity, shared pins, snapshot,
permissions, assumptions and gaps to production; preserve latest partial commits
when acceptance is unavailable.
