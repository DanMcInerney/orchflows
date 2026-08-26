"""What `tickets.py gate` emits: a gate stub carries its root's authority.

A gate is the last door a delivery passes before terminal, so a stub that
lost the root's isolation, exclusions or fixed inputs would grade the work
with less authority than the work itself was granted. These cases pin the
three halves of that: the authority is inherited byte-for-byte, only
gate-specific records are added beside it, and each stub inherits the root
generation until the completed graph is sealed.

The sink idiom (a temporary ``ORCHFLOWS_STATE_HOME``) is restated here
rather than imported, the same convention `tests/test_tickets_view.py`
states, so this module runs alone under `tools/run_tests.py`'s per-module
child.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scripts.tickets as tickets_mod  # noqa: E402

STATE_HOME_ENV_VAR = "ORCHFLOWS_STATE_HOME"

# One record of each shape a root actually carries: a git-tree identity, a
# plain literal, and a literal whose value holds the commas and quotes that
# a re-serializing copy would be most likely to move.
ROOT_INPUTS = [
    '- input: {"identity":{"kind":"git-tree","repo":"run-project","revision":"%s"},"name":"baseline","type":"identity"}' % ("a" * 40),
    '- input: {"name":"target-repository","type":"literal","value":"C:/host/checkout"}',
    '- input: {"name":"acceptance-as-runnable-checks","type":"literal","value":["python tools/validate.py","git diff --check"]}',
    '- input: {"identity":{"kind":"artifact","locator":"sink:improvement/proposals/p","sha256":"%s"},"name":"proposal","type":"identity"}' % ("b" * 64),
]

# Prose entries, one of them carrying a comma and a semicolon: the block
# form is the only shape that reads back as one entry, so an inherited copy
# that re-rendered these inline would silently split them.
ROOT_EXCLUSIONS = [
    "vcs.push",
    "vcs.open-pr",
    "vcs.integrate",
    "Rewriting claimed or terminal ticket history, dated research documents, or run state outside this run.",
    "Editing a proposal file in the user-scope sink; covered lines are the join's act after the delivery lands.",
]

ROOT_TICKET = """---
id: R
run: testrun
status: claimed
admission: pending
root_generation: root:R:1:sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
executor: orch-decompose
pack: orch-code-pack
independence: gate
depends_on: []
write_scope: [scripts/, tests/]
mutations: [write:scripts/, write:tests/]
{authority}bound: 4h
claimed_by: planner-a
claimed_at: 2026-08-24T21:44:45Z
---

## Objective

The whole delivery lands under one root.

## Fixed inputs

{inputs}

## Completion test

- the suite exits 0 | oracle: `python tools/run_tests.py` | oracle_class: deterministic | provenance: pre-existing

## Return fields

status; result; verification; feedback; risks

## Result

## Verification

## Feedback

## Risks
"""

UNIT_TICKET = """---
id: {tid}
run: testrun
status: complete
admission: pending
root_generation: root:R:1:sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
executor: orch-tdd
pack: orch-code-pack
independence: checker
depends_on: [R]
write_scope: [scripts/one.py]
mutations: [change:scripts/one.py]
excluded_actions: [vcs.push]
isolation: required
bound: 30m
claimed_by: agent-a
claimed_at: 2026-08-24T22:00:00Z
---

## Objective

Unit {tid} lands.

## Fixed inputs

- input: {{"name":"none","type":"literal","value":null}}

## Completion test

- the suite exits 0 | oracle: `python -m unittest` | oracle_class: deterministic | provenance: pre-existing

## Return fields

status; result

## Result

changed scripts/one.py

## Verification

PASS: the suite exits 0

## Feedback

[]

## Risks

[]
"""


def use_sink(tmp: Path) -> Path:
    """Point ``ORCHFLOWS_STATE_HOME`` at a sink under this test's tempdir."""

    sink = (tmp / "state-sink").resolve()
    os.environ[STATE_HOME_ENV_VAR] = str(sink)
    return sink


