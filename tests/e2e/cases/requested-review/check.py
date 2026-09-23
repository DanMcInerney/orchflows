from common import children


ANSWERS = (b'42', b'42\n', b'42\r\n')  # The request allows one optional trailing line break.


def check(c):
    path = c.stage() / 'answer.txt'
    content = path.read_bytes() if path.is_file() else None
    c.require(content in ANSWERS, 'answer.txt is 42 with at most one trailing line break',
              'stages/target/workspace/answer.txt: ' + repr(content)[:60])
    agents, evidence = children(c.stage().parent)
    c.require(len(agents) >= 1, 'The requested review launched a native child', evidence)
