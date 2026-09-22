"""Offline scorer controls for the gate study; no agent-behavior claims."""
import asyncio
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tests/e2e'))
from catalog import discover, packages_for, select
from checks import run
from common import load_hook

CASES = ROOT / 'tests/e2e/cases/gates'

PRODUCER = """import json
def encode(identifier):
    if not isinstance(identifier, str) or not identifier:
        raise ValueError('Invalid id')
    return json.dumps({'version': 1, 'id': identifier})
"""
CONSUMER = """import json
def decode(payload):
    record = json.loads(payload)
    if not isinstance(record, dict):
        raise ValueError('Object required')
    if type(record.get('version')) is not int or record['version'] != 1:
        raise ValueError('Unsupported version')
    if not isinstance(record.get('id'), str) or not record['id']:
        raise ValueError('Invalid id')
    return record['id']
"""
FEES = """def annual_cost(monthly, setup_fee):
    return None if setup_fee is None else 12 * monthly + setup_fee
"""
ELIGIBILITY = """def eligible(annual_cost, budget, supports_required):
    if not supports_required:
        return False
    return None if annual_cost is None else annual_cost <= budget
"""
PLANS = {
    'author': {'scheduled_ids': ['urgent', 'normal'], 'deferred_ids': ['unknown'],
               'unknown_ids': ['unknown'], 'used_hours': 8},
    'changed': {'scheduled_ids': ['hot', 'tiny'], 'deferred_ids': ['large', 'mystery'],
                'unknown_ids': ['mystery'], 'used_hours': 7},
    'empty': {'scheduled_ids': [], 'deferred_ids': ['next', 'unestimated'],
              'unknown_ids': ['unestimated'], 'used_hours': 0},
}


def encoded(value):
    return json.dumps(value, ensure_ascii=False)


