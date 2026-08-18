"""Read protected-evidence declarations without silent fallback."""

import json

from .common import _text


class ProtectedEvidenceError(Exception):
    """The covered manifest does not state its protected paths."""


def protected_files(cases_dir):
    """Return every protected path the covered manifest names."""
    path = cases_dir.parent / "manifest.json"
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ProtectedEvidenceError("cannot read %s: %s" % (path, error))
    evidence = manifest.get("protected_evidence") if isinstance(manifest, dict) else None
    files = evidence.get("files") if isinstance(evidence, dict) else None
    if not (isinstance(files, list) and all(_text(name) for name in files)):
        raise ProtectedEvidenceError(
            "%s states no 'protected_evidence.files' list of paths (found %r)" % (path, files)
        )
    return tuple(sorted(files))
