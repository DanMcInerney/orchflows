"""The required-check runner: order, exit mapping, payload, and its cache."""

from __future__ import annotations

import hashlib
import io
import json
import re
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from tests.test_run_required_cases.harness import (
    REPO_ROOT,
    RunRequiredCase,
    Stub,
    git,
    moment,
    runtime_directory_name,
)

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

SURFACE_ORDER = (
    ["tools/validate.py"],
    ["tools/run_tests.py"],
    ["tools/run_serial_compat.py"],
    ["install.py", "--dry-run"],
)
WHITESPACE_CHECK = ["git", "diff", "--check"]
CHEAP = ("validate.py", "install.py", "diff")
COMMAND_KEYS = {
    "argv", "started_at", "ended_at", "exit_status",
    "stdout_sha256", "stderr_sha256", "cached",
}
RECORD_KEYS = {
    "kind", "repository_identity", "tree_identity", "dirty", "commands", "exit",
}
# Spelled out rather than imported: a record's kind is what a reader of the
# JSON matches on, so renaming the constant must not rename the contract.
RUN_KIND = "required-check-run/v1"
REPLAY_KIND = "required-check-replay/v1"


def stream_digest(record, tag: str) -> str:
    """What the stub must have put on that stream, digested.

    `git diff --check` is the one check the stub never sees, and it says
    nothing here, so both of its streams are the digest of no bytes at all.
    """

    if Path(record["argv"][0]).name == "git":
        payload = b""
    else:
        argv = " ".join(record["argv"][1:])
        payload = "{0} {1}\n".format(tag, argv).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


class TestRefusal(RunRequiredCase):
    """Exit 2 is reserved for what the runner cannot honestly attempt."""

    def test_a_directory_that_is_not_a_checkout_is_refused(self):
        outside = Path(self.repo).parent / "not-a-checkout"
        outside.mkdir()
        status, _, _, err = self.invoke("--repo", str(outside))
        self.assertEqual(2, status)
        self.assertIn("git", err)
        self.assertEqual([], self.stub.calls())

    def test_a_missing_interpreter_is_refused(self):
        missing = Path(self.repo).parent / "stub" / "absent-python"
        status, _, _, err = self.invoke("--python", str(missing))
        self.assertEqual(2, status)
        self.assertIn("interpreter", err)
        self.assertEqual([], self.stub.calls())

    def test_a_refusal_names_itself_in_the_json_stream(self):
        outside = Path(self.repo).parent / "also-not-a-checkout"
        outside.mkdir()
        _, payload, _, _ = self.invoke("--repo", str(outside))
        self.assertIsNotNone(payload)
        self.assertEqual("required-check-refusal/v1", payload["kind"])
        self.assertTrue(payload["reason"])


class TestOrderAndPhases(RunRequiredCase):
    """The surface's order is what the record says; the phases are timing."""

    def test_the_record_lists_the_five_in_the_surface_order(self):
        status, payload, _, _ = self.invoke()
        self.assertEqual(0, status)
        stub = str(self.stub.path.resolve())
        expected = [[stub] + list(args) for args in SURFACE_ORDER]
        expected.append(WHITESPACE_CHECK)
        self.assertEqual(expected, [r["argv"] for r in payload["commands"]])

    def test_the_interpreter_is_asked_for_itself_exactly_once(self):
        _, payload, _, _ = self.invoke()
        self.assertEqual(1, len(self.stub.probes()))
        self.assertEqual(
            [["install.py", "--dry-run"], ["tools/run_serial_compat.py"],
             ["tools/run_tests.py"], ["tools/validate.py"]],
            sorted(self.stub.calls()),
        )

    def test_the_cheap_three_share_one_window(self):
        self.stub.plan({
            "validate.py": {"sleep": 0.5},
            "install.py": {"sleep": 0.5},
        })
        _, payload, _, _ = self.invoke()
        cheap = [self.named(payload, needle) for needle in CHEAP]
        latest_start = max(moment(record["started_at"]) for record in cheap)
        earliest_end = min(moment(record["ended_at"]) for record in cheap)
        self.assertLess(latest_start, earliest_end, cheap)

    def test_each_long_check_starts_after_everything_before_it_ended(self):
        self.stub.plan({
            "validate.py": {"sleep": 0.2},
            "run_tests.py": {"sleep": 0.2},
        })
        _, payload, _, _ = self.invoke()
        cheap = [self.named(payload, needle) for needle in CHEAP]
        tests = self.named(payload, "run_tests.py")
        serial = self.named(payload, "run_serial_compat.py")
        self.assertGreaterEqual(
            moment(tests["started_at"]),
            max(moment(record["ended_at"]) for record in cheap),
        )
        self.assertGreaterEqual(
            moment(serial["started_at"]), moment(tests["ended_at"])
        )