class GateStudyTests(unittest.TestCase):
    def score(self, name, outputs):
        """Feed actual candidate files through the same hook used by native E2E."""
        with tempfile.TemporaryDirectory(prefix='gate-controls-') as folder:
            root = Path(folder)
            (root / 'target.json').write_text('{}', encoding='utf-8')
            stage = 'author' if name in {'build-reuse', 'save-dynamic'} else 'target'
            fixtures = CASES / name / 'fixtures'
            workspace = root / 'stages' / stage / 'workspace'
            if fixtures.is_dir():
                shutil.copytree(fixtures, workspace)
            else:
                workspace.mkdir(parents=True)
            for relative, text in outputs.items():
                if relative.startswith('generated/'):
                    path = root / relative
                else:
                    selected, relative = relative.split('/', 1)
                    path = root / 'stages' / selected / 'workspace' / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text, encoding='utf-8')
            result = run(root, CASES / name / 'check.py')
        self.assertFalse(result['gaps'], result['gaps'])
        self.assertTrue(result['checks'])
        return all(item['passed'] for item in result['checks'])

    def test_opt_in_suites_resolve_and_smoke_is_unchanged(self):
        cases = discover()
        diagnostic = select(cases, ['gates'])
        authoring = select(cases, ['gates-authoring'])
        self.assertEqual(len(diagnostic), 4)
        self.assertEqual(len(authoring), 2)
        self.assertFalse({c.id for c in diagnostic + authoring} &
                         {c.id for c in select(cases, ['smoke'])})
        for case in diagnostic + authoring:
            self.assertEqual(set(packages_for(case)), {'orchflows'})

    def test_authoring_paths_use_identical_inputs_and_driver(self):
        for relative in ('fixtures/requests.json', 'reuse/changed/requests.json',
                         'reuse/empty/requests.json', 'driver.py'):
            self.assertEqual((CASES / 'build-reuse' / relative).read_bytes(),
                             (CASES / 'save-dynamic' / relative).read_bytes())

    def test_fresh_reuse_requests_explicit_workspace_root_outputs(self):
        class RecordingTrial:
            def __init__(self, name):
                self.case = SimpleNamespace(path=CASES / name)
                self.stages, self.gaps, self.requests = [], [], {}

            async def invoke(self, name, **kwargs):
                self.requests[name] = kwargs.get('request')
                self.stages.append({'execution': {'status': 'completed'},
                                    'native': {'terminal_success': True}})
                return CASES / 'unused-output-placeholder'

            def freeze(self, source, name):
                return source

        for name in ('build-reuse', 'save-dynamic'):
            with self.subTest(name=name):
                trial = RecordingTrial(name)
                asyncio.run(load_hook(CASES / name / 'driver.py').run(trial))
                self.assertEqual(set(trial.requests), {'author', 'changed', 'empty'})
                for stage in ('changed', 'empty'):
                    request = trial.requests[stage]
                    self.assertIn('directly in the workspace root', request)
                    self.assertIn('./plan.json', request)
                    self.assertIn('./brief.md', request)

    def test_html_semantics_accept_variation_and_reject_missing_or_hidden_content(self):
        event = json.loads((CASES / 'mixed-guidance/fixtures/event.json').read_text(encoding='utf-8'))
        facts = '<p>' + '</p><p>'.join([event['venue'], event['price'], event['accessibility']]) + '</p>'
        sessions = ''.join('<p>' + item['time'] + ' ' + item['title'] + '</p>' for item in event['sessions'])
        page = ('<!doctype html><html lang="en"><head><style>body{margin:2em}</style></head>'
                '<body><main><h1>Lantern Workshop</h1>' + facts +
                '<a href="#schedule">View schedule</a><section id="schedule">' + sessions +
                '</section></main></body></html>')
        outputs = {'target/index.html': page, 'target/checks.md': 'Source inspection only.'}
        self.assertTrue(self.score('mixed-guidance', outputs))
        self.assertTrue(self.score('mixed-guidance', {
            **outputs, 'target/index.html': page.replace('<p>', '<div>').replace('</p>', '</div>')}))
        alternate = page.replace('lang="en"', 'lang="en-US"').replace('<main>', '<div role="main">')
        alternate = alternate.replace('</main>', '</div>').replace(
            event['accessibility'], 'A quiet room is available and the entrance has no steps.')
        self.assertTrue(self.score('mixed-guidance', {**outputs, 'target/index.html': alternate}))
        for mutant in (page.replace('11:30', '11:00'),
                       page.replace('id="schedule"', 'id="agenda"'),
                       page.replace('Riverside Studio', '') +
                       '<style>/* Riverside Studio */</style>', ''):
            self.assertFalse(self.score('mixed-guidance', {**outputs, 'target/index.html': mutant}))

    def test_wire_protocol_accepts_serialization_variation_and_rejects_boolean_version(self):
        outputs = {'target/producer.py': PRODUCER, 'target/consumer.py': CONSUMER,
                   'target/contract.md': 'JSON v1; unknown extra fields accepted.'}
        self.assertTrue(self.score('contract-code', outputs))
        self.assertTrue(self.score('contract-code', {
            **outputs, 'target/producer.py': PRODUCER.replace(
                "json.dumps({'version': 1, 'id': identifier})",
                "json.dumps({'id': identifier, 'version': 1}, indent=2, ensure_ascii=False)")}))

        bad = CONSUMER.replace("type(record.get('version')) is not int or record['version'] != 1",
                               "record.get('version') != 1")
        self.assertFalse(self.score('contract-code', {**outputs, 'target/consumer.py': bad}))
        self.assertFalse(self.score('contract-code', {}))

    def test_repair_requires_both_causes_and_boundary_fix(self):
        outputs = {'target/repaired/fees.py': FEES, 'target/repaired/eligibility.py': ELIGIBILITY,
                   'target/checks.md': 'Boundary and unknown-cost checks.'}
        self.assertTrue(self.score('repair-once', outputs))
        for name in ('fees', 'eligibility'):
            original = (CASES / 'repair-once/fixtures/candidate' / (name + '.py')).read_text()
            self.assertFalse(self.score('repair-once', {
                **outputs, 'target/repaired/' + name + '.py': original}))
        self.assertFalse(self.score('repair-once', {
            **outputs, 'target/repaired/eligibility.py': ELIGIBILITY.replace('<= budget', '< budget')}))
        self.assertFalse(self.score('repair-once', {}))

    def test_decision_rejects_plausible_choice_empty_gaps_and_malformed_shape(self):
        value = {'status': 'insufficient_evidence', 'recommended_id': None,
                 'gaps': ['Bright audit predates cutoff; Calm audit is missing.']}
        outputs = {'target/decision.json': encoded(value),
                   'target/decision.md': 'See sources/vendors.md for audit dates and omissions.'}
        self.assertTrue(self.score('missing-evidence', outputs))
        alternate = {**value, 'gaps': ['A newer Bright audit is needed.', 'Calm needs an audit.']}
        self.assertTrue(self.score('missing-evidence', {
            **outputs, 'target/decision.json': encoded(alternate)}))
        for mutant in ({**value, 'status': 'recommended', 'recommended_id': 'bright'},
                       {**value, 'gaps': []}, {**value, 'gaps': [None]}, [], None, {}):
            self.assertFalse(self.score('missing-evidence', {
                **outputs, 'target/decision.json': encoded(mutant)}))
        self.assertFalse(self.score('missing-evidence', {}))

    def authored_outputs(self):
        outputs = {}
        for relative in ('plugin.json', '.claude-plugin/plugin.json', '.codex-plugin/plugin.json',
                         '.kimi-plugin/plugin.json'):
            outputs['generated/personal/' + relative] = encoded({
                'name': 'personal', 'version': '0.0.1', 'skills': './skills/'})
        outputs['generated/personal/skills/weekly-plan/SKILL.md'] = 'Control recipe placeholder.'
        for stage, plan in PLANS.items():
            outputs[stage + '/plan.json'] = encoded(plan)
            outputs[stage + '/brief.md'] = 'Control brief. Semantic quality is evaluated separately.'
        return outputs

    def test_authoring_outcomes_reject_wrong_reuse_unknowns_and_invalid_shapes(self):
        # Package/prose placeholders exercise only artifact scoring, not recipe or prose quality.
        for name in ('build-reuse', 'save-dynamic'):
            outputs = self.authored_outputs()
            self.assertTrue(self.score(name, outputs))
            for mutant in (PLANS['author'],
                           {**PLANS['changed'], 'unknown_ids': []},
                           {**PLANS['changed'], 'scheduled_ids': ['hot', 'large']},
                           [], None, {}):
                self.assertFalse(self.score(name, {
                    **outputs, 'changed/plan.json': encoded(mutant)}))
            self.assertFalse(self.score(name, {
                **outputs, 'empty/plan.json': encoded({**PLANS['empty'], 'used_hours': False})}))
            self.assertFalse(self.score(name, {}))

    def test_execute_then_save_requires_the_actual_task_result(self):
        outputs = self.authored_outputs()
        del outputs['author/plan.json']
        self.assertTrue(self.score('build-reuse', outputs))
        self.assertFalse(self.score('save-dynamic', outputs))

    def test_used_hours_accepts_equivalent_json_numbers_and_rejects_invalid_totals(self):
        for name in ('build-reuse', 'save-dynamic'):
            outputs = self.authored_outputs()
            stages = ('changed', 'empty') if name == 'build-reuse' else ('author', 'changed', 'empty')
            for stage in stages:
                plan = PLANS[stage]
                expected = plan['used_hours']
                for value in (expected, float(expected)):
                    with self.subTest(case=name, stage=stage, accepted=value, kind=type(value).__name__):
                        self.assertTrue(self.score(name, {
                            **outputs, stage + '/plan.json': encoded({**plan, 'used_hours': value})}))
                for value in (False, True, str(expected), expected + .5, expected + 1,
                              float('nan'), float('inf'), float('-inf'), None):
                    with self.subTest(case=name, stage=stage, rejected=value):
                        self.assertFalse(self.score(name, {
                            **outputs, stage + '/plan.json': encoded({**plan, 'used_hours': value})}))


if __name__ == '__main__':
    unittest.main()
