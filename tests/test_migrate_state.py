"""migrate_state.py copies a pre-existing state tree into the sink.

Three properties carry the whole item, and each is asserted against a
fixture tree built in the OS temp directory — never against a real
``.orch`` on this host, and never against the real sink: it is
idempotent, it is non-destructive, and the plan a dry run prints is the
plan a real run executes.

Every case sets ``ORCHFLOWS_STATE_HOME`` for its own sink.
``tests/__init__`` already points it at a temporary directory for the
whole process; these cases narrow it further to one per test, so no case
reads another's leftovers.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# migrate_state.py imports its siblings as `scripts.x` in-repo, falling back
# to a flat `x` beside it once installed. Neither name is importable from
# `tests/` alone, so put the repository root on the path before the module
# body runs.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_spec = importlib.util.spec_from_file_location(
    "migrate_state", ROOT / "scripts" / "migrate_state.py"
)
migrate_state = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_spec and migrate_state)

from scripts import tickets  # noqa: E402  the owner of project identity

STATE_HOME_ENV_VAR = "ORCHFLOWS_STATE_HOME"
# A legacy entry: the shape the stream carried before it said which project
# an entry arose in. No `project`, no `project_source`, no
# `sink_convention` -- exactly what migration has to answer for.
LEGACY_KEYS = ("ts", "cwd", "git_rev", "host", "session",
               "category", "skill", "ticket", "run", "observed", "expected")


def legacy_entry(cwd, observed="something happened", **overrides):
    entry = {
        "ts": "2026-01-02T03:04:05Z",
        "cwd": str(cwd),
        "git_rev": "abc1234",
        "host": "claude-code",
        "session": None,
        "category": "workaround",
        "skill": None,
        "ticket": None,
        "run": None,
        "observed": observed,
        "expected": "it not to",
    }
    entry.update(overrides)
    return json.dumps(entry, ensure_ascii=False)


def make_repo(path: Path, origin=None) -> Path:
    """A directory that answers "which project" the way a checkout does.

    ``state_root.find_repo_root`` looks for ``.git`` and ``tickets.py``
    reads ``origin`` out of ``.git/config``; neither shells out to git, so
    a real repository is not needed to exercise either.
    """

    (path / ".git").mkdir(parents=True, exist_ok=True)
    config = '[core]\n\trepositoryformatversion = 0\n'
    if origin is not None:
        config += f'[remote "origin"]\n\turl = {origin}\n'
    (path / ".git" / "config").write_text(config, encoding="utf-8")
    return path


def write(path: Path, text: str) -> Path:
    """``Path.write_text`` takes no ``newline`` before 3.10, and the floor
    here is 3.9; these fixtures are byte-compared, so the line ending has to
    be the same one on every platform."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    return path


def tree_state(root: Path):
    """Every file under ``root`` by relative path -> (sha256, size, mtime_ns).

    mtime is part of the identity on purpose: criterion 2 is that a source
    is untouched, and a tool that rewrote a file with identical bytes would
    still be a tool that wrote to a source.
    """

    if not root.exists():
        return {}
    state = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        data = path.read_bytes()
        info = path.stat()
        state[str(path.relative_to(root))] = (
            hashlib.sha256(data).hexdigest(), info.st_size, info.st_mtime_ns
        )
    return state


def sink_bytes(root: Path):
    """Every file under ``root`` by relative path -> bytes. mtime is excluded:
    ``shutil.copy2`` carries a source's mtime across, so a destination's
    timestamps say nothing about whether a second run wrote anything."""

    if not root.exists():
        return {}
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in sorted(root.rglob("*")) if path.is_file()
    }