class TestExitMapping(RunRequiredCase):
    """0 for all five green, 1 for any red; 2 stays refusal's alone."""

    def test_all_five_green_is_zero(self):
        status, payload, _, _ = self.invoke()
        self.assertEqual(0, status)
        self.assertEqual(0, payload["exit"])
        self.assertEqual([0] * 5, [r["exit_status"] for r in payload["commands"]])

    def test_one_red_check_is_one(self):
        self.stub.plan({"run_serial_compat.py": {"exit": 7}})
        status, payload, _, _ = self.invoke()
        self.assertEqual(1, status)
        self.assertEqual(1, payload["exit"])
        self.assertEqual(7, self.named(payload, "run_serial_compat.py")["exit_status"])

    def test_a_red_cheap_check_does_not_cancel_the_long_ones(self):
        self.stub.plan({"validate.py": {"exit": 1}})
        status, payload, _, _ = self.invoke()
        self.assertEqual(1, status)
        self.assertEqual(5, len(payload["commands"]))
        self.assertEqual(0, self.named(payload, "run_tests.py")["exit_status"])


class TestRecordShape(RunRequiredCase):
    """The payload is the evidence; its keys are the contract."""

    def test_the_record_carries_exactly_the_stated_keys(self):
        _, payload, _, _ = self.invoke()
        self.assertEqual("required-check-run/v1", payload["kind"])
        self.assertEqual(RECORD_KEYS, set(payload))
        for record in payload["commands"]:
            self.assertEqual(COMMAND_KEYS, set(record))

    def test_the_record_names_the_commit_and_the_tree_it_judged(self):
        _, payload, _, _ = self.invoke()
        self.assertEqual(git(self.repo, "rev-parse", "HEAD"),
                         payload["repository_identity"])
        self.assertEqual(git(self.repo, "rev-parse", "HEAD^{tree}"),
                         payload["tree_identity"])
        self.assertFalse(payload["dirty"])

    def test_a_working_change_is_reported_dirty(self):
        self.touch_tracked()
        _, payload, _, _ = self.invoke()
        self.assertTrue(payload["dirty"])

    def test_an_untracked_file_is_dirt_but_an_ignored_one_is_not(self):
        (self.repo / "ignored").mkdir()
        (self.repo / "ignored" / "junk.txt").write_text("x", encoding="utf-8")
        _, payload, _, _ = self.invoke()
        self.assertFalse(payload["dirty"])
        (self.repo / "loose.txt").write_text("x", encoding="utf-8")
        _, payload, _, _ = self.invoke("--no-cache")
        self.assertTrue(payload["dirty"])

    def test_each_command_digests_its_own_two_streams(self):
        _, payload, _, _ = self.invoke()
        digests = set()
        for record in payload["commands"]:
            for key in ("stdout_sha256", "stderr_sha256"):
                self.assertRegex(record[key], r"\A[0-9a-f]{64}\Z")
            digests.add(record["stdout_sha256"])
            # Named for a stream, so digested from that stream: two
            # hex strings of the right shape prove nothing on their own.
            for key, tag in (("stdout_sha256", "stub-out"),
                             ("stderr_sha256", "stub-err")):
                self.assertEqual(stream_digest(record, tag), record[key])
        self.assertEqual(5, len(digests))

    def test_a_freshly_run_command_is_not_marked_cached(self):
        _, payload, _, _ = self.invoke()
        self.assertEqual([False] * 5, [r["cached"] for r in payload["commands"]])


