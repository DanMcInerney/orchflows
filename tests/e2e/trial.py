"""Case context: isolated files, explicit native stages, and evidence."""
import asyncio
from collections import Counter
from dataclasses import replace
import fnmatch
import os
from pathlib import Path
import shutil
import sys
import time

from common import HERE, copy_package, files_under, load_hook, read_json, snapshot, write_json


def observed(parts):
    """Sum native model/effort tallies of agents, stages or attempts; requests are recorded elsewhere."""
    tallies = {'models': Counter(), 'efforts': Counter()}
    for part in parts:
        for key, tally in tallies.items():
            tally.update(part.get(key) or {})
    return {key: dict(tally) for key, tally in tallies.items()}


class Trial:
    def __init__(self, case, root, host, scheduler, sources):
        self.root, self.host, self.scheduler = Path(root), host, scheduler
        self.end = min(scheduler.end, time.monotonic() + case.timeout)
        self.packages, self.package_records, self.stages, self.gaps = {}, {}, [], []
        self.root.mkdir(parents=True, exist_ok=False)
        evaluation = self.root / 'evaluation'
        shutil.copytree(files_under(case.path), evaluation,
                        ignore=shutil.ignore_patterns('packages', '__pycache__'))
        self.case = replace(case, path=evaluation)
        shutil.copy2(HERE / 'review.md', evaluation / 'review.md')
        for name, source in sources.items():
            self.package_records[name] = copy_package(source, self.root / 'packages' / name)
            self.packages[name] = self.root / 'packages' / name
        write_json(self.root / 'packages.json', self.package_records)

    async def invoke(self, name='target', *, request=None, entrypoint=None, fixtures=None,
                     packages=None, profile=None, timeout=None):
        if not name or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-_' for c in name):
            raise ValueError('Invalid stage name')
        directory = self.root / 'stages' / name
        directory.mkdir(parents=True, exist_ok=False)
        workspace = directory / 'workspace'
        if fixtures is None:
            fixtures = self.case.path / 'fixtures'
        if Path(fixtures).is_dir():
            shutil.copytree(files_under(fixtures), workspace)
        else:
            workspace.mkdir()
        chosen = dict(self.packages)
        for key, path in (packages or {}).items():
            destination = directory / 'packages' / key
            copy_package(path, destination)
            chosen[key] = destination
        orch_home = workspace / '.orchflows'
        orch_home.mkdir(exist_ok=True)
        original = request if request is not None else (self.case.path / 'request.md').read_text(encoding='utf-8')
        for key, path in chosen.items():
            original = original.replace('{PACKAGE:' + key + '}', path.as_posix())
        original = original.replace('{CORE}', chosen.get('orchflows', Path('UNAVAILABLE')).as_posix())
        original = original.replace('{HOME}', orch_home.as_posix())
        original = original.replace('{WORKSPACE}', workspace.as_posix())
        original = original.replace('{HOST_CLI}', self.host.name)
        if entrypoint is None:
            entrypoint = self.case.config.get('entrypoint')
        prompt = self.host.invocation(entrypoint, original)
        (directory / 'request.txt').write_text(prompt, encoding='utf-8')
        if hasattr(self.host, 'prepare'):
            self.host.prepare(workspace, chosen)
        before = snapshot(workspace)
        package_before = {key: snapshot(path) for key, path in chosen.items()}
        write_json(directory / 'before.json', {'inputs': before, 'packages': package_before})
        selected_profile = profile or self.case.config.get('profile', 'local')
        command = self.host.command(chosen, selected_profile, directory=directory)
        env = dict(os.environ, ORCHFLOWS_HOME=str(orch_home), PYTHONDONTWRITEBYTECODE='1')
        execution = await self.scheduler.process(command, cwd=workspace, directory=directory,
            prompt=prompt, timeout=timeout or self.case.timeout, until=self.end, env=env,
            label=self.case.id + ':' + name)
        native = self.host.result(directory)
        write_json(directory / 'native.json', native)
        if native.get('session_id'):
            await self.scheduler.process([sys.executable, '-B', str(HERE / 'evidence.py'), self.host.name,
                native['session_id'], str(directory / 'evidence')], cwd=workspace,
                directory=directory / 'collection', timeout=15, native=False,
                label='collect:' + name)
        evidence_path = directory / 'evidence/index.json'
        evidence = read_json(evidence_path) if evidence_path.exists() else {'gaps': ['Native evidence unavailable']}
        after = snapshot(workspace)
        violations = []
        writable = self.case.config.get('writable_inputs', [])
        for relative, value in before.items():
            if not any(fnmatch.fnmatchcase(relative, pattern) for pattern in writable) and after.get(relative) != value:
                violations.append({'passed': False, 'invariant': True, 'requirement': 'Preserve supplied references',
                                   'evidence': f'stages/{name}/before.json: {relative}'})
        for key, path in chosen.items():
            if snapshot(path) != package_before[key]:
                violations.append({'passed': False, 'invariant': True, 'requirement': 'Preserve runtime packages',
                                   'evidence': f'stages/{name}/before.json: {key}'})
        registration = self.host.registration_gaps(native, chosen)
        gaps = [*execution['gaps'], *native['gaps'], *evidence.get('gaps', [])]
        if registration:
            gaps.append('Native package registration not established: ' + ', '.join(registration))
        if execution['status'] != 'completed':
            gaps.append('Stage execution: ' + execution['status'])
        record = {'name': name, 'execution': execution, 'native': native, 'violations': violations,
                  'gaps': gaps, 'observed': observed(evidence.get('agents', [])), 'after': after,
                  'workspace': str(workspace)}
        write_json(directory / 'stage.json', record)
        self.stages.append(record)
        return workspace

    async def local(self, command, *, cwd, name, timeout=20):
        return await self.scheduler.process(command, cwd=cwd, directory=self.root / 'local' / name,
            timeout=timeout, until=self.end, native=False, label='local:' + name)

    def freeze(self, source, name):
        destination = self.root / 'generated' / name
        record = copy_package(source, destination)
        write_json(self.root / ('generated-' + name + '.json'), record)
        return destination

    def report(self):
        gaps = [*self.gaps, *(g for stage in self.stages for g in stage['gaps'])]
        return {'case': self.case.id, 'config': self.case.config, 'host': self.host.name,
                'host_version': self.host.version, 'stages': self.stages,
                'completed': bool(self.stages) and not self.gaps and all(s['execution']['status'] == 'completed'
                    and s['native'].get('terminal_success') for s in self.stages), 'gaps': gaps,
                'observed': observed(s['observed'] for s in self.stages),
                'conditions': 'Package and fixture copies; evaluator inputs withheld from target context. '
                              'Filesystem/network confinement is not guaranteed by the harness.'}

    async def execute(self):
        try:
            driver = self.root / 'evaluation/driver.py'
            if driver.exists():
                await asyncio.wait_for(load_hook(driver).run(self), max(.001, self.end - time.monotonic()))
            else:
                await self.invoke()
        except Exception as error:
            self.gaps.append(f'{type(error).__name__}: {error}')
        target = self.report()
        write_json(self.root / 'target.json', target)
        return target
