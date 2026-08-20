"""The ticket script's issue path: the two shape functions, `new`, and
`instantiate`.

`tests/test_tickets.py` covers the query and write path this module's
subject sits beside; the sink idiom (a temporary `ORCHFLOWS_STATE_HOME`)
is the same one, restated here rather than imported so this module runs
alone under `tools/run_tests.py`'s per-module child.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scripts.tickets as tickets_mod  # noqa: E402

TICKETS_PY = ROOT / "scripts" / "tickets.py"
STATE_HOME_ENV_VAR = "ORCHFLOWS_STATE_HOME"

# One criterion in the shape `new --criterion` writes and `packet` grades.
GOOD_CRITERION = "the suite exits 0 | oracle: `python -m unittest` | oracle_class: deterministic"

GOOD_TICKET = """---
id: T1
run: testrun
status: ready
executor: orch-tdd
pack: orch-code-pack
depends_on: []
write_scope: [scratch/t1.txt]
mutations: [change:scratch/t1.txt]
isolation: required
bound: 30m
claimed_by:
claimed_at:
---

## Objective

Add `double(n)`.

## Fixed inputs

None.

## Completion test

- {criterion}

## Return fields

status; result; verification.

## Result

## Verification

## Feedback

[]

## Risks

[]
""".format(criterion=GOOD_CRITERION)

# A stub is the same ticket missing only `run`, `status` and `claimed_*`.
GOOD_STUB = "\n".join(
    line
    for line in GOOD_TICKET.splitlines()
    if not line.startswith(("run:", "status:", "claimed_by:", "claimed_at:"))
) + "\n"


def use_sink(tmp: Path) -> Path:
    """Point ``ORCHFLOWS_STATE_HOME`` at a sink under this test's tempdir.

    Resolved before it is published, and set for the process rather than
    restored: ``tests/__init__.py`` holds the floor at a temporary
    directory regardless, so the worst a stale value can do is fail a
    test. A subprocess launched afterwards inherits it.
    """

    sink = (tmp / "state-sink").resolve()
    os.environ[STATE_HOME_ENV_VAR] = str(sink)
    return sink


def run_cmd(*args):
    """One dispatch in this process, as the payload a reader of stdout gets."""

    payload = tickets_mod._dispatch([str(arg) for arg in args])
    return json.loads(json.dumps(payload, ensure_ascii=False))


def run_full(cwd: Path, *args):
    """A real process: argv, exit code, and one JSON document on stdout."""

    return subprocess.run(
        [sys.executable, str(TICKETS_PY), *[str(a) for a in args]],
        capture_output=True, text=True, encoding="utf-8",
        errors="replace", cwd=str(cwd),
    )


def criterion(text: str) -> list:
    return tickets_mod.criterion_defects(text)


# A ticket whose instruction is padded to an exact word count. Every part
# the counter reads is a slot here, so this module can spend the budget with
# `str.split` -- its own arithmetic, not the owner's -- and the two have to
# agree on the number the refusal states.
CEILING_EXCLUDED = ("adding a third-party dependency", "editing a T0 contract")
CEILING_RETURNS = "status; result; verification."
CEILING_TICKET = """---
id: {ticket_id}
run: testrun
status: ready
executor: {executor}
depends_on: []
write_scope: [scratch/t1.txt]
excluded_actions:
  - {excluded_one}
  - {excluded_two}
bound: 30m
claimed_by:
claimed_at:
---

## Objective

{objective}

## Fixed inputs

{inputs}

## Completion test

- {criterion}

## Return fields

{returns}

## Result

## Verification

## Feedback

[]

## Risks

[]
"""


def ceiling_ticket(total, inputs="None.", executor="orch-tdd", ticket_id="T1"):
    """One ticket whose instruction is exactly ``total`` words.

    The objective takes whatever the excluded actions, the criterion and the
    return fields have not already spent; `## Fixed inputs` is free of the
    count by law, so a caller pads it to prove exactly that.
    """

    spent = sum(
        len(part.split())
        for part in (*CEILING_EXCLUDED, "- " + GOOD_CRITERION, CEILING_RETURNS)
    )
    return CEILING_TICKET.format(
        ticket_id=ticket_id,
        executor=executor,
        excluded_one=CEILING_EXCLUDED[0],
        excluded_two=CEILING_EXCLUDED[1],
        objective=" ".join(["word"] * (total - spent)),
        inputs=inputs,
        criterion=GOOD_CRITERION,
        returns=CEILING_RETURNS,
    )


def place(sink: Path, run: str, ticket_id: str, text: str) -> Path:
    """Put one ticket in the sink at the path every workspace agrees on."""

    run_dir = sink / "tickets" / run
    run_dir.mkdir(parents=True, exist_ok=True)
    path = run_dir / f"{ticket_id}.md"
    path.write_text(text, encoding="utf-8")
    return path

TEMPLATE_MD = """---
name: demo
description: Three stubs, one placeholder and one edgeless, for these tests.
entry: named
placeholders: [target]
---

What the template is for, in prose no instantiation reads.
"""

STUB = """---
id: {tid}
executor: {executor}
depends_on: {deps}
write_scope: [{scope}]
bound: 30m
---

## Objective

{objective}

## Fixed inputs

None.

## Completion test

- {criterion}

## Return fields

status; result.

## Result

## Verification

## Feedback

[]

## Risks

[]
"""


def stub(tid: str, deps: str = "[]", *, executor: str = "orch-tdd",
         scope: str = "scratch/x.txt", criterion: str = GOOD_CRITERION,
         objective: str = "one stub's end state") -> str:
    text = STUB.format(
        tid=tid, executor=executor, deps=deps, scope=scope,
        criterion=criterion, objective=objective,
    )
    if executor == "orch-tdd":
        text = text.replace(
            "executor: orch-tdd",
            f"executor: orch-tdd\npack: orch-code-pack\nisolation: required\nmutations: [change:{scope}]",
        )
    return text


def make_template(root: Path, stubs: dict, template_md: str = TEMPLATE_MD) -> Path:
    """A template directory: `template.md` plus one file per stub."""

    directory = root / "compositions" / "demo"
    directory.mkdir(parents=True, exist_ok=True)
    if template_md is not None:
        (directory / "template.md").write_text(template_md, encoding="utf-8")
    for tid, text in stubs.items():
        (directory / f"{tid}.md").write_text(text, encoding="utf-8")
    return directory


def three_stubs() -> dict:
    """A → B → C, with A → C as well: one edgeless stub, one terminal, and
    one placeholder to fill."""

    return {
        "A": stub("A", scope="{{target}}"),
        "B": stub("B", "[A]"),
        "C": stub("C", "[A, B]"),
    }