class TestCacheLocation(RunRequiredCase):
    """A verdict memo is runtime state, so it lives where runtime state does."""

    def test_the_cache_sits_under_the_runners_own_gitignored_directory(self):
        from tools.run_required_support import cache

        directory = cache.runtime_cache_dir(self.repo)
        self.assertEqual(self.repo, directory.parent.parent)
        self.assertEqual(runtime_directory_name(), directory.parent.name)
        self.assertEqual("required_cache", directory.name)

    def test_a_green_clean_run_stores_exactly_one_entry_named_by_its_key(self):
        self.invoke()
        entries = self.cache_entries()
        self.assertEqual(1, len(entries))
        self.assertRegex(entries[0].stem, r"\A[0-9a-f]{64}\Z")
        stored = json.loads(entries[0].read_text(encoding="utf-8"))
        self.assertEqual(0, stored["exit"])

    def test_the_stored_entry_is_ignored_by_the_checkout(self):
        self.invoke()
        entries = self.cache_entries()
        relative = entries[0].relative_to(self.repo).as_posix()
        self.assertEqual(relative, git(self.repo, "check-ignore", relative))


class TestCacheService(RunRequiredCase):
    """What may be served, and what must be run again."""

    def test_an_unchanged_clean_tree_is_served_without_running_a_check(self):
        first = self.invoke()[1]
        self.stub.forget()
        status, payload, _, _ = self.invoke()
        self.assertEqual(0, status)
        self.assertEqual([], self.stub.calls())
        self.assertEqual([True] * 5, [r["cached"] for r in payload["commands"]])
        self.assertEqual(
            [r["started_at"] for r in first["commands"]],
            [r["started_at"] for r in payload["commands"]],
        )

    def test_touching_one_tracked_file_invalidates_the_entry(self):
        self.invoke()
        self.stub.forget()
        self.touch_tracked()
        git(self.repo, "add", "README.md")
        git(self.repo, "commit", "--quiet", "-m", "second")
        _, payload, _, _ = self.invoke()
        self.assertEqual(4, len(self.stub.calls()))
        self.assertEqual([False] * 5, [r["cached"] for r in payload["commands"]])

    def test_dirt_after_a_stored_run_is_never_served(self):
        self.invoke()
        for dirty in (self.touch_tracked, self.add_untracked):
            self.stub.forget()
            dirty()
            _, payload, _, _ = self.invoke()
            self.assertTrue(payload["dirty"])
            self.assertEqual(4, len(self.stub.calls()))
            self.assertEqual(
                [False] * 5, [r["cached"] for r in payload["commands"]]
            )
            git(self.repo, "checkout", "--", "README.md")

    def test_another_interpreter_is_another_key(self):
        self.invoke()
        self.stub.forget()
        other = Stub(Path(self.repo).parent / "second-stub")
        status, _, _, _ = self.invoke("--python", str(other.path))
        self.assertEqual(0, status)
        self.assertEqual(4, len(other.calls()))
        self.assertEqual(2, len(self.cache_entries()))

    def test_the_runners_own_memo_never_counts_as_a_change(self):
        (self.repo / ".gitignore").write_text("ignored/\n", encoding="utf-8")
        git(self.repo, "add", ".gitignore")
        git(self.repo, "commit", "--quiet", "-m", "stop ignoring runtime state")
        _, payload, _, _ = self.invoke()
        self.assertFalse(payload["dirty"])
        self.assertEqual(1, len(self.cache_entries()))
        self.stub.forget()
        _, payload, _, _ = self.invoke()
        self.assertEqual([], self.stub.calls())
        self.assertEqual([True] * 5, [r["cached"] for r in payload["commands"]])

    def test_no_cache_runs_again_and_stores_nothing_new(self):
        self.invoke()
        stored = self.cache_entries()[0].read_bytes()
        self.stub.forget()
        _, payload, _, _ = self.invoke("--no-cache")
        self.assertEqual(4, len(self.stub.calls()))
        self.assertEqual([False] * 5, [r["cached"] for r in payload["commands"]])
        self.assertEqual(stored, self.cache_entries()[0].read_bytes())


