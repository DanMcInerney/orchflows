"""The document lane: an adapter that establishes no candidate still dispatches.

``document-tree`` gives no item a tree of its own -- its
``establishes_isolation`` is False, so the item's derived isolation is
``none`` -- and the establishment used to judge the adapter's strategy before
it read that. Every content-pack ticket therefore refused at the dispatch
trunk with ``adapter-not-establishable``, which is the refusal a live run hit
and which nothing here had ever driven. What the lane records instead is the
tree its caller stands in, carrying no branch and no baseline, and the return
side skips integration and retirement as ``not isolated``.
"""

from datetime import datetime, timedelta, timezone
from unittest import mock

from .common import *  # noqa: F401,F403

from tests import _retired_commands as retired_commands
from scripts import workspace_candidate  # noqa: F401
from scripts.tickets_format import parse_canonical_json

REFUSAL = (
    "adapter-not-establishable: document-tree does not establish a "
    "candidate workspace"
)
CONTENT_PACK = "orch-content-pack"


def document_fixture(tmp: Path, isolation=None):
    """A sealed content-pack work item, and the plain tree it is dispatched in.

    The tree is no checkout, deliberately: the whole claim of this lane is
    that a document workspace needs no Git, and a fixture that handed it one
    would prove nothing about the tickets that refused in the field.
    """

    sink = use_sink(tmp)
    run_dir = sink / "tickets" / "testrun"
    run_dir.mkdir(parents=True)
    prose = tmp / "prose"
    prose.mkdir()
    ticket = make_ticket(run_dir, "T1", pack=CONTENT_PACK, isolation=isolation)
    return ticket, prose


