"""Offline release-case controls: no native/model execution or behavior claims."""
import asyncio
import json
from pathlib import Path
import shutil
import sys
import tempfile
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tests/e2e'))
from catalog import discover, packages_for, select
from checks import run
from common import load_hook

CASES = ROOT / 'tests/e2e/cases/next-stage'
MANIFESTS = ('plugin.json', '.claude-plugin/plugin.json', '.codex-plugin/plugin.json',
             '.kimi-plugin/plugin.json')


def source_for(stage):
    relative = 'release-direct/fixtures' if stage in ('target', 'representative') else 'release-build/reuse/' + stage
    return json.loads((CASES / relative / 'changes.json').read_text(encoding='utf-8'))


def candidate(stage, layout='headings', unknown='Unknown'):
    """Readable controls, not a proposed implementation of the target workflow."""
    source = source_for(stage)
    notes = [f"# {source['product']} {source['version']} — {source['released_at']}"]
    checklist = ['# Migration checklist']
    for item in source['changes']:
        if item['status'] != 'shipped' or item['visibility'] != 'public':
            continue
        identity = f"[{item['id']}]({item['source_url']})"
        impact = ' '.join(item['details'])
        if item['breaking'] is None:
            impact += ' Compatibility impact: ' + unknown + '.'
        elif item['breaking']:
            impact += ' Breaking change.'
        details = item['migration'] or {}
        action = details.get('action') or unknown
        deadline = details.get('deadline') or unknown
        migration = f'Migration action: {action} Deadline: {deadline}.'
        if item['breaking'] is None:
            migration += ' Compatibility impact: ' + unknown + '.'
        if layout == 'headings':
            notes.append(f'## {identity}: {item["summary"]}\n\n{impact}')
            entry = f'## {identity}\n\n{migration}'
        elif layout == 'bullets':
            notes.append(f'- {identity} — {impact}')
            entry = f'- [ ] {identity} — {migration}'
        elif layout == 'table':
            notes.append(f'| {identity} | {impact} |')
            entry = f'| {identity} | {migration} |'
        else:
            raise AssertionError(layout)
        if item['breaking'] is not False:
            checklist.append(entry)
    if layout == 'table':
        for document in (notes, checklist):
            document.insert(1, '| Change | Details |\n| --- | --- |')
    return {'release-notes.md': '\n\n'.join(notes) + '\n',
            'migration-checklist.md': '\n\n'.join(checklist) + '\n'}


