"""The routine method's documented plan crosses the executable validation seam."""

import copy
import json
from pathlib import Path
import re
import unittest

from acquire_plan import PlanError, validate


ROOT = Path(__file__).resolve().parents[1]


class SkillPreparationContractTests(unittest.TestCase):
    def test_method_links_reachable_essential_and_manual_owners(self):
        links = set(re.findall(r"\]\(([^)#]+)", (ROOT / "SKILL.md").read_text(encoding="utf-8")))
        required = {"references/acquisition.md", "references/selection-routes.md",
                    "references/protocol.md", "references/operating.md"}
        self.assertTrue(required <= links)
        self.assertTrue(all((ROOT / link).is_file() for link in required))

    def test_documented_plan_validates_and_its_wrong_cap_is_refused(self):
        method = (ROOT / "references/acquisition.md").read_text(encoding="utf-8")
        plan = json.loads(re.search(r"```json\n(.*?)\n```", method, re.DOTALL).group(1))
        manifest = validate(plan)
        self.assertEqual(manifest.steps[0].window_end, plan["window"]["end"])
        wrong = copy.deepcopy(plan)
        wrong["limits"]["max_records"] = 1
        with self.assertRaises(PlanError):
            validate(wrong)


if __name__ == "__main__":
    unittest.main()
