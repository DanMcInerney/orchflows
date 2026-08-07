#!/usr/bin/env python3
"""csvmerge equivalent: dict-merge implementation, same observable contract."""
import sys

USAGE = "usage: csvmerge.py [--prefer a|b] A_CSV B_CSV\n"


def split_argv(argv):
    prefer, files, pending = "a", [], False
    for arg in argv:
        if pending:
            if arg not in ("a", "b"):
                return None
            prefer, pending = arg, False
        elif arg == "--prefer":
            pending = True
        elif arg.startswith("-"):
            return None
        else:
            files.append(arg)
    if pending or len(files) != 2:
        return None
    return prefer, files


def read_rows(path):
    with open(path, "rb") as handle:
        text = handle.read().replace(b"\r\n", b"\n").decode("utf-8")
    table = {}
    order = []
    for line in text.split("\n"):
        if line == "":
            continue
        head = line.split(",", 1)[0]
        if not (head.lstrip("+-").isdigit() and head.lstrip("+-")):
            raise ValueError("non-integer key %r" % head)
        key = int(head)
        if order and key <= order[-1]:
            raise ValueError("unsorted key %d" % key)
        order.append(key)
        table[key] = line
    return table


def main():
    parsed = split_argv(sys.argv[1:])
    if parsed is None:
        sys.stderr.write(USAGE)
        return 2
    prefer, files = parsed
    tables = []
    for path in files:
        try:
            tables.append(read_rows(path))
        except OSError:
            sys.stderr.write("csvmerge: cannot read %s\n" % path)
            return 2
        except ValueError as error:
            sys.stderr.write("csvmerge: %s\n" % error)
            return 1
    merged = dict(tables[1])
    merged.update(tables[0])
    if prefer == "b":
        merged = dict(tables[0])
        merged.update(tables[1])
    chunks = [merged[key].encode("utf-8") + b"\n" for key in sorted(merged)]
    sys.stdout.buffer.write(b"".join(chunks))
    return 0


if __name__ == "__main__":
    sys.exit(main())