class ReleaseAuthoringCasesTests(unittest.TestCase):
    def score(self, name, outputs, missing_package=None):
        with tempfile.TemporaryDirectory(prefix='release-case-control-') as folder:
            root = Path(folder)
            (root / 'target.json').write_text('{}', encoding='utf-8')
            stages = ('target',) if name == 'release-direct' else ('representative', 'changed', 'sparse')
            for stage in stages:
                fixtures = CASES / name / ('fixtures' if stage in ('target', 'representative') else 'reuse/' + stage)
                shutil.copytree(fixtures, root / 'stages' / stage / 'workspace')
            if name == 'release-build':
                for relative in (*MANIFESTS, 'skills/release-brief/SKILL.md'):
                    if relative == missing_package:
                        continue
                    path = root / 'generated/personal' / relative
                    path.parent.mkdir(parents=True, exist_ok=True)
                    # Presence controls only; package/process validity is independently audited.
                    path.write_text('Offline presence control, not a delivered workflow.', encoding='utf-8')
            for relative, content in outputs.items():
                stage, filename = relative.split('/', 1)
                path = root / 'stages' / stage / 'workspace' / filename
                path.write_text(content, encoding='utf-8')
            result = run(root, CASES / name / 'check.py')
        self.assertEqual(result['gaps'], [], result['gaps'])
        self.assertTrue(result['checks'])
        return all(check['passed'] for check in result['checks'])

    def outputs(self, name, **kwargs):
        stages = ('target',) if name == 'release-direct' else ('representative', 'changed', 'sparse')
        return {stage + '/' + filename: text
                for stage in stages for filename, text in candidate(stage, **kwargs).items()}

    def test_cases_discover_with_core_only_and_do_not_enlarge_smoke(self):
        cases = discover()
        for name, deadline in (('release-direct', 480), ('release-build', 2100)):
            case = cases['core/next-stage/' + name]
            self.assertEqual(set(packages_for(case)), {'orchflows'})
            self.assertEqual(case.timeout, deadline)
            self.assertEqual(case.config['profile'], 'local')
            self.assertNotIn(case.id, {entry.id for entry in select(cases, 'smoke')})
        self.assertNotIn('entrypoint', cases['core/next-stage/release-direct'].config)
        self.assertEqual(cases['core/next-stage/release-build'].config['entrypoint'],
                         'orchflows:orch-build-workflow')

    def test_matching_public_contract_and_evaluator_material_stays_outside_fixtures(self):
        direct, build = CASES / 'release-direct', CASES / 'release-build'
        for filename in ('README.md', 'changes.json'):
            self.assertEqual((direct / 'fixtures' / filename).read_bytes(),
                             (build / 'fixtures' / filename).read_bytes())
        for folder in (direct / 'fixtures', build / 'fixtures',
                       build / 'reuse/changed', build / 'reuse/sparse'):
            self.assertEqual({p.name for p in folder.iterdir()}, {'README.md', 'changes.json'})
            self.assertEqual((folder / 'README.md').read_bytes(),
                             (direct / 'fixtures/README.md').read_bytes())
        for case in (direct, build):
            for filename in ('check.py', 'predictions.md', 'expected-behavior.md'):
                self.assertTrue((case / filename).is_file())

    def test_direct_request_is_outcome_only_and_build_records_native_trial_evidence(self):
        direct = (CASES / 'release-direct/request.md').read_text(encoding='utf-8').lower()
        for process_hint in ('agent', 'review', 'gate', 'workflow', 'trial'):
            self.assertNotIn(process_hint, direct)
        build = (CASES / 'release-build/request.md').read_text(encoding='utf-8')
        self.assertIn('author-only', build)
        self.assertIn('actual native trial session IDs', build)
        self.assertIn('model-service transport is permitted', build)
        self.assertIn('at most four child agents', build)

    def test_source_shapes_and_unseen_identifiers_are_distinct(self):
        identities = []
        for stage in ('target', 'changed', 'sparse'):
            source = source_for(stage)
            ids = {item['id'] for item in source['changes']}
            self.assertEqual(len(ids), len(source['changes']))
            identities.append(ids)
            for item in source['changes']:
                self.assertRegex(item['id'], r'^REL-\d{3}$')
                self.assertIn(item['status'], ('shipped', 'planned'))
                self.assertIn(item['visibility'], ('public', 'internal'))
                self.assertIsInstance(item['details'], list)
                self.assertTrue(item['breaking'] is None or type(item['breaking']) is bool)
                if item['migration'] is not None:
                    self.assertEqual(set(item['migration']), {'action', 'deadline'})
        self.assertFalse(identities[0] & identities[1] or identities[0] & identities[2]
                         or identities[1] & identities[2])

    def test_headings_bullets_tables_and_equivalent_unknown_labels_pass(self):
        for name in ('release-direct', 'release-build'):
            for layout in ('headings', 'bullets', 'table'):
                for label in ('Unknown', 'Not provided', 'Unspecified', 'Needs confirmation',
                              'What does the release owner require?'):
                    with self.subTest(case=name, layout=layout, label=label):
                        self.assertTrue(self.score(name, self.outputs(name, layout=layout, unknown=label)))

    def test_reference_links_and_additional_clear_prose_pass(self):
        outputs = self.outputs('release-direct')
        for key, text in outputs.items():
            links = []
            for item in source_for('target')['changes']:
                inline = f'[{item["id"]}]({item["source_url"]})'
                if inline in text:
                    text = text.replace(inline, f'[{item["id"]}][source-{item["id"]}]')
                    links.append(f'[source-{item["id"]}]: {item["source_url"]}')
            outputs[key] = text + '\n' + '\n'.join(links) + '\n\nThese drafts reflect the supplied release source.\n'
        self.assertTrue(self.score('release-direct', outputs))

    def test_readable_date_formats_and_item_subheadings_pass(self):
        outputs = self.outputs('release-direct')
        notes = 'target/release-notes.md'
        checklist = 'target/migration-checklist.md'
        for displayed_release, displayed_deadline in (('September 18, 2026', 'December 1, 2026'),
                                                      ('18 Sept 2026', '1 Dec 2026'),
                                                      ('September 18th, 2026', 'December 1st, 2026')):
            with self.subTest(date=displayed_release):
                changed = {**outputs,
                           notes: outputs[notes].replace('2026-09-18', displayed_release),
                           checklist: outputs[checklist].replace('2026-12-01', displayed_deadline)
                               .replace('\n\nMigration action:', '\n\n### Migration details\n\nMigration action:')}
                self.assertTrue(self.score('release-direct', changed))

    def test_missing_outputs_and_wrong_release_identity_fail(self):
        for name in ('release-direct', 'release-build'):
            good = self.outputs(name)
            self.assertFalse(self.score(name, {}))
            for key in good:
                with self.subTest(case=name, missing=key):
                    self.assertFalse(self.score(name, {k: v for k, v in good.items() if k != key}))
            stage = 'target' if name == 'release-direct' else 'changed'
            key = stage + '/release-notes.md'
            for field in ('product', 'version', 'released_at'):
                bad = good[key].replace(source_for(stage)[field], 'WRONG')
                self.assertFalse(self.score(name, {**good, key: bad}))

    def test_omitted_ids_url_only_ids_and_missing_links_fail(self):
        good = self.outputs('release-direct')
        key = 'target/release-notes.md'
        identifier = 'REL-110'
        url = source_for('target')['changes'][0]['source_url']
        for bad in (good[key].replace(f'[{identifier}]({url})', f'[Source]({url})'),
                    good[key].replace(url, 'https://unrelated.example/notice'),
                    good[key].replace(f'[{identifier}]({url})', identifier)):
            self.assertFalse(self.score('release-direct', {**good, key: bad}))

    def test_excluded_planned_internal_or_extra_migration_items_fail(self):
        good = self.outputs('release-direct')
        for item in (source_for('target')['changes'][4], source_for('target')['changes'][5]):
            key = 'target/release-notes.md'
            leak = f'\n- [{item["id"]}]({item["source_url"]}) {item["summary"]}\n'
            self.assertFalse(self.score('release-direct', {**good, key: good[key] + leak}))
        extra = source_for('target')['changes'][0]
        key = 'target/migration-checklist.md'
        leak = f'\n- [{extra["id"]}]({extra["source_url"]}) No migration action.\n'
        self.assertFalse(self.score('release-direct', {**good, key: good[key] + leak}))

    def test_missing_unknowns_and_borrowed_deadlines_fail(self):
        for name in ('release-direct', 'release-build'):
            good = self.outputs(name)
            stage = 'target' if name == 'release-direct' else 'sparse'
            key = stage + '/migration-checklist.md'
            for replacement in ('No action needed', '2027-02-01'):
                self.assertFalse(self.score(name, {**good, key: good[key].replace('Unknown', replacement)}))
        good = self.outputs('release-build')
        key = 'sparse/release-notes.md'
        self.assertFalse(self.score('release-build', {
            **good, key: good[key].replace('Compatibility impact: Unknown.', 'Fully backward compatible.')}))

    def test_known_deadline_loss_and_stale_author_example_fail(self):
        for name, stage, date in (('release-direct', 'target', '2026-12-01'),
                                  ('release-build', 'changed', '2027-01-15')):
            good = self.outputs(name)
            key = stage + '/migration-checklist.md'
            self.assertFalse(self.score(name, {**good, key: good[key].replace(date, '2027-02-01')}))
        good = self.outputs('release-build')
        stale = {'changed/' + key: text for key, text in candidate('target').items()}
        self.assertFalse(self.score('release-build', {**good, **stale}))

    def test_hidden_or_code_dumped_identifiers_do_not_satisfy_visible_output(self):
        good = self.outputs('release-direct')
        key = 'target/release-notes.md'
        for wrapper in ('<!--\n{}\n-->', '```markdown\n{}\n```', '<style>{}</style>'):
            self.assertFalse(self.score('release-direct', {**good, key: wrapper.format(good[key])}))

    def test_build_requires_package_but_not_author_example_task_delivery(self):
        good = self.outputs('release-build')
        self.assertTrue(self.score('release-build', good))
        for relative in (*MANIFESTS, 'skills/release-brief/SKILL.md'):
            self.assertFalse(self.score('release-build', good, missing_package=relative))

    def recording_trial(self, folder, *, status='completed', success=True):
        case_path = CASES / 'release-build'

        class RecordingTrial:
            def __init__(self):
                self.case = SimpleNamespace(path=case_path)
                self.stages, self.gaps, self.events, self.calls = [], [], [], {}
                self.active, self.peak = 0, 0

            async def invoke(self, name, **kwargs):
                self.events.append(name)
                self.calls[name] = kwargs
                self.active += 1
                self.peak = max(self.peak, self.active)
                await asyncio.sleep(0)
                self.active -= 1
                self.stages.append({'name': name, 'execution': {'status': status},
                                    'native': {'terminal_success': success}})
                return Path(folder) / 'stages' / name / 'workspace'

            def freeze(self, source, name):
                self.events.append('freeze')
                self.frozen_from, self.frozen_name = source, name
                # The mock does not generate a substitute package.
                return Path(folder) / 'generated' / name

        return RecordingTrial()

    def test_driver_scopes_transport_budgets_and_freezes_author_package_before_parallel_reuse(self):
        with tempfile.TemporaryDirectory() as folder:
            trial = self.recording_trial(folder)
            asyncio.run(load_hook(CASES / 'release-build/driver.py').run(trial))
            self.assertEqual(trial.events[:2], ['author', 'freeze'])
            self.assertEqual(set(trial.calls), {'author', 'representative', 'changed', 'sparse'})
            self.assertEqual(trial.calls['author'], {'profile': 'authoring', 'timeout': 900})
            self.assertEqual(trial.frozen_from,
                             Path(folder) / 'stages/author/workspace/.orchflows/libraries/personal')
            self.assertEqual(trial.frozen_name, 'personal')
            self.assertEqual(trial.peak, 3)
            for name in ('representative', 'changed', 'sparse'):
                call = trial.calls[name]
                self.assertEqual(call['profile'], 'local')
                self.assertEqual(call['timeout'], 480)
                self.assertEqual(call['entrypoint'], 'personal:release-brief')
                self.assertEqual(call['packages'], {'personal': Path(folder) / 'generated/personal'})
                self.assertEqual(call['fixtures'], CASES / 'release-build' / (
                    'fixtures' if name == 'representative' else 'reuse/' + name))
                for output in ('./release-notes.md', './migration-checklist.md'):
                    self.assertIn(output, call['request'])
                self.assertIn('at most four child agents', call['request'])
                self.assertNotIn('model', call)

    def test_driver_does_not_freeze_or_reuse_incomplete_authoring(self):
        for status, success in (('timeout', False), ('completed', False), ('failed', True)):
            with self.subTest(status=status, success=success), tempfile.TemporaryDirectory() as folder:
                trial = self.recording_trial(folder, status=status, success=success)
                asyncio.run(load_hook(CASES / 'release-build/driver.py').run(trial))
                self.assertEqual(trial.events, ['author'])
                self.assertEqual(len(trial.gaps), 1)
                self.assertIn('did not complete', trial.gaps[0])


if __name__ == '__main__':
    unittest.main()
