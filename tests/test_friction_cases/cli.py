from __future__ import annotations

from .common import *
from .common import _IsolatedRepoTestCase

class TestMainWritesEntry(_IsolatedRepoTestCase):
    def test_appends_exactly_one_json_line_with_required_keys(self):
        rc, out = self._run_main(["observed thing", "expected thing"])
        self.assertEqual(rc, 0)
        self.assertEqual(out.strip(), "friction logged")
        lines = self._log_path().read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 1)
        entry = json.loads(lines[0])
        self.assertEqual(set(entry), REQUIRED_ENTRY_KEYS)
        self.assertEqual(entry["observed"], "observed thing")
        self.assertEqual(entry["expected"], "expected thing")

    def test_second_call_appends_a_second_line_not_a_rewrite(self):
        self._run_main(["first observed", "first expected"])
        prefix = self._log_path().read_bytes()
        self._run_main(["second observed", "second expected"])
        self.assertEqual(prefix, self._log_path().read_bytes()[:len(prefix)])
        lines = self._log_path().read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 2)
        self.assertEqual(json.loads(lines[0])["observed"], "first observed")
        self.assertEqual(json.loads(lines[1])["observed"], "second observed")

    def test_flag_equals_value_forms_parse(self):
        rc, _ = self._run_main([
            "o", "e",
            "--skill=orch-tdd",
            "--ticket=t2-friction-hardening", "--run=20260717T161634Z-adversarial-test-sweep",
        ])
        self.assertEqual(rc, 0)
        entry = json.loads(self._log_path().read_text(encoding="utf-8").splitlines()[-1])
        self.assertEqual(entry["skill"], "orch-tdd")
        self.assertEqual(entry["ticket"], "t2-friction-hardening")
        self.assertEqual(entry["run"], "20260717T161634Z-adversarial-test-sweep")

    def test_mixed_space_and_equals_flag_forms_parse_together(self):
        rc, _ = self._run_main(["o", "e", "--ticket", "t1", "--skill=orch-tdd"])
        self.assertEqual(rc, 0)
        entry = json.loads(self._log_path().read_text(encoding="utf-8").splitlines()[-1])
        self.assertEqual(entry["ticket"], "t1")
        self.assertEqual(entry["skill"], "orch-tdd")

    def test_first_call_with_only_observed_and_expected_has_no_extra_label(self):
        rc, _ = self._run_main(["o", "e"])
        self.assertEqual(rc, 0)
        entry = json.loads(self._log_path().read_text(encoding="utf-8").splitlines()[-1])
        self.assertEqual(REQUIRED_ENTRY_KEYS, set(entry))
        self.assertIsNone(entry["skill"])

    def test_git_lookup_missing_executable_still_appends_entry(self):
        with mock.patch.object(friction.subprocess, "run", side_effect=FileNotFoundError("git")):
            rc, out = self._run_main(["o", "e"])
        self.assertEqual(rc, 0)
        self.assertEqual(out.strip(), "friction logged")
        entry = json.loads(self._log_path().read_text(encoding="utf-8").splitlines()[-1])
        self.assertIsNone(entry["git_rev"])

    def test_git_lookup_timeout_still_appends_entry(self):
        timeout_error = friction.subprocess.TimeoutExpired(cmd="git", timeout=friction.GIT_REV_TIMEOUT_SECONDS)
        with mock.patch.object(friction.subprocess, "run", side_effect=timeout_error):
            rc, out = self._run_main(["o", "e"])
        self.assertEqual(rc, 0)
        self.assertEqual(out.strip(), "friction logged")
        entry = json.loads(self._log_path().read_text(encoding="utf-8").splitlines()[-1])
        self.assertIsNone(entry["git_rev"])

    def test_git_lookup_nonzero_exit_yields_none_git_rev(self):
        result = mock.Mock(returncode=1, stdout=b"")
        with mock.patch.object(friction.subprocess, "run", return_value=result):
            rc, _ = self._run_main(["o", "e"])
        self.assertEqual(rc, 0)
        entry = json.loads(self._log_path().read_text(encoding="utf-8").splitlines()[-1])
        self.assertIsNone(entry["git_rev"])

    def test_a_worktree_and_its_main_checkout_append_to_one_stream(self):
        # Build a linked worktree of a separate main checkout and log from
        # both: one stream, two lines, and no `.orch/` in either tree.
        main = self.tmp / "main-checkout"
        (main / ".git" / "worktrees" / "wt").mkdir(parents=True)
        wt = self.tmp / "wt"
        wt.mkdir()
        (wt / ".git").write_text(
            f"gitdir: {main / '.git' / 'worktrees' / 'wt'}\n", encoding="utf-8"
        )
        os.chdir(main)
        self.assertEqual(0, self._run_main(["from the main checkout", "e"])[0])
        os.chdir(wt)
        self.assertEqual(0, self._run_main(["from the worktree", "e"])[0])
        lines = self._log_path().read_text(encoding="utf-8").splitlines()
        self.assertEqual(
            ["from the main checkout", "from the worktree"],
            [json.loads(line)["observed"] for line in lines],
        )
        self.assertFalse((main / ".orch").exists())
        self.assertFalse((wt / ".orch").exists())

    def test_the_entry_records_the_directory_it_was_logged_from(self):
        # One stream for every repository, so where an entry came from is a
        # field on it, never its location. `cwd` is the literal directory;
        # `TestFrictionProjectFields` owns the identity of it.
        self._run_main(["o", "e"])
        entry = json.loads(self._log_path().read_text(encoding="utf-8").splitlines()[-1])
        self.assertEqual(str(self.repo), entry["cwd"])
