"""Loss-vocabulary ownership checks."""

import unittest

from .source_roster_support import (
    DECLARED_NEVER_LOADED,
    UNSHIPPED_CODES,
    backticked,
    declared_loss_constants,
    loss_code_spelling,
    loss_table_rows,
    module_name,
    names_a_loss_code,
)
from .support import ADAPTER_DIR, package_sources

class LossVocabularyIsReadOffTheSourceTest(unittest.TestCase):
    """`protocol.md`'s loss tables, checked against the package's own syntax.

    Every other enumeration in this suite is pinned and these were not, so
    they drifted the way an unpinned table does: `http_status` was documented
    with three emitters and had thirteen, `schema_drift` five against ten,
    `malformed_json` three against nine. The root cause is not arithmetic. The
    same code is spelled two ways — a module-level constant in some files, a
    bare literal in others — so no one search finds both halves, and a reader
    correcting the table by grep would have corrected it wrong.

    This is what `THREAT_REMAP` gets and for the same reason. The table stays in
    the document, where a reader meets it; the assertion runs against the
    document, so it cannot be corrected in one place and left in the other.
    """

    def setUp(self):
        self.rows = loss_table_rows()
        self.codes = tuple(code for names, _ in self.rows for code in names)
        self.spelling, self.declaring = loss_code_spelling(set(self.codes))

    def test_the_tables_were_found_and_every_row_names_one_code(self):
        # If the parse silently found nothing, every assertion below passes
        # while checking no table at all.
        self.assertGreaterEqual(len(self.rows), 20)
        for names, _ in self.rows:
            self.assertEqual(len(names), 1, "a loss row names {0} codes".format(len(names)))
        self.assertEqual(len(set(self.codes)), len(self.codes), "a code is tabled twice")

    def test_each_row_names_exactly_the_modules_that_spell_its_code(self):
        for names, cell in self.rows:
            code = names[0]
            with self.subTest(code=code):
                documented = set(backticked(cell)) - {code}
                self.assertEqual(
                    documented,
                    self.spelling[code],
                    "protocol.md says {0} is named by {1}; the source says {2}".format(
                        code, sorted(documented), sorted(self.spelling[code])
                    ),
                )

    def test_a_code_the_tables_call_absent_is_absent(self):
        for code in UNSHIPPED_CODES:
            with self.subTest(code=code):
                self.assertIn(code, self.codes, "protocol.md stopped naming " + code)
                self.assertEqual(self.spelling[code], set())
                self.assertEqual(self.declaring[code], set())

    def test_a_constant_declared_and_never_loaded_stays_that_way(self):
        # The other direction, and the one that makes "a name with zero loads is
        # checkable from outside the module" worth writing down.
        for code, modules in sorted(DECLARED_NEVER_LOADED.items()):
            with self.subTest(code=code):
                self.assertEqual(self.declaring[code], set(modules))

    def test_every_module_a_cell_names_is_a_module(self):
        # The cells are parsed by taking their backticked tokens, so a term of
        # art in backticks would read as a module and quietly widen a row. This
        # is the rule that keeps the parse honest, stated where it is relied on.
        known = {module_name(path) for path in package_sources()}

        for names, cell in self.rows:
            for token in backticked(cell):
                with self.subTest(code=names[0], token=token):
                    self.assertIn(token, known | set(self.codes))

    def test_the_scan_tells_a_declaration_from_an_emission(self):
        # The oracle can fail: a module that only binds the name is not named by
        # the table, and one that loads it is. Both directions on one code, so a
        # scan that collapsed them would be caught here rather than by silently
        # widening every row above.
        constants = declared_loss_constants({"auth_required", "schema_drift"})
        declared = ADAPTER_DIR / "reddit_feed.py"
        emitting = ADAPTER_DIR / "web_search.py"

        self.assertIn("auth_required", names_a_loss_code(declared, {"auth_required"}, constants)[1])
        self.assertEqual(names_a_loss_code(declared, {"auth_required"}, constants)[0], set())
        self.assertIn("schema_drift", names_a_loss_code(emitting, {"schema_drift"}, constants)[0])
        self.assertEqual(names_a_loss_code(emitting, {"schema_drift"}, constants)[1], set())
