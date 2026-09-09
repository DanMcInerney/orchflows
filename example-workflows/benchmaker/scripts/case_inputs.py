"""Resolve immutable case inputs and oracle from a benchmark Git revision."""
import json
from pathlib import Path, PurePosixPath

from native import digest
from provenance import git, git_revision, normalized
from records import require


def committed_file(repository, revision, manifest, relative):
    path = PurePosixPath(relative)
    require(not path.is_absolute() and '..' not in path.parts and '\\' not in str(relative), 'case locator escapes benchmark')
    name = (PurePosixPath(manifest).parent / path).as_posix()
    return git(repository, 'show', revision + ':' + name)


def resolve_binding(request):
    repository = Path(request['repository']).resolve()
    revision = git_revision(repository, request['benchmark_revision'])
    manifest = PurePosixPath(request['manifest'])
    require(not manifest.is_absolute() and '..' not in manifest.parts and '\\' not in str(manifest), 'manifest must be repository-relative')
    index = json.loads(git(repository, 'show', revision + ':' + manifest.as_posix()))
    case_set = json.loads(committed_file(repository, revision, manifest, index['runnable_cases']))
    matches = [case for case in case_set['cases'] if case['case_id'] == request['case_id'] and case['split'] == request['split']]
    require(len(matches) == 1, 'case/split does not resolve at measured revision')
    case = matches[0]
    require(case['oracle'] == 'python-json-solve-v1', 'unsupported committed oracle')
    require(case['input_files'], 'missing committed candidate inputs')
    for name in case['input_files']:
        path = PurePosixPath(name)
        require(not path.is_absolute() and '..' not in path.parts and '.git' not in path.parts and '\\' not in name, 'unsafe candidate input path')
    return dict(repository=str(repository), benchmark_revision=revision, manifest=manifest.as_posix(),
                case_id=case['case_id'], split=case['split'], oracle=case['oracle'],
                prompt=case['prompt'], checks=case['checks'], input_files=case['input_files'])


def expected_file(binding, relative):
    return committed_file(binding['repository'], binding['benchmark_revision'], binding['manifest'], relative)


def verify_file(binding, relative, actual, label):
    require(normalized(Path(actual).read_bytes()) == normalized(expected_file(binding, relative)),
            label + ' differs from committed case input')


def capture_inputs(request, repository, prompt, output):
    binding = resolve_binding(request)
    verify_file(binding, binding['prompt'], prompt, 'native prompt')
    repository, output = Path(repository).resolve(), Path(output).resolve()
    files = {path.relative_to(repository).as_posix(): path for path in repository.rglob('*')
             if path.is_file() and '.git' not in path.relative_to(repository).parts}
    require(set(files) == set(binding['input_files']), 'candidate repository input inventory differs')
    observations = {}
    for name, relative in binding['input_files'].items():
        verify_file(binding, relative, files[name], 'candidate file')
        destination = output / 'inputs' / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(files[name].read_bytes())
        observations[name] = dict(locator=str(destination), sha256=digest(destination))
    return binding, observations


def check_binding(record, receipt, checks):
    binding = resolve_binding(receipt['case_binding'])
    require(binding == receipt['case_binding'] == record['case_binding'], 'case binding changed')
    for key in ('benchmark_revision', 'case_id', 'split'):
        require(record[key] == binding[key], 'attempt differs from bound ' + key)
    verify_file(binding, binding['prompt'], record['prompt_locator'], 'native prompt')
    verify_file(binding, binding['checks'], checks, 'evaluator checks')
    require(set(receipt['input_observations']) == set(binding['input_files']), 'missing input observations')
    for name, observation in receipt['input_observations'].items():
        require(digest(observation['locator']) == observation['sha256'], 'candidate input snapshot changed')
        verify_file(binding, binding['input_files'][name], observation['locator'], 'candidate input snapshot')
    return binding
