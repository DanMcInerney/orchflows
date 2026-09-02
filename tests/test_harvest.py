"""Checks for scripts/harvest.py (and its scripts/harvest_cluster.py seam):
the deterministic harvest command -- window/selector slicing, covered-matcher
exclusion, greedy-union clustering, the improvement law rule 4 arithmetic,
the digest's own covered ``watermark``, and the ``--list-runs`` resolver
(including the writer/reader seam it crosses -- ``TestWriterReaderSeam``
drives the real ``tickets.py frame-open`` rather than a fixture). Never
touches the real sink: the sink env var is pointed at a fresh tempdir
for every case.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

from tests._repo_root import ROOT
# harvest.py imports its resolvers as `scripts.state_root` / `scripts.console`
# / `scripts.harvest_cluster` in-repo; neither name is importable from
# `tests/` alone, so put the repository root on the path first.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

HARVEST_PY = ROOT / "scripts" / "harvest.py"
_spec = importlib.util.spec_from_file_location("harvest", HARVEST_PY)
harvest = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(harvest)

# The real writer, for the one test (TestWriterReaderSeam) that has to drive
# it instead of a fixture -- see scripts.tickets_frame's frame-open.
from scripts import state_root, tickets

STATE_HOME_ENV_VAR = state_root.ENV_VAR


def _ts(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _friction_entry(ts, observed, expected, *, session=None, run=None,
                     host="claude-code", skill=None, ticket=None, project=None):
    return {
        "sink_convention": "orchflows.friction.v1",
        "ts": ts,
        "cwd": "C:/repo",
        "workspace": "C:/repo",
        "project": project,
        "project_source": "cwd" if project else "none",
        "git_rev": "abc1234",
        "host": host,
        "session": session,
        "skill": skill,
        "ticket": ticket,
        "run": run,
        "observed": observed,
        "expected": expected,
    }


def _frame_open(ts, run, workflow, goal_head):
    # Field spellings match the real writer (scripts/tickets_frame.py's
    # `_cmd_frame_open` and scripts/tickets_store.py's `SINK_CONVENTION`,
    # an int) -- F4: an invented spelling here is exactly what let F1 ship.
    return {
        "sink_convention": tickets.SINK_CONVENTION, "ts": ts,
        "project": None, "run": run, "ticket": None, "host": "claude-code",
        "session": None, "event": "frame-open", "workflow": workflow,
        "goal_head": goal_head,
    }


def _write_jsonl(path: Path, entries) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8", newline="\n") as handle:
        for entry in entries:
            handle.write(json.dumps(entry) + "\n")


class _HarvestTestCase(unittest.TestCase):
    """Base for every case: a synthetic sink, never the real one."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name).resolve()
        self.sink = self.tmp / "sink"
        patcher = mock.patch.dict(os.environ, {STATE_HOME_ENV_VAR: str(self.sink)})
        patcher.start()
        self.addCleanup(patcher.stop)

    def _friction_path(self, month="2026-08"):
        return self.sink / "friction" / f"{month}.jsonl"

    def _events_path(self, month="2026-08"):
        return self.sink / "events" / f"{month}.jsonl"

    def _covered_path(self):
        return self.sink / "improvement" / "covered.jsonl"

    def _out_path(self, name="digest.json"):
        return self.tmp / name

    def _run(self, argv):
        out_buf, err_buf = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out_buf), contextlib.redirect_stderr(err_buf):
            rc = harvest.main(argv)
        return rc, out_buf.getvalue(), err_buf.getvalue()

    def _harvest(self, argv, out_name="digest.json"):
        out = self._out_path(out_name)
        rc, stdout, stderr = self._run(["--out", str(out)] + list(argv))
        digest = json.loads(out.read_text(encoding="utf-8")) if out.is_file() else None
        return rc, digest, stdout, stderr

    @staticmethod
    def _observed(digest):
        return {m["observed"] for c in digest["clusters"] for m in c["members"]}


