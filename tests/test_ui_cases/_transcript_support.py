"""Shared transcript fixtures and case base."""

from tests.test_ui_cases._web import *  # noqa: F401,F403
def build_fixture(stack) -> tuple:
    """``(temporary directory, main checkout, transcript root)``, all three
    torn down when ``stack`` closes."""

    tmp = Path(stack.enter_context(tempfile.TemporaryDirectory()))
    return tmp, make_sink(tmp), make_transcripts(tmp)


class TranscriptCase(unittest.TestCase):
    """A fixture transcript root and a fixture checkout, plus a clean parse
    cache -- the cache is module state that outlives a test, so a case that
    counts parses must not inherit another case's hits.

    One materialization for the whole class: `setUpClass`, not `setUp`,
    because copying the corpus costs ~40ms and most of these cases only read
    it. A case that writes into the tree calls `own_fixture` first and works
    on a private copy -- a class-scoped tree shared with a mutating case is a
    leak, and a leak surfaces as an order-dependent failure in some later
    case that did nothing wrong. `shared_tree_is_intact` closes that gap from
    the other side: an unannounced write fails the case that made it rather
    than the next case along.
    """

    @classmethod
    def setUpClass(cls):
        stack = contextlib.ExitStack()
        cls.addClassCleanup(stack.close)
        cls.tmp, cls.main, cls.transcripts = build_fixture(stack)
        cls.pristine = snapshot(cls.tmp)

    def setUp(self):
        ui.TRANSCRIPT_CACHE.clear()
        self.addCleanup(ui.TRANSCRIPT_CACHE.clear)
        self.addCleanup(self.shared_tree_is_intact)

    def own_fixture(self):
        """A private copy of the fixture, for a case that writes into it.

        The instance attributes shadow the class's, so the body below reads
        exactly as it did when every case built its own tree. Idempotent, so
        a helper the case calls in a loop rebuilds once.
        """

        if "tmp" in vars(self):
            return
        stack = contextlib.ExitStack()
        self.addCleanup(stack.close)
        self.tmp, self.main, self.transcripts = build_fixture(stack)

    def shared_tree_is_intact(self):
        if "tmp" in vars(self):
            return
        self.assertEqual(
            type(self).pristine,
            snapshot(type(self).tmp),
            "wrote into the class-scoped fixture: call own_fixture() first",
        )

    def sessions(self, transcripts=True) -> str:
        root = self.transcripts if transcripts is True else transcripts
        status, page = ui.render_route(self.main, ui.SESSIONS_ROUTE, root)
        self.assertEqual(200, status)
        return page
