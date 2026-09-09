"""Bind a committed direction blob to a fixed independent-review snapshot.

This integrity probe cannot establish that the snapshot truthfully reports a
review. The caller checks that semantic binding before freezing its hash.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys

NAMES = ('orch-code', 'short-videos', 'orchflows-marketing-videos')


def verify(args):
    if not re.fullmatch(r'[0-9a-f]{40}', args.commit):
        raise ValueError('commit must be a full immutable Git identity')
    path = PurePosixPath(args.path)
    if path.is_absolute() or '..' in path.parts or ':' in args.path or '\\' in args.path:
        raise ValueError('direction path must be repository-relative')
    if any(not re.fullmatch(r'sha256:[0-9a-f]{64}', d) for d in args.digests):
        raise ValueError('expected standard digests must be normalized SHA256 pins')
    result = subprocess.run(['git', '-C', str(args.project), 'show',
                             f'{args.commit}:{path.as_posix()}'],
                            capture_output=True, timeout=30, check=True)
    if hashlib.sha256(result.stdout).hexdigest() != args.sha256:
        raise ValueError('committed direction bytes differ')
    raw = args.review.read_bytes()
    if hashlib.sha256(raw).hexdigest() != args.review_sha256:
        raise ValueError('review snapshot bytes differ')
    review = json.loads(raw)
    expected = [{'name': n, 'digest': d} for n, d in zip(NAMES, args.digests)]
    if (review.get('artifact') != f'git:{args.commit}'
            or review.get('standards') != expected
            or review.get('blockers') != []
            or not review.get('review_identity')):
        raise ValueError('review does not bind this artifact and ordered pins without blockers')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--commit', required=True)
    parser.add_argument('--path', required=True)
    parser.add_argument('--sha256', required=True)
    parser.add_argument('--review', type=Path, required=True)
    parser.add_argument('--review-sha256', required=True)
    parser.add_argument('--digests', nargs=3, required=True)
    args = parser.parse_args()
    try:
        verify(args)
    except (OSError, ValueError, AttributeError, subprocess.SubprocessError) as exc:
        print(f'direction integrity failed: {exc}', file=sys.stderr)
        return 1
    print('direction commit and independent-review snapshot bound')
    return 0


if __name__ == '__main__':
    sys.exit(main())