class TestEmptySinkAndWindow(_HarvestTestCase):
    def test_empty_sink_writes_a_zeroed_digest(self):
        rc, digest, stdout, _ = self._harvest([])
        self.assertEqual(0, rc)
        self.assertEqual([], digest["clusters"])
        self.assertEqual(0, digest["totals"]["friction_entries"])
        self.assertEqual(0, digest["totals"]["event_entries"])
        self.assertIn("0 clusters", stdout)

    def test_window_matching_nothing_still_reports_totals(self):
        _write_jsonl(self._friction_path(), [_friction_entry(_ts(datetime(2026, 8, 1, tzinfo=timezone.utc)), "o", "e")])
        rc, digest, _, _ = self._harvest(["--since", "2027-01-01T00:00:00Z"])
        self.assertEqual(0, rc)
        self.assertEqual([], digest["clusters"])
        self.assertEqual(1, digest["totals"]["friction_entries"])
        self.assertEqual(0, digest["totals"]["friction_selected"])

    def test_list_runs_over_empty_sink_prints_nothing(self):
        rc, stdout, _ = self._run(["--list-runs"])
        self.assertEqual(0, rc)
        self.assertEqual("", stdout)

    def test_missing_events_directory_is_tolerated_not_fatal(self):
        _write_jsonl(self._friction_path(), [_friction_entry(_ts(datetime(2026, 8, 1, tzinfo=timezone.utc)), "o", "e")])
        self.assertFalse(self._events_path().parent.is_dir())
        rc, digest, _, _ = self._harvest(["--since", "2026-01-01T00:00:00Z"])
        self.assertEqual(0, rc)
        self.assertEqual(0, digest["totals"]["event_entries"])


class TestSinceUntilEdges(_HarvestTestCase):
    def test_since_is_inclusive_and_until_is_exclusive(self):
        entries = [
            _friction_entry("2026-08-01T00:00:00Z", "at-since", "e"),
            _friction_entry("2026-08-15T00:00:00Z", "inside", "e"),
            _friction_entry("2026-09-01T00:00:00Z", "at-until", "e"),
        ]
        _write_jsonl(self._friction_path("2026-08"), entries[:2])
        _write_jsonl(self._friction_path("2026-09"), entries[2:])
        rc, digest, _, _ = self._harvest(["--since", "2026-08-01T00:00:00Z", "--until", "2026-09-01T00:00:00Z"])
        self.assertEqual(0, rc)
        self.assertEqual({"at-since", "inside"}, self._observed(digest))

    def test_before_since_is_excluded(self):
        entries = [
            _friction_entry("2026-07-31T23:59:59Z", "too-early", "e"),
            _friction_entry("2026-08-01T00:00:00Z", "on-time", "e"),
        ]
        _write_jsonl(self._friction_path("2026-07"), entries[:1])
        _write_jsonl(self._friction_path("2026-08"), entries[1:])
        rc, digest, _, _ = self._harvest(["--since", "2026-08-01T00:00:00Z"])
        self.assertEqual({"on-time"}, self._observed(digest))

    def test_since_relative_days_measures_from_now(self):
        fixed_now = datetime(2026, 8, 20, tzinfo=timezone.utc)
        entries = [
            _friction_entry(_ts(fixed_now - timedelta(days=10)), "too-old", "e"),
            _friction_entry(_ts(fixed_now - timedelta(days=3)), "recent", "e"),
        ]
        _write_jsonl(self._friction_path("2026-08"), entries)
        out = self._out_path()
        rc = harvest._run(["--out", str(out), "--since", "7d"], now=fixed_now)
        self.assertEqual(0, rc)
        digest = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual({"recent"}, self._observed(digest))


class TestOnDaysDisjointUnion(_HarvestTestCase):
    def test_two_on_days_select_nothing_between_them(self):
        entries = [
            _friction_entry("2026-08-01T12:00:00Z", "day1", "e"),
            _friction_entry("2026-08-02T12:00:00Z", "day2-between", "e"),
            _friction_entry("2026-08-03T12:00:00Z", "day3", "e"),
        ]
        _write_jsonl(self._friction_path(), entries)
        rc, digest, _, _ = self._harvest(["--on", "2026-08-01", "--on", "2026-08-03"])
        self.assertEqual(0, rc)
        self.assertEqual({"day1", "day3"}, self._observed(digest))

    def test_bad_on_date_is_a_usage_error(self):
        rc, _, stderr = self._run(["--out", str(self._out_path()), "--on", "not-a-date"])
        self.assertEqual(2, rc)
        self.assertIn("--on", stderr)