class TestWhatIsNeverStored(RunRequiredCase):
    """The three ways a run forfeits its memo."""

    def test_a_red_run_is_not_stored(self):
        self.stub.plan({"run_tests.py": {"exit": 1}})
        status, _, _, _ = self.invoke()
        self.assertEqual(1, status)
        self.assertEqual([], self.cache_entries())

    def test_a_dirty_tree_is_run_but_never_stored(self):
        self.touch_tracked()
        status, payload, _, _ = self.invoke()
        self.assertEqual(0, status)
        self.assertTrue(payload["dirty"])
        self.assertEqual(4, len(self.stub.calls()))
        self.assertEqual([], self.cache_entries())
        self.stub.forget()
        self.invoke()
        self.assertEqual(4, len(self.stub.calls()))

    def test_a_tree_changed_by_the_checks_themselves_is_not_stored(self):
        self.stub.plan({
            "validate.py": {"touch": str(self.repo / "written-by-a-check.txt")},
        })
        status, payload, _, _ = self.invoke()
        self.assertEqual(0, status)
        self.assertFalse(payload["dirty"])
        self.assertEqual([], self.cache_entries())

    def poison(self, mutate):
        """Store a green run, corrupt the entry, and run again."""

        green = self.invoke()[1]
        entry = self.cache_entries()[0]
        stored = json.loads(entry.read_text(encoding="utf-8"))
        mutate(stored)
        entry.write_text(json.dumps(stored), encoding="utf-8")
        self.stub.forget()
        status, payload, _, _ = self.invoke()
        self.assertEqual(0, status)
        self.assertEqual(4, len(self.stub.calls()))
        self.assertEqual([False] * 5, [r["cached"] for r in payload["commands"]])
        self.assertEqual(green["tree_identity"], payload["tree_identity"])

    def test_a_stored_overall_non_zero_exit_is_never_served(self):
        def mutate(stored):
            stored["exit"] = 1

        self.poison(mutate)

    def test_a_stored_red_command_is_never_served(self):
        def mutate(stored):
            stored["commands"][1]["exit_status"] = 1

        self.poison(mutate)

    def test_an_unreadable_entry_is_never_served(self):
        def mutate(stored):
            stored.clear()
            stored["kind"] = "something else entirely"

        self.poison(mutate)

    def test_a_red_run_does_not_overwrite_nothing_it_could_be_served_from(self):
        self.stub.plan({"run_tests.py": {"exit": 1}})
        status, _, _, _ = self.invoke()
        self.assertEqual(1, status)
        self.assertEqual([], self.cache_entries())
        self.stub.plan({})
        self.stub.forget()
        status, payload, _, _ = self.invoke()
        self.assertEqual(0, status)
        self.assertEqual(4, len(self.stub.calls()))
        self.assertEqual(1, len(self.cache_entries()))


class TestTextReport(RunRequiredCase):
    """A reader gets every check's own output, then the verdict."""

    def test_text_carries_each_check_its_own_output_and_the_verdict(self):
        status, payload, text, _ = self.invoke("--format", "text")
        self.assertEqual(0, status)
        self.assertIsNone(payload)
        self.assertEqual(4, text.count("stub-out"))
        for needle in ("tools/validate.py", "git diff --check", "exit 0"):
            self.assertIn(needle, text)

    def test_a_served_run_says_which_commands_it_did_not_run(self):
        self.invoke("--format", "text")
        status, _, text, _ = self.invoke("--format", "text")
        self.assertEqual(0, status)
        self.assertEqual(5, text.count("(cached)"))
        self.assertNotIn("stub-out", text)


