# Minimal live authoring request

This is invocation input, not a prebuilt workflow or proof of execution. Use
two disposable git repositories: `source` for authoring and `product` for the
produced workflow's output. Source begins with a committed baseline; product
is a fresh clone of its accepted commit. Resolve the
candidate builder from accepted source through the ordinary library doors.

Invoke orch-build-workflow with:

- `request`: Create the project-scoped public workflow `receipt-build`. It
  accepts a git workspace and per-call bound and calls checkpointed-build to
  produce only `receipt.txt` containing exactly the UTF-8 bytes
  `layered workflow admitted` followed by LF. Make and judge use orch-code
  with the recurring `receipt-quality` narrowing. Put that narrowing in the
  project ring's top-level standards directory so checkpointed-build can
  resolve it after the public call. Its quality bar is exact receipt content
  and no unrelated product edits. The produced workflow supplies the external
  probe below, its concrete goal,
  workspace, bound, both standards, and narrowing list to the public call.
- `workspace`: absolute `source` repository path.
- `scope`: project, under `<source>/.orchflows/`.
- `authoring-owner`: the resolved library's docs/custom-workflow-authoring.md.
- `bound`: 10m per call.
- `admission`: static command `orchflows check <source/.orchflows>`; disposable
  project `product`; runtime request “Use receipt-build to produce the exact
  receipt”; invocation inputs `workspace` = absolute product path and `bound`
  = 10m; external probe below.

Clone source at the fixed accepted commit into product, preserving its project
ring and top-level standard. Record that baseline and use ordinary first-use
trust for the authored bundle. Do not copy just the public body and lose the
narrowing. Invoke the actual receipt-build body and follow every emitted
launch and landing; fabricated outcomes cannot satisfy this exercise. The
receipt request changes only receipt.txt relative to the cloned baseline.

Save this probe outside the product repository and run it through the verified
Python interpreter, passing the absolute product path as its only argument.
The regression executes these exact bytes as Python; it does not infer that
the surrounding workflow prose ran.

```python
from pathlib import Path
import sys

receipt = Path(sys.argv[1]) / "receipt.txt"
try:
    valid = receipt.read_bytes() == b"layered workflow admitted\n"
except OSError:
    valid = False
print("receipt admitted" if valid else "receipt absent or corrupt")
raise SystemExit(0 if valid else 1)
```

Observe nonzero with no receipt before the runtime invocation;
observe zero on the live landed output. A corrupt-byte case is also covered
by the deterministic probe regression, not claimed as live workflow evidence.

Record the two workflow frame trees, issued tickets, broad-to-narrow standard
pins at making and judgment, their artifact and findings lines, static check
and external probe exits, and any unexercised branch. Root driving this
exercise owns live evidence; authoring the fixture alone supplies none.