class TestDigestWatermark(_HarvestTestCase):
    """F2: the digest header's own `watermark` -- the newest entry
    timestamp this run actually read, or the window's own closing edge
    when nothing was read. `improvement --covered` is meant to carry this
    verbatim (SKILL.md's Frame law), so a covered line built from it must
    never claim a date past what this harvest saw.
    """

    def test_watermark_is_the_newest_selected_entry(self):
        entries = [
            _friction_entry("2026-08-01T00:00:00Z", "a", "e"),
            _friction_entry("2026-08-10T00:00:00Z", "b", "e"),
        ]
        _write_jsonl(self._friction_path(), entries)
        rc, digest, _, _ = self._harvest(["--since", "2026-01-01T00:00:00Z"])
        self.assertEqual("2026-08-10T00:00:00Z", digest["watermark"])

    def test_watermark_counts_a_selected_entry_even_when_covered_drops_it(self):
        # the entry is read (selected) before covered exclusion runs, so it
        # still dates the watermark despite never reaching a cluster.
        _write_jsonl(self._friction_path(), [
            _friction_entry("2026-08-01T00:00:00Z", "old failure marker", "e"),
        ])
        _write_jsonl(self._covered_path(), [{
            "matcher": ["failure marker"], "watermark": "2026-08-05T00:00:00Z",
        }])
        rc, digest, _, _ = self._harvest(["--since", "2026-01-01T00:00:00Z"])
        self.assertEqual(1, digest["totals"]["covered_dropped"])
        self.assertEqual(0, digest["totals"]["clustered_entries"])
        self.assertEqual("2026-08-01T00:00:00Z", digest["watermark"])

    def test_empty_selection_with_a_bounded_until_uses_the_window_end(self):
        rc, digest, _, _ = self._harvest([
            "--since", "2026-01-01T00:00:00Z", "--until", "2026-06-01T00:00:00Z",
        ])
        self.assertEqual(0, digest["totals"]["friction_selected"])
        self.assertEqual("2026-06-01T00:00:00Z", digest["watermark"])

    def test_empty_selection_with_an_on_day_uses_the_days_end(self):
        rc, digest, _, _ = self._harvest(["--on", "2026-08-01"])
        self.assertEqual(0, digest["totals"]["friction_selected"])
        self.assertEqual("2026-08-02T00:00:00Z", digest["watermark"])

    def test_empty_selection_with_an_unbounded_window_is_null(self):
        rc, digest, _, _ = self._harvest(["--since", "2026-01-01T00:00:00Z"])
        self.assertEqual(0, digest["totals"]["friction_selected"])
        self.assertIsNone(digest["watermark"])


class TestCoveredMatcherExclusion(_HarvestTestCase):
    def test_at_or_before_watermark_is_dropped_after_survives(self):
        entries = [
            _friction_entry("2026-08-01T00:00:00Z", "old failure marker", "e"),
            _friction_entry("2026-08-10T00:00:00Z", "new failure marker", "e"),
        ]
        _write_jsonl(self._friction_path(), entries)
        _write_jsonl(self._covered_path(), [{
            "matcher": ["failure marker"], "watermark": "2026-08-05T00:00:00Z",
        }])
        rc, digest, _, _ = self._harvest(["--since", "2026-01-01T00:00:00Z"])
        self.assertEqual(1, digest["totals"]["covered_dropped"])
        self.assertEqual({"new failure marker"}, self._observed(digest))

    def test_non_matching_pattern_never_drops_anything(self):
        _write_jsonl(self._friction_path(), [_friction_entry("2026-08-01T00:00:00Z", "unrelated text", "e")])
        _write_jsonl(self._covered_path(), [{
            "matcher": ["nothing-matches-this"], "watermark": "2026-09-01T00:00:00Z",
        }])
        rc, digest, _, _ = self._harvest(["--since", "2026-01-01T00:00:00Z"])
        self.assertEqual(0, digest["totals"]["covered_dropped"])
        self.assertEqual({"unrelated text"}, self._observed(digest))


