def check(c):
    workspace = c.stage()
    source = (workspace / 'notice.txt').read_bytes()
    path = workspace / 'corrected.txt'
    c.require(path.is_file() and path.read_bytes() == source.replace(b'tickte', b'ticket'),
              'Correct only the requested spelling mistake and preserve line breaks', str(path))
