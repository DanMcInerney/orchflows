"""Parser for the documented ``case.toml`` subset.

This module stays dependency-free and supports Python 3.9.  The public
``validate_cases`` facade re-exports its established parser seam.
"""
from __future__ import annotations

from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # tomllib is 3.11+; the validator supports 3.9.
    tomllib = None


class TomlError(Exception):
    """The file is outside the subset, or malformed."""


class _Incomplete(Exception):
    """The value continues on the next line."""


_ESCAPES = {
    "b": "\b",
    "t": "\t",
    "n": "\n",
    "f": "\f",
    "r": "\r",
    '"': '"',
    "\\": "\\",
}
_HEX = "0123456789abcdefABCDEF"
_BARE = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-")


def _skip(text, i, newlines):
    while i < len(text):
        char = text[i]
        if char in " \t":
            i += 1
        elif char in "\r\n":
            if not newlines:
                return i
            i += 1
        elif char == "#":
            while i < len(text) and text[i] not in "\r\n":
                i += 1
        else:
            return i
    return i


def _escape(text, i):
    if i + 1 >= len(text):
        raise _Incomplete()
    char = text[i + 1]
    if char in _ESCAPES:
        return _ESCAPES[char], i + 2
    if char in "uU":
        width = 4 if char == "u" else 8
        digits = text[i + 2 : i + 2 + width]
        if len(digits) < width:
            raise _Incomplete()
        if any(d not in _HEX for d in digits):
            raise TomlError("bad unicode escape \\{}{}".format(char, digits))
        return chr(int(digits, 16)), i + 2 + width
    raise TomlError("unsupported escape \\{}".format(char))


def _quoted(text, i, quote, escapes):
    out = []
    j = i + 1
    while True:
        if j >= len(text):
            raise _Incomplete()
        char = text[j]
        if char in "\r\n":
            raise TomlError("newline inside a single-line string")
        if char == quote:
            return "".join(out), j + 1
        if escapes and char == "\\":
            decoded, j = _escape(text, j)
            out.append(decoded)
            continue
        out.append(char)
        j += 1


def _triple(text, i, delim, escapes):
    j = i + 3
    if text.startswith("\n", j):
        j += 1
    out = []
    while True:
        if j >= len(text):
            raise _Incomplete()
        if text.startswith(delim, j):
            return "".join(out), j + 3
        char = text[j]
        if escapes and char == "\\":
            k = j + 1
            while k < len(text) and text[k] in " \t":
                k += 1
            if k >= len(text):
                raise _Incomplete()
            if text[k] in "\r\n":
                while k < len(text) and text[k] in " \t\r\n":
                    k += 1
                j = k
                continue
            decoded, j = _escape(text, j)
            out.append(decoded)
            continue
        out.append(char)
        j += 1


def _integer(text, i):
    j = i
    if j < len(text) and text[j] in "+-":
        j += 1
    start = j
    while j < len(text) and (text[j].isdigit() or text[j] == "_"):
        j += 1
    digits = text[start:j].replace("_", "")
    if not digits:
        return None
    return int(text[i:start] + digits), j


def _array(text, i):
    items = []
    j = i + 1
    while True:
        j = _skip(text, j, newlines=True)
        if j >= len(text):
            raise _Incomplete()
        if text[j] == "]":
            return items, j + 1
        item, j = _value(text, j, newlines=True)
        items.append(item)
        j = _skip(text, j, newlines=True)
        if j >= len(text):
            raise _Incomplete()
        if text[j] == ",":
            j += 1
            continue
        if text[j] == "]":
            return items, j + 1
        raise TomlError("expected ',' or ']' inside an array")


def _value(text, i, newlines):
    i = _skip(text, i, newlines)
    if i >= len(text):
        raise _Incomplete()
    if text.startswith('"""', i):
        return _triple(text, i, '"""', True)
    if text.startswith("'''", i):
        return _triple(text, i, "'''", False)
    char = text[i]
    if char == '"':
        return _quoted(text, i, '"', True)
    if char == "'":
        return _quoted(text, i, "'", False)
    if char == "[":
        return _array(text, i)
    if text.startswith("true", i):
        return True, i + 4
    if text.startswith("false", i):
        return False, i + 5
    parsed = _integer(text, i)
    if parsed is not None:
        return parsed
    raise TomlError("unsupported value syntax at {!r}".format(text[i : i + 24]))


def _table(data, header):
    """Enter the table named by a ``[header]`` line."""
    if header.startswith("[["):
        raise TomlError("arrays of tables are outside the case schema")
    if not header.endswith("]"):
        raise TomlError("malformed table header: {!r}".format(header))
    name = header[1:-1].strip()
    if not name:
        raise TomlError("empty table header")
    table = data
    for part in name.split("."):
        part = part.strip()
        if not part or any(c not in _BARE for c in part):
            raise TomlError("table names must be bare: {!r}".format(name))
        table = table.setdefault(part, {})
        if not isinstance(table, dict):
            raise TomlError("key {!r} redefined as a table".format(part))
    return table


def parse_toml(text):
    """Parse the case.toml subset. Raises TomlError outside it."""
    data = {}
    table = data
    lines = text.splitlines()
    index = 0
    while index < len(lines):
        stripped = lines[index].strip()
        index += 1
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("["):
            table = _table(data, stripped)
            continue
        key, sep, rest = stripped.partition("=")
        key = key.strip()
        if not sep:
            raise TomlError("not a 'key = value' line: {!r}".format(stripped))
        if not key or any(c not in _BARE for c in key):
            raise TomlError("keys must be bare: {!r}".format(key))
        if key in table:
            raise TomlError("duplicate key {!r}".format(key))
        buffer = rest
        while True:
            try:
                value, end = _value(buffer, 0, newlines=False)
            except _Incomplete:
                if index >= len(lines):
                    raise TomlError("unterminated value for key {!r}".format(key))
                buffer += "\n" + lines[index]
                index += 1
                continue
            if _skip(buffer, end, newlines=True) != len(buffer):
                raise TomlError("trailing text after the value for key {!r}".format(key))
            table[key] = value
            break
    return data


def load_case_toml(path):
    text = Path(path).read_text(encoding="utf-8")
    data = parse_toml(text)
    if tomllib is not None:
        try:
            reference = tomllib.loads(text)
        except tomllib.TOMLDecodeError as error:
            raise TomlError("invalid TOML: {}".format(error))
        if reference != data:
            raise TomlError(
                "this validator's parser and tomllib disagree; keep case.toml "
                "inside the subset documented in validate_cases.py"
            )
    return data