class TestDefaultSinceFromCoveredWatermark(_HarvestTestCase):
    def test_no_selector_defaults_since_to_the_newest_watermark(self):
        _write_jsonl(self._friction_path("2026-07"), [_friction_entry("2026-07-01T00:00:00Z", "before-watermark", "e")])
        _write_jsonl(self._friction_path("2026-08"), [_friction_entry("2026-08-15T00:00:00Z", "after-watermark", "e")])
        _write_jsonl(self._covered_path(), [{"matcher": ["no-such-text"], "watermark": "2026-08-01T00:00:00Z"}])
        rc, digest, _, _ = self._harvest([])
        self.assertTrue(digest["window"]["since_defaulted_from_covered_watermark"])
        self.assertEqual({"after-watermark"}, self._observed(digest))

    def test_no_covered_file_at_all_means_everything(self):
        _write_jsonl(self._friction_path("2020-01"), [_friction_entry("2020-01-01T00:00:00Z", "ancient", "e")])
        rc, digest, _, _ = self._harvest([])
        self.assertFalse(digest["window"]["since_defaulted_from_covered_watermark"])
        self.assertEqual(1, digest["totals"]["friction_selected"])

    def test_one_explicit_selector_suppresses_the_default(self):
        _write_jsonl(self._covered_path(), [{"matcher": ["x"], "watermark": "2026-08-01T00:00:00Z"}])
        _write_jsonl(self._friction_path("2020-01"), [_friction_entry("2020-01-01T00:00:00Z", "o", "e", run="R9")])
        rc, digest, _, _ = self._harvest(["--run", "R9"])
        self.assertFalse(digest["window"]["since_defaulted_from_covered_watermark"])
        self.assertEqual(1, digest["totals"]["friction_selected"])


class TestSelectorComposition(_HarvestTestCase):
    def test_repeated_run_flag_ors_together(self):
        entries = [
            _friction_entry("2026-08-01T00:00:00Z", "a", "e", run="R1"),
            _friction_entry("2026-08-01T00:00:00Z", "b", "e", run="R2"),
            _friction_entry("2026-08-01T00:00:00Z", "c", "e", run="R3"),
        ]
        _write_jsonl(self._friction_path(), entries)
        rc, digest, _, _ = self._harvest(["--since", "2026-01-01T00:00:00Z", "--run", "R1", "--run", "R3"])
        self.assertEqual({"a", "c"}, self._observed(digest))

    def test_different_selector_kinds_and_together(self):
        project = {"root": "C:/r", "origin": None, "name": "proj-a"}
        entries = [
            _friction_entry("2026-08-01T00:00:00Z", "a", "e", host="claude-code", project=project),
            _friction_entry("2026-08-01T00:00:00Z", "b", "e", host="codex", project=project),
        ]
        _write_jsonl(self._friction_path(), entries)
        rc, digest, _, _ = self._harvest([
            "--since", "2026-01-01T00:00:00Z", "--project", "proj-a", "--host", "claude-code",
        ])
        self.assertEqual({"a"}, self._observed(digest))

    def test_workflow_selector_resolves_through_frame_open_events(self):
        _write_jsonl(self._friction_path(), [
            _friction_entry("2026-08-01T00:00:00Z", "a", "e", run="R1"),
            _friction_entry("2026-08-01T00:00:00Z", "b", "e", run="R2"),
        ])
        _write_jsonl(self._events_path(), [
            _frame_open("2026-08-01T00:00:00Z", "R1", "self-improve", "Deliver the thing"),
            _frame_open("2026-08-01T00:00:00Z", "R2", "other-workflow", "Do something else"),
        ])
        rc, digest, _, _ = self._harvest(["--since", "2026-01-01T00:00:00Z", "--workflow", "self-improve"])
        self.assertEqual({"a"}, self._observed(digest))


