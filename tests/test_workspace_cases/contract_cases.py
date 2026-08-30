"""Workspace script-shape and contract-key behavior."""

from .common import *  # noqa: F401,F403

class TestScriptShape(unittest.TestCase):
    """Completion criterion 5: stdlib-only, network-free, the resolver
    imported rather than copied, and the exit-code deviation documented."""

    @staticmethod
    def collapsed(text: str) -> str:
        return " ".join(text.split())

    def test_the_module_docstring_names_what_the_deviation_is_read_against(self):
        """The names, never the sentences. That the deviation is real -- a
        `tickets.py` payload reporting failure at exit 0, graded by
        `workspace.py` into a non-zero exit -- is
        `TestTicketsPayloadIsGradedNotItsExitStatus`'s to decide, and it does.
        What a docstring check can still hold is that a reader of the
        deviation is routed at the two files it is read against
        (docs/documentation.md law 5); how that is worded is law 6's, and a
        pin on the wording went red for every rewrite of it."""

        docstring = ast.get_docstring(ast.parse(WORKSPACE_PY.read_text(encoding="utf-8")))
        collapsed = self.collapsed(docstring or "")
        self.assertIn("scripts/tickets.py", collapsed)
        self.assertIn("contracts/work-item.md", collapsed)

    def test_the_resolvers_are_imported_never_copied(self):
        source = WORKSPACE_PY.read_text(encoding="utf-8")
        collapsed = self.collapsed(source)
        self.assertIn("import state_root", collapsed)
        self.assertIn("import tickets", collapsed)
        self.assertNotIn("def _find_repo_root", source)
        self.assertNotIn("def _main_checkout_root", source)
        self.assertNotIn("def state_root", source)
        self.assertNotIn("gitdir:", source)
        self.assertNotIn(".orch", source)
        self.assertEqual(
            str(STATE_ROOT_PY.resolve()),
            str(Path(workspace.state_root.__file__).resolve()),
        )
        self.assertEqual(
            str(TICKETS_PY.resolve()),
            str(Path(workspace.tickets.__file__).resolve()),
        )

    def test_the_script_is_stdlib_only_and_network_free(self):
        tree = ast.parse(WORKSPACE_PY.read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                imported.add(node.module.split(".")[0])
        self.assertEqual(
            set(),
            imported - {
                "__future__", "json", "subprocess", "sys", "pathlib",
                "state_root", "tickets",
            },
            f"unexpected import in workspace.py: {sorted(imported)}",
        )
        self.assertIn("__future__", imported, "the 3.9 floor needs the future import")


LEADING_KEY_RE = re.compile(r"^(?:(?:and|optional)\s+)?`([a-z_]+)`(?:,\s*)?")


def contract_frontmatter_bullets():
    """Every frontmatter bullet ``contracts/work-item.md`` declares, from the
    contract's own bytes: the block its ``Frontmatter`` lead-in opens and its
    ``System-owned metadata`` section closes, one entry per top-level bullet,
    each entry the run of backticked names the bullet opens with plus the
    bullet's whole text. Nothing here is a list of key names typed into this
    test."""

    lines = CONTRACT.read_text(encoding="utf-8").splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith("Frontmatter"))
    end = next(
        i for i, line in enumerate(lines)
        if i > start and line.startswith("## ")
    )
    bullets, current = [], None
    for line in lines[start:end]:
        if line.startswith("- "):
            current = [line[2:]]
            bullets.append(current)
        elif current is not None and line.startswith("  ") and line.strip():
            current.append(line.strip())
        else:
            current = None
    parsed = []
    for bullet in bullets:
        # the whole bullet, because a run of names wraps onto its continuation
        # lines and the keys past the wrap are keys the contract declares
        keys, rest = [], " ".join(bullet)
        while True:
            match = LEADING_KEY_RE.match(rest)
            if match is None:
                break
            keys.append(match.group(1))
            rest = rest[match.end():]
        parsed.append((keys, " ".join(bullet)))
    return parsed


class TestContractKeySeam(unittest.TestCase):
    """Completion criterion 6. Both sides are collected mechanically: the code
    side from the module constant the script itself uses, the contract side
    from ``contracts/work-item.md``'s own bytes. A key spelled one way in the
    script and another way in the contract fails here and nowhere else."""

    def test_the_key_names_the_script_uses_are_the_contracts_own_both_ways(self):
        bullets = contract_frontmatter_bullets()
        declared = {key for keys, _ in bullets for key in keys}
        self.assertIn("id", declared, "the contract's frontmatter block did not parse")

        code_keys = set(workspace.FRONTMATTER_KEYS)
        self.assertTrue(code_keys, "workspace.py declares no frontmatter keys")
        self.assertEqual(
            [], sorted(code_keys - declared),
            "workspace.py uses a frontmatter key contracts/work-item.md does "
            "not declare",
        )

        # The contract names the tool rather than the file, so the side is
        # collected by the word the bullets use for this concern, still from
        # the contract's own bytes and never from a list typed in here.
        workspace_keys = {
            key for keys, text in bullets for key in keys if "workspace" in text
        }
        self.assertTrue(workspace_keys, "the contract declares no workspace keys")
        self.assertEqual(
            [], sorted(code_keys - workspace_keys),
            "workspace.py uses a key contracts/work-item.md does not describe "
            "as workspace mechanics",
        )

    def test_each_key_the_script_uses_names_where_it_is_written_or_read(self):
        for key, role in workspace.FRONTMATTER_KEYS.items():
            with self.subTest(key=key):
                self.assertRegex(role, r"start|check")
