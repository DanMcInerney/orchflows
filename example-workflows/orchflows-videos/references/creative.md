# Direction Git handoff

Direction fixes an original Markdown script/storyboard in the video's Git
repository before rendering. Its isolated maker and independent judge stamp
orchflows-marketing-videos, expanding exactly orch-code, short-videos,
orchflows-marketing-videos in the public owner's scope. Production consumes the
accepted commit, not a mutable path or an unreviewed repair.

Goal carries the complete brief; Context preserves research identities, dated
observations/gaps, renderer pins, voice/citation requirements, permissions,
authoring-owner pointer and bound. The direction contains the timed beat plan,
claim/source and asset/rights ledgers, research-to-choice rationale and unresolved
production questions. Its acceptance says nothing about future playback or hearing.

Before closing, inspect the actual independent review ticket: it must review the
exact direction commit with the maker's ordered pins and no blocking findings.
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

Retain absent/corrupt and actual readings. It checks committed bytes and review
binding; changed direction or pins require a fresh independent review. Pass the
accepted Git identity, actual findings/review identity, shared pins, snapshot,
permissions, assumptions and gaps to production; preserve latest partial commits
when acceptance is unavailable.