class TestClusterDeterminism(_HarvestTestCase):
    def test_same_input_yields_the_same_digest_modulo_generated_at(self):
        entries = [
            _friction_entry(f"2026-08-0{i}T00:00:00Z", f"error at file{i}.py line {i}", "fix it", session=f"s{i}")
            for i in range(1, 4)
        ]
        _write_jsonl(self._friction_path(), entries)
        rc1, d1, _, _ = self._harvest(["--since", "2026-01-01T00:00:00Z"], out_name="d1.json")
        rc2, d2, _, _ = self._harvest(["--since", "2026-01-01T00:00:00Z"], out_name="d2.json")
        self.assertEqual(0, rc1)
        self.assertEqual(0, rc2)
        self.assertNotEqual(d1["generated_at"], None)
        d1.pop("generated_at")
        d2.pop("generated_at")
        self.assertEqual(d1, d2)


class TestClusteringAndRecurrence(_HarvestTestCase):
    def test_paths_normalize_regardless_of_slash_direction(self):
        entries = [
            _friction_entry("2026-08-01T00:00:00Z", "failed at scripts/foo.py line 3", "fix", session="s1"),
            _friction_entry("2026-08-02T00:00:00Z", "failed at scripts\\foo.py line 3", "fix", session="s2"),
        ]
        _write_jsonl(self._friction_path(), entries)
        rc, digest, _, _ = self._harvest(["--since", "2026-01-01T00:00:00Z"])
        self.assertEqual(1, len(digest["clusters"]))
        self.assertEqual(2, digest["clusters"][0]["counts"]["members"])

    def test_three_members_alone_qualify_recurrence(self):
        entries = [
            _friction_entry(f"2026-08-0{i}T00:00:00Z", "same failure pattern here", "same fix", session="s1", run="R", host="h")
            for i in range(1, 4)
        ]
        _write_jsonl(self._friction_path(), entries)
        rc, digest, _, _ = self._harvest(["--since", "2026-01-01T00:00:00Z"])
        cluster = digest["clusters"][0]
        self.assertEqual(3, cluster["counts"]["members"])
        self.assertTrue(cluster["recurrence_met"])

    def test_two_members_one_session_does_not_qualify(self):
        entries = [
            _friction_entry("2026-08-01T00:00:00Z", "same failure pattern here", "same fix", session="s1"),
            _friction_entry("2026-08-02T00:00:00Z", "same failure pattern here", "same fix", session="s1"),
        ]
        _write_jsonl(self._friction_path(), entries)
        rc, digest, _, _ = self._harvest(["--since", "2026-01-01T00:00:00Z"])
        cluster = digest["clusters"][0]
        self.assertEqual(2, cluster["counts"]["members"])
        self.assertFalse(cluster["recurrence_met"])

    def test_two_distinct_sessions_qualify_with_two_members(self):
        entries = [
            _friction_entry("2026-08-01T00:00:00Z", "same failure pattern here", "same fix", session="s1"),
            _friction_entry("2026-08-02T00:00:00Z", "same failure pattern here", "same fix", session="s2"),
        ]
        _write_jsonl(self._friction_path(), entries)
        rc, digest, _, _ = self._harvest(["--since", "2026-01-01T00:00:00Z"])
        cluster = digest["clusters"][0]
        self.assertTrue(cluster["recurrence_met"])

    def test_two_distinct_run_host_pairs_without_session_qualify(self):
        entries = [
            _friction_entry("2026-08-01T00:00:00Z", "same failure pattern here", "same fix", run="R1", host="h1"),
            _friction_entry("2026-08-02T00:00:00Z", "same failure pattern here", "same fix", run="R2", host="h2"),
        ]
        _write_jsonl(self._friction_path(), entries)
        rc, digest, _, _ = self._harvest(["--since", "2026-01-01T00:00:00Z"])
        cluster = digest["clusters"][0]
        self.assertEqual(0, cluster["counts"]["distinct_sessions"])
        self.assertEqual(2, cluster["counts"]["distinct_run_host_pairs"])
        self.assertTrue(cluster["recurrence_met"])

    def test_dissimilar_entries_land_in_separate_clusters(self):
        entries = [
            _friction_entry("2026-08-01T00:00:00Z", "completely unrelated alpha topic", "e", session="s1"),
            _friction_entry("2026-08-02T00:00:00Z", "an entirely different beta subject", "e", session="s2"),
        ]
        _write_jsonl(self._friction_path(), entries)
        rc, digest, _, _ = self._harvest(["--since", "2026-01-01T00:00:00Z"])
        self.assertEqual(2, len(digest["clusters"]))

    def test_clusters_are_ranked_by_member_count_descending(self):
        entries = [
            _friction_entry("2026-08-01T00:00:00Z", "solo unrelated report", "e", session="only"),
            _friction_entry("2026-08-02T00:00:00Z", "repeated shared incident", "e", session="s1"),
            _friction_entry("2026-08-03T00:00:00Z", "repeated shared incident", "e", session="s2"),
        ]
        _write_jsonl(self._friction_path(), entries)
        rc, digest, _, _ = self._harvest(["--since", "2026-01-01T00:00:00Z"])
        sizes = [c["counts"]["members"] for c in digest["clusters"]]
        self.assertEqual(sorted(sizes, reverse=True), sizes)
        self.assertEqual(2, sizes[0])

    def test_members_beyond_the_cap_are_omitted_and_counted(self):
        base = datetime(2026, 8, 1, tzinfo=timezone.utc)
        entries = [
            _friction_entry(_ts(base + timedelta(seconds=i)), "identical repeated failure text", "e", session=f"s{i}")
            for i in range(15)
        ]
        _write_jsonl(self._friction_path(), entries)
        rc, digest, _, _ = self._harvest(["--since", "2026-01-01T00:00:00Z"])
        cluster = digest["clusters"][0]
        self.assertEqual(15, cluster["counts"]["members"])
        self.assertEqual(12, len(cluster["members"]))
        self.assertEqual(3, cluster["omitted"])

    def test_matcher_draft_regexes_match_the_entries_that_produced_them(self):
        entries = [
            _friction_entry("2026-08-01T00:00:00Z", "timeout waiting for reply", "e", session="s1"),
            _friction_entry("2026-08-02T00:00:00Z", "timeout waiting for reply", "e", session="s2"),
        ]
        _write_jsonl(self._friction_path(), entries)
        rc, digest, _, _ = self._harvest(["--since", "2026-01-01T00:00:00Z"])
        cluster = digest["clusters"][0]
        self.assertTrue(cluster["matcher_draft"])
        text = "timeout waiting for reply e"
        for pattern in cluster["matcher_draft"]:
            self.assertRegex(text, pattern)


