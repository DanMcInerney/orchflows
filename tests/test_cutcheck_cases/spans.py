"""Cutcheck behavioral cases loaded explicitly by tests.test_cutcheck."""

from tests.test_cutcheck import *  # noqa: F401,F403

try:
    del load_tests
except NameError:
    pass

SPAN_EXECUTORS = ("_wrote", "_run_once", "_exit_code")

# What a span this module runs may name. Frozen sets, never a probe of the
# host: `importlib.util.find_spec("pytest")` answers PRESENT wherever pytest
# is installed and ABSENT on every CI leg, so a check resting on it agrees
# with whichever host it is asked on and is silent exactly where the defect
# lives. `sys.stdlib_module_names` is 3.10 and later while this repository's
# floor is 3.9, so reading that would split the verdict by leg instead.
# The search heads are admitted because they are the one head `_run_once`
# never spawns: a `grep` span is decided by cutcheck's own matcher, so it
# needs no program CI would have to install -- which is the fact
# `SearchSpanMatcherTest` grades, and the reason its spans may stand here.
SPAN_MODULES = frozenset({"unittest"})


def executed_spans(tree):
    """``(lineno, command)`` for every literal span a parsed module runs.

    A span assembled at run time is outside this reading; every span this
    module runs today is written out at its call site, and the vacuity node
    below is what keeps saying so.
    """

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not node.args:
            continue
        func = node.func
        called = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", None)
        if called not in SPAN_EXECUTORS:
            continue
        first = node.args[0]
        if isinstance(first, ast.Constant) and isinstance(first.value, str):
            yield first.lineno, first.value


class SpanDependencyTest(unittest.TestCase):
    """No span this module runs needs anything a bare CI runner lacks.

    Nine legs -- three interpreters across three operating systems -- install
    nothing past the interpreter, so a span naming a pip package writes
    nothing there and every assertion about what it wrote goes red. The defect
    is invisible on a developer machine, where the package is installed and
    the node is green; that is how two of them lived here through several
    passes. Caught by reading, because the alternative -- importing the name
    to see whether it resolves -- answers about the host doing the asking.
    """

    def setUp(self):
        sources = [Path(__file__).with_name(name + ".py") for name in CASE_MODULES]
        self.spans = [
            span
            for source in sources
            for span in executed_spans(ast.parse(source.read_text(encoding="utf-8")))
        ]

    def test_the_reading_sees_the_spans_it_exists_to_grade(self):
        """An empty reading passes the node below for free; this is what stops it."""

        commands = [command for _, command in self.spans]
        self.assertTrue(commands, "no span was found to check")
        self.assertIn("git checkout-index --prefix=probe_dir/ LICENSE", commands)
        self.assertIn("git checkout-index --prefix=.pytest_cache/ LICENSE", commands)

    def test_no_span_names_a_program_or_module_outside_the_standard_set(self):
        allowed = {"program": SPAN_PROGRAMS, "module": SPAN_MODULES}
        self.assertEqual(
            [
                "line {}: {} {!r} in {!r}".format(lineno, kind, name, command)
                for lineno, command in self.spans
                for kind, name in span_requirements(command)
                if name not in allowed[kind]
            ],
            [],
            "a span here needs something CI does not install",
        )

    def test_the_reading_reports_the_spellings_that_were_here(self):
        """The can-fail direction, on the two shapes this node was cut for."""

        self.assertIn(
            ("module", "pytest"),
            span_requirements(
                "python3 -m pytest --junitxml=probe_dir/r.xml tests/test_installer.py"
            ),
        )
        self.assertIn(("program", "pytest"), span_requirements("pytest tests"))
        self.assertNotIn(
            ("module", "pytest"),
            span_requirements("git checkout-index --prefix=probe_dir/ LICENSE"),
        )
