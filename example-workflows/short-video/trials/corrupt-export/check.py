from pathlib import Path
import re

FIXTURE = Path(__file__).resolve().parent / 'fixtures' / 'export.mp4'


def check(c):
    export, review = c.stage()/'export.mp4', c.stage()/'review.md'
    c.require(export.is_file() and export.read_bytes() == FIXTURE.read_bytes(),
              'Preserve the supplied export byte-for-byte', 'export.mp4')
    text = review.read_text(encoding='utf-8', errors='replace') if review.is_file() else ''
    c.require(bool(text.strip()), 'Return review evidence and gaps', 'review.md')
    size = FIXTURE.stat().st_size
    c.require('export.mp4' in text and re.search(rf'(?<!\d){size}(?!\d)', text) is not None,
              'Identify the inspected export by path and byte size', 'review.md')
