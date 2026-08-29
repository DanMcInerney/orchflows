"""Folder identity and terminal timing on the run summary.

`/now` groups running and past work by the folder it ran in and orders the
past sections by completion recency. Both facts are already recorded --
`runs/<run>/run.json` carries `project.name`, `terminal_at` and
`terminal_status` -- and the projection used to drop them, hardcoding
`repository` and `client` to empty strings. These are the regressions for
the one drop point, `scripts.ui_experience._run_summaries`.

`client` stays empty on purpose: `run.json` carries no projection-safe
client source, so there is nothing honest to project and the field holds
its empty string until one exists.
"""

import json

from reader.tests.test_ui_cases._web import *  # noqa: F401,F403

import reader.scripts.ui_experience as experience


def write_identity(root: Path, run: str, **fields) -> Path:
    """One run's `run.json`, with exactly the keys a case names."""

    path = root / "runs" / run / "run.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    record = dict({"run": run}, **fields)
    path.write_text(json.dumps(record), encoding="utf-8")
    return path


def summaries(root: Path) -> dict:
    """The run summaries `/now` consumes, indexed by run id."""

    projected = experience.project_experience(root)
    return {run["id"]: run for run in projected["runs"]}


class RunFolderProjectionTests(unittest.TestCase):
    def test_repository_is_the_recorded_project_leaf_name(self):
        """The grouping key `/now` needs, from the one place it is recorded."""

        with tempfile.TemporaryDirectory() as tmp:
            root = make_sink(Path(tmp), runs=("run-alpha", "run-beta"))
            write_identity(root, "run-alpha", project={
                "root": "C:/Users/someone/tools/orchflows-public",
                "origin": "https://github.com/someone/orchflows-public.git",
                "name": "orchflows-public",
            })
            before = snapshot(root)

            indexed = summaries(root)

            self.assertEqual(before, snapshot(root))

        self.assertEqual("orchflows-public", indexed["run-alpha"]["repository"])
        # No `run.json` at all: unrecorded is the empty string, not a guess
        # derived from the sink's own location.
        self.assertEqual("", indexed["run-beta"]["repository"])

    def test_an_unrecorded_or_unusable_project_name_stays_empty(self):
        """Every shape short of a recorded leaf reads as unrecorded.

        The sink is untrusted data, so each of these is a value the reader
        can actually meet rather than a shape only a broken writer emits.
        """

        cases = {
            "run-alpha": {"project": {"root": "C:/private/project"}},
            "run-beta": {"project": {"name": ""}},
            "run-gamma": {"project": {"name": ["orchflows-public"]}},
            "run-delta": {"project": "orchflows-public"},
            "run-epsilon": {},
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = make_sink(Path(tmp))
            for run, fields in cases.items():
                write_identity(root, run, **fields)

            indexed = summaries(root)

        for run in cases:
            self.assertEqual("", indexed[run]["repository"], run)

    def test_a_run_json_naming_another_run_is_not_this_runs_identity(self):
        """The same self-identification guard the workflow id already keeps.

        A `run.json` that names a different run is a misfiled document, and
        reading a folder name off it would group the run under a folder no
        evidence puts it in.
        """

        with tempfile.TemporaryDirectory() as tmp:
            root = make_sink(Path(tmp), runs=("run-alpha",))
            write_identity(root, "run-alpha", project={"name": "right-folder"})
            path = root / "runs" / "run-alpha" / "run.json"
            path.write_text(
                json.dumps({
                    "run": "run-beta",
                    "project": {"name": "wrong-folder"},
                    "terminal_at": "2026-08-24T22:25:00Z",
                    "terminal_status": "complete",
                }),
                encoding="utf-8",
            )

            indexed = summaries(root)

        self.assertEqual("", indexed["run-alpha"]["repository"])
        self.assertEqual("", indexed["run-alpha"]["terminal_at"])
        self.assertEqual("", indexed["run-alpha"]["terminal_status"])

    def test_terminal_timing_is_projected_verbatim_and_empty_while_live(self):
        """What orders the past sections by completion recency."""

        with tempfile.TemporaryDirectory() as tmp:
            root = make_sink(Path(tmp), runs=("run-alpha", "run-beta", "run-gamma"))
            write_identity(
                root,
                "run-alpha",
                project={"name": "orchflows-public"},
                terminal_at="2026-08-24T22:25:00Z",
                terminal_status="complete",
            )
            write_identity(
                root,
                "run-beta",
                project={"name": "orchflows-public"},
                terminal_at="2026-08-23T09:00:00Z",
                terminal_status="limited",
            )
            # Live: opened, never terminal.
            write_identity(root, "run-gamma", project={"name": "other-folder"})

            indexed = summaries(root)

        self.assertEqual("2026-08-24T22:25:00Z", indexed["run-alpha"]["terminal_at"])
        self.assertEqual("complete", indexed["run-alpha"]["terminal_status"])
        self.assertEqual("2026-08-23T09:00:00Z", indexed["run-beta"]["terminal_at"])
        self.assertEqual("limited", indexed["run-beta"]["terminal_status"])
        self.assertEqual("", indexed["run-gamma"]["terminal_at"])
        self.assertEqual("", indexed["run-gamma"]["terminal_status"])
        # The ordering the past sections are built on is decidable from the
        # projected field alone -- no second read of the sink.
        past = sorted(
            (run for run in indexed.values() if run["terminal_at"]),
            key=lambda run: run["terminal_at"],
            reverse=True,
        )
        self.assertEqual(["run-alpha", "run-beta"], [run["id"] for run in past])

    def test_client_stays_empty_because_no_projection_safe_source_exists(self):
        """A field held open, not quietly filled from an adjacent value."""

        with tempfile.TemporaryDirectory() as tmp:
            root = make_sink(Path(tmp), runs=("run-alpha",))
            write_identity(
                root,
                "run-alpha",
                project={"name": "orchflows-public"},
                orchflows={"client": "claude-code"},
            )

            indexed = summaries(root)

        self.assertEqual("", indexed["run-alpha"]["client"])

    def test_the_summary_carries_exactly_the_now_schemas_keys(self):
        """The consumed shape, stated once so a silent addition fails here."""

        with tempfile.TemporaryDirectory() as tmp:
            root = make_sink(Path(tmp), runs=("run-alpha",))
            write_identity(root, "run-alpha", project={"name": "orchflows-public"})

            indexed = summaries(root)

        self.assertEqual(
            {
                "id", "workflow", "execution", "ticket_count", "active",
                "objective", "repository", "client", "terminal_at",
                "terminal_status", "last_activity", "unreadable", "tickets",
            },
            set(indexed["run-alpha"]),
        )

    def test_the_folder_name_opens_no_path_origin_or_workspace(self):
        """The privacy wall, at the field that newly reads `run.json`.

        `project.name` is projectable because it is a leaf, on the precedent
        the session list already sets. Its siblings never are, and a
        `project.name` that is itself a full host path is a misrecorded leaf,
        not a licence to project one.
        """

        with tempfile.TemporaryDirectory() as tmp:
            root = make_sink(Path(tmp), runs=("run-alpha", "run-beta"))
            write_identity(root, "run-alpha", project={
                "root": "C:/private/project",
                "origin": "https://github.com/private/secret-repo.git",
                "name": "C:/private/project",
            }, workspaces=[{"path": "C:/private/worktree"}])
            write_identity(root, "run-beta", project={
                "name": "/home/private/posix-project",
            })

            encoded = json.dumps(experience.project_experience(root), sort_keys=True)
            indexed = summaries(root)

        for secret in (
            "C:/private/project",
            "C:/private/worktree",
            "https://github.com/private/secret-repo.git",
            "/home/private/posix-project",
        ):
            self.assertNotIn(secret, encoded)
        # A misrecorded leaf degrades to the leaf, never to the path.
        self.assertEqual("project", indexed["run-alpha"]["repository"])
        self.assertEqual("posix-project", indexed["run-beta"]["repository"])


if __name__ == "__main__":
    unittest.main()