def lines_of(path: Path):
    return [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


class MigrationCase(unittest.TestCase):
    """A temporary home, a sink inside it, and sources built per test."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="orchflows-migrate-")
        self.addCleanup(self._tmp.cleanup)
        self.home = Path(self._tmp.name).resolve()
        self.sink = self.home / "sink"
        previous = os.environ.get(STATE_HOME_ENV_VAR)
        os.environ[STATE_HOME_ENV_VAR] = str(self.sink)

        def restore():
            if previous is None:
                os.environ.pop(STATE_HOME_ENV_VAR, None)
            else:
                os.environ[STATE_HOME_ENV_VAR] = previous

        self.addCleanup(restore)

    def migrate(self, *roots, dry_run=False):
        argv = []
        for root in roots:
            argv += ["--from", str(root)]
        if dry_run:
            argv.append("--dry-run")
        result = migrate_state.run(argv)
        self.assertNotIn("error", result, result)
        return result["migrate_state"]

    def source_root(self, repo_name, origin=None):
        """A ``<repo>/.orch`` in its own checkout, the shape being migrated."""

        repo = make_repo(self.home / repo_name, origin=origin)
        root = repo / ".orch"
        root.mkdir(parents=True, exist_ok=True)
        return root


class TestMigrationIdempotent(MigrationCase):
    """Run it twice: the sink settles after the first pass, and every source
    file is byte-unchanged -- the constraint the whole item exists to
    honour."""

    def build_source(self):
        root = self.source_root("alpha", origin="git@github.com:acme/alpha.git")
        write(root / "runs" / "20260101T000000Z-a" / "worklog.md", "# a\n\nnote\n")
        write(root / "runs" / "20260101T000000Z-a" / "run.json",
              json.dumps({"run": "20260101T000000Z-a", "sink_convention": 2}) + "\n")
        write(root / "tickets" / "20260101T000000Z-a" / "01-thing.md", "---\nid: 01\n---\n")
        write(root / "friction" / "2026-01.jsonl",
              legacy_entry(root.parent, "one") + "\n" + legacy_entry(root.parent, "two") + "\n")
        write(root / "improvement" / "proposals" / "2026-01-01-slug.md", "# proposal\n")
        write(root / "improvement" / "covered.jsonl",
              json.dumps({"cluster": "c1", "watermark": "2026-01-01"}) + "\n")
        return root

    def test_a_second_run_changes_nothing_and_plans_nothing(self):
        root = self.build_source()

        first = self.migrate(root)
        after_one = sink_bytes(self.sink)
        self.assertTrue(first["plan"], "the first run planned nothing at all")

        second = self.migrate(root)
        after_two = sink_bytes(self.sink)

        self.assertEqual(after_one, after_two)
        self.assertEqual(second["plan"], [])
        self.assertEqual(second["sources"][0]["friction"]["write"], 0)
        self.assertEqual(second["sources"][0]["friction"]["duplicates"], 2)
        self.assertEqual(second["sources"][0]["runs"]["files"], 0)
        self.assertEqual(second["sources"][0]["runs"]["existing"], 2)
        self.assertEqual(second["sources"][0]["differing"], [])

    def test_every_source_file_is_byte_unchanged_after_both_runs(self):
        root = self.build_source()
        before = tree_state(root)
        self.assertTrue(before, "the fixture source is empty")

        self.migrate(root)
        self.assertEqual(tree_state(root), before)
        self.migrate(root)
        self.assertEqual(tree_state(root), before)

    def test_a_read_only_source_still_migrates(self):
        """A source whose directories deny writes proves copying rather than
        moving in the one way an assertion on bytes cannot: the tool has no
        permission to be destructive, and still succeeds."""

        if os.name == "nt":  # pragma: no cover - POSIX mode bits only
            self.skipTest("directory write permission is not enforced this way on Windows")
        root = self.build_source()
        directories = [path for path in root.rglob("*") if path.is_dir()] + [root]
        modes = {path: path.stat().st_mode for path in directories}

        def restore():
            for path, mode in modes.items():
                path.chmod(mode)

        self.addCleanup(restore)
        for path in sorted(directories, reverse=True):
            path.chmod(stat.S_IRUSR | stat.S_IXUSR)

        report = self.migrate(root)
        self.assertEqual(report["errors"], [])
        self.assertTrue((self.sink / "runs" / "20260101T000000Z-a" / "worklog.md").is_file())
        self.assertEqual(
            lines_of(self.sink / "friction" / "2026-01.jsonl").__len__(), 2
        )


class TestLegacyFriction(MigrationCase):
    """Legacy entries gain the project they arose in, or say they cannot --
    and never a guess. Both conventions then read as one stream."""

    def build_source(self):
        self.repo = make_repo(self.home / "beta", origin="git@github.com:acme/beta.git")
        root = self.repo / ".orch"
        self.gone = self.home / "deleted-checkout"
        known = legacy_entry(self.repo, "resolvable")
        write(root / "friction" / "2026-02.jsonl", "\n".join([
            known,                                   # cwd inside a live repository
            known,                                   # the same line, exactly
            legacy_entry(self.gone, "vanished"),     # cwd that no longer exists
            "{not json at all",                      # a broken write
        ]) + "\n")
        return root

    def test_a_live_cwd_is_backfilled_and_the_duplicate_lands_once(self):
        root = self.build_source()
        self.migrate(root)

        lines = lines_of(self.sink / "friction" / "2026-02.jsonl")
        resolvable = [json.loads(line) for line in lines
                      if line.startswith("{") and "resolvable" in line]
        self.assertEqual(len(resolvable), 1, lines)
        entry = resolvable[0]
        # `.get` and one equality, not a chain of subscripts: a tool that
        # skipped the backfill leaves `project` null, and this has to read
        # red for that rather than raising on `None["root"]`.
        self.assertEqual(entry.get("project"), {
            "root": str(self.repo),
            "origin": "git@github.com:acme/beta.git",
            "name": "beta",
        })
        self.assertEqual(entry.get("project_source"), "cwd")

    def test_a_vanished_cwd_keeps_a_null_project_and_says_why(self):
        root = self.build_source()
        self.migrate(root)

        entry = next(json.loads(line)
                     for line in lines_of(self.sink / "friction" / "2026-02.jsonl")
                     if line.startswith("{") and "vanished" in line)
        self.assertIsNone(entry["project"])
        self.assertEqual(entry["project_source"], "none")
        self.assertFalse(self.gone.exists(), "the fixture's vanished cwd must not exist")

    def test_a_line_that_is_not_json_is_carried_across_unaltered(self):
        root = self.build_source()
        report = self.migrate(root)

        lines = lines_of(self.sink / "friction" / "2026-02.jsonl")
        self.assertIn("{not json at all", lines)
        self.assertEqual(report["sources"][0]["friction"]["unparsed"], 1)

    def test_every_migrated_entry_is_stamped_and_says_where_it_came_from(self):
        root = self.build_source()
        self.migrate(root)

        for line in lines_of(self.sink / "friction" / "2026-02.jsonl"):
            if not line.startswith("{") or "not json" in line:
                continue
            entry = json.loads(line)
            self.assertEqual(entry["sink_convention"], 1, line)
            self.assertEqual(entry["migrated_from"], str(root), line)
            for key in LEGACY_KEYS:
                self.assertIn(key, entry, f"{key} was dropped from {line}")

    def test_an_entry_that_already_names_its_convention_keeps_it(self):
        """A source may hold live entries written after the sink landed.
        Restamping one ``sink_convention: 1`` would say it predates a field
        it carries, so migration adds provenance and changes nothing else."""

        root = self.source_root("gamma")
        live = json.loads(legacy_entry(root.parent, "already current"))
        live.update({"sink_convention": tickets.SINK_CONVENTION,
                     "project": {"root": "/elsewhere", "origin": None, "name": "elsewhere"},
                     "project_source": "run"})
        write(root / "friction" / "2026-03.jsonl", json.dumps(live) + "\n")

        self.migrate(root)
        month = self.sink / "friction" / "2026-03.jsonl"
        self.assertTrue(month.is_file(), "the month file never reached the sink")
        entry = json.loads(lines_of(month)[0])
        self.assertEqual(entry.get("sink_convention"), tickets.SINK_CONVENTION)
        self.assertEqual(entry.get("project"),
                         {"root": "/elsewhere", "origin": None, "name": "elsewhere"})
        self.assertEqual(entry.get("project_source"), "run")
        self.assertEqual(entry.get("migrated_from"), str(root))

    def test_both_conventions_read_as_one_stream(self):
        """The promise the sink actually makes: a reader of the month file
        parses every line and gets an answer to "which project" from each,
        whichever convention wrote it."""

        root = self.build_source()
        self.migrate(root)
        month = self.sink / "friction" / "2026-02.jsonl"
        live = json.loads(legacy_entry(self.repo, "written after migration"))
        live.update({"sink_convention": tickets.SINK_CONVENTION,
                     "project": {"root": str(self.repo), "origin": None, "name": "beta"},
                     "project_source": "cwd"})
        with open(month, "a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(live) + "\n")

        stream = lines_of(month)
        conventions, answered = set(), 0
        for line in stream:
            if line == "{not json at all":
                continue  # carried verbatim by design; it never parsed to begin with
            entry = json.loads(line)
            conventions.add(entry["sink_convention"])
            self.assertIn("project", entry, line)
            self.assertIn(entry["project_source"], ("cwd", "run", "none"), line)
            answered += 1
        self.assertEqual(conventions, {1, tickets.SINK_CONVENTION})
        # the deduplicated legacy pair, the vanished one, the broken one, the live one
        self.assertEqual(len(stream), 4)
        self.assertEqual(answered, 3)


class TestMigrationLayout(MigrationCase):
    """Where each stream lands, what is left where it stands, and what a run
    id two projects both claim does."""

    def build_source(self):
        root = self.source_root("delta", origin="git@github.com:acme/delta.git")
        write(root / "runs" / "20260201T000000Z-r" / "worklog.md", "# r\n")
        write(root / "runs" / "20260201T000000Z-r" / "composition.md", "# c\n")
        write(root / "tickets" / "20260201T000000Z-r" / "01-x.md", "x\n")
        write(root / "friction" / "2026-02.jsonl", legacy_entry(root.parent) + "\n")
        write(root / "improvement" / "proposals" / "2026-02-01-p.md", "# p\n")
        write(root / "improvement" / "covered.jsonl",
              json.dumps({"cluster": "c2"}) + "\n")
        write(root / "canary" / "golden" / "spec.md", "# canary\n")
        write(root / "bin" / "tickets.py", "# installed\n")
        write(root / "events" / "2026-02.log", "event\n")
        return root

    def test_each_stream_lands_where_the_sink_layout_fixes_it(self):
        root = self.build_source()
        self.migrate(root)

        for relative in (
            "runs/20260201T000000Z-r/worklog.md",
            "runs/20260201T000000Z-r/composition.md",
            "tickets/20260201T000000Z-r/01-x.md",
            "friction/2026-02.jsonl",
            "improvement/proposals/2026-02-01-p.md",
            "improvement/covered.jsonl",
        ):
            with self.subTest(path=relative):
                self.assertTrue((self.sink / relative).is_file(),
                                f"{relative} is missing from the sink")

    def test_canary_and_bin_stay_in_the_repository_and_are_reported(self):
        root = self.build_source()
        report = self.migrate(root)

        self.assertEqual(sorted(report["sources"][0]["retained"]), ["bin/", "canary/"])
        self.assertFalse((self.sink / "canary").exists())
        self.assertFalse((self.sink / "bin").exists())
        self.assertTrue((root / "canary" / "golden" / "spec.md").is_file())
        self.assertTrue((root / "bin" / "tickets.py").is_file())

    def test_an_unrecognised_directory_is_named_and_not_copied(self):
        root = self.build_source()
        report = self.migrate(root)

        self.assertIn("events/", report["sources"][0]["unrecognised"])
        self.assertFalse((self.sink / "events").exists())
        self.assertTrue((root / "events" / "2026-02.log").is_file())

    def test_each_coverage_line_gains_the_project_it_arose_in(self):
        root = self.build_source()
        self.migrate(root)

        record = self.sink / "improvement" / "covered.jsonl"
        # Checked before it is indexed: a tool that never migrated the stream
        # at all has to read red here, not raise on an empty list.
        self.assertTrue(record.is_file(), "the coverage record never reached the sink")
        entry = json.loads(lines_of(record)[0])
        self.assertEqual(entry["cluster"], "c2")
        self.assertEqual(entry.get("project"), {
            "root": str(root.parent),
            "origin": "git@github.com:acme/delta.git",
            "name": "delta",
        })
        self.assertEqual(entry.get("migrated_from"), str(root))

    def test_a_run_two_projects_claim_is_refused_and_the_rest_migrates(self):
        shared = "20260301T000000Z-shared"
        first = self.source_root("epsilon", origin="git@github.com:acme/epsilon.git")
        second = self.source_root("zeta", origin="git@github.com:acme/zeta.git")
        for root in (first, second):
            write(root / "runs" / shared / "worklog.md", f"# from {root.parent.name}\n")
            write(root / "tickets" / shared / "01-x.md", f"from {root.parent.name}\n")
        write(first / "runs" / "20260301T000000Z-own" / "worklog.md", "# mine\n")

        report = self.migrate(first, second)

        self.assertEqual([entry["run"] for entry in report["collisions"]], [shared])
        claimants = sorted(claim["project"] for claim in report["collisions"][0]["claims"])
        self.assertEqual(claimants, ["git@github.com:acme/epsilon",
                                     "git@github.com:acme/zeta"])
        self.assertFalse((self.sink / "runs" / shared).exists())
        self.assertFalse((self.sink / "tickets" / shared).exists())
        self.assertTrue((self.sink / "runs" / "20260301T000000Z-own" / "worklog.md").is_file())
        for source in report["sources"]:
            self.assertIn(shared, source["runs"]["skipped_collision"])
            self.assertIn(shared, source["tickets"]["skipped_collision"])

    def test_two_workspaces_of_one_project_are_not_a_collision(self):
        """Two clones of one origin are one project with two workspaces --
        item 03's rule, and refusing them here would strand every run opened
        from a worktree."""

        shared = "20260301T000000Z-shared"
        origin = "git@github.com:acme/eta.git"
        first = self.source_root("eta", origin=origin)
        second = self.source_root("eta-clone", origin=origin)
        for root, body in ((first, "# one\n"), (second, "# one\n")):
            write(root / "runs" / shared / "worklog.md", body)

        report = self.migrate(first, second)

        self.assertEqual(report["collisions"], [])
        self.assertTrue((self.sink / "runs" / shared / "worklog.md").is_file())

    def test_a_dry_run_plans_exactly_what_a_real_run_does_and_writes_nothing(self):
        root = self.build_source()
        before = sink_bytes(self.sink)

        planned = self.migrate(root, dry_run=True)
        self.assertEqual(sink_bytes(self.sink), before)
        self.assertFalse(self.sink.exists() and any(self.sink.rglob("*")))

        executed = self.migrate(root)
        self.assertEqual(planned["plan"], executed["plan"])
        self.assertTrue(planned["plan"], "a dry run over a populated source planned nothing")
        del planned["dry_run"], executed["dry_run"]
        self.assertEqual(planned, executed)

    def test_a_record_already_at_the_destination_is_never_overwritten(self):
        root = self.build_source()
        write(self.sink / "runs" / "20260201T000000Z-r" / "worklog.md", "# already here\n")

        report = self.migrate(root)

        self.assertEqual(
            (self.sink / "runs" / "20260201T000000Z-r" / "worklog.md").read_text(encoding="utf-8"),
            "# already here\n",
        )
        self.assertEqual(
            [entry["source"] for entry in report["sources"][0]["differing"]],
            [str(root / "runs" / "20260201T000000Z-r" / "worklog.md")],
        )

    def test_the_sink_cannot_be_migrated_into_itself(self):
        self.sink.mkdir(parents=True, exist_ok=True)
        report = self.migrate(self.sink)

        self.assertEqual(report["plan"], [])
        self.assertEqual(len(report["errors"]), 1, report["errors"])
        self.assertIn("cannot be migrated into itself", report["errors"][0])

    def test_a_source_that_does_not_exist_is_reported_not_raised(self):
        missing = self.home / "nowhere" / ".orch"
        report = self.migrate(missing)

        self.assertEqual(report["plan"], [])
        self.assertIn("is not a directory", report["errors"][0])


class TestUsage(MigrationCase):
    """One JSON document, always; a refusal is a payload, never a traceback."""

    def test_no_source_is_a_usage_error(self):
        self.assertIn("error", migrate_state.run([]))

    def test_an_unknown_flag_is_refused_rather_than_guessed(self):
        result = migrate_state.run(["--from", str(self.home), "--force"])
        self.assertIn("error", result)
        self.assertIn("--force", result["error"])


if __name__ == "__main__":
    unittest.main()
