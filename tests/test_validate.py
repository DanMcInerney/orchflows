"""Where a record lives, asserted against the files that state it.

Separate from ``tests/test_contracts.py``, which freezes the T0 contracts'
shape and the description budget every skill respects: nothing moved out of
that module. This one holds only the sink invariants — the path each
contract states, the work-item Location invariant's four conjuncts, and
``run.json``'s field list — so a location supersession is provably a
location change and not a shape change.
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTRACTS = ROOT / "contracts"

# The one path each contract states for the record it owns. The resolver's
# rule and the environment variable's semantics stay with their owner,
# `scripts/state_root.py`; a contract states a sub-path under it and links.
SINK_PATHS = {
    "work-item.md": "`<state-root>/tickets/<run>/<id>.md`",
    "worklog.md": "`<state-root>/runs/<run>/worklog.md`",
    "composition.md": "`<state-root>/runs/<run>/composition.md`",
}

# The `.orch` references allowed to survive anywhere in `contracts/`.
# Enumerated, not counted: after the supersession no contract composes a
# run-state path from the repository, so the allow-list is empty.
ALLOWED_ORCH_REFERENCES = ()

# The work-item Location invariant, conjunct by conjunct. The fourth is what
# the supersession buys: before it, the invariant held only while the
# repository existed, because the path was inside it.
LOCATION_CONJUNCTS = (
    "identical from the orchestrator",
    "from every executor workspace",
    "after any workspace is removed",
    "after the repository is removed",
)

# Every field `run.json` carries, from the writer's own recorded shape
# (`scripts/tickets.py`, item 03's `run_json_shape`). The contract may name
# these and no others, so contract and writer cannot drift in either
# direction.
RUN_JSON_FIELDS = frozenset({
    "run",
    "sink_convention",
    "opened_at",
    "project",
    "project.root",
    "project.origin",
    "project.name",
    "workspaces",
    "workspaces[].path",
    "workspaces[].first_seen",
})

RUN_JSON_MARKER = "`<state-root>/runs/<run>/run.json`"

# Each contract's declared shape at this run's baseline `ef336e0`, read with
# `git show ef336e0:contracts/<name>`: the headings it declares, and every
# backticked token on the first line of each top-level bullet — field names
# and the enums they range over. A location supersession changes none of it.
BASELINE_HEADINGS = {
    "work-item.md": ("# Work-item contract (ticket)",),
    "worklog.md": ("# Worklog contract",),
    "composition.md": ("# Composition contract",),
}
BASELINE_FIELDS = {
    "work-item.md": (
        "id", "run", "status", "pending", "ready", "claimed", "suspended",
        "complete", "executor", "pack", "independence", "gate", "checker",
        "checked_by", "depends_on", "write_scope", "authority",
        "excluded_actions", "authority", "isolation", "authority",
        "required", "none", "bound", "bounds", "claimed_by", "claimed_at",
        "workspace_branch", "workspace_baseline", "profile", "profile",
        "## Objective", "objective", "## Fixed inputs", "inputs",
        "## Completion test", "## Return fields", "return_contract",
        "## Result", "## Verification", "## Feedback", "[]", "## Risks",
        "[]", "## Handoff",
    ),
    "worklog.md": (
        "goal", "spec", "tickets", "iterations", "blame_classes",
        "failed_approaches", "queued_scope", "terminal", "complete",
    ),
    "composition.md": (
        "name", "description", "entry", "routed", "named", "scheduled",
        "steps", "id", "unit", "pack", "edges", "seq", "invariants",
        "Never:", "done_check", "Require:", "Return:", "Return:",
    ),
}

# The only shape this supersession adds: `run.json`'s five top-level field
# names, appended to the worklog contract's own list. Enumerated so the
# addition is pinned rather than merely tolerated.
ADDED_FIELDS = {
    "worklog.md": ("run", "sink_convention", "opened_at", "project", "workspaces"),
}

HEADING = re.compile(r"^#{1,6} .*$", re.M)
BULLET = re.compile(r"^- (.*)$", re.M)
TOKEN = re.compile(r"`([^`]+)`")


def read(name):
    return (CONTRACTS / name).read_text(encoding="utf-8")


def flat(text):
    """Text with whitespace collapsed, so a wrapped clause matches as one."""

    return re.sub(r"\s+", " ", text)


def paragraph(name, needle):
    """The blank-line-delimited paragraph of ``name`` that carries ``needle``.

    Anchored to text rather than to a line number, so rewrapping a contract
    never silently moves what a case is reading.
    """

    for block in read(name).split("\n\n"):
        if needle in block:
            return flat(block).strip()
    return ""


def declared_shape(name):
    """A contract's headings and the field names its bullets declare."""

    text = read(name)
    tokens = []
    for line in BULLET.findall(text):
        tokens.extend(TOKEN.findall(line))
    return tuple(HEADING.findall(text)), tuple(tokens)