class TestAReplayIsNotAnExecution(RunRequiredCase):
    """A memo may answer, but never in an execution's name.

    A gate's whole job is a run's one outside execution, and one was handed
    five green `(cached)` lines at a tree a unit had already proved. The
    memo was right, but the record it served called itself a run, so
    nothing downstream could tell the replay from the execution asked for.
    """

    def test_a_served_verdict_is_named_a_replay_and_not_a_run(self):
        fresh = self.invoke()[1]
        self.stub.forget()
        status, replay, _, _ = self.invoke()
        self.assertEqual(0, status)
        self.assertEqual([], self.stub.calls())
        self.assertEqual(RUN_KIND, fresh["kind"])
        self.assertEqual(REPLAY_KIND, replay["kind"])
        self.assertEqual(RECORD_KEYS, set(replay))
        self.assertEqual([True] * 5, [r["cached"] for r in replay["commands"]])

    def test_a_replay_says_so_on_the_line_every_reader_reads(self):
        executed = self.invoke("--format", "text")[2]
        status, _, replayed, _ = self.invoke("--format", "text")
        self.assertEqual(0, status)
        self.assertNotIn("replay", executed)
        self.assertIn("replay", replayed.splitlines()[-1])
        self.assertIn("--no-cache", replayed.splitlines()[-1])

    def test_asking_for_an_execution_runs_them_at_the_proved_tree(self):
        fresh = self.invoke()[1]
        self.stub.forget()
        status, again, _, _ = self.invoke("--no-cache")
        self.assertEqual(0, status)
        self.assertEqual(4, len(self.stub.calls()))
        self.assertEqual(RUN_KIND, again["kind"])
        self.assertEqual([False] * 5, [r["cached"] for r in again["commands"]])
        self.assertEqual(fresh["tree_identity"], again["tree_identity"])


class TestConsoleCodec(unittest.TestCase):
    """A report is bytes, not a favour the console's codec may grant."""

    # A glyph cp1252 has no room for, and the replacement character a
    # faithful decode leaves behind: neither may cost a reader the report.
    GLYPHS = chr(0x2605) + " and " + chr(0xFFFD) + chr(10)

    def render(self, form: str, raw: bytes):
        """Render one report into a cp1252 console; return what landed."""

        from tools import run_required

        record = {
            "argv": ["git", "diff", "--check"],
            "started_at": "2026-08-23T00:00:00Z",
            "ended_at": "2026-08-23T00:00:01Z",
            "exit_status": 0,
            "stdout_sha256": "0" * 64,
            "stderr_sha256": "1" * 64,
            "cached": False,
        }
        payload = {
            "kind": "required-check-run/v1",
            "repository_identity": "a" * 40,
            "tree_identity": "b" * 40,
            "dirty": False,
            "commands": [record],
            "exit": 0,
        }
        out, err = io.BytesIO(), io.BytesIO()
        console = io.TextIOWrapper(out, encoding="cp1252")
        console_err = io.TextIOWrapper(err, encoding="cp1252")
        with redirect_stdout(console), redirect_stderr(console_err):
            run_required.report([("whitespace", record, raw, b"")], payload, form)
        console.flush()
        console_err.flush()
        return out.getvalue(), err.getvalue()

    def test_a_text_report_survives_a_console_that_cannot_spell_it(self):
        landed, _ = self.render("text", self.GLYPHS.encode("utf-8"))
        self.assertIn(self.GLYPHS.encode("utf-8"), landed)
        self.assertIn(b"exit 0", landed)
        self.assertIn(b"git diff --check", landed)

    def test_a_json_record_survives_the_same_console(self):
        landed, echoed = self.render("json", self.GLYPHS.encode("utf-8"))
        self.assertIn(b'"required-check-run/v1"', landed)
        self.assertIn(self.GLYPHS.encode("utf-8"), echoed)


class TestTheSurfaceNamesTheRunner(unittest.TestCase):
    """`AGENTS.md` stays the owner of the five; it now also names the runner."""

    SURFACE = REPO_ROOT / "AGENTS.md"

    def surface(self) -> str:
        return self.SURFACE.read_text(encoding="utf-8")

    def test_the_surface_names_the_runner_and_still_lists_the_five(self):
        text = self.surface()
        self.assertIn("tools/run_required.py", text)
        for command in ("python tools/validate.py",
                        "python tools/run_tests.py",
                        "python tools/run_serial_compat.py",
                        "python install.py --dry-run",
                        "git diff --check"):
            self.assertIn(command, text)

    def test_the_surface_never_names_the_runtime_state_directory(self):
        pattern = re.compile(re.escape(runtime_directory_name()) + r"\b")
        self.assertIsNone(pattern.search(self.surface()))

    def test_the_surface_stays_inside_its_every_turn_budget(self):
        from tools.validate_support.packages import SURFACE_BUDGET, body_words

        self.assertLessEqual(
            body_words(self.surface()), SURFACE_BUDGET["AGENTS.md"]
        )


if __name__ == "__main__":
    unittest.main()
