"""Preserve explicitly referenced candidate evidence before its tree retires.

Only named files under reserved scratch, and explicit findings files inside
this candidate, enter custody. Runtime dependencies and unknown content are
never inferred, copied or deleted. Hashes describe producer bytes, not Git's
text-normalized blobs. The manifest survives the producer checkout.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

try:
    from . import state_root, tickets_format, tickets_store, workspace_git
except ImportError:
    import state_root
    import tickets_format
    import tickets_store
    import workspace_git

Refused = workspace_git.Refused


def _directory(run, ticket_id):
    for kind, value in (('run id', run), ('ticket id', ticket_id)):
        defect = state_root.segment_defect(kind, value)
        if defect:
            raise Refused(defect)
    return state_root.state_root() / state_root.WORKSPACES_SUBPATH / run / ticket_id / 'custody'


def _read_manifest(directory):
    path = directory / 'manifest.json'
    if not path.exists():
        return {'version': 1, 'files': []}
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        if data.get('version') != 1 or not isinstance(data.get('files'), list):
            raise ValueError('invalid custody manifest shape')
        for entry in data['files']:
            if not isinstance(entry, dict) or set(entry) != {'source', 'destination', 'sha256'}:
                raise ValueError('invalid custody entry')
            _verified_destination(directory, entry)
        return data
    except (OSError, ValueError, TypeError) as error:
        raise Refused(f'cannot read custody manifest {path}: {error}') from error


def _verified_destination(directory, entry):
    digest = entry['sha256']
    if not isinstance(digest, str) or not re.fullmatch(r'[0-9a-f]{64}', digest):
        raise ValueError('invalid custody hash')
    destination = directory / 'bytes' / digest
    if (str(destination.absolute()) != entry['destination']
            or destination.resolve().parent != (directory / 'bytes').resolve()
            or destination.is_symlink()):
        raise ValueError('custody destination escapes its hash-addressed owner')
    if hashlib.sha256(destination.read_bytes()).hexdigest() != digest:
        raise ValueError('archived evidence hash mismatch')
    return destination


def archived_path(run, ticket_id, source, *, sha256=None):
    """Resolve an original producer path using verified durable custody only."""
    directory = _directory(run, ticket_id)
    source = str(Path(source).resolve())
    for entry in _read_manifest(directory)['files']:
        if entry['source'] == source:
            if sha256 is not None and sha256.removeprefix('sha256:') != entry['sha256']:
                raise Refused('requested producer hash differs from archived evidence')
            return _verified_destination(directory, entry)
    raise Refused(f'no archived evidence for {source}')


def _report_text(run, ticket_id):
    path = state_root.tickets_root() / run / f'{ticket_id}.md'
    if not path.is_file():
        return ''
    text = path.read_text(encoding='utf-8')
    data = tickets_format._parse_frontmatter(text)
    report = tickets_format._sections(text).get('Report', '')
    # The dispatch record preserves content as JSON strings. Decode that
    # one owned shape instead of guessing escaped path spellings.
    dispatch = data.get('dispatch_v1')
    if isinstance(dispatch, str):
        try:
            dispatch = json.loads(dispatch)
        except ValueError:
            dispatch = None
    if isinstance(dispatch, dict):
        for attempt in dispatch.get('attempts') or []:
            for record in attempt.get('records') or []:
                content = record.get('content')
                if isinstance(content, str):
                    report += '\n' + content
                    try:
                        decoded = json.loads(content)
                    except ValueError:
                        continue
                    if isinstance(decoded, dict):
                        report += '\n' + '\n'.join(value for value in decoded.values() if isinstance(value, str))
    return report.replace('\\\\', '/').replace('\\', '/')


def _referenced_files(target, report, references):
    found = set()
    scratch = target / workspace_git.NOTES_DIR
    if scratch.is_dir():
        for source in scratch.rglob('*'):
            if not source.is_file():
                continue
            relative = source.relative_to(target).as_posix()
            absolute = source.absolute().as_posix()
            if any(re.search(r'(?<![\w./:\\-])' + re.escape(name) + r'(?=$|[\s`\"\'<>),;:@])', report) for name in (relative, absolute)):
                found.add(source)
    for line in report.splitlines():
        match = re.match(r'^\s*findings:\s*(.+?)\s*$', line)
        if match:
            references = (*references, match.group(1).strip('`<>"'))
    for value in references:
        source = Path(value).expanduser()
        if not source.is_absolute():
            source = target / source
        try:
            source.resolve().relative_to(target.resolve())
        except ValueError:
            raise Refused(f'evidence path is outside its candidate: {source}')
        found.add(source)
    return sorted(found)


def archive(run, ticket_id, workspace, *, references=()):
    """Copy producer bytes and atomically commit source/destination hashes."""
    target = Path(workspace).resolve()
    directory = _directory(run, ticket_id)
    manifest = _read_manifest(directory)
    entries = {entry['source']: entry for entry in manifest['files']}
    report = _report_text(run, ticket_id)
    for source in _referenced_files(target, report, references):
        source_name = str(source.resolve())
        if not source.exists() and source_name in entries:
            continue  # replay after the producer was retired; manifest was verified
        try:
            resolved = source.resolve()
            resolved.relative_to(target)
            if source.is_symlink() or any(parent.is_symlink() for parent in source.parents if parent != target and target in parent.parents):
                raise ValueError('linked evidence is not owned scratch')
            raw = source.read_bytes()
        except (OSError, ValueError) as error:
            raise Refused(f'cannot archive evidence {source}: {error}') from error
        digest = hashlib.sha256(raw).hexdigest()
        source_name = str(resolved)
        prior = entries.get(source_name)
        if prior is not None and prior['sha256'] != digest:
            raise Refused(f'producer evidence changed after custody was recorded: {source}')
        destination = directory / 'bytes' / digest
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            if destination.read_bytes() != raw:
                raise Refused(f'custody bytes disagree with their hash at {destination}')
        else:
            # Exclusive create plus verification: interruption leaves a refused
            # partial blob, never a manifest claiming bytes it did not retain.
            with destination.open('xb') as handle:
                handle.write(raw)
        if hashlib.sha256(destination.read_bytes()).hexdigest() != digest:
            raise Refused(f'custody copy verification failed: {destination}')
        entries[source_name] = {'source': source_name, 'destination': str(destination.resolve()), 'sha256': digest}
    manifest['files'] = sorted(entries.values(), key=lambda entry: entry['source'])
    if manifest['files']:
        directory.mkdir(parents=True, exist_ok=True)
        tickets_store._write_text_atomically(directory / 'manifest.json', json.dumps(manifest, indent=2) + '\n')
    return {'manifest': str(directory / 'manifest.json') if manifest['files'] else None, 'files': manifest['files']}


def release_scratch(workspace, custody):
    """Remove only hash-verified, untracked scratch already in durable custody."""
    target = Path(workspace).resolve()
    read = workspace_git._git_out(target)
    tracked = set(read('ls-files', '-z').split('\0'))
    for entry in custody['files']:
        source = Path(entry['source'])
        try:
            relative = source.relative_to(target)
        except ValueError:
            continue
        if not relative.parts or relative.parts[0] != workspace_git.NOTES_DIR:
            continue
        if relative.as_posix() in tracked or not source.exists():
            continue
        if source.is_symlink() or hashlib.sha256(source.read_bytes()).hexdigest() != entry['sha256']:
            raise Refused(f'archived scratch changed before retirement: {source}')
        source.unlink()
        parent = source.parent
        while parent != target:
            try:
                parent.rmdir()
            except OSError:
                break
            parent = parent.parent