class TestListRuns(_HarvestTestCase):
    def test_run_with_frame_open_reports_workflow_and_goal(self):
        _write_jsonl(self._friction_path(), [_friction_entry("2026-08-01T00:00:00Z", "o", "e", run="R1")])
        _write_jsonl(self._events_path(), [_frame_open("2026-08-01T00:00:00Z", "R1", "self-improve", "Deliver the thing")])
        rc, stdout, _ = self._run(["--list-runs", "--since", "2026-01-01T00:00:00Z"])
        self.assertEqual(0, rc)
        fields = stdout.strip().splitlines()[0].split("\t")
        self.assertEqual(["R1", "self-improve", "Deliver the thing"], fields[:3])
        self.assertEqual("1", fields[5])  # friction count
        self.assertEqual("1", fields[6])  # event count

    def test_run_without_frame_open_reports_null_workflow_and_goal(self):
        _write_jsonl(self._friction_path(), [_friction_entry("2026-08-01T00:00:00Z", "o", "e", run="R2")])
        rc, stdout, _ = self._run(["--list-runs", "--since", "2026-01-01T00:00:00Z"])
        self.assertEqual(0, rc)
        fields = stdout.strip().splitlines()[0].split("\t")
        self.assertEqual(["R2", "null", "null"], fields[:3])

    def test_newest_run_by_latest_timestamp_lists_first(self):
        _write_jsonl(self._friction_path("2026-07"), [_friction_entry("2026-07-01T00:00:00Z", "o", "e", run="OLD")])
        _write_jsonl(self._friction_path("2026-08"), [_friction_entry("2026-08-15T00:00:00Z", "o", "e", run="NEW")])
        rc, stdout, _ = self._run(["--list-runs", "--since", "2026-01-01T00:00:00Z"])
        lines = stdout.strip().splitlines()
        self.assertEqual("NEW", lines[0].split("\t")[0])
        self.assertEqual("OLD", lines[1].split("\t")[0])

    def test_list_runs_rejects_out(self):
        rc, _, stderr = self._run(["--list-runs", "--out", str(self._out_path())])
        self.assertEqual(2, rc)


