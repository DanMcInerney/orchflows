"""A run belongs to one project, and only that project writes to it.

The state sink is user-scope: every project on the host shares one
`tickets/` and one `runs/` tree.  Nothing mechanical used to assert which
project a run belongs to, so three separable failures were all reachable
through that one gap -- a packet-less fork scavenged the sink and nearly
claimed another project's ticket, a claim was attempted from the sibling
checkout of the project the run's baseline lives in, and a run was
silently attributed to whichever session happened to write to the sink
first while its tickets named a different repository.

Two laws close it, and they are separate laws rather than one applied
twice.  *Attribution*: a run belongs to the project recorded by the
workspace that issues it. Context is semantic evidence, never system
authority, so a ticket cannot redirect project binding through prose.
*Admission*: `claim` and terminal-status writes compare the writing
workspace's resolved project against the run's recorded one and refuse a
mismatch, so a context standing in the wrong checkout is stopped at the
boundary rather than discovered later by a baseline that will not
resolve.

Every case here drives a real subprocess from a real directory: the
project a write comes from is resolved from the process's own working
directory, and an in-process pin would grade the pin rather than the
resolution.
"""

import json
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

TICKETS_PY = ROOT / "scripts" / "tickets.py"
STATE_HOME_ENV_VAR = "ORCHFLOWS_STATE_HOME"
RUN = "testrun"
# The one phrase every binding refusal carries, whichever door refused.  A
# case that must tell "this law refused me" from "some other law did" reads
# for this and not for the presence of an error.
HELD = "is held by project"

ROOT_TICKET = """---
id: 00-root
run: {run}
status: {status}
executor: orch-decompose
depends_on: []
bound: 30m
---

## Goal

Bind this run to its issuing project.

## Context

{context}

## Result

## Verification

## Feedback

[]

## Risks

[]
"""

UNIT_TICKET = """---
id: {tid}
run: {run}
status: {status}
executor: orch-tdd
depends_on: []
bound: 30m
---

## Goal

A unit of the bound run.

## Context

[]

## Result

## Verification

## Feedback

[]

## Risks

[]
"""


