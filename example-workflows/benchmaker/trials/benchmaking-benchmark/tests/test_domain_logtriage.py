import contextlib
import importlib.util
import io
import json
import random
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
import unittest.mock
from pathlib import Path

BB = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BB))

from metabench.domains import logtriage as lt  # noqa: E402

FIX = Path(__file__).resolve().parent / "fixtures" / "logtriage"
SUBJECT = BB / "meta-tasks" / "logtriage-llm" / "subject" / "agent"
PUBLIC = ["900000001", "900000003", "900000005", "900000007"]
ANSI = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]|\x1b")
# id -> (log lines, 1-based chunk spans in the full log, text on the first and last chunk line)
EXPECTED = {
    "900000001": (51, [(36, 46)], "test_render_table_width", "test_render.py:31: AssertionError"),
    "900000002": (37, [(32, 32)], "E501 line too long", "E501 line too long"),
    "900000003": (52, [(42, 46)], "--- FAIL: TestRouteTimeout", "internal/router\t0.452s"),
    "900000004": (60, [(22, 24)], "# github.com/acme/gateway/internal/router", "argument to Mount"),
    "900000005": (37, [(22, 25), (29, 32)], "Posting.java:[42,31]", "location: class acme.ledger.Money"),
    "900000006": (57, [(28, 39)], "Tests run: 5, Failures: 1", "reconcilesAcrossCurrencies:73 Expected"),
    "900000007": (58, [(26, 29)], "not ok restarts service", "systemctl: command not found"),
    "900000008": (22, [(16, 18)], "shellcheck: deploy.sh:31:7", "2 scripts have issues"),
}