class TestWriterReaderSeam(_HarvestTestCase):
    """F4: the seam itself, not a fixture standing in for it. Drives the
    real writer -- `tickets.py frame-open` (scripts/tickets_frame.py), the
    way a driver actually invokes it -- against this test's own temp sink,
    then reads the same sink back with harvest's real `--list-runs`. A
    fixture that invents the reader's spelling cannot fail when the
    writer's spelling drifts (that is exactly how F1 shipped green); this
    test is built precisely so it can, on either side.
    """

    def setUp(self):
        super().setUp()
        worktrees_patch = mock.patch.dict(
            os.environ, {"ORCHFLOWS_WORKTREES_HOME": str(self.tmp / "worktrees")},
        )
        worktrees_patch.start()
        self.addCleanup(worktrees_patch.stop)
        self.goal_file = self.tmp / "goal.md"
        self.goal_file.write_text("Deliver the thing.\nsecond line.\n", encoding="utf-8")

    def _real_frame_open(self, run, workflow):
        # Workspace establishment is the one side effect this seam does not
        # own -- mocked exactly as tests/test_events.py mocks it, so this
        # stays a test of the frame-open/harvest seam and not of the
        # workspace machinery underneath it.
        facade = tickets._tickets_dispatch_facade_module
        with mock.patch.object(
            facade, "_workspace_establish",
            side_effect=lambda *_: {"establish": {"workspace_path": str(self.tmp)}},
        ), mock.patch.object(
            facade, "_workspace_prepare", return_value={"outcome": "skipped"},
        ):
            answer = tickets._dispatch([
                "frame-open", run, "--goal-file", str(self.goal_file),
                "--workflow", workflow,
            ])
        self.assertNotIn("error", answer, answer)
        return answer["frame_open"]

    def test_real_writer_and_reader_agree_on_workflow_and_goal(self):
        self._real_frame_open("R1", "self-improve")
        rc, stdout, _ = self._run(["--list-runs", "--since", "2020-01-01T00:00:00Z"])
        self.assertEqual(0, rc)
        fields = stdout.strip().splitlines()[0].split("\t")
        self.assertEqual(["R1", "self-improve", "Deliver the thing."], fields[:3])


class TestCliUsageErrors(_HarvestTestCase):
    def test_out_is_required_unless_list_runs(self):
        rc, _, stderr = self._run([])
        self.assertEqual(2, rc)

    def test_bad_since_is_a_usage_error(self):
        rc, _, stderr = self._run(["--out", str(self._out_path()), "--since", "not-a-timestamp"])
        self.assertEqual(2, rc)

    def test_bad_until_is_a_usage_error(self):
        rc, _, stderr = self._run(["--out", str(self._out_path()), "--until", "not-a-timestamp"])
        self.assertEqual(2, rc)


class TestWindowsPathHandling(_HarvestTestCase):
    def test_out_path_several_directories_deep_is_created(self):
        _write_jsonl(self._friction_path(), [_friction_entry("2026-08-01T00:00:00Z", "o", "e")])
        nested = self.tmp / "nested" / "deeper" / "digest.json"
        rc, stdout, _ = self._run(["--out", str(nested), "--since", "2026-01-01T00:00:00Z"])
        self.assertEqual(0, rc)
        self.assertTrue(nested.is_file())
        json.loads(nested.read_text(encoding="utf-8"))  # parses cleanly

    def test_sink_directories_resolve_under_a_windows_style_state_home(self):
        # The sink env var itself is a Windows path with backslashes on
        # this host; state_root.py resolves it via pathlib either way, and
        # this re-affirms harvest.py never hand-joins one with "/".
        _write_jsonl(self._friction_path(), [_friction_entry("2026-08-01T00:00:00Z", "o", "e")])
        rc, digest, _, _ = self._harvest(["--since", "2026-01-01T00:00:00Z"])
        self.assertEqual(0, rc)
        self.assertEqual(1, digest["totals"]["friction_selected"])


if __name__ == "__main__":
    unittest.main()
