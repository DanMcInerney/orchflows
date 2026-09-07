"""Can-fail harness tests. The native event producer is a control, not a model run."""
import json
import shutil
from pathlib import Path
import sys
import tempfile
import unittest



class CalibrationFixture:
    def setUp(self):
        from tests import test_benchmaker_calibration as api
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.revision = self.git_repository(self.root / 'product')
        self.source_revision = self.git_repository(self.root / 'source')
        self.config = {'model': 'test-event-control', 'reasoning_effort': 'low'}
        self.policy = dict(case_ids=['case'], split='development', round=0,
                           trials_per_case=1, target_configuration=self.config, band=[0.3, 0.5])
        self.prompt = self.root / 'prompt.txt'
        self.prompt.write_text('Return source implementing solve(x) = x + 1.', encoding='utf-8')
        self.checks = self.root / 'checks.json'
        api.write_json(self.checks, {'checks': [{'args': [2], 'expected': 3}, {'args': [-1], 'expected': 0}]})

    def git_repository(self, path):
        from tests import test_benchmaker_calibration as api
        path.mkdir()
        for command in (['git', 'init', '-q'], ['git', '-c', 'user.name=Fixture', '-c',
                        'user.email=fixture@example.invalid', 'commit', '--allow-empty', '-qm', 'fixture']):
            result = api.run_process(command, cwd=path, timeout=10)
            self.assertEqual(result['exit_code'], 0, result['stderr'])
        return api.run_process(['git', 'rev-parse', 'HEAD'], cwd=path, timeout=10)['stdout'].decode().strip()

    def attempt(self, source='def solve(x): return x + 1', name='attempt', code=None, timeout=5, configuration_observation=None):
        from tests import test_benchmaker_calibration as api
        events = [{'type': 'turn.started'}, {'type': 'item.completed', 'item': {
            'type': 'agent_message', 'text': json.dumps({'source': source})}},
            {'type': 'turn.completed', 'usage': {'input_tokens': 3, 'output_tokens': 4}}]
        script = self.root / (name + '.py')
        script.write_text(code or 'print(' + repr('\n'.join(json.dumps(e) for e in events)) + ')', encoding='utf-8')
        api.collect([sys.executable, '-u', str(script)], case_repository=self.root, prompt=self.prompt,
                output=self.root / name, configuration=self.config, timeout=timeout,
                configuration_observation=configuration_observation)
        return api.make_record(self.root / name / 'launch.json', self.checks, dict(
            case_id='case', split='development', round=0, trial=1,
            target_configuration=self.config, benchmark_revision=self.revision, candidate_kind='agent_attempt'))

    def envelope(self, record):
        from tests import test_benchmaker_calibration as api
        product = self.root / 'product'
        evidence = self.root / 'evidence'
        evidence.mkdir()
        (product / 'benchmark').mkdir()
        manifest = product / 'benchmark' / 'manifest.json'
        api.write_json(manifest, dict(schema_version=2, profile='empirical-calibration', target_configuration=self.config))
        source = self.root / 'source'
        shutil.copytree(api.SCRIPTS.parent, source / 'example-workflows' / 'benchmaker', ignore=shutil.ignore_patterns('__pycache__'))
        shutil.copytree(api.SCRIPTS.parents[2] / 'scripts', source / 'scripts', ignore=shutil.ignore_patterns('__pycache__'))
        for command in (['git', 'add', '.'], ['git', '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '-qm', 'source fixture']):
            self.assertEqual(api.run_process(command, cwd=source, timeout=20)['exit_code'], 0)
        self.source_revision = api.run_process(['git', 'rev-parse', 'HEAD'], cwd=source, timeout=10)['stdout'].decode().strip()
        invoked = product / '.orchflows' / 'workflows' / 'benchmaker'
        shutil.copytree(source / 'example-workflows' / 'benchmaker', invoked)
        components = {}
        for name in ('benchmark-construct', 'benchmark-qualify', 'benchmark-calibrate', 'benchmark-quality', 'benchmark-evidence'):
            kind, filename = ('standards', 'STANDARD.md') if name in {'benchmark-quality', 'benchmark-evidence'} else ('workflows', 'SKILL.md')
            components[name] = str(invoked / kind / name / filename)
        from scripts.tickets_pins import tree_digest
        pin = tree_digest('workflow', invoked)
        for command in (['git', 'add', '.'], ['git', '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '-qm', 'benchmark fixture']):
            self.assertEqual(api.run_process(command, cwd=product, timeout=10)['exit_code'], 0)
        self.revision = api.run_process(['git', 'rev-parse', 'HEAD'], cwd=product, timeout=10)['stdout'].decode().strip()
        record['benchmark_revision'] = self.revision
        api.write_json(self.root / 'attempt' / 'attempt.json', record)
        summary = self.root / 'summary.json'
        api.write_json(summary, api.summarize([record], self.policy))
        audit = evidence / 'audit.json'
        api.write_json(audit, {'fixture': 'independent audit control'})
        journal = evidence / 'journal.md'
        journal.write_text('---\nid: fixture\nrun: fixture-run\nworkflow: benchmaker\nworkflow_digest: ' + pin +
            '\nstandards: [benchmark-quality@sha256:control]\n---\n## Report\nartifact: git:' + self.revision + '\nfindings: ' + str(audit) + '\n', encoding='utf-8')
        value = dict(benchmark_manifest=str(manifest), component_locators=components,
            runtime=dict(run='fixture-run', frame='fixture', tickets=['fixture'],
                standard_pins={'maker': ['benchmark-quality@sha256:control'], 'judge': ['benchmark-quality@sha256:control']},
                artifacts=['git:' + self.revision], findings=[str(audit)], workflow_digest=pin,
                package_revision=self.source_revision, journal_locators=[str(journal)]),
            qualification=dict(validity='VALID', revisions={self.revision: dict(validity='VALID', criterion_gaps=[])},
                audits=[dict(case_id='case', benchmark_revision=self.revision,
                builder='builder-control', auditor='auditor-control', reference_outcome='PASS',
                inert_outcome='FAIL', near_miss_outcome='FAIL', evidence_locator=str(audit))]),
            rounds=[dict(policy=self.policy, attempts=[str(self.root / 'attempt' / 'attempt.json')],
                         qualification_revision=self.revision, validity='VALID',
                         summary=str(summary), criterion_gaps=[])], revision_ledger=[],
            infrastructure_retry_budget=0, selected_development_round=0,
            development_decision=api.summarize([record], self.policy)['decision'],
            frozen_revision=None, final_record=None, decision=api.summarize([record], self.policy)['decision'])
        api.write_json(evidence / 'admission.json', value)
        return value