def run_cmd(*args):
    """One dispatch in this process, as the payload a reader of stdout gets."""

    payload = tickets_mod._dispatch([str(arg) for arg in args])
    return json.loads(json.dumps(payload, ensure_ascii=False))


def root_text(*, inputs=None, exclusions=None, isolation="required") -> str:
    """One root ticket, with the authority a caller wants it to hold."""

    lines = []
    entries = ROOT_EXCLUSIONS if exclusions is None else exclusions
    if entries:
        lines.append("excluded_actions:")
        lines.extend(f"- {entry}" for entry in entries)
    if isolation:
        lines.append(f"isolation: {isolation}")
    authority = "".join(f"{line}\n" for line in lines)
    records = ROOT_INPUTS if inputs is None else inputs
    return ROOT_TICKET.format(authority=authority, inputs="\n".join(records))


def make_run(sink: Path, root: str, units=("R.01", "R.02")) -> Path:
    run_dir = sink / "tickets" / "testrun"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "R.md").write_text(root, encoding="utf-8")
    for unit in units:
        (run_dir / f"{unit}.md").write_text(
            UNIT_TICKET.format(tid=unit), encoding="utf-8"
        )
    return run_dir


def gate(*extra):
    """A multi-lens gate: the full three-kind family under grade.

    Two lenses on purpose: a single lens collapses the family to the
    critique-repair chain (no separate repair stub), and these cases pin
    the repair stub's inheritance alongside its siblings'. The chained
    shape has its own pins in `tests/test_tickets_gate_chain.py`.
    """

    return run_cmd("gate", "testrun", "R", "--lens", "code,style", *extra)


def sections_of(text: str) -> dict:
    return tickets_mod._sections(text)


def input_lines(text: str) -> list:
    body = sections_of(text).get("Fixed inputs", "")
    return [line for line in body.splitlines() if line.startswith("- input: ")]


def record_names(text: str) -> list:
    return [
        json.loads(line[len("- input: "):])["name"] for line in input_lines(text)
    ]


