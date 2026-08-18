"""Case-set guards against the retired benchmark seal."""

import unittest

from tests.test_validate_cases_schema import (
    CASES,
    COMPONENT_DIGEST_KEYS,
    COMPONENTS,
    DIGEST_RE,
    REPO_ROOT,
    RETIRED_RECIPE_PHRASES,
    RETIRED_TOKENS,
    case_documents,
    case_files,
    walk_objects,
)


class RetiredSealTest(unittest.TestCase):
    """T05a criterion 2: no case demands a sealed package."""

    def test_no_case_file_names_a_retired_seal_field(self):
        offenders = []
        for path in case_files():
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            for line_number, line in enumerate(text.splitlines(), 1):
                for token in RETIRED_TOKENS:
                    if token in line:
                        offenders.append(
                            "%s:%d %s"
                            % (path.relative_to(REPO_ROOT), line_number, line.strip()[:110])
                        )
        self.assertEqual([], offenders, "%d line(s) name a retired seal field" % len(offenders))

    def test_no_component_reference_carries_a_digest_beside_its_locator(self):
        offenders = []
        for path, data in case_documents():
            for obj in walk_objects(data):
                if not isinstance(obj.get("locator"), str):
                    continue
                for key in COMPONENT_DIGEST_KEYS:
                    value = obj.get(key)
                    if isinstance(value, str) and DIGEST_RE.search(value):
                        offenders.append(
                            "%s: {%r: %r} beside locator %r"
                            % (path.relative_to(REPO_ROOT), key, value[:24], obj["locator"])
                        )
        self.assertEqual([], offenders, "%d component digest(s) survive" % len(offenders))

    def test_no_qualification_cover_addresses_a_component_by_digest(self):
        offenders = []
        for path, data in case_documents():
            for obj in walk_objects(data):
                covers = obj.get("covers")
                if covers is None:
                    continue
                values = []
                if isinstance(covers, str):
                    values = [covers]
                elif isinstance(covers, list):
                    values = [v for v in covers if isinstance(v, str)]
                elif isinstance(covers, dict):
                    values = [v for v in covers.values() if isinstance(v, str)]
                for value in values:
                    if DIGEST_RE.search(value):
                        offenders.append(
                            "%s: covers %r" % (path.relative_to(REPO_ROOT), value[:70])
                        )
        self.assertEqual([], offenders, "%d cover(s) address a component by digest" % len(offenders))

    def test_every_interchange_states_the_surviving_manifest_schema(self):
        """T05a criterion 3: contracts name locators, not retired seals."""
        contracts = sorted(CASES.glob("*/evidence/interchange.md"))
        self.assertEqual(13, len(contracts), "the interchange contract set moved")
        offenders = []
        for path in contracts:
            text = path.read_text(encoding="utf-8")
            lowered = text.lower()
            name = path.relative_to(CASES).parts[0]
            if "manifest" not in lowered:
                continue
            for phrase in RETIRED_RECIPE_PHRASES:
                if phrase in lowered:
                    offenders.append("%s: states %r" % (name, phrase))
            if "locator" not in lowered:
                offenders.append("%s: names no component locator" % name)
            for component in COMPONENTS:
                if component not in text:
                    offenders.append("%s: omits component %r" % (name, component))
        self.assertEqual([], offenders, "%d interchange defect(s)" % len(offenders))
