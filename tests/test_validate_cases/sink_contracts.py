"""Where a record lives, asserted against the files that state it.

Separate from ``tests/test_contracts.py``, which freezes the T0 contracts'
shape and the description budget every skill respects: nothing moved out of
that module. This one holds only the sink invariants — the path each
contract states, the work-item Location invariant's one path and the
resolver it names, and ``run.json``'s field list at its writer. Its second half holds the prose
invariants: the root the amended sink law points at, the one prose owner of
that path, and which ``.orch`` mentions may survive.

Its third half is ``tools/validate.py``'s two remaining owned-literal
checks and the cross-tier duplication check that replaced ``validate_sync``
(REVIEW-2026-08-15 T2). ``tests/test_sync.py`` held
them until the sync check it was named for was deleted; what survived it —
``scripts/tickets.py``'s ``PACK_WORKSPACE_MECHANISMS`` against the packs'
own cells, and the friction log's one location against every copy of it —
lives here now, because a copy checked against its owner is the same
subject as a copy the compiler refuses outright.
"""
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
CONTRACTS = ROOT / "contracts"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scripts.tickets as tickets_mod  # noqa: E402

VALIDATE = ROOT / "tools" / "validate.py"
PACKS = ROOT / "packs"
TEMPLATES = ROOT / "templates"
TICKETS_PY = ROOT / "scripts" / "tickets.py"

# The one path each contract states for the record it owns. The resolver's
# rule and the environment variable's semantics stay with their owner,
# `scripts/state_root.py`; a contract states a sub-path under it and links.
SINK_PATHS = {
    "work-item.md": "`<state-root>/tickets/<run>/<id>.md`",
    "worklog.md": "`<state-root>/runs/<run>/worklog.md`",
}

# The `.orch` references allowed to survive anywhere in `contracts/`.
# Enumerated, not counted: after the supersession no contract composes a
# run-state path from the repository, so the allow-list is empty.
ALLOWED_ORCH_REFERENCES = ()

# Every field `run.json` carries, from the writer's own recorded shape
# (`scripts/tickets.py`). Its docstring may name these and no others, so
# statement and writer cannot drift in either direction.
RUN_JSON_FIELDS = frozenset({
    "run",
    "sink_convention",
    "opened_at",
    "orchflows",
    "orchflows.receipt_version",
    "orchflows.source_commit",
    "terminal_at",
    "terminal_ticket_id",
    "terminal_status",
    "elapsed_ms",
    "project",
    "project.root",
    "project.origin",
    "project.name",
    "workspaces",
    "workspaces[].path",
    "workspaces[].first_seen",
})

RUN_JSON_MARKER = "``<sink>/runs/<run>/run.json``"

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

    def test_the_clause_states_exactly_one_path(self):
        paths = [t for t in TOKEN.findall(self.clause) if t.endswith(".md")]
        self.assertEqual(
            [SINK_PATHS["work-item.md"].strip("`")], paths,
            "the Location clause must state exactly one ticket path",
        )

    def test_the_clause_names_the_resolver_rather_than_restating_the_root(self):
        """Where the root sits is `rules/visibility.md` §6's fact and no
        contract's -- `TestOneProseOwnerForThePath` is what holds that to
        one owner. This contract's own fact is the sub-path above and the
        resolver it hangs off, and both are backticked identifiers, so the
        paragraph around them stays the contract's to reword.

        The clause's vantage list -- the same path from the orchestrator,
        from every executor workspace, after either is removed -- is that
        one fact in prose. It is proved where it is enforced instead, in
        tests/test_state_root.py: all three writers resolve to the one
        sink, two workspaces of one project write one sink, and outside
        any repository the sink still resolves.
        """

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
    """`run.json`'s fields, stated by its one writer: the field list lives in
    scripts/tickets.py's module docstring, and the
    docstring may name these fields and no others, so writer and statement
    cannot drift in either direction."""

    def block(self):
        text = (ROOT / "scripts" / "tickets.py").read_text(encoding="utf-8")
        docstring = text.split('"""', 2)[1]
        self.assertIn(RUN_JSON_MARKER, docstring, "tickets.py's docstring does not state run.json's path")
        return docstring.split(RUN_JSON_MARKER, 1)[1].replace("``", "`")

    def test_the_contract_names_every_field_run_json_carries(self):
        self.assertEqual(set(), RUN_JSON_FIELDS - set(TOKEN.findall(self.block())))

    def test_the_contract_names_no_field_run_json_does_not_carry(self):
        self.assertEqual(set(), set(TOKEN.findall(self.block())) - RUN_JSON_FIELDS)

    def test_installed_revision_and_terminal_timing_have_single_owners(self):
        declared = TOKEN.findall(self.block())
        for field in (
            "orchflows.receipt_version",
            "orchflows.source_commit",
            "terminal_at",
            "terminal_ticket_id",
            "terminal_status",
            "elapsed_ms",
        ):
            with self.subTest(field=field):
                self.assertEqual(1, declared.count(field), field)

        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(
            tickets_mod.state_root, "state_root", return_value=Path(tmp) / "state"
        ):
            self.assertEqual(
                {"receipt_version": None, "source_commit": None},
                tickets_mod._installed_orchflows_metadata(),
            )
        source = TICKETS_PY.read_text(encoding="utf-8")
        self.assertEqual(1, source.count("def _installed_orchflows_metadata"))
        self.assertEqual(1, source.count("def _terminal_identity_update"))
