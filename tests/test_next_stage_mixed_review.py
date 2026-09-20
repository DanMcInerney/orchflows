"""Controls for basic page scoring; no claims about rendered or model behavior."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
import json

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / 'tests/e2e/cases/next-stage/mixed-review'
spec = importlib.util.spec_from_file_location('mixed_review_check', CASE / 'check.py')
scorer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scorer)


class Context:
    def __init__(self, root):
        self.root, self.results = root, []

    def stage(self):
        return self.root

    def json(self, path):
        return json.loads(path.read_text(encoding='utf-8'))

    def require(self, condition, requirement, evidence):
        self.results.append(bool(condition))


class MixedReviewChecks(unittest.TestCase):
    def score(self, html):
        with tempfile.TemporaryDirectory(prefix='mixed-review-check-') as raw:
            root = Path(raw)
            (root / 'brief.json').write_bytes((CASE / 'fixtures/brief.json').read_bytes())
            if html is not None:
                (root / 'index.html').write_text(html, encoding='utf-8')
            (root / 'checks.md').write_text('Source checks only.', encoding='utf-8')
            context = Context(root)
            scorer.check(context)
            return all(context.results)

    def valid(self):
        html = (CASE / 'fixtures/candidate/index.html').read_text(encoding='utf-8')
        return html.replace('#agenda', '#schedule').replace(
            "The city's highest-rated creative workshop, trusted by over 10,000 guests.",
            'Fold, shape and play with light.').replace('#b5b5b5', '#46564c')

    def test_accepts_valid_content_and_alternate_anchor(self):
        self.assertTrue(self.score(self.valid()))
        self.assertTrue(self.score(self.valid().replace('#schedule', '#times').replace('id="schedule"', 'id="times"')))

    def test_rejects_seeded_claims_broken_target_wrong_facts_and_absence(self):
        original = (CASE / 'fixtures/candidate/index.html').read_text(encoding='utf-8')
        for html in (original, self.valid().replace('#schedule', '#missing'),
                     self.valid().replace('#schedule', '#missing') + '<a href="#schedule">Other link</a>',
                     self.valid().replace('$24', '$0'), self.valid().replace('11:30', '12:30'), None):
            with self.subTest(html=str(html)[:40]):
                self.assertFalse(self.score(html))


if __name__ == '__main__':
    unittest.main()