def _imported_modules(node):
    """The top-level module names one import statement reaches for."""

    if isinstance(node, ast.Import):
        return {alias.name.split(".")[0] for alias in node.names}
    if isinstance(node, ast.ImportFrom) and not node.level:
        return {(node.module or "").split(".")[0]}
    return set()


def _imported_names(node):
    """Those, plus what a `from X import y` binds: a sibling script is named
    by the package it came out of in one form and by the bound name in the
    other, and both spellings are the same import."""

    bound = (
        {alias.name for alias in node.names}
        if isinstance(node, ast.ImportFrom) and not node.level
        else set()
    )
    return _imported_modules(node) | bound


STDLIB_DIR = Path(sysconfig.get_paths()["stdlib"]).resolve()
# The one import friction.py takes under a try/except because the platform
# may not have it: msvcrt ships with CPython on Windows and nowhere else, so
# off Windows there is no spec to resolve and its absence is the contract.
PLATFORM_OPTIONAL_IMPORTS = frozenset({"msvcrt"})


def outside_the_standard_library(names):
    """The subset of `names` this interpreter does not ship.

    ``sys.stdlib_module_names`` answers this in one line and exists only
    from 3.10; this repository's floor is 3.9, where that branch never ran
    and the assertion resting on it was not coverage. Resolving each name
    against the interpreter's own stdlib directory answers the same
    question on every supported version.
    """

    outside = set()
    for name in names:
        if name in sys.builtin_module_names:
            continue
        try:
            spec = importlib.util.find_spec(name)
        except (ImportError, ValueError):
            spec = None
        if spec is None:
            if name not in PLATFORM_OPTIONAL_IMPORTS:
                outside.add(name)
            continue
        if spec.origin in (None, "built-in", "frozen"):
            continue
        if not Path(spec.origin).resolve().is_relative_to(STDLIB_DIR):
            outside.add(name)
    return outside


def _imports_in(nodes, deferred=False):
    """Every import under `nodes`, each with the fact that decides whether it
    can break the file's import: whether a function defers it. Tracked by
    descending, because ``ast.walk`` flattens the tree and loses it."""

    for node in nodes:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            yield node, deferred
            continue
        below = deferred or isinstance(
            node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)
        )
        yield from _imports_in(list(ast.iter_child_nodes(node)), below)


def _read_imports(path):
    return _imports_in(ast.parse(path.read_text(encoding="utf-8")).body)


