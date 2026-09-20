"""Offline artifact-scorer controls; these are not native process evaluations."""
from copy import deepcopy
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tests/e2e'))
from catalog import discover, packages_for
from checks import run

CASES = ROOT / 'tests/e2e/cases/next-stage'


def metric(responses, answered, total, favorable, rec_answered, yes):
    """Control values are hand-counted, independent of the scorer's CSV reader."""
    return {'responses': responses,
            'satisfaction': {'answered': answered, 'missing': responses - answered,
                             'mean': round(total / answered, 2), 'favorable': favorable,
                             'pct_favorable': round(100 * favorable / answered, 2)},
            'recommend': {'answered': rec_answered, 'missing': responses - rec_answered,
                          'yes': yes, 'pct_yes': round(100 * yes / rec_answered, 2)}}


SUMMARY = {'overall': metric(24, 19, 69, 11, 19, 12),
           'department': {'Support': metric(8, 6, 22, 4, 6, 4),
                          'Product': metric(8, 7, 30, 6, 7, 6),
                          'Operations': metric(8, 6, 17, 1, 6, 2)},
           'tenure': {'Under 1 year': metric(12, 10, 37, 6, 10, 5),
                      '1 year or more': metric(11, 8, 29, 5, 8, 6),
                      'Unknown': metric(1, 1, 3, 0, 1, 1)}}


def report_page():
    rows = []
    for groups in ({'Overall': SUMMARY['overall']}, SUMMARY['department'], SUMMARY['tenure']):
        for group, value in groups.items():
            sat, rec = value['satisfaction'], value['recommend']
            cells = [group, value['responses'], sat['answered'], sat['missing'], sat['mean'],
                     str(sat['favorable']) + '/' + str(sat['answered']) + ' (' + str(sat['pct_favorable']) + '%)',
                     rec['answered'], rec['missing'],
                     str(rec['yes']) + '/' + str(rec['answered']) + ' (' + str(rec['pct_yes']) + '%)']
            rows.append('<tr><th>' + str(cells[0]) + '</th>' + ''.join('<td>' + str(cell) + '</td>'
                                                                    for cell in cells[1:]) + '</tr>')
    charts = []
    for dimension, measure, numerator in [('department', 'satisfaction', 'pct_favorable'),
                                           ('tenure', 'recommend', 'pct_yes')]:
        bars = []
        for i, (group, value) in enumerate(SUMMARY[dimension].items()):
            data = value[measure]
            count = data['favorable' if measure == 'satisfaction' else 'yes']
            label = group + ': ' + str(data[numerator]) + '% (' + str(count) + '/' + str(data['answered']) + ')'
            bars.append('<rect x="0" y="' + str(i * 25) + '" width="' + str(data[numerator]) +
                        '" height="10"/><text x="110" y="' + str(i * 25 + 10) + '">' + label + '</text>')
        title = 'Favorable satisfaction by department' if dimension == 'department' else 'Recommendation yes by tenure'
        charts.append('<h2>' + title + '</h2><svg viewBox="0 0 450 110"><title>' + title +
                      '</title>' + ''.join(bars) + '<text x="0" y="105">0–100% of answered records</text></svg>')
    headings = ['Group', 'Responses', 'Satisfaction answered', 'Satisfaction missing', 'Mean satisfaction',
                'Favorable', 'Recommendation answered', 'Recommendation missing', 'Recommendation yes']
    return ('<!doctype html><html lang="en"><head><style>body{margin:2em}svg{width:100%;max-width:50em}'
            'td,th{padding:.3em}rect{fill:teal}</style></head><body><main><h1>Survey respondents</h1>'
            '<p>Among 24 respondents, 11 of 19 answered satisfaction scores were favorable. '
            'Product had the highest observed rate (6/7), and Operations the lowest (1/6).</p>' +
            ''.join(charts) + '<table><tr>' + ''.join('<th>' + label + '</th>' for label in headings) +
            '</tr>' + ''.join(rows) + '</table><h2>Limits and next steps</h2>'
            '<p>This synthetic convenience sample cannot establish workforce rates, participation, causality '
            'or significance. Five answers are missing per measure on different rows; denominators exclude '
            'only that measure’s missing answers. Unknown tenure is one person, so its 100% is fragile.</p>'
            '<ol><li>Invite Operations respondents to describe difficulties without presuming a cause.</li>'
            '<li>Use a broader systematic follow-up and record invitation counts and missingness.</li></ol>'
            '</main></body></html>')


