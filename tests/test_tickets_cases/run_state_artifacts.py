"""Behavioral ticket regression cases."""

import time

from .common import *  # noqa: F401,F403
from scripts import tickets_result as tickets_result_mod
from scripts import tickets_store as tickets_store_mod
from scripts import tickets_store_writes as tickets_writes_mod

def run_state_lines(prompt: str) -> list:
    return [line for line in prompt.splitlines() if " run-state " in line]


class TestRunStateWorklog(unittest.TestCase):
    """rules/visibility.md §6: run state reaches the one user-scope sink
    from any workspace in any repository, or it fails loudly."""

    def test_a_note_from_a_worktree_appends_in_the_sink(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, worktree, _ = make_worktree(tmp, {"T1": ("claimed", "[]")})
            payload = run_cmd(worktree, "run-state", "testrun", "--note", "slice one landed")
            self.assertEqual("note", payload["run_state"]["mode"])
            self.assertEqual(
                str(notes_of().resolve()), payload["run_state"]["path"]
            )
            self.assertEqual(
                "slice one landed\n", notes_of().read_text(encoding="utf-8")
            )
            # the run tree is the sink's alone
            self.assertFalse((worktree / ".orch").exists())
            self.assertFalse((main / ".orch").exists())

    def test_a_prior_line_and_an_outside_writer_both_survive(self):
        """Append mode, never read-modify-write: scripts/friction.py opens the
        shared log with ``"a"`` and an explicit ``newline`` for exactly this."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, worktree, _ = make_worktree(tmp, {"T1": ("claimed", "[]")})
            run_cmd(worktree, "run-state", "testrun", "--note", "first from the channel")
            with open(notes_of(), "a", encoding="utf-8", newline="\n") as handle:
                handle.write("second from another worktree\n")
            run_cmd(worktree, "run-state", "testrun", "--note", "third from the channel")
            self.assertEqual(
                [
                    "first from the channel",
                    "second from another worktree",
                    "third from the channel",
                ],
                notes_of().read_text(encoding="utf-8").splitlines(),
            )

    def test_concurrent_notes_all_land_whole(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, worktree, _ = make_worktree(tmp, {"T1": ("claimed", "[]")})
            notes = [f"writer-{i} " + "x" * 2000 for i in range(8)]
            # eight processes, never eight threads: the contention this grades
            # is between writers the platform serialises at the file, and
            # in-process callers would share one interpreter's own ordering
            with ThreadPoolExecutor(max_workers=8) as pool:
                payloads = list(
                    pool.map(
                        lambda note: run_json(worktree, "run-state", "testrun", "--note", note),
                        notes,
                    )
                )
            # A writer that reported an error and a writer whose line was lost
            # are two different defects, and the file check alone reports the
            # second for both -- the payloads are the only place the first is
            # visible, and this test used to throw them away.
            self.assertEqual([], [p["error"] for p in payloads if "error" in p])
            self.assertEqual(
                sorted(notes),
                sorted(notes_of().read_text(encoding="utf-8").splitlines()),
            )

    def test_a_note_waits_past_the_windows_finite_lock_window(self):
        """A run mutation waits for ownership instead of failing after the
        finite retry window built into ``msvcrt.LK_LOCK``.

        Holding the real product lock past that window makes the old locking
        mode exit with ``PermissionError``.  The child must remain blocked,
        then append one whole line after the owner releases it.
        """

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, worktree, _ = make_worktree(tmp, {"T1": ("claimed", "[]")})
            note = "writer waited and landed " + "x" * 2000
            command = [
                sys.executable, str(TICKETS_PY), "run-state", "testrun",
                "--note", note,
            ]
            with tickets_store_mod._run_lock("testrun"):
                process = subprocess.Popen(
                    command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    text=True, encoding="utf-8", errors="replace",
                    cwd=str(worktree),
                )
                time.sleep(10.5)
                premature_exit = process.poll()
            stdout, stderr = process.communicate(timeout=10)
            self.assertIsNone(
                premature_exit,
                f"writer stopped waiting before release: {stdout or stderr}",
            )
            self.assertEqual(0, process.returncode, stdout or stderr)
            self.assertEqual([note], notes_of().read_text(encoding="utf-8").splitlines())


    def test_an_append_waits_past_a_refusal_longer_than_the_finite_window(self):
        """The sibling case above holds the *run* lock, so its child blocks
        there and never reaches this one. `LK_LOCK` stops retrying after ten
        attempts and raises; byte zero here is contended by every appender,
        and eight of them on one runner outlast that -- reported as
        `unwritable run state: [Errno 13] Permission denied`.
        """

        if tickets_writes_mod.msvcrt is None:
            self.skipTest("the finite retry window is Windows-only")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "notes.md"
            path.write_text("first\n", encoding="utf-8")
            real = tickets_writes_mod.msvcrt.locking
            refusals = {"count": 0}

            def refusing(descriptor, mode, size):
                # Both lock modes, never the unlock: a mode that gives up at
                # ten must fail this, and one that waits must clear it.
                if mode != tickets_writes_mod.msvcrt.LK_UNLCK and refusals["count"] < 25:
                    refusals["count"] += 1
                    raise PermissionError(13, "Permission denied")
                return real(descriptor, mode, size)

            with mock.patch.object(
                tickets_writes_mod.msvcrt, "locking", refusing
            ), mock.patch.object(
                tickets_store_mod, "WINDOWS_LOCK_RETRY_SECONDS", 0.001
            ):
                tickets_result_mod._append_one_line(path, "second\n")
            self.assertEqual(25, refusals["count"], "the appender stopped waiting early")
            self.assertEqual("first\nsecond\n", path.read_text(encoding="utf-8"))


class TestRunStateArtifact(unittest.TestCase):
    """Anything not append-only is partitioned by run id, so two runs in two
    workspaces never write one file."""

    def test_a_named_artifact_lands_under_the_run_partition(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, worktree, _ = make_worktree(tmp, {"T1": ("claimed", "[]")})
            payload = run_cmd(
                worktree, "run-state", "testrun", "--artifact", "evidence.md",
                "--text", "the bytes at the main root\n",
            )
            artifact = run_dir_of() / "evidence.md"
            self.assertEqual("artifact", payload["run_state"]["mode"])
            self.assertEqual(str(artifact.resolve()), payload["run_state"]["path"])
            self.assertEqual(
                "the bytes at the main root\n", artifact.read_text(encoding="utf-8")
            )
            self.assertFalse((worktree / ".orch").exists())

    def test_the_body_can_come_from_a_file_inside_the_workspace(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, worktree, _ = make_worktree(tmp, {"T1": ("claimed", "[]")})
            body = worktree / "evidence-body.md"
            body.write_text("read inside, written outside\n", encoding="utf-8")
            run_cmd(
                worktree, "run-state", "testrun", "--artifact", "checks.md",
                "--file", str(body),
            )
            self.assertEqual(
                "read inside, written outside\n",
                (run_dir_of() / "checks.md").read_text(encoding="utf-8"),
            )


# Reading is the thing an append does not do. Any of these inside the writer
# says the write depends on what the file held at some earlier moment, which
# is the whole of the hazard whether the write itself appends or not.
READ_CALLS = frozenset({"read", "readline", "readlines", "read_text", "read_bytes"})


def _constant(node):
    """A literal argument's value, or ``None`` where it is not a literal."""

    return node.value if isinstance(node, ast.Constant) else None


def _open_mode(call, positional: int):
    """The mode an ``open`` call asks for, however the call spells it:
    positionally, by keyword, or by omission -- the default is a read.

    ``open(path, mode)`` and ``path.open(mode)`` carry it in different
    positions, so the caller says which one this call is.
    """

    for keyword in call.keywords:
        if keyword.arg == "mode":
            return _constant(keyword.value)
    if len(call.args) > positional:
        return _constant(call.args[positional])
    return "r"


def append_mechanism(source: str, name: str) -> dict:
    """How the function ``name`` in ``source`` opens its file, read off the
    AST rather than the text.

    A grep pins one spelling of the call: it said nothing once the call moved
    one function away, and it fails on ``open(path, 'a'``, on
    ``open(path, mode="a")`` and on ``path.open("a")`` -- false failures, no
    change in mechanism. What separates an append from a read-modify-write is
    how many opens there are, in what mode, and whether anything reads.
    """

    defined = [
        node
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.FunctionDef) and node.name == name
    ]
    if len(defined) != 1:
        raise AssertionError(f"{len(defined)} functions named {name!r} in this source")
    modes, reads = [], []
    for call in ast.walk(defined[0]):
        if not isinstance(call, ast.Call):
            continue
        if isinstance(call.func, ast.Attribute):
            called, position = call.func.attr, 0  # path.open(mode)
        elif isinstance(call.func, ast.Name):
            called, position = call.func.id, 1  # open(path, mode)
        else:
            continue
        if called == "open":
            modes.append(_open_mode(call, position))
        elif called in READ_CALLS:
            reads.append(called)
    return {"open_modes": modes, "reads": reads}


