#!/usr/bin/env python3
"""csvmerge reference: streaming two-pointer merge per evidence/spec.md."""
import sys


class DataError(Exception):
    pass


def parse_args(argv):
    prefer = "a"
    files = []
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--prefer":
            if i + 1 >= len(argv) or argv[i + 1] not in ("a", "b"):
                return None, None
            prefer = argv[i + 1]
            i += 2
            continue
        if arg.startswith("-"):
            return None, None
        files.append(arg)
        i += 1
    if len(files) != 2:
        return None, None
    return prefer, files


def load(path):
    try:
        with open(path, "rb") as handle:
            raw = handle.read()
    except OSError:
        return None
    rows = []
    previous = None
    for line in raw.replace(b"\r\n", b"\n").split(b"\n"):
        if not line:
            continue
        text = line.decode("utf-8")
        key_text = text.split(",", 1)[0]
        try:
            key = int(key_text)
        except ValueError:
            raise DataError("non-integer key: %r" % key_text)
        if previous is not None and key <= previous:
            raise DataError("keys not strictly ascending at %d" % key)
        previous = key
        rows.append((key, text))
    return rows


def merge(a_rows, b_rows, prefer):
    out = []
    i = j = 0
    while i < len(a_rows) or j < len(b_rows):
        if j >= len(b_rows):
            out.append(a_rows[i])
            i += 1
        elif i >= len(a_rows):
            out.append(b_rows[j])
            j += 1
        elif a_rows[i][0] < b_rows[j][0]:
            out.append(a_rows[i])
            i += 1
        elif b_rows[j][0] < a_rows[i][0]:
            out.append(b_rows[j])
            j += 1
        else:
            out.append(a_rows[i] if prefer == "a" else b_rows[j])
            i += 1
            j += 1
    return out


def main():
    prefer, files = parse_args(sys.argv[1:])
    if prefer is None:
        sys.stderr.write("usage: csvmerge.py [--prefer a|b] A_CSV B_CSV\n")
        return 2
    loaded = []
    for path in files:
        try:
            rows = load(path)
        except DataError as error:
            sys.stderr.write("csvmerge: %s\n" % error)
            return 1
        if rows is None:
            sys.stderr.write("csvmerge: cannot read %s\n" % path)
            return 2
        loaded.append(rows)
    merged = merge(loaded[0], loaded[1], prefer)
    body = b"".join(text.encode("utf-8") + b"\n" for _, text in merged)
    sys.stdout.buffer.write(body)
    return 0


if __name__ == "__main__":
    sys.exit(main())