ATLAS = '''from decimal import Decimal, InvalidOperation
def normalize(record):
    if not isinstance(record, dict):
        raise ValueError('Object required')
    identifier, timing, result = record.get('ref'), record.get('timing'), record.get('result')
    if not isinstance(identifier, str) or not identifier or not isinstance(timing, dict):
        raise ValueError('Invalid identifier or timing')
    value = timing.get('seconds')
    if not isinstance(value, str) or result not in ('passed', 'failed'):
        raise ValueError('Invalid duration or outcome')
    try:
        elapsed = Decimal(value) * 1000
        if not elapsed.is_finite() or elapsed < 0 or elapsed != elapsed.to_integral_value():
            raise ValueError('Invalid duration')
    except InvalidOperation as error:
        raise ValueError('Invalid decimal') from error
    return dict(id=identifier, elapsed_ms=int(elapsed), outcome='success' if result == 'passed' else 'failure')
'''

BEACON = '''def normalize(record):
    if not isinstance(record, dict):
        raise ValueError('Object required')
    identifier, elapsed, state = record.get('key'), record.get('elapsed'), record.get('state')
    if not isinstance(identifier, str) or not identifier or type(elapsed) is not int:
        raise ValueError('Invalid identifier or duration')
    if elapsed < 0 or elapsed % 1000 or state not in ('complete', 'error'):
        raise ValueError('Invalid duration or outcome')
    return dict(id=identifier, elapsed_ms=elapsed // 1000, outcome='success' if state == 'complete' else 'failure')
'''

TESTS = '''import unittest
from atlas import normalize as a
from beacon import normalize as b
class Adapters(unittest.TestCase):
    def test_current_exports(self):
        for state, outcome in [('passed','success'), ('failed','failure')]:
            for seconds, milliseconds in [('1.25',1250), ('0',0), ('0.001',1)]:
                self.assertEqual(a(dict(ref='001', timing={'seconds':seconds}, result=state)),
                                 dict(id='001', elapsed_ms=milliseconds, outcome=outcome))
        for state, outcome in [('complete','success'), ('error','failure')]:
            for micros, milliseconds in [(1000,1), (0,0), (1250000,1250)]:
                self.assertEqual(b(dict(key='002', elapsed=micros, state=state)),
                                 dict(id='002', elapsed_ms=milliseconds, outcome=outcome))
    def test_bad_exports(self):
        for fn in (a, b):
            with self.assertRaises(ValueError):
                fn({})
'''