class GateInheritsRootAuthorityTest(unittest.TestCase):
    """The three stubs carry what the root was granted, unchanged."""

    def stubs(self, run_dir: Path, payload) -> dict:
        self.assertNotIn("error", payload)
        return {
            Path(path).stem: Path(path).read_text(encoding="utf-8")
            for path in payload["gate"]["paths"]
        }

    def test_every_stub_carries_the_roots_isolation(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = make_run(use_sink(Path(tmp)), root_text())
            for stub_id, text in self.stubs(run_dir, gate()).items():
                with self.subTest(stub=stub_id):
                    self.assertEqual(
                        "required",
                        tickets_mod._parse_frontmatter(text).get("isolation"),
                    )

    def test_every_stub_carries_the_roots_exclusions_entry_for_entry(self):
        """Byte-for-byte, and as entries rather than one re-split string.

        The last two entries carry a comma and a semicolon. Read back as a
        list they must still be two entries, not four: the inline
        frontmatter form splits on the comma, so an inherited copy that
        chose that shape would grant back part of what the root refused.
        """

        with tempfile.TemporaryDirectory() as tmp:
            run_dir = make_run(use_sink(Path(tmp)), root_text())
            for stub_id, text in self.stubs(run_dir, gate()).items():
                with self.subTest(stub=stub_id):
                    self.assertEqual(
                        ROOT_EXCLUSIONS,
                        tickets_mod._parse_frontmatter(text).get("excluded_actions"),
                    )

    def test_every_stub_carries_every_root_input_record_verbatim(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = make_run(use_sink(Path(tmp)), root_text())
            for stub_id, text in self.stubs(run_dir, gate()).items():
                with self.subTest(stub=stub_id):
                    carried = input_lines(text)
                    for record in ROOT_INPUTS:
                        self.assertIn(record, carried)

    def test_a_note_under_the_records_costs_the_root_no_record(self):
        """A root may end `## Fixed inputs` with prose, and 16 of this
        host's 90 root tickets do. Nothing refuses that shape: the ticket
        contract passes it and `gate` writes the whole family without
        complaint.

        `input_groups` appends every later non-blank line to the group the
        last `- ` opened, so the final record and that prose arrive as one
        two-line group. Skipping the group whole would drop a record the
        root plainly states -- and drop it silently, which is the half that
        matters for a gate: the stub would grade a delivery holding less
        authority than the root granted, and nothing would say so.
        """

        note = "  (a note the author left under the records)"
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = make_run(
                use_sink(Path(tmp)), root_text(inputs=ROOT_INPUTS + [note])
            )
            for stub_id, text in self.stubs(run_dir, gate()).items():
                with self.subTest(stub=stub_id):
                    carried = input_lines(text)
                    for record in ROOT_INPUTS:
                        self.assertIn(record, carried)

    def test_a_root_that_holds_no_authority_lends_the_stubs_none(self):
        """Inheritance copies; it never invents what the root never held."""

        with tempfile.TemporaryDirectory() as tmp:
            run_dir = make_run(
                use_sink(Path(tmp)), root_text(exclusions=[], isolation="")
            )
            for stub_id, text in self.stubs(run_dir, gate()).items():
                with self.subTest(stub=stub_id):
                    data = tickets_mod._parse_frontmatter(text)
                    self.assertIsNone(data.get("isolation"))
                    self.assertIn(data.get("excluded_actions"), (None, []))


class GateAddsOnlyItsOwnRecordsTest(unittest.TestCase):
    """Beside the inherited authority, each stub states the inputs its own
    job needs -- and nothing the root already named is stated twice."""

    def stub_text(self, run_dir: Path, payload, stub_id: str) -> str:
        self.assertNotIn("error", payload)
        return (run_dir / f"{stub_id}.md").read_text(encoding="utf-8")

    def test_the_critique_keeps_its_lens_and_unit_results(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = make_run(use_sink(Path(tmp)), root_text())
            names = record_names(
                self.stub_text(run_dir, gate(), "R.gate.critique.code")
            )
            self.assertIn("lens", names)
            self.assertIn("acceptance", names)
            self.assertIn("unit-result-r-01", names)
            self.assertIn("unit-result-r-02", names)

    def test_the_repair_and_verify_keep_the_records_they_are_decided_by(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = make_run(use_sink(Path(tmp)), root_text())
            payload = gate()
            self.assertIn(
                "critique-result-r-gate-critique-code",
                record_names(self.stub_text(run_dir, payload, "R.gate.repair")),
            )
            verify = record_names(self.stub_text(run_dir, payload, "R.gate.verify"))
            self.assertIn("repair-result", verify)
            self.assertIn("mutation-plan-paths", verify)

    def test_no_stub_states_one_input_name_twice(self):
        """The root here names `lens`, `acceptance` and `baseline` -- every
        name the generated stubs also reach for. `render_inputs` refuses a
        duplicate name outright, so an inheritance that copied blindly
        would not merely double a record: it would refuse the whole gate.
        """

        with tempfile.TemporaryDirectory() as tmp:
            make_run(use_sink(Path(tmp)), root_text(inputs=ROOT_INPUTS + [
                '- input: {"name":"lens","type":"literal","value":"the-roots-idea"}',
                '- input: {"name":"acceptance","type":"literal","value":"the-roots-idea"}',
            ]))
            payload = gate()
            self.assertNotIn("error", payload)
            for path in payload["gate"]["paths"]:
                names = record_names(Path(path).read_text(encoding="utf-8"))
                with self.subTest(stub=Path(path).stem):
                    self.assertEqual(sorted(set(names)), sorted(names))

    def test_the_gates_own_record_wins_a_name_the_root_also_used(self):
        """A root naming `lens` does not get to tell the critique what its
        lens is: the record that names the gate's own job is the gate's."""

        with tempfile.TemporaryDirectory() as tmp:
            run_dir = make_run(
                use_sink(Path(tmp)),
                root_text(inputs=ROOT_INPUTS + [
                    '- input: {"name":"lens","type":"literal","value":"the-roots-idea"}'
                ]),
            )
            text = self.stub_text(run_dir, gate(), "R.gate.critique.code")
            lenses = [
                json.loads(line[len("- input: "):])
                for line in input_lines(text)
                if json.loads(line[len("- input: "):])["name"] == "lens"
            ]
            self.assertEqual(1, len(lenses))
            self.assertEqual("code", lenses[0]["value"])

    def test_the_one_surviving_baseline_is_the_roots_own(self):
        """The root names a `baseline`, and the git-pack producer would
        insert one of its own from the live HEAD if none were there.

        Exactly one must survive, and it must be the root's: a gate decides
        a delivery at the revision the root was cut against, so a stub that
        quietly carried the HEAD of the moment would grade the same work at
        a different identity than the units did.
        """

        with tempfile.TemporaryDirectory() as tmp:
            make_run(use_sink(Path(tmp)), root_text())
            payload = gate()
            self.assertNotIn("error", payload)
            for path in payload["gate"]["paths"]:
                records = [
                    json.loads(line[len("- input: "):])
                    for line in input_lines(Path(path).read_text(encoding="utf-8"))
                ]
                baselines = [r for r in records if r["name"] == "baseline"]
                with self.subTest(stub=Path(path).stem):
                    self.assertEqual(1, len(baselines))
                    self.assertEqual(
                        "a" * 40, baselines[0]["identity"]["revision"]
                    )


class GateGradesWhatItIsAboutToWriteTest(unittest.TestCase):
    """The fifth emitting door grades its emission before it writes.

    `new`, `amend`, `recut`, `instantiate` and `stamp-generation` all run
    `tickets_emission.grade_run_emission` and refuse rather than emit. The
    gate checked contract shape and id collisions and then wrote, so it
    could spend the run's time issuing three stubs the very next door
    refuses -- which is the defect this run is named for.

    The instance: a root with no pack still carries a `git-tree` fixed
    input, and the gate copies that input into all three stubs verbatim.
    With no pack no adapter resolves the `git-tree` kind, so every stub is
    born carrying a refusable `adapter-kind-unsupported`. Contract shape is
    clean and no id collides, so nothing the door already checked sees it.

    The assertion is the refusal, not the call. A case that only proved
    `grade_run_emission` was reached would pass against a grade whose
    verdict the door discarded, and a version-only check is exactly what
    let this defect stand while a gate case sat green beside it.
    """

    def _run(self, root):
        with tempfile.TemporaryDirectory() as tmp:
            sink = use_sink(Path(tmp))
            run_dir = make_run(sink, root)
            return gate(), sorted(path.name for path in run_dir.glob("R.gate.*.md"))

    def test_the_gate_refuses_an_emission_the_next_door_refuses(self):
        payload, written = self._run(root_text().replace("pack: orch-code-pack\n", ""))

        self.assertIn("gate refuses to emit", str(payload.get("error")))
        self.assertEqual(
            {"adapter-kind-unsupported"},
            {finding.get("code") for finding in payload.get("findings") or []})
        self.assertEqual(
            ["R.gate.critique.code", "R.gate.critique.style",
             "R.gate.repair", "R.gate.verify"],
            sorted({finding.get("ticket") for finding in payload["findings"]}),
            "the refusal names every stub it would have written")
        self.assertEqual([], written, "a refused gate writes no stub")

    def test_a_root_whose_stubs_grade_clean_still_gates(self):
        """The refusal is the grade's, not a blanket one: the same door on
        the same fixture emits the whole family when the emission is clean."""

        payload, written = self._run(root_text())

        self.assertNotIn("error", payload)
        self.assertEqual(
            ["R.gate.critique.code.md", "R.gate.critique.style.md",
             "R.gate.repair.md", "R.gate.verify.md"],
            written)

if __name__ == "__main__":
    unittest.main()