def load_agent():
    spec = importlib.util.spec_from_file_location("logtriage_run_agent", SUBJECT / "run_agent.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


agent = load_agent()


def read_log(log_id: str) -> str:
    path = next((FIX / "source" / "logs").rglob(f"{log_id}.log"))
    return path.read_bytes().decode("utf-8")


def workspace_with(root: Path, text: str, name: str = "ws") -> Path:
    ws = root / name
    ws.mkdir(exist_ok=True)
    (ws / "build.log").write_bytes(text.encode("utf-8"))
    return ws


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.store = Path(cls.tmp.name)
        lt.build_split(FIX / "source", lt.material_dir(cls.store), PUBLIC, attribution="Synthetic fixture, CC BY 4.0.")
        lt.configure(cls.store)

    @classmethod
    def tearDownClass(cls):
        lt.configure(None)
        cls.tmp.cleanup()

    def setUp(self):
        self.work = tempfile.TemporaryDirectory()
        self.addCleanup(self.work.cleanup)
        self.root = Path(self.work.name)

    def recognize_text(self, text: str):
        return lt.recognize(workspace_with(self.root, text), "")

    def instance(self, log_id: str) -> dict:
        found = self.recognize_text(read_log(log_id))
        self.assertIsNotNone(found, log_id)
        return found


def out(span, summary="s") -> dict:
    return {lt.OUTPUT: lt._dump(span, summary)}


class LineConvention(unittest.TestCase):
    def test_line_ends_and_final_break(self):
        self.assertEqual(lt.delivered_lines("a\r\nb\nc\rd\n"), ["a", "b", "c", "d"])
        self.assertEqual(lt.delivered_lines("a\n\n"), ["a", ""])
        self.assertEqual(lt.delivered_lines("a"), ["a"])
        self.assertEqual(lt.delivered_lines(""), [])
        self.assertEqual(lt.delivered_lines("\n"), [""])

    def test_subject_numbers_lines_the_same_way(self):
        for text in ("a\r\nb\nc\rd\n", "x\n\n\ny", "", "\r\r\n", read_log("900000008"), read_log("900000001")):
            self.assertEqual(agent.split_lines(text), lt.delivered_lines(text))


class ChunkLocation(unittest.TestCase):
    def test_every_fixture_chunk_is_found_contiguously(self):
        for entry in lt.load_entries(FIX / "source"):
            count, spans, first, last = EXPECTED[entry["id"]]
            lines = lt.delivered_lines(entry["path"].read_bytes().decode("utf-8"))
            found = lt.chunk_spans(lines, entry["chunk"])
            self.assertEqual(len(lines), count, entry["id"])
            self.assertEqual([(a + 1, b + 1) for a, b in found], spans, entry["id"])
            self.assertIn(first, ANSI.sub("", lines[found[0][0]]))
            self.assertIn(last, ANSI.sub("", lines[found[0][1]]))

    def test_chunk_that_lost_escapes_and_angle_brackets_still_matches(self):
        entry = next(e for e in lt.load_entries(FIX / "source") if e["id"] == "900000001")
        self.assertNotIn("\x1b", entry["chunk"])
        self.assertNotIn("<built-in", entry["chunk"])
        self.assertIn("<built-in", read_log("900000001"))
        self.assertEqual(len(lt.chunk_spans(lt.delivered_lines(read_log("900000001")), entry["chunk"])), 1)

    def test_absent_or_empty_chunk(self):
        lines = lt.delivered_lines(read_log("900000003"))
        self.assertEqual(lt.chunk_spans(lines, "this text is not in the log"), [])
        self.assertEqual(lt.chunk_spans(lines, "  \n ... "), [])

    def test_labels_load_in_the_archive_structure(self):
        entries = lt.load_entries(FIX / "source")
        self.assertEqual(len(entries), 8)
        one = next(e for e in entries if e["id"] == "900000003")
        self.assertEqual((one["language"], one["repo"], one["category"]), ("Go", "acme/gateway", "0"))
        self.assertEqual(one["log"], "Go/acme@gateway/failed/900000003.log")


class Recognition(Base):
    def test_whole_logs_public_and_held_out(self):
        for log_id, (count, spans, _, _) in EXPECTED.items():
            inst = self.instance(log_id)
            self.assertEqual(inst["n_lines"], count)
            self.assertEqual([tuple(s) for s in inst["spans"]], spans)
            self.assertEqual(inst["split"], "public" if log_id in PUBLIC else "held-out")
            self.assertEqual(inst["id"], log_id)

    def test_ansi_stripped_copy_and_other_line_ends(self):
        text = read_log("900000006")
        stripped = "\n".join(ANSI.sub("", line) for line in lt.delivered_lines(text)) + "\n"
        self.assertEqual([tuple(s) for s in self.recognize_text(stripped)["spans"]], [(28, 39)])
        cr_only = "\r".join(lt.delivered_lines(text))
        self.assertEqual(self.recognize_text(cr_only)["n_lines"], 57)

    def test_excerpt_numbers_lines_from_its_own_start(self):
        lines = lt.delivered_lines(read_log("900000006"))
        inst = self.recognize_text("\n".join(lines[19:50]) + "\n")
        self.assertEqual(inst["n_lines"], 31)
        self.assertEqual([tuple(s) for s in inst["spans"]], [(9, 20)])
        self.assertEqual(inst["id"], "900000006")

    def test_leading_and_trailing_blank_lines_are_ignored(self):
        lines = lt.delivered_lines(read_log("900000003"))
        inst = self.recognize_text("\n\n" + "\n".join(lines[10:]) + "\n\n\n")
        self.assertEqual([tuple(s) for s in inst["spans"]], [(2 + 42 - 10, 2 + 46 - 10)])

    def test_cut_chunk_is_uncovered(self):
        lines = lt.delivered_lines(read_log("900000006"))
        self.assertIsNone(self.recognize_text("\n".join(lines[:35]) + "\n"))
        self.assertIsNone(self.recognize_text("\n".join(lines[30:]) + "\n"))
        self.assertIsNotNone(self.recognize_text("\n".join(lines[27:39]) + "\n"))

    def test_partly_covered_repeated_chunk_keeps_the_occurrence_inside(self):
        lines = lt.delivered_lines(read_log("900000005"))
        inst = self.recognize_text("\n".join(lines[20:26]) + "\n")
        self.assertEqual([tuple(s) for s in inst["spans"]], [(2, 5)])

    def test_prefilter_words_skip_dot_runs_and_tolerate_hidden_words(self):
        self.assertEqual(lt._probes(["." * 40, "ok", "-" * 30]), [])
        words = lt._probes(lt.delivered_lines(read_log("900000006")))
        self.assertTrue(1 <= len(words) <= 5 and all(re.search(rb"[A-Za-z]", w) for w in words))
        text = read_log("900000006")
        real = [b"acme.ledger.ReconcileTest.reconcilesAcrossCurrencies", b"maven-surefire-plugin:2.22.2:test"]
        with unittest.mock.patch.object(lt, "_probes", lambda lines: [*real, b"ansi-split-word-not-in-the-log"]):
            self.assertIsNotNone(self.recognize_text(text))
        with unittest.mock.patch.object(lt, "_probes", lambda lines: [b"word-that-is-nowhere-1", b"word-that-is-nowhere-2"]):
            self.assertIsNone(self.recognize_text(text))

    def test_chunk_repeated_too_often_is_uncovered(self):
        with unittest.mock.patch.object(lt, "MAX_OCCURRENCES", 1):
            self.assertIsNone(self.recognize_text(read_log("900000005")))
            self.assertIsNotNone(self.recognize_text(read_log("900000006")))

    def test_unknown_missing_or_empty_input(self):
        self.assertIsNone(self.recognize_text("Run 4 of 9\nnothing like a fixture log\n"))
        self.assertIsNone(self.recognize_text(""))
        self.assertIsNone(self.recognize_text("\n\n  \n"))
        self.assertIsNone(lt.recognize(self.root / "empty-dir", ""))


class OracleAndChecker(Base):
    def test_oracle_is_valid_for_every_fixture(self):
        for log_id, (_, spans, _, _) in EXPECTED.items():
            inst = self.instance(log_id)
            outputs = lt.solve(inst)
            self.assertEqual(len(outputs), len(spans))
            for files in outputs:
                self.assertEqual(lt.check(inst, files)["label"], "valid", log_id)

    def test_labels(self):
        inst = self.instance("900000006")   # chunk 28-39 of 57 lines
        label = lambda span: lt.check(inst, out(span))["label"]
        self.assertEqual(label((28, 39)), "valid")
        self.assertEqual(label((26, 41)), "suboptimal")      # edges within two lines
        self.assertEqual(label((30, 39)), "suboptimal")
        self.assertEqual(label((28, 49)), "suboptimal")      # overlap 12/22
        self.assertEqual(label((1, 57)), "invalid")          # dump-all earns nothing
        self.assertEqual(label((1, 20)), "invalid")
        self.assertEqual(label((40, 52)), "invalid")
        self.assertEqual(label((20, 29)), "invalid")         # overlap 2/20
        self.assertEqual(label((30, 20)), "invalid")
        self.assertEqual(label((0, 12)), "invalid")
        self.assertEqual(label((50, 80)), "invalid")

    def test_edges_close_to_a_short_chunk_are_suboptimal(self):
        inst = self.instance("900000002")   # a single line, 32 of 37
        label = lambda span: lt.check(inst, out(span))["label"]
        self.assertEqual(label((32, 32)), "valid")
        self.assertEqual(label((30, 34)), "suboptimal")
        self.assertEqual(label((33, 33)), "suboptimal")
        self.assertEqual(label((29, 35)), "invalid")
        self.assertEqual(label((34, 36)), "invalid")

    def test_every_occurrence_is_accepted(self):
        inst = self.instance("900000005")
        for span in ((22, 25), (29, 32)):
            self.assertEqual(lt.check(inst, out(span))["label"], "valid")
        self.assertEqual(lt.check(inst, out((25, 29)))["label"], "invalid")

    def test_unparseable_outputs(self):
        inst = self.instance("900000003")
        bad = [None, b"", b"not json", b"[1, 2]", b'{"summary": "x"}', b'{"failure_lines": [1]}',
               b'{"failure_lines": [1, 2, 3]}', b'{"failure_lines": ["1", "2"]}', b'{"failure_lines": [1.0, 2]}',
               b'{"failure_lines": [true, 2]}', b'{"failure_lines": 5}', b"\xff\xfe"]
        for raw in bad:
            files = {} if raw is None else {lt.OUTPUT: raw}
            self.assertEqual(lt.check(inst, files)["label"], "unparseable", raw)

    def test_summary_problems_are_noted_without_changing_the_label(self):
        inst = self.instance("900000003")
        result = lt.check(inst, {lt.OUTPUT: b'{"failure_lines": [42, 46]}'})
        self.assertEqual(result["label"], "valid")
        self.assertTrue(any("summary" in r for r in result["reasons"]))

    def test_apply_writes_outputs(self):
        lt.apply(self.root / "w", {lt.OUTPUT: b"{}", "sub/x.txt": b"x"})
        self.assertEqual((self.root / "w" / "sub" / "x.txt").read_bytes(), b"x")

    def test_labeled_rows_agree_with_the_checker(self):
        want = {"valid": {"valid"}, "invalid": {"invalid", "unparseable"}, "lenient": {"suboptimal"}}
        for log_id in EXPECTED:
            inst = self.instance(log_id)
            rows = lt.labeled(inst)
            self.assertEqual({r["label"] for r in rows} - {"valid", "invalid", "lenient"}, set())
            for row in rows:
                self.assertIn(lt.check(inst, row["files"])["label"], want[row["label"]], (log_id, row["kind"]))
            kinds = {r["kind"] for r in rows}
            self.assertLessEqual({"json-variant", "not-json", "wrong-schema"}, kinds)
            self.assertEqual(sum(r["kind"] == "alternate-occurrence" for r in rows), len(inst["spans"]) - 1)

    def test_labeled_rows_cover_wrong_ranges_and_lenient_variants(self):
        rows = lt.labeled(self.instance("900000006"))
        kinds = {(r["label"], r["kind"]) for r in rows}
        self.assertIn(("invalid", "dump-all"), kinds)
        self.assertIn(("invalid", "after"), kinds)
        self.assertIn(("lenient", "valid-lenient"), kinds)
        exact = {r["files"][lt.OUTPUT] for r in rows if r["label"] == "valid"}
        self.assertEqual(len(exact), 5)
        for row in rows:
            doc = json.loads(row["files"][lt.OUTPUT]) if row["kind"] not in ("not-json",) else {}
            if "failure_lines" in doc:
                self.assertTrue(1 <= doc["failure_lines"][0] <= doc["failure_lines"][1] <= 57)


class Heuristics(Base):
    def run_heuristic(self, name: str, log_id: str):
        ws = workspace_with(self.root, read_log(log_id))
        files = lt.HEURISTICS[name](ws, "")
        return self.instance(log_id), files

    def test_tail_50(self):
        inst, files = self.run_heuristic("tail_50", "900000003")      # 52 lines
        self.assertEqual(json.loads(files[lt.OUTPUT])["failure_lines"], [3, 52])
        self.assertEqual(lt.check(inst, files)["label"], "invalid")
        inst, files = self.run_heuristic("tail_50", "900000008")      # 22 lines
        self.assertEqual(json.loads(files[lt.OUTPUT])["failure_lines"], [1, 22])

    def test_dump_all_earns_nothing(self):
        for log_id in EXPECTED:
            inst, files = self.run_heuristic("dump_all", log_id)
            self.assertEqual(json.loads(files[lt.OUTPUT])["failure_lines"], [1, inst["n_lines"]])
            self.assertEqual(lt.check(inst, files)["label"], "invalid", log_id)

    def test_grep_first_and_last_error(self):
        inst, files = self.run_heuristic("grep_first_error", "900000008")
        self.assertEqual(json.loads(files[lt.OUTPUT])["failure_lines"], [14, 18])   # first match is line 16
        self.assertEqual(lt.check(inst, files)["label"], "suboptimal")
        inst, files = self.run_heuristic("grep_last_error", "900000008")
        self.assertEqual(json.loads(files[lt.OUTPUT])["failure_lines"], [15, 19])   # last match is line 17
        inst, early = self.run_heuristic("grep_first_error", "900000001")           # "test_errors.py" matches long before the failure
        self.assertEqual(lt.check(inst, early)["label"], "invalid")

    def test_no_match_falls_back_to_the_last_line(self):
        ws = workspace_with(self.root, "all good\nstill fine\n")
        files = lt.HEURISTICS["grep_first_error"](ws, "")
        self.assertEqual(json.loads(files[lt.OUTPUT])["failure_lines"], [2, 2])


class Defects(Base):
    def test_shifted_moves_past_the_chunk(self):
        for log_id, (_, spans, _, _) in EXPECTED.items():
            inst = self.instance(log_id)
            for seed in range(8):
                files = lt.DEFECTS["shifted"](inst, random.Random(seed))
                got = tuple(json.loads(files[lt.OUTPUT])["failure_lines"])
                self.assertNotIn(got, spans[:1])
                if len(spans) == 1:    # a repeated chunk can be hit by chance
                    label = lt.check(inst, files)["label"]
                    self.assertNotEqual(label, "valid", (log_id, seed, got))
                    if spans[0][1] - spans[0][0] >= 2:
                        self.assertEqual(label, "invalid", (log_id, seed, got))

    def test_first_error_matches_the_heuristic(self):
        inst = self.instance("900000004")
        ws = workspace_with(self.root, read_log("900000004"))
        self.assertEqual(lt.DEFECTS["first_error"](inst, random.Random(0)), lt.HEURISTICS["grep_first_error"](ws, ""))

    def test_diagnostic_defects(self):
        self.assertEqual(lt.DIAGNOSTIC, {"first_line_only", "format_drift"})
        inst = self.instance("900000006")
        first = lt.DEFECTS["first_line_only"](inst, random.Random(0))
        self.assertEqual(json.loads(first[lt.OUTPUT])["failure_lines"], [28, 28])
        self.assertEqual(lt.check(inst, first)["label"], "invalid")
        drift = lt.DEFECTS["format_drift"](inst, random.Random(0))
        self.assertIn(b"```json", drift[lt.OUTPUT])
        self.assertEqual(lt.check(inst, drift)["label"], "unparseable")
        self.assertEqual(lt.check(self.instance("900000002"), lt.DEFECTS["first_line_only"](self.instance("900000002"), random.Random(0)))["label"], "valid")


class Material(unittest.TestCase):
    def test_material_record(self):
        spec = json.loads((BB / "meta-tasks" / "logtriage-llm" / "material.json").read_text(encoding="utf-8"))
        self.assertEqual(spec["licence"]["name"], "CC BY 4.0")
        self.assertEqual(spec["record"], "https://zenodo.org/records/3632351")
        self.assertRegex(spec["retrieved"], r"^\d{4}-\d{2}-\d{2}$")
        self.assertIn("10.5281/zenodo.3632351", spec["attribution"])
        self.assertIn("CC BY 4.0", spec["attribution"])
        self.assertEqual(len(spec["public"]), len(set(spec["public"])))
        self.assertTrue(55 <= len(spec["public"]) <= 65)
        self.assertTrue(all(re.fullmatch(r"\d+", i) for i in spec["public"]))

    def test_split_writes_public_held_out_and_notices(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "material"
            split = lt.build_split(FIX / "source", dest, PUBLIC, attribution="Credit line.")
            self.assertEqual(sorted(split["public"]), PUBLIC)
            self.assertEqual(len(split["held_out"]), 4)
            self.assertEqual(json.loads((dest / "split.json").read_text(encoding="utf-8")), split)
            public = lt.load_entries(dest / "public")
            self.assertEqual(sorted(e["id"] for e in public), PUBLIC)
            self.assertEqual(sorted(e["id"] for e in lt.load_entries(dest / "held-out")), sorted(set(EXPECTED) - set(PUBLIC)))
            for entry in public:
                self.assertEqual(entry["path"].read_bytes(), (FIX / "source" / "logs" / entry["log"]).read_bytes())
            readme = (dest / "public" / "README.md").read_text(encoding="utf-8")
            self.assertIn("Credit line.", readme)
            self.assertIn("public since 2020", readme)
            first = {p.relative_to(dest).as_posix(): p.read_bytes() for p in dest.rglob("*") if p.is_file()}
            lt.build_split(FIX / "source", dest, PUBLIC, attribution="Credit line.")
            self.assertEqual(first, {p.relative_to(dest).as_posix(): p.read_bytes() for p in dest.rglob("*") if p.is_file()})

    def test_unknown_public_id_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                lt.build_split(FIX / "source", Path(tmp), ["1"])

    def test_store_default_and_override(self):
        lt.configure(None)
        with unittest.mock.patch.dict("os.environ", {"METABENCH_STORE": "X:/store"}):
            self.assertEqual(lt.store_root(), Path("X:/store"))
        lt.configure("Y:/other")
        self.assertEqual(lt.store_root(), Path("Y:/other"))
        lt.configure(None)


class Subject(unittest.TestCase):
    def setUp(self):
        self.work = tempfile.TemporaryDirectory()
        self.addCleanup(self.work.cleanup)
        self.root = Path(self.work.name)
        self.log = "".join(f"step {i} output\n" for i in range(1, 41))
        self.ws = workspace_with(self.root, self.log)

    def run_main(self, output, code=0, *, extra=(), claude_prefix=None):
        capture = self.root / "stdin.txt"
        claude = claude_prefix or [sys.executable, str(FIX / "fake_claude.py"), str(FIX / "results" / output), str(code), str(capture)]
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            status = agent.main(["--workspace", str(self.ws), "--prompt-file", str(self.root / "prompt.md"),
                                 "--transcript", str(self.root / "t" / "transcript.jsonl"), "--timeout", "20", *extra], claude=claude)
        lines = stdout.getvalue().strip().splitlines()
        self.assertEqual(len(lines), 1)
        return status, json.loads(lines[0]), capture

    def test_config_and_template(self):
        self.assertEqual(json.loads((SUBJECT / "config.json").read_text(encoding="utf-8")), {"model": "claude-haiku-4-5", "effort": "low"})
        template = (SUBJECT / "prompt.md").read_text(encoding="utf-8")
        self.assertEqual((template.count("{{LOG}}"), template.count("{{LINE_COUNT}}")), (1, 1))

    def test_command_construction(self):
        config = json.loads((SUBJECT / "config.json").read_text(encoding="utf-8"))
        self.assertEqual(agent.build_command(config, ["claude"]),
                         ["claude", "-p", "--safe-mode", "--model", "claude-haiku-4-5", "--effort", "low", "--tools", "",
                          "--permission-mode", "dontAsk", "--no-session-persistence", "--output-format", "json"])

    def test_print_command_calls_nothing(self):
        done = subprocess.run([sys.executable, str(SUBJECT / "run_agent.py"), "--workspace", str(self.ws), "--print-command"],
                              capture_output=True, text=True, timeout=30)
        self.assertEqual(done.returncode, 0, done.stderr)
        shown = json.loads(done.stdout)
        self.assertEqual(shown["command"][1:3], ["-p", "--safe-mode"])
        self.assertIn("     1 | step 1 output", shown["prompt"])
        self.assertIn("    40 | step 40 output", shown["prompt"])
        self.assertIn("(40 lines)", shown["prompt"])
        self.assertNotIn("{{", shown["prompt"])
        self.assertFalse((self.ws / "triage.json").exists())

    def test_numbering_cleans_and_windows_long_logs(self):
        text = agent.numbered(["\x1b[31mred\x1b[0m  ", "x" * 900])
        self.assertTrue(text.startswith("     1 | red\n     2 | xxx"))
        self.assertIn("...[line cut]", text)
        lines = [f"line {i} " + "y" * 90 for i in range(1, 5001)]
        windowed = agent.numbered(lines, 50_000)
        self.assertLessEqual(len(windowed), 50_100)
        self.assertIn("lines omitted", windowed)
        self.assertIn("     1 | line 1 ", windowed)
        self.assertIn("  5000 | line 5000 ", windowed)
        self.assertEqual(agent.numbered(lines[:10], 50_000).count("omitted"), 0)

    def test_recorded_outputs_classify(self):
        read = lambda name: (FIX / "results" / name).read_text(encoding="utf-8")
        cases = {"success.json": "completed", "fenced.json": "completed", "array_output.json": "completed",
                 "api_error.json": "error", "usage_limit.json": "usage-limit", "refusal.json": "refused"}
        for name, status in cases.items():
            self.assertEqual(agent.classify(agent.parse_output(read(name)), 0, "")[0], status, name)
        cut = json.loads(read("success.json"))
        cut["stop_reason"] = "max_tokens"
        self.assertEqual(agent.classify(cut, 0, "")[0], "cut-off")
        talk = json.loads(read("success.json"))
        talk["result"] = "The log shows we hit the usage limit of the registry."
        self.assertEqual(agent.classify(talk, 0, "")[0], "completed")
        self.assertEqual(agent.classify(None, 1, "Error: Claude usage limit reached.")[0], "usage-limit")
        self.assertEqual(agent.classify(None, 1, "boom")[0], "error")
        self.assertIsNone(agent.parse_output("not json"))
        self.assertEqual(agent.parse_output("warning\n" + read("success.json"))["type"], "result")

    def test_extracting_the_answer(self):
        ok = agent.extract_triage('{"failure_lines": [3, 5], "summary": "boom"}', 10)
        self.assertEqual(ok, ({"failure_lines": [3, 5], "summary": "boom"}, ""))
        self.assertEqual(agent.extract_triage('Sure:\n```json\n{"failure_lines": [3, 5]}\n```', 10)[0],
                         {"failure_lines": [3, 5], "summary": ""})
        self.assertEqual(agent.extract_triage('Result {"failure_lines": [1, 2], "summary": "a"} done', 10)[0]["failure_lines"], [1, 2])
        for reply in ("no idea", '{"failure_lines": [5, 3]}', '{"failure_lines": [1, 11]}', '{"failure_lines": [0, 2]}',
                      '{"failure_lines": "3-5"}', '{"failure_lines": [1.5, 2]}', "[3, 5]", ""):
            self.assertIsNone(agent.extract_triage(reply, 10)[0], reply)

    def test_completed_run_writes_the_answer(self):
        status, line, capture = self.run_main("success.json")
        self.assertEqual(status, 0)
        self.assertEqual((line["status"], line["exit_code"], line["model"], line["cost_usd"]), ("completed", 0, "claude-haiku-4-5", 0.0214))
        self.assertGreaterEqual(line["seconds"], 0)
        self.assertIn("test_render_table_width fails", line["final"])
        answer = json.loads((self.ws / "triage.json").read_text(encoding="utf-8"))
        self.assertEqual(answer["failure_lines"], [12, 20])
        sent = capture.read_text(encoding="utf-8")
        self.assertIn("    12 | step 12 output", sent)
        events = [json.loads(l) for l in (self.root / "t" / "transcript.jsonl").read_text(encoding="utf-8").splitlines()]
        self.assertEqual([e["event"] for e in events], ["call", "return"])
        self.assertEqual(events[0]["command"][-2:], ["--output-format", "json"])

    def test_fenced_reply_is_parsed(self):
        self.assertEqual(self.run_main("fenced.json")[0], 0)
        self.assertEqual(json.loads((self.ws / "triage.json").read_text(encoding="utf-8"))["failure_lines"], [12, 20])

    def test_statuses_and_exit_codes(self):
        for output, code, status, exit_code in (("api_error.json", 0, "error", 1), ("usage_limit.json", 0, "usage-limit", 3),
                                                ("refusal.json", 0, "refused", 0)):
            ws_answer = self.ws / "triage.json"
            ws_answer.unlink(missing_ok=True)
            got, line, _ = self.run_main(output, code)
            self.assertEqual((got, line["status"]), (exit_code, status), output)
            self.assertFalse(ws_answer.exists())

    def test_unusable_reply_completes_without_an_answer(self):
        bad = self.root / "bad.json"
        bad.write_text(json.dumps({"type": "result", "is_error": False, "result": '{"failure_lines": [30, 90]}',
                                   "total_cost_usd": 0.01, "modelUsage": {"claude-haiku-4-5": {}}}), encoding="utf-8")
        capture = self.root / "stdin.txt"
        status, line, _ = self.run_main("", 0, claude_prefix=[sys.executable, str(FIX / "fake_claude.py"), str(bad), "0", str(capture)])
        self.assertEqual((status, line["status"]), (0, "completed"))
        self.assertFalse((self.ws / "triage.json").exists())

    def test_crash_without_output_is_an_error(self):
        status, line, _ = self.run_main("", 0, claude_prefix=[sys.executable, "-c", "import sys; sys.stderr.write('segfault'); sys.exit(7)"])
        self.assertEqual((status, line["status"], line["exit_code"]), (1, "error", 7))
        self.assertIn("segfault", line["final"])
        status, line, _ = self.run_main("", 0, claude_prefix=[str(self.root / "no-such-claude")])
        self.assertEqual((status, line["status"]), (1, "error"))

    def test_timeout_stops_the_call(self):
        started = time.monotonic()
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            status = agent.main(["--workspace", str(self.ws), "--timeout", "1"], claude=[sys.executable, "-c", "import time; time.sleep(60)"])
        line = json.loads(stdout.getvalue())
        self.assertEqual((status, line["status"], line["exit_code"]), (2, "timeout", None))
        self.assertLess(time.monotonic() - started, 15)

    def test_missing_and_empty_logs(self):
        (self.ws / "build.log").unlink()
        status, line, _ = self.run_main("success.json")
        self.assertEqual((status, line["status"]), (1, "error"))
        (self.ws / "build.log").write_bytes(b"")
        status, line, capture = self.run_main("success.json")
        self.assertEqual((status, line["status"]), (0, "completed"))
        self.assertFalse(capture.exists())
        self.assertFalse((self.ws / "triage.json").exists())


if __name__ == "__main__":
    unittest.main()
