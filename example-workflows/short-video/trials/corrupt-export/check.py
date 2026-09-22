from pathlib import Path
import re

from common import read_json


FIXTURE = Path(__file__).resolve().parent / 'fixtures' / 'export.mp4'
EXPORT = re.compile(r'(?<![\w.-])export\.mp4(?![\w.-])')
HEADING = re.compile(r'\s*#{1,6}\s[^\n]*')
BYTES = re.compile(r'(?i)\bbytes?\b')


def blocks(text):
    """Paragraphs, list runs and table runs; a lone heading joins the block after it."""
    result, heading = [], ''
    for block in re.split(r'\n[ \t]*\n', text.replace('\r\n', '\n')):
        if HEADING.fullmatch(block):
            heading += block + '\n'
        elif block.strip():
            result.append(heading + block)
            heading = ''
    return result


def states_identity(text, size):
    """One block names export.mp4 and its byte size: '69 bytes', '69-byte', '69 B', or 69 under a bytes label."""
    number = r'(?<![\w.,])(?:' + '|'.join(map(re.escape, {str(size), f'{size:,}'})) + ')'
    sized = re.compile(number + r'\s*-?\s*(?:(?i:bytes?)|B)\b')
    bare = re.compile(number + r'(?!\w|[.,]\d)')
    return any(EXPORT.search(block) and (sized.search(block) or (bare.search(block) and BYTES.search(block)))
               for block in blocks(text))


def delegation(c):
    """Target-stage agents from the harness evidence index: the root's children, and any deeper agents."""
    index = read_json(c.stage().parent / 'evidence/index.json')
    if index.get('gaps'):
        raise RuntimeError('Native agent discovery incomplete: ' + str(index['gaps']))
    root = index['root_id']
    children = [a['id'] for a in index['agents'] if a.get('parent_id') == root]
    nested = [a['id'] for a in index['agents'] if a['id'] != root and a.get('parent_id') != root]
    return children, nested, f'stages/target/evidence/index.json: children {len(children)}, nested {nested}'


def check(c):
    export, review = c.stage()/'export.mp4', c.stage()/'review.md'
    c.require(export.is_file() and export.read_bytes() == FIXTURE.read_bytes(),
              'Preserve the supplied export byte-for-byte', 'export.mp4')
    text = review.read_text(encoding='utf-8', errors='replace') if review.is_file() else ''
    c.require(bool(text.strip()), 'Return review evidence and gaps', 'review.md')
    size = FIXTURE.stat().st_size
    c.require(states_identity(text, size),
              f'State the inspected export path and byte size ({size} bytes) together as its identity', 'review.md')
    children, nested, evidence = delegation(c)
    c.require(len(children) == 1, 'The named workflow launches exactly one reviewer', evidence)
    c.require(not nested, 'Only the coordinator launches agents', evidence)
