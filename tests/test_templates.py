"""Regression collection for the canonical ticket-template seams.

The case classes live in non-discoverable modules and are re-exported here so
the stable ``tests.test_templates`` seam remains the collection owner.
"""

import unittest

from tests.test_templates_cases import closure as _closure
from tests.test_templates_cases.shape import (
    TestPlaceholders,
    TestStubExecutorResolves,
    TestStubGraph,
    TestStubShape,
    TestTemplateManifest,
    TestTheValidatorRefusesWhatTheOwnerRefuses,
)

TestProducerConsumerClosure = _closure.TestProducerConsumerClosure
TestTemplateBudgets = _closure.TestTemplateBudgets


class TestCanonicalTemplatesClose(_closure.TestCanonicalTemplatesClose):
    def test_every_shipped_composition_passes_its_own_door(self):
        placeholders = {
            "bound": "30m",
            "brief_bound": "30m",
            "executor": "orch-tdd",
            "isolation": "required",
            "mutations": "change:scripts/a.py",
            "oracle_command": "uv run --no-project python -m unittest tests.test_templates",
            "oracle_name": "the named fixture oracle",
            "oracle_provenance": "pre-existing",
            "paths": "scripts/a.py",
            "simple_task": "Deliver one simple code change.",
            "skill": "orch-tdd",
            "target": "scripts/a.py",
            "window": "the last seven days",
        }
        for directory in self.directories():
            manifest = _closure.tickets._parse_frontmatter(
                (directory / _closure.tickets.TEMPLATE_FILE).read_text(encoding="utf-8")
            )
            settings = []
            for name in manifest.get("placeholders") or []:
                settings += ["--set", f"{name}={placeholders.get(name, f'{name}-identity')}"]
            with self.subTest(template=directory.name), _closure._temporary_sink():
                result = _closure.tickets._cmd_instantiate(
                    [str(directory), "--run", f"20260101T000000Z-{directory.name}"]
                    + settings
                )
                self.assertNotIn("error", result, result)

    test_every_canonical_template_instantiates_under_closure = (
        test_every_shipped_composition_passes_its_own_door
    )


if __name__ == "__main__":
    unittest.main()