class TestTheDocumentLaneObservesTheTreeItStandsIn(unittest.TestCase):
    def test_it_records_the_callers_tree_and_claims_no_git_fact(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            ticket, prose = document_fixture(tmp)

            done = run_workspace(
                prose, "establish", "testrun", "T1", "--repo", str(prose)
            )

            self.assertEqual(0, done.returncode, done.stdout + done.stderr)
            self.assertEqual(
                {
                    "run": "testrun", "id": "T1", "ticket": str(ticket),
                    "mechanism": "document-tree", "isolated": False,
                    workspace.PATH_KEY: str(prose.resolve()),
                    "workspace_root": str(prose.resolve()),
                },
                payload_of(done)["establish"],
            )
            self.assertEqual(str(prose.resolve()), recorded_workspace(ticket))
            # a document revision is no commit: the two Git-only stamps are
            # what `check` and `cutcheck` grade a candidate branch by, and an
            # item that never had a branch may not carry either
            stamped = ticket.read_text(encoding="utf-8")
            self.assertNotIn(workspace.BRANCH_KEY, stamped)
            self.assertNotIn(workspace.BASELINE_KEY, stamped)

    def test_start_observes_the_same_tree_establish_does(self):
        """`start` and `establish` are one lane here -- neither creates a
        tree -- so the verb a caller reaches for may not change the answer."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            ticket, prose = document_fixture(tmp)

            done = run_workspace(prose, "start", "testrun", "T1")

            self.assertEqual(0, done.returncode, done.stdout + done.stderr)
            self.assertEqual(
                str(prose.resolve()), payload_of(done)["start"][workspace.PATH_KEY]
            )
            self.assertEqual(str(prose.resolve()), recorded_workspace(ticket))


class TestTheTrunkDispatchesAndLandsADocumentItem(unittest.TestCase):
    """The path the field repro took, end to end: `tickets.py dispatch` on a
    content-pack ticket, and then the return that has to answer for a tree
    nothing cut and nothing can retire."""

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.sink = use_sink(Path(self.temporary.name))
        self.tree = Path(self.temporary.name) / "prose"
        self.tree.mkdir()

    def tearDown(self):
        self.temporary.cleanup()

    def command(self, *arguments):
        result = retired_commands.run(list(arguments))
        self.assertNotIn("error", result, result)
        return result

    def ticket_path(self) -> Path:
        return self.sink / "tickets" / "run" / "T.md"

    def sealed(self) -> str:
        """This attempt's assignment seal, which `land` is identified by."""

        data = tickets._parse_frontmatter(
            self.ticket_path().read_text(encoding="utf-8")
        )
        state = parse_canonical_json(data["dispatch_v1"])
        return state["attempts"][0]["assignment_seal"]

    def test_a_content_pack_ticket_dispatches_and_lands_unisolated(self):
        self.command(
            "new", "run", "T", "--executor", "orch-do",
            "--goal", "Deliver the document.",
            "--context", "The brief is authoritative.",
            "--pack", CONTENT_PACK,
        )
        self.command("stamp-generation", "run", "T")
        validated = self.command("draft-validate", "run", "T")
        self.command(
            "seal", "run", "T",
            "--cut-generation", validated["draft_validation"]["cut_generation"],
        )
        self.command("ready", "--run", "run")
        lease = (
            datetime.now(timezone.utc) + timedelta(hours=1)
        ).isoformat().replace("+00:00", "Z")

        dispatched = self.command(
            "dispatch", "run", "T", "--by", "worker", "--dispatch-id", "D1",
            "--lease-expires-at", lease, "--workspace", str(self.tree),
        )

        # the launch names the tree the caller stands in, and it is the tree
        # the establishment itself recorded -- not the `--workspace` argument
        # relayed around it
        self.assertIn(str(self.tree.resolve()), dispatched["launch"]["prompt"])
        self.assertEqual(
            str(self.tree.resolve()), recorded_workspace(self.ticket_path())
        )
        seal = self.sealed()
        self.command("dispatch-outcome", "run", "T", "--note", "delivered")

        landed = self.command(
            "land", "run", "T", "--assignment-seal", seal, "--dispatch-id", "D1",
            "--outcome-record-id", "outcome", "--by", "root-join",
            "--status", "complete",
        )

        self.assertEqual("complete", landed["land"]["status"])
        self.assertEqual(
            [
                {"step": "workspace-integrate", "outcome": "skipped",
                 "reason": "not isolated"},
                {"step": "workspace-retire", "outcome": "skipped",
                 "reason": "not isolated"},
            ],
            [step for step in landed["land"]["steps"]
             if step["step"].startswith("workspace-")],
        )


class TestTheRefusalSurvivesForWhatCannotBeGiven(unittest.TestCase):
    """Two readings of the one refusal this fix narrowed rather than removed.

    The first is a real ticket asking a non-establishing adapter for a
    candidate outright. The second is the ordering the field repro came from,
    restored by making the isolation answer what the pre-fix establishment
    never asked it.
    """

    def test_an_explicit_required_override_is_still_refused_unstamped(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            ticket, prose = document_fixture(tmp, isolation="required")
            before = ticket.read_bytes()

            done = run_workspace(
                prose, "establish", "testrun", "T1", "--repo", str(prose)
            )

            self.assertEqual(1, done.returncode, done.stdout + done.stderr)
            self.assertEqual(
                {"code": 1, "error": REFUSAL, "verdict": "error"}, payload_of(done)
            )
            self.assertEqual(before, ticket.read_bytes())

    def test_an_unconsulted_isolation_reproduces_the_field_refusal(self):
        """The mutant. The pre-fix establishment never read the item's
        isolation before judging the adapter's strategy, which is the same
        answer as an isolation that always reads ``required``; restore that
        one reading and the refusal a live run hit comes straight back.

        Patched through the facade's own attribute, not through
        ``scripts.tickets_adapters``: the flat installed layout gives the
        facade its own copy of both modules, and that copy is the one the
        establishment under test actually calls.
        """

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            ticket, prose = document_fixture(tmp)
            noise = io.StringIO()

            with mock.patch.object(
                workspace.workspace_candidate.tickets_adapters,
                "derived_isolation",
                return_value=workspace_candidate.REQUIRED,
            ), redirect_stdout(noise), redirect_stderr(noise):
                code = workspace.main(
                    ["establish", "testrun", "T1", "--repo", str(prose)]
                )

            self.assertEqual(1, code, noise.getvalue())
            self.assertEqual(
                {"code": 1, "error": REFUSAL, "verdict": "error"},
                json.loads(noise.getvalue().splitlines()[0]),
            )
            self.assertIsNone(recorded_workspace(ticket))