class ProjectBindingFixture(unittest.TestCase):
    """Two repositories sharing one sink: the run's own, and a stranger's.

    `alpha` is what the root ticket names; `beta` is any other checkout on
    the host, which is the whole population the user-scope sink exposes a
    run to.
    """

    def setUp(self):
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        tmp = Path(self._tmp.name).resolve()
        self.sink = tmp / "state-sink"
        self.alpha = tmp / "alpha"
        self.beta = tmp / "beta"
        for repo in (self.alpha, self.beta):
            (repo / ".git").mkdir(parents=True)
        self.run_dir = self.sink / "tickets" / RUN
        self.run_dir.mkdir(parents=True)

    def env(self) -> dict:
        import os

        environment = dict(os.environ)
        environment[STATE_HOME_ENV_VAR] = str(self.sink)
        return environment

    def tickets(self, cwd: Path, *args):
        """One real process, from `cwd`, against this test's sink."""

        return subprocess.run(
            [sys.executable, str(TICKETS_PY), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(cwd),
            env=self.env(),
        )

    def payload(self, cwd: Path, *args) -> dict:
        completed = self.tickets(cwd, *args)
        return json.loads(completed.stdout or completed.stderr or "{}")

    def write_root(self, *, names: Path = None, status: str = "ready"):
        context = f"- reported workspace: {names}" if names is not None else "[]"
        (self.run_dir / "00-root.md").write_text(
            ROOT_TICKET.format(run=RUN, status=status, context=context),
            encoding="utf-8",
        )

    def write_unit(self, tid: str, *, status: str = "ready"):
        (self.run_dir / f"{tid}.md").write_text(
            UNIT_TICKET.format(tid=tid, run=RUN, status=status), encoding="utf-8"
        )

    def identity(self) -> dict:
        path = self.sink / "runs" / RUN / "run.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def open_run_from(self, cwd: Path):
        """Open the run's identity by writing one ordinary note from `cwd`."""

        return self.payload(cwd, "run-state", RUN, "--note", "opening")


class TestAttribution(ProjectBindingFixture):
    """A run is attributed to its issuing workspace, not semantic Context."""

    def test_run_creation_stamps_the_issuing_project(self):
        self.write_root(names=self.alpha)
        self.open_run_from(self.beta)
        recorded = self.identity()["project"]
        self.assertEqual(str(self.beta), recorded["root"])
        self.assertEqual("beta", recorded["name"])

    def test_the_writing_workspace_is_still_recorded_as_a_workspace(self):
        """Attribution moves; the workspace census does not.

        `workspaces[]` answers *where has this run been written from*,
        which stays the caller's own directory even when the project the
        run belongs to is the root ticket's.  Collapsing the two would
        lose the only record of a write's actual origin.
        """

        self.write_root(names=self.alpha)
        self.open_run_from(self.beta)
        seen = [entry["path"] for entry in self.identity()["workspaces"]]
        self.assertIn(str(self.beta), seen)

    def test_a_root_ticket_naming_no_workspace_leaves_the_writer_owning_it(self):
        """No named workspace is no authority, not a refusal.

        A cut that names no target repository has said nothing about which
        project it belongs to, and inventing one would be the same guess
        from the other direction.
        """

        self.write_root(names=None)
        self.open_run_from(self.beta)
        self.assertEqual(str(self.beta), self.identity()["project"]["root"])

    def test_semantic_context_does_not_reassign_a_recorded_project(self):
        """A Context workspace fact is not lifecycle authority."""

        self.open_run_from(self.beta)
        self.assertEqual(str(self.beta), self.identity()["project"]["root"])
        self.write_root(names=self.alpha)
        self.open_run_from(self.beta)
        self.assertEqual(str(self.beta), self.identity()["project"]["root"])


class TestClaimAdmission(ProjectBindingFixture):
    """A ticket is claimable only from a workspace of the run's project."""

    def setUp(self):
        super().setUp()
        self.write_root(names=self.alpha, status="claimed")
        self.write_unit("00-root.01")
        self.open_run_from(self.alpha)

    def test_a_claim_from_a_foreign_project_is_refused(self):
        completed = self.tickets(
            self.beta, "dispatch-open", RUN, "00-root.01", "--by", "stranger",
            "--dispatch-id", "foreign-D1", "--lease-expires-at", "2099-01-01T00:00:00Z",
        )
        payload = json.loads(completed.stdout or "{}")
        self.assertNotEqual(0, completed.returncode)
        self.assertIn("error", payload)
        self.assertIn(str(self.alpha), payload["error"])
        self.assertIn(str(self.beta), payload["error"])

    def test_a_refused_claim_writes_nothing(self):
        before = (self.run_dir / "00-root.01.md").read_text(encoding="utf-8")
        completed = self.tickets(
            self.beta, "dispatch-open", RUN, "00-root.01", "--by", "stranger",
            "--dispatch-id", "foreign-D1", "--lease-expires-at", "2099-01-01T00:00:00Z",
        )
        after = (self.run_dir / "00-root.01.md").read_text(encoding="utf-8")
        self.assertEqual(before, after)
        self.assertIn(HELD, json.loads(completed.stdout or "{}")["error"])

    def test_a_claim_from_the_runs_own_project_is_admitted_by_the_binding(self):
        """The binding is the only law this case grades.

        A ticket carrying no admission receipt is refused further down the
        claim path for reasons that predate this unit, so asserting a
        successful claim here would grade that older law instead.  What
        must hold is that the binding itself lets its own project past.
        """

        payload = self.payload(
            self.alpha, "dispatch-open", RUN, "00-root.01", "--by", "worker",
            "--dispatch-id", "own-D1", "--lease-expires-at", "2099-01-01T00:00:00Z",
        )
        self.assertNotIn(HELD, payload.get("error", ""))


class TestTerminalAdmission(ProjectBindingFixture):
    """A terminal status is recorded only from the run's own project."""

    def setUp(self):
        super().setUp()
        self.write_root(names=self.alpha, status="claimed")
        self.write_unit("00-root.01", status="claimed")
        self.open_run_from(self.alpha)

    def test_a_terminal_write_from_a_foreign_project_is_refused(self):
        completed = self.tickets(
            self.beta, "set-status", RUN, "00-root.01", "blocked"
        )
        payload = json.loads(completed.stdout or "{}")
        self.assertNotEqual(0, completed.returncode)
        self.assertIn(str(self.alpha), payload["error"])

    def test_a_terminal_write_from_the_runs_own_project_proceeds(self):
        payload = self.payload(self.alpha, "set-status", RUN, "00-root.01", "blocked")
        self.assertNotIn("error", payload)
        self.assertEqual("blocked", payload["set_status"]["status"])


class TestLegacyRuns(ProjectBindingFixture):
    """A run whose identity records no project binds nothing.

    The check is an assertion about a recorded fact.  Where the fact was
    never recorded there is nothing to compare, and refusing every write
    would strand runs that predate the identity document rather than
    protecting them.
    """

    def test_a_run_with_no_recorded_project_admits_any_workspace(self):
        self.write_root(names=self.alpha, status="claimed")
        self.write_unit("00-root.01")
        identity_dir = self.sink / "runs" / RUN
        identity_dir.mkdir(parents=True, exist_ok=True)
        (identity_dir / "run.json").write_text(
            json.dumps({"run": RUN, "sink_convention": 2}) + "\n", encoding="utf-8"
        )
        payload = self.payload(
            self.beta, "dispatch-open", RUN, "00-root.01", "--by", "worker",
            "--dispatch-id", "legacy-D1", "--lease-expires-at", "2099-01-01T00:00:00Z",
        )
        self.assertNotIn(HELD, payload.get("error", ""))


class TestTheSeamMoved(unittest.TestCase):
    """The claim-admission seam has one owner, and the facade is unchanged.

    The extraction is what made the growth lawful -- `tickets_lifecycle`
    sat six lines under its ceiling -- so the move is part of the
    delivery, not an incidental tidy, and is pinned as such.  Every name
    the facade and its siblings import must survive it: a split that
    silently drops one is exactly the breakage a facade exists to
    prevent.
    """

    SEAM = ("_do_claim", "_cmd_claim", "_claim_under_run_lock")

    def test_the_seam_is_defined_in_the_project_module(self):
        from scripts import tickets_project

        for name in self.SEAM:
            self.assertEqual(
                "scripts.tickets_project",
                getattr(tickets_project, name).__module__,
                f"{name} is not owned by scripts/tickets_project.py",
            )

    def test_the_lifecycle_module_and_the_facade_still_export_the_seam(self):
        from scripts import tickets, tickets_lifecycle

        for name in self.SEAM:
            self.assertTrue(hasattr(tickets_lifecycle, name), name)
            self.assertTrue(hasattr(tickets, name), name)

    def test_no_stale_copy_of_the_seam_survives_where_it_left(self):
        """A re-export, not a second definition.

        The two cases above pin that `tickets_project` owns the seam and
        that the lifecycle module and the facade still reach *a* name --
        and a copy left behind in `tickets_lifecycle.py` satisfies both,
        because ownership is read off the project module and the export
        check only asks whether an attribute exists.  The facade binds
        the lifecycle module's name (`scripts/tickets.py`,
        `_do_claim = _tickets_lifecycle_module._do_claim`), so a stale
        definition there is precisely what every caller through the
        facade would get.  What must hold is one definition reached by
        every door, which is what makes the extraction a move rather
        than a copy.
        """

        from scripts import tickets, tickets_lifecycle

        for name in self.SEAM:
            for module, where in ((tickets_lifecycle, "scripts/tickets_lifecycle.py"),
                                  (tickets, "scripts/tickets.py")):
                self.assertEqual(
                    "scripts.tickets_project",
                    getattr(module, name).__module__,
                    f"{name} reached through {where} is not the project module's",
                )

    def test_the_project_module_owns_the_binding_law(self):
        from scripts import tickets_project

        self.assertTrue(callable(tickets_project.binding_refusal))
        self.assertTrue(callable(tickets_project.root_ticket_project))


if __name__ == "__main__":
    unittest.main()