def assert_one_append_open_and_no_read(test, source: str, name: str) -> None:
    """Assert ``name`` appends: exactly one open, in append mode, nothing read.

    One check, both directions: the real function is graded by it and so is
    every wrong implementation built beside the tree, so what passes and what
    fails are decided by the same instrument.
    """

    mechanism = append_mechanism(source, name)
    test.assertEqual(["a"], mechanism["open_modes"], name)
    test.assertEqual([], mechanism["reads"], name)


# One mechanism, three spellings, and not one of them a string the grep
# could find. A check that fails on any of these reports a rewrite that
# never happened.
APPEND_SPELLINGS = {
    "single quotes": """
def _append_one_line(path, block):
    with open(path, 'a', encoding="utf-8", newline="\\n") as handle:
        handle.write(block)
""",
    "mode keyword": """
def _append_one_line(path, block):
    with open(path, mode="a", encoding="utf-8", newline="\\n") as handle:
        handle.write(block)
""",
    "Path.open": """
def _append_one_line(path, block):
    with path.open("a", encoding="utf-8", newline="\\n") as handle:
        handle.write(block)
""",
}

# The real function writes on two branches and flushes on one; a third branch
# would move that count again without moving anything the append depends on.
BRANCHED_APPEND = """
def _append_one_line(path, block):
    with open(path, "a", encoding="utf-8", newline="\\n") as handle:
        if msvcrt is None:
            handle.write(block)
            return
        handle.write(block)
        handle.flush()
        handle.write("")
"""

# Two implementations that are wrong and satisfy the behavioural test anyway.
# Each reproduces its expectation exactly, because the write that test
# interleaves lands between two complete invocations -- so nothing there can
# tell either of these from the real function. The first rewrites the whole
# file; the second appends, but only after deciding from a read that another
# writer can invalidate before the write lands.
WRONG_APPENDS = {
    "whole-file rewrite": """
def _append_one_line(path, block):
    existing = path.read_text(encoding="utf-8")
    with open(path, "w", encoding="utf-8", newline="\\n") as handle:
        handle.write(existing + block)
""",
    "append decided by a stale read": """
def _append_one_line(path, block):
    if block in path.read_text(encoding="utf-8"):
        return
    with open(path, "a", encoding="utf-8", newline="\\n") as handle:
        handle.write(block)
""",
}


def load_beside_the_tree(directory: Path, name: str, source: str):
    """Import ``source`` as a module of its own, beside the tree, never in it.

    A wrong implementation is evidence only if it is a real one, and
    rules/verification.md §8 rules out the other way of getting one: editing
    the tree under test and putting it back, where the harm is the window and
    not the commit.
    """

    path = directory / (name + ".py")
    path.write_text(source, encoding="utf-8")
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
