"""External evidence probe; it replays graders rather than trusting row labels."""
from pathlib import Path

from grader import grade
from native import classify_execution, digest, parse_native, read_json
from records import INFRA, require, summarize
from provenance import check_runtime, check_revision, check_manifest_revision, check_frozen


def check_attempt(record, policy):
    receipt = read_json(record['launch_receipt_locator'])
    for field in ('requested_command', 'resolved_command', 'requested_configuration',
                  'resolved_configuration', 'raw_transcript_locator', 'prompt_locator',
                  'result_artifact_locator', 'exit_code', 'elapsed_seconds', 'token_usage', 'classification'):
        require(record[field] == receipt[field], 'receipt mismatch: ' + field)
    if 'configuration_observation' in receipt:
        observation = receipt['configuration_observation']
        require(digest(observation['locator']) == observation['sha256'] and
                digest(observation['evidence_locator']) == observation['evidence_sha256'], 'configuration evidence changed')
        require(read_json(observation['locator'])['configuration'] == record['resolved_configuration'], 'configuration observation mismatch')
    root = Path(record['launch_receipt_locator']).parent
    require(set(receipt['sha256']) >= {'stdout.jsonl', 'stderr.txt', 'prompt.txt'}, 'missing raw integrity bindings')
    for name, expected in receipt['sha256'].items():
        require(Path(name).name == name and digest(root / name) == expected, 'corrupt raw artifact: ' + name)
    require(Path(record['raw_transcript_locator']).resolve() == (root / 'stdout.jsonl').resolve(), 'transcript linkage mismatch')
    raw = (root / 'stdout.jsonl').read_bytes()
    if record['classification'] in INFRA and not raw:
        parsed = None
    else:
        parsed = parse_native(raw)
    require(classify_execution(receipt, parsed or dict(established=False, completed=False, source=None, native_error=False))
            == receipt['classification'], 'classification differs from raw native events')
    requested, resolved = receipt['requested_command'], receipt['resolved_command']
    require(requested[1:] == resolved[1:], 'resolved argv differs from requested argv')
    if '--model' in requested:
        require(requested[requested.index('--model') + 1] == policy['target_configuration'].get('model'), 'command model differs from target configuration')
    if record['classification'] not in INFRA:
        require(parsed and parsed['established'], 'no actual established native attempt')
    if record['classification'] == 'completed':
        require(parsed['completed'] and parsed['source'] is not None, 'missing native completion/source')
        require(Path(record['result_artifact_locator']).read_text(encoding='utf-8') == parsed['source'], 'source differs from native output')
        require(record['token_usage'] == parsed['token_usage'], 'token usage differs from native output')
    observation = read_json(record['grader_observation_locator'])
    require(observation['oracle_outcome'] == record['oracle_outcome'] and
            observation['failure_class'] == record['failure_class'], 'grader linkage mismatch')
    require(digest(observation['checks_locator']) == observation['checks_sha256'], 'grader checks changed')
    if record['classification'] == 'completed':
        require(observation['source_sha256'] == digest(record['result_artifact_locator']), 'graded source differs')
        require(observation['grader_sha256'] == digest(Path(__file__).with_name('grader.py')), 'grader implementation changed')
        if record['evaluator_classification'] == 'environment_failure':
            require(observation['oracle_outcome'] == 'UNVERIFIED' and
                    any(call.get('launch_error') for call in observation['calls']), 'missing grader setup exclusion evidence')
            return parsed is not None and parsed['established']
        replay = grade(record['result_artifact_locator'], observation['checks_locator'])
        require(replay['oracle_outcome'] == observation['oracle_outcome'] and
                replay['source_sha256'] == observation['source_sha256'], 'independent outcome replay differs')
    return parsed is not None and parsed['established']


