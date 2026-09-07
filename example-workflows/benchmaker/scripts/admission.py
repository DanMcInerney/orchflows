"""Concrete disposable inputs and measurement doors, never simulated workflow execution."""
import argparse
import json
from pathlib import Path
import sys

from native import codex_command, collect, read_json, write_json
from probe import probe
from records import EvidenceError, summarize

PACKAGE = Path(__file__).resolve().parent.parent
SUBMISSION_SCHEMA = {
    'type': 'object', 'properties': {'source': {'type': 'string'}},
    'required': ['source'], 'additionalProperties': False,
}


def prepare(root):
    root = Path(root).resolve()
    root.mkdir(parents=True, exist_ok=False)
    for name in ('source', 'product', 'attempts', 'evidence'):
        (root / name).mkdir()
    (root / 'product' / 'records').mkdir()
    (root / 'product' / 'records' / '.gitattributes').write_text('* -text\n', encoding='utf-8')
    request = PACKAGE / 'references' / 'live-admission.md'
    (root / 'request.md').write_bytes(request.read_bytes())
    write_json(root / 'submission-schema.json', SUBMISSION_SCHEMA)
    policy = dict(case_ids=['topological-order', 'interval-difference', 'lru-ttl'],
                  split='development', round=0, trials_per_case=2, band=[0.30, 0.50],
                  infrastructure_retry_budget=1, require_resolved_configuration=True,
                  required_configuration_fields=['model', 'reasoning_effort', 'cli_version',
                      'instruction_layers', 'scaffold', 'delegation', 'tools_network'],
                  optional_configuration_fields=['temperature', 'seed'],
                  target_configuration=dict(model='gpt-5.6-sol', reasoning_effort='low',
                      host='codex exec', context='fresh ephemeral; no prior turns', sandbox='read-only',
                      cli_version={'unavailable_reason': 'Confirm native version before sealing'},
                      instruction_layers={'unavailable_reason': 'Inspect loaded instructions before sealing'},
                      tools_network={'unavailable_reason': 'Observe native capabilities before sealing'},
                      scaffold={'unavailable_reason': 'Pin loaded prompt and scaffold before sealing'},
                      delegation={'unavailable_reason': 'Observe delegation authority before sealing'},
                      temperature={'unavailable_reason': 'Provider does not expose this metadata'},
                      seed={'unavailable_reason': 'Provider does not expose this metadata'}))
    write_json(root / 'policy-input.json', policy)
    result = dict(root=str(root), semantic_goal=str(root / 'request.md'),
                  policy_input=str(root / 'policy-input.json'), schema=str(root / 'submission-schema.json'),
                  product=str(root / 'product'), records='records', evidence_export=str(root / 'evidence'), evidence=str(root / 'evidence'),
                  next='Invoke actual benchmaker with request.md; prepare creates no results or acceptance receipt')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    for name in ('prepare', 'probe'):
        child = sub.add_parser(name)
        child.add_argument('--root', required=True)
        if name == 'probe':
            child.add_argument('--require-calibrated', action='store_true')
    child = sub.add_parser('collect')
    for name in ('repository', 'schema', 'prompt', 'configuration', 'output'):
        child.add_argument('--' + name, required=True)
    child.add_argument('--executable', default='codex')
    child.add_argument('--timeout', type=float, default=90)
    child.add_argument('--configuration-observation')
    child.add_argument('--case-binding', required=True)
    child = sub.add_parser('summarize')
    child.add_argument('--input', required=True, help='JSON with policy, attempt locators and explicit evidence gaps')
    child.add_argument('--output', required=True)
    args = parser.parse_args()
    try:
        if args.action == 'prepare':
            result = prepare(args.root)
        elif args.action == 'collect':
            result = collect(codex_command(args.repository, args.schema, args.executable),
                             case_repository=args.repository, prompt=args.prompt, output=args.output,
                             configuration=read_json(args.configuration), timeout=args.timeout,
                             configuration_observation=args.configuration_observation, case_binding=read_json(args.case_binding))
        elif args.action == 'summarize':
            request = read_json(args.input)
            result = summarize([read_json(path) for path in request['attempts']], request['policy'],
                               criterion_gaps=request['criterion_gaps'], validity=request['validity'])
            write_json(args.output, result)
        else:
            result = probe(args.root)
            print(json.dumps(result, indent=2))
            return 2 if args.require_calibrated and not result['calibrated_benchmark_eligible'] else 0
        print(json.dumps(result, indent=2))
        return 0
    except (EvidenceError, OSError, ValueError, KeyError, TypeError) as error:
        print(json.dumps(dict(workflow_admission=False, error=str(error))), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