class TestWorkItemLocationInvariant(unittest.TestCase):
    """Spec A13: the invariant is strengthened, not weakened."""

    def setUp(self):
        self.clause = paragraph("work-item.md", "Location:")
        self.assertTrue(self.clause, "work-item.md carries no Location paragraph")

    def test_the_clause_carries_all_four_conjuncts(self):
        for conjunct in LOCATION_CONJUNCTS:
            self.assertIn(
                conjunct, self.clause,
                "the work-item Location invariant does not state {0!r}".format(conjunct),
            )

    def test_the_clause_states_exactly_one_path(self):
        paths = [t for t in TOKEN.findall(self.clause) if t.endswith(".md")]
        self.assertEqual(
            [SINK_PATHS["work-item.md"].strip("`")], paths,
            "the Location clause must state exactly one ticket path",
        )

    def test_the_one_path_survives_the_repository_it_was_cut_in(self):
        """The fourth conjunct holds only of a root outside every clone.

        So the clause has to say that, and has to name the owner that
        resolves it rather than restating the rule.
        """

        self.assertIn("outside every repository", self.clause)
        self.assertIn("`scripts/state_root.py`", self.clause)


class TestContractsNameTheSink(unittest.TestCase):
    """Spec A12's text half: all three contracts state a sink path."""

    def test_each_contract_states_its_sink_path(self):
        for name, path in SINK_PATHS.items():
            with self.subTest(contract=name):
                self.assertIn(
                    path, read(name),
                    "{0} does not state its record's path under the state root".format(name),
                )

    def test_no_contract_composes_a_run_state_path_from_the_repository(self):
        found = []
        for path in sorted(CONTRACTS.glob("*.md")):
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if ".orch" in line:
                    found.append("{0}:{1}: {2}".format(path.name, number, line.strip()))
        self.assertEqual(list(ALLOWED_ORCH_REFERENCES), found)


class TestWorklogStatesRunIdentity(unittest.TestCase):
    """Spec A5's contract half: `run.json`'s fields, stated where the run's
    other durable file is stated."""

    def block(self):
        text = read("worklog.md")
        self.assertIn(RUN_JSON_MARKER, text, "worklog.md does not state run.json's path")
        return text.split(RUN_JSON_MARKER, 1)[1]

    def test_the_contract_names_every_field_run_json_carries(self):
        self.assertEqual(set(), RUN_JSON_FIELDS - set(TOKEN.findall(self.block())))

    def test_the_contract_names_no_field_run_json_does_not_carry(self):
        self.assertEqual(set(), set(TOKEN.findall(self.block())) - RUN_JSON_FIELDS)


class TestContractShapeUnchanged(unittest.TestCase):
    """Spec A12's other half: a location supersession, never a shape one.

    A shape change is breaking and lands only through its own supersession
    PR (AGENTS.md), so the shape is pinned here as literals read from the
    baseline revision rather than re-derived from whatever is on disk.
    """

    def test_no_contract_declares_a_heading_it_did_not_declare_at_baseline(self):
        for name, headings in BASELINE_HEADINGS.items():
            with self.subTest(contract=name):
                self.assertEqual(headings, declared_shape(name)[0])

    def test_no_contract_gains_or_loses_a_field_beyond_the_enumerated_addition(self):
        for name, fields in BASELINE_FIELDS.items():
            with self.subTest(contract=name):
                self.assertEqual(fields + ADDED_FIELDS.get(name, ()), declared_shape(name)[1])


if __name__ == "__main__":
    unittest.main()
