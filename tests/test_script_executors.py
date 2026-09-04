"""A `script:<path>` executor is admissible on a stamped ticket.

`contracts/work-item.md` (Executor form) and `rules/token-economy.md` §4
both say a repeated deterministic step becomes `executor: script:<path>`
-- a tested script as a graph node, so the step costs no agent.
`authority_findings` refused every executor outside the stamped standard's
skill-binding registry, and a script is not a skill, so the form graded
`executor-standard-mismatch` on any ticket carrying a standard.  Because
`tickets_packet.py` refuses to emit a packet for a ticket with any
admission finding, the law was reachable only on a standard-less or
legacy-unadmitted ticket -- which is why the tree carried no real usage.

The refusal a script executor still owes is its own: a path that names
no file in the tree is not a tested script, and admission says so.
"""
from __future__ import annotations

import sys
import unittest

from tests._repo_root import ROOT
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import tickets_admission as admission  # noqa: E402

RESOLVING_SCRIPT = "tools/validate.py"
ABSENT_SCRIPT = "scripts/no-such-script.py"


def ticket_text(executor: str, *, standard: str = "orch-code") -> str:
    """One stamped, otherwise-clean ticket carrying the given executor."""

    return f"""---
id: T1
run: script-executor-fixture
status: pending
admission: pending
executor: {executor}
standard: {standard}
depends_on: []
write_scope:
  - scripts/a.py
mutations: [change:scripts/a.py]
excluded_actions:
  - vcs.push
isolation: required
bound: 10m
---

## Goal

Run one repeated deterministic step as a graph node.

## Context

[]

## Report
"""


def finding_codes(executor: str, **kwargs) -> set:
    text = ticket_text(executor, **kwargs)
    graded = admission.grade_admission("T1", text, {"T1": text})
    return {item["code"] for item in graded["findings"]}


class ScriptExecutorAdmissionTest(unittest.TestCase):
    """The stamped ticket is the case the registry check made unreachable."""

    def test_a_script_executor_resolving_in_the_tree_is_admitted(self):
        codes = finding_codes(f"script:{RESOLVING_SCRIPT}")
        self.assertNotIn("executor-standard-mismatch", codes)
        self.assertNotIn("script-executor-unresolved", codes)

    def test_a_script_executor_naming_no_file_in_the_tree_is_refused(self):
        codes = finding_codes(f"script:{ABSENT_SCRIPT}")
        self.assertIn("script-executor-unresolved", codes)

    def test_a_bare_script_prefix_names_no_path_and_is_refused(self):
        self.assertIn("script-executor-unresolved", finding_codes("script:"))

    def test_the_refusal_names_the_path_that_did_not_resolve(self):
        text = ticket_text(f"script:{ABSENT_SCRIPT}")
        graded = admission.grade_admission("T1", text, {"T1": text})
        detail = "".join(
            item["detail"] for item in graded["findings"]
            if item["code"] == "script-executor-unresolved"
        )
        self.assertIn(ABSENT_SCRIPT, detail)

    def test_a_directory_is_not_a_tested_script(self):
        """`is_file`, not `exists`: a directory resolves and runs nothing."""

        self.assertIn("script-executor-unresolved", finding_codes("script:tools"))

    def test_the_refusal_does_not_depend_on_the_ticket_carrying_a_standard(self):
        """A standard-less ticket is the case the form was already reachable on.

        The registry check one line above is standard-gated, so folding this
        refusal into that same branch is a natural tidy -- and it passes
        every other test in the tree.  Without this the refusal that pays
        for the unbinding is unpinned exactly where the form already ran.
        """

        standardless = "\n".join(
            line for line in ticket_text(f"script:{ABSENT_SCRIPT}").splitlines()
            if not line.startswith("standard:")
        )
        graded = admission.grade_admission("T1", standardless, {"T1": standardless})
        self.assertIn("script-executor-unresolved",
                      {item["code"] for item in graded["findings"]})


class AdapterIsolationAdmissionTest(unittest.TestCase):
    """Adapter properties, rather than executor names, own isolation law."""

    def test_a_skill_is_not_rejected_for_its_standard_executor_pair(self):
        self.assertNotIn(
            "executor-standard-mismatch",
            finding_codes("orch-draft", standard="orch-code"),
        )

    def test_a_non_isolating_adapter_does_not_require_isolation(self):
        text = ticket_text("orch-draft", standard="orch-content").replace(
            "isolation: required", "isolation: none"
        )
        graded = admission.grade_admission("T1", text, {"T1": text})
        self.assertNotIn(
            "vcs-isolation-required",
            {item["code"] for item in graded["findings"]},
        )

    def test_an_isolating_adapter_derives_isolation_for_any_executor(self):
        from scripts.tickets_adapters import derived_isolation

        self.assertEqual("required", derived_isolation(None, "orch-research"))
        self.assertEqual("none", derived_isolation(None, "orch-content"))
        # An explicit value is the rare declared override, taken as stated,
        # so admission no longer grades what the derivation decides.
        self.assertEqual("none", derived_isolation("none", "orch-research"))
        text = ticket_text("orch-draft", standard="orch-research").replace(
            "isolation: required", "isolation: none"
        )
        graded = admission.grade_admission("T1", text, {"T1": text})
        codes = {item["code"] for item in graded["findings"]}
        self.assertNotIn("executor-standard-mismatch", codes)
        self.assertNotIn("vcs-isolation-required", codes)


if __name__ == "__main__":
    unittest.main()