class PlainCaseScoringTests(unittest.TestCase):
    def score(self, name, outputs):
        with tempfile.TemporaryDirectory(prefix='next-stage-controls-') as folder:
            root = Path(folder)
            (root / 'target.json').write_text('{}', encoding='utf-8')
            workspace = root / 'stages/target/workspace'
            shutil.copytree(CASES / name / 'fixtures', workspace)
            for relative, value in outputs.items():
                path = workspace / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(value, encoding='utf-8')
            result = run(root, CASES / name / 'check.py')
        self.assertEqual(result['gaps'], [], result)
        self.assertTrue(result['checks'], result)
        return all(item['passed'] for item in result['checks'])

    def survey(self):
        return {'summary.json': json.dumps(SUMMARY), 'report.html': report_page(),
                'checks.md': 'Recomputed counts and inspected source. Rendering was not checked.'}

    def adapters(self):
        return {'atlas.py': ATLAS, 'beacon.py': BEACON, 'tests/test_adapters.py': TESTS,
                'research.md': 'deployments.md pins Atlas 3 and Beacon 2; beacon-correction.md overrides '
                               'the original reference. Newer quickstart edit dates do not migrate schemas.'}

    def test_core_only_manifests_and_private_evaluator_material(self):
        cases = discover()
        for name in ('survey-brief', 'research-code-plain'):
            case = cases['core/next-stage/' + name]
            self.assertEqual(case.config['entrypoint'], 'orchflows:orch-dynamic-workflow')
            self.assertEqual(set(packages_for(case)), {'orchflows'})
            self.assertTrue(600 <= case.timeout <= 900)
            self.assertTrue((case.path / 'predictions.md').is_file())
            request = (case.path / 'request.md').read_text(encoding='utf-8').lower()
            for term in ('reviewer', 'gate', 'parallel', 'staffing', 'phase', 'model', 'research-first'):
                self.assertNotRegex(request, r'\b' + term + r's?\b')
            self.assertFalse(any(path.name in {'check.py', 'predictions.md', 'expected-behavior.md'}
                                 for path in (case.path / 'fixtures').rglob('*')))

    def test_survey_accepts_order_markup_and_numeric_variation(self):
        outputs = self.survey()
        self.assertTrue(self.score('survey-brief', outputs))
        alternate = deepcopy(SUMMARY)
        alternate['overall']['responses'] = 24.0
        alternate['overall']['satisfaction']['mean'] = 69 / 19
        alternate['department'] = dict(reversed(list(alternate['department'].items())))
        page = report_page().replace('<main>', '<div role="main">').replace('</main>', '</div>')
        page = page.replace('lang="en"', 'lang="en-US"').replace('<title>', '<text>').replace('</title>', '</text>')
        self.assertTrue(self.score('survey-brief', {**outputs, 'summary.json': json.dumps(alternate),
                                                   'report.html': page}))

    def test_survey_rejects_wrong_denominators_and_missing_segments(self):
        outputs = self.survey()
        variants = []
        wrong = deepcopy(SUMMARY)
        wrong['overall']['satisfaction']['pct_favorable'] = 100 * 11 / 24
        variants.append(wrong)
        wrong = deepcopy(SUMMARY)
        wrong['department']['Support']['recommend']['pct_yes'] = 50
        variants.append(wrong)
        wrong = deepcopy(SUMMARY)
        wrong['tenure'].pop('Unknown')
        variants.append(wrong)
        wrong = deepcopy(SUMMARY)
        wrong['tenure']['Unknown']['responses'] = True
        variants.append(wrong)
        for value in variants:
            with self.subTest(value=value):
                self.assertFalse(self.score('survey-brief', {**outputs, 'summary.json': json.dumps(value)}))

    def test_survey_rejects_malformed_values_and_omitted_artifacts(self):
        outputs = self.survey()
        for value in (None, [], {}, {'overall': []}, {'overall': {'responses': '24'}}):
            self.assertFalse(self.score('survey-brief', {**outputs, 'summary.json': json.dumps(value)}))
        for number in (float('nan'), float('inf'), '3.63', True):
            value = deepcopy(SUMMARY)
            value['overall']['satisfaction']['mean'] = number
            self.assertFalse(self.score('survey-brief', {**outputs, 'summary.json': json.dumps(value)}))
        self.assertFalse(self.score('survey-brief', {**outputs, 'summary.json': '{broken'}))
        for name in outputs:
            self.assertFalse(self.score('survey-brief', {k: v for k, v in outputs.items() if k != name}))
        for page in ('', report_page().replace('<svg ', '<div ').replace('</svg>', '</div>'),
                     report_page().replace('<style>', '<style>@import "https://example.invalid/style.css";')):
            self.assertFalse(self.score('survey-brief', {**outputs, 'report.html': page}))

    def test_adapters_accept_two_independent_implementation_shapes(self):
        outputs = self.adapters()
        self.assertTrue(self.score('research-code-plain', outputs))
        alternate = ATLAS.replace('from decimal import Decimal, InvalidOperation', 'from fractions import Fraction')
        alternate = alternate.replace('Decimal(value)', 'Fraction(value)')
        alternate = alternate.replace('not elapsed.is_finite() or elapsed < 0 or elapsed != elapsed.to_integral_value()',
                                      'elapsed < 0 or elapsed.denominator != 1')
        alternate = alternate.replace('except InvalidOperation as error:', 'except (ValueError, ZeroDivisionError) as error:')
        self.assertTrue(self.score('research-code-plain', {**outputs, 'atlas.py': alternate,
            'beacon.py': BEACON.replace('elapsed // 1000', 'divmod(elapsed, 1000)[0]')}))

    def test_adapters_reject_retired_units_status_and_lossy_math(self):
        outputs = self.adapters()
        mutants = [
            {'beacon.py': BEACON.replace('elapsed // 1000', 'elapsed')},
            {'beacon.py': BEACON.replace("'complete'", "'done'")},
            {'atlas.py': ATLAS.replace('int(elapsed)', 'int(float(elapsed))')},
            {'atlas.py': "def normalize(record):\n    return dict(id=str(record['id']), elapsed_ms=record['elapsed_ms'], outcome='success' if record['ok'] else 'failure')\n"},
        ]
        for mutant in mutants:
            with self.subTest(mutant=mutant):
                self.assertFalse(self.score('research-code-plain', {**outputs, **mutant}))

    def test_adapters_reject_missing_malformed_and_empty_test_outputs(self):
        outputs = self.adapters()
        for name in outputs:
            self.assertFalse(self.score('research-code-plain', {k: v for k, v in outputs.items() if k != name}))
        for mutant in ({'atlas.py': 'not valid Python!!!'},
                       {'beacon.py': 'def normalize(record):\n    return []\n'},
                       {'tests/test_adapters.py': '# no discovered tests\n'},
                       {'tests/test_adapters.py': TESTS.replace("fn({})", "fn(dict(key='x', elapsed=1000, state='complete'))")},
                       {'research.md': ''}):
            self.assertFalse(self.score('research-code-plain', {**outputs, **mutant}))


if __name__ == '__main__':
    unittest.main()