def probe(root):
    root = Path(root).resolve()
    envelope = read_json(root / 'evidence' / 'admission.json')
    manifest_path = Path(envelope['benchmark_manifest'])
    require(manifest_path.is_relative_to(root / 'product'), 'benchmark must land in disposable product')
    manifest = read_json(manifest_path)
    require(manifest.get('schema_version') == 2 and manifest.get('profile') == 'empirical-calibration', 'not empirical manifest v2')
    require(manifest.get('target_configuration'), 'missing manifest configuration')
    check_runtime(root, envelope['runtime'], envelope['component_locators'])
    qualification = envelope['qualification']
    require(qualification['validity'] in {'VALID', 'INVALID', 'UNVERIFIED'}, 'missing typed validity verdict')
    audited = set()
    for audit in qualification['audits']:
        require(audit.get('builder') and audit.get('auditor') and audit['builder'] != audit['auditor'], 'absent independent audit identities')
        require(all(audit.get(key) in {'PASS', 'FAIL', 'UNVERIFIED'} for key in
                    ('reference_outcome', 'inert_outcome', 'near_miss_outcome')), 'missing control observations')
        if qualification['revisions'][audit['benchmark_revision']]['validity'] == 'VALID':
            require(audit['reference_outcome'] == 'PASS' and audit['inert_outcome'] == 'FAIL'
                    and audit['near_miss_outcome'] == 'FAIL', 'missing discriminating controls')
        require(Path(audit['evidence_locator']).is_file(), 'missing audit evidence')
        audited.add((audit['case_id'], audit['benchmark_revision']))
    require(envelope['rounds'], 'no declared attempted rounds')
    established, summaries, identities = 0, [], set()
    development_rounds = [entry['policy']['round'] for entry in envelope['rounds'] if entry['policy']['split'] == 'development']
    require(development_rounds == list(range(len(envelope['revision_ledger']) + 1)), 'missing or reordered declared development round')
    for round_record in envelope['rounds']:
        policy = round_record['policy']
        require(round_record['validity'] in {'VALID', 'INVALID', 'UNVERIFIED'}, 'missing round qualification')
        bound_qualification = qualification['revisions'][round_record['qualification_revision']]
        require(round_record['validity'] == bound_qualification['validity'], 'round qualification differs')
        require(set(bound_qualification['criterion_gaps']) <= set(round_record['criterion_gaps']), 'qualification gaps omitted')
        require(policy['target_configuration'] == manifest['target_configuration'], 'round configuration changed')
        records = [read_json(path) for path in round_record['attempts']]
        for revision in {record['benchmark_revision'] for record in records}:
            check_revision(root, revision)
            require(revision == round_record['qualification_revision'], 'qualification revision differs')
        for record in records:
            identity = (record['benchmark_revision'], record['split'], record['round'], record['case_id'], record['trial'])
            require(identity not in identities, 'duplicate cross-round trial')
            identities.add(identity)
            if record['candidate_kind'] == 'agent_attempt':
                established += int(check_attempt(record, policy))
                require((record['case_id'], record['benchmark_revision']) in audited, 'case/revision lacks independent audit')
        expected = summarize(records, policy, criterion_gaps=round_record['criterion_gaps'],
                             validity=round_record['validity'],
                             revision_ledger=envelope['revision_ledger'],
                             frozen_revision=envelope.get('frozen_revision'),
                             final_record=envelope.get('final_record'))
        require(read_json(round_record['summary']) == expected, 'summary differs from recomputed evidence')
        summaries.append(expected)
    retries = sum(sum(record.get('retry_of') is not None for record in [read_json(path) for path in entry['attempts']]) for entry in envelope['rounds'])
    require(retries <= envelope['infrastructure_retry_budget'], 'global infrastructure retry allocation exceeded')
    require(established > 0, 'native-tool gap: no actual established agent attempts')
    selected = envelope['selected_development_round']
    development = [summary for summary in summaries if summary['split'] == 'development' and summary['round'] == selected]
    require(len(development) == 1 and selected == development_rounds[-1], 'invalid selected development round')
    development = development[0]
    require(envelope['development_decision'] == development['decision'], 'development decision differs')
    require(qualification['validity'] == development['validity'], 'selected qualification differs')
    check_manifest_revision(root, manifest_path, envelope.get('frozen_revision') or development['benchmark_revision'])
    if envelope.get('frozen_revision'):
        check_revision(root, envelope['frozen_revision'])
        require(development['decision'] == 'CALIBRATED', 'freeze requires calibrated development')
        check_frozen(root, manifest_path, envelope['frozen_revision'])
    final = read_json(envelope['final_record']) if envelope.get('final_record') else None
    if final and not final.get('not_performed_reason'):
        require(envelope.get('frozen_revision') and final.get('before') and final.get('after'), 'missing frozen evidence')
        require(final['before'] == final['after'], 'frozen bytes changed during final measurement')
        require(final.get('frozen_revision') == envelope['frozen_revision'], 'final revision differs')
        require(final.get('measurement_round') in envelope['rounds'], 'final measurement lacks checked attempts')
        require(final.get('evaluation_scope') in {'protected_final', 'public_confirmation', 'development'}, 'missing final scope')
        if final['evaluation_scope'] == 'protected_final':
            protection = final.get('protection', {})
            require(protection.get('status') == 'VERIFIED' and protection.get('mechanism') and
                    Path(protection.get('probe_locator', '')).is_file(), 'unverified protected final claim')
        require(final['measurement_round']['policy']['split'] != 'development', 'final cannot reuse development attempts')
        check_frozen(root, manifest_path, envelope['frozen_revision'], final['before'])
        check_frozen(root, manifest_path, envelope['frozen_revision'], final['after'])
    final_summaries = [summary for summary in summaries if summary['split'] != 'development']
    require(not final_summaries or (envelope.get('final_record') and development['decision'] == 'CALIBRATED'),
            'final attempts require calibrated development and final record')
    require(len(final_summaries) <= 1, 'multiple final measurements')
    require(not final_summaries or (final and not final.get('not_performed_reason')), 'final observations declared not performed')
    final_gaps = sorted({gap for summary in final_summaries for gap in summary['criterion_gaps']})
    final_invalid = any(summary['validity'] == 'INVALID' for summary in final_summaries)
    final_unverified = any(summary['validity'] == 'UNVERIFIED' for summary in final_summaries)
    decision = ('INVALID' if final_invalid else 'UNVERIFIED' if final_gaps or final_unverified else development['decision'])
    require(envelope['decision'] == decision, 'declared decision differs')
    eligible = decision == 'CALIBRATED' and bool(envelope.get('frozen_revision'))
    return dict(workflow_admission=True, calibrated_benchmark_eligible=eligible,
                decision=decision, established_native_attempts=established,
                declared_rounds=len(summaries), criterion_gaps=sorted(set(development['criterion_gaps'] + final_gaps)),
                development_decision=development['decision'],
                final_observations=[dict(estimate=row['estimate'], band_observation=row['band_observation'],
                    drift=None if row['estimate'] is None or development['estimate'] is None else row['estimate'] - development['estimate'])
                    for row in final_summaries])
