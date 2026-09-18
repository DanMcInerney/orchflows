from common import digest


def check(c):
    path = c.stage()/'review.md'
    c.require(path.is_file() and bool(path.read_text().strip()), 'Return review evidence and gaps', 'review.md')
    if path.is_file():
        c.require(digest(c.stage()/'export.mp4') in path.read_text(), 'Identify the inspected export by hash', 'review.md')