def module_scope_imports(path):
    """Only the imports that run when the file is imported. An import inside
    a function body runs when that function is called, where ``main``'s broad
    ``except`` still stands over it; one out here runs before ``main``
    exists."""

    imported = set()
    for node, deferred in _read_imports(path):
        if not deferred:
            imported |= _imported_modules(node)
    return imported


def deferred_siblings(path, siblings):
    """Each named sibling this file imports, mapped to whether every import
    of it sits inside a function. One import at module scope is enough to
    break the file, so a sibling seen twice keeps the weaker sighting."""

    found = {}
    for node, deferred in _read_imports(path):
        for name in _imported_names(node) & siblings:
            found[name] = found.get(name, True) and deferred
    return found


class FrictionImportSurfaceTest(unittest.TestCase):
    """friction.py must never fail, so nothing that can fail runs at import.

    It holds no second copy of the sink resolver or of project identity:
    ``scripts/state_root.py`` owns the first, ``scripts/tickets.py`` owns the
    second, and a copy nobody compares silently diverges. It imports them
    instead, and pays for that with placement -- inside the function that
    needs them, never at module scope, so ``main``'s broad ``except`` is
    already standing when a partial install has no sibling to import. What
    that costs then is the fields the sibling feeds and never the entry,
    which ``TestFrictionNeverFails`` grades from the outside.
    """

    SIBLINGS = frozenset({"scripts", "state_root", "tickets"})
    # The four the two owners define. A copy of any of them here is the
    # duplication this file used to compare byte-for-byte and now forbids.
    OWNED_ELSEWHERE = ("main_checkout_root", "find_repo_root",
                       "_writer_identity", "_read_identity")

    def _defined_here(self, path):
        return {
            node.name
            for node in ast.parse(path.read_text(encoding="utf-8")).body
            if isinstance(node, ast.FunctionDef)
        }

    def test_nothing_outside_the_standard_library_runs_at_import(self):
        imported = module_scope_imports(FRICTION_PY)
        self.assertEqual(
            {
                "__future__", "datetime", "json", "msvcrt", "os",
                "pathlib", "subprocess", "sys", "time",
            },
            imported,
            f"friction.py must import standalone: {sorted(imported)}",
        )
        self.assertEqual(
            set(),
            outside_the_standard_library(imported),
            "friction.py imports something this interpreter does not ship",
        )

    def test_a_third_party_import_is_caught_as_outside_the_standard_library(self):
        """Without this the check above passes on any input that happens to
        resolve, and nothing shows it can convict. `tests` is this
        repository's own package: importable here, shipped with no
        interpreter."""

        self.assertEqual({"tests"}, outside_the_standard_library({"json", "tests"}))
        self.assertEqual({"no_such_module_anywhere"},
                         outside_the_standard_library({"no_such_module_anywhere"}))

    def test_the_resolvers_are_called_at_their_owners_never_copied_here(self):
        here = self._defined_here(FRICTION_PY)
        tickets_store = TICKETS_PY.with_name("tickets_store.py")
        owners = (
            self._defined_here(STATE_ROOT_PY)
            | self._defined_here(TICKETS_PY)
            | self._defined_here(tickets_store)
        )
        for name in self.OWNED_ELSEWHERE:
            self.assertIn(name, owners, f"nothing owns {name} any more")
            self.assertNotIn(
                name, here, f"friction.py copies {name} instead of calling its owner"
            )

    def test_every_sibling_import_is_deferred_into_the_function_that_needs_it(self):
        found = deferred_siblings(FRICTION_PY, self.SIBLINGS)
        self.assertTrue(found, "friction.py imports neither owner")
        for name, deferred in sorted(found.items()):
            self.assertTrue(deferred, f"the {name} import runs at module scope")

    def test_a_module_scope_sibling_import_is_caught(self):
        """The check above convicts only if it can. tickets.py imports
        state_root at module scope -- correctly, it has no such bar to meet,
        and it is the exact shape friction.py may not have."""

        found = deferred_siblings(TICKETS_PY.with_name("tickets_store.py"), self.SIBLINGS)
        self.assertIn("state_root", found)
        self.assertFalse(found["state_root"])
