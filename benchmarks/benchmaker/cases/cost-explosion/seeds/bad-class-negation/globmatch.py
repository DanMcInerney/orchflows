"""Glob-style pattern matching against a whole subject string.

Pattern language:

    *       any run of characters, including the empty run
    ?       exactly one character
    [set]   one character drawn from set
    [!set]  one character not drawn from set

Inside a set, ``x-y`` is a range inclusive of both endpoints, a ``]``
written first is a literal ``]``, and a ``-`` with no character after it
is a literal ``-``. An unterminated ``[`` is a literal ``[``. Every other
pattern character matches only itself.

``match`` succeeds only when the pattern consumes the entire subject.
"""


def _parse_class(pattern, start):
    """Parse the bracket set at ``pattern[start]``.

    Returns ``(members, negated, next_index)``, where members are
    inclusive ``(low, high)`` pairs, or ``None`` when the set is
    unterminated.
    """
    index = start + 1
    negated = False
    members = []
    first = True
    while index < len(pattern):
        char = pattern[index]
        if char == "]" and not first:
            return members, negated, index + 1
        first = False
        if (
            index + 2 < len(pattern)
            and pattern[index + 1] == "-"
            and pattern[index + 2] != "]"
        ):
            members.append((char, pattern[index + 2]))
            index += 3
        else:
            members.append((char, char))
            index += 1
    return None


def _in_class(members, negated, char):
    hit = any(low <= char <= high for low, high in members)
    return hit != negated


def match(pattern, subject):
    """Return True when ``pattern`` matches the whole of ``subject``."""
    memo = {}

    def walk(pi, si):
        key = (pi, si)
        if key not in memo:
            memo[key] = _step(pi, si)
        return memo[key]

    def _step(pi, si):
        if pi == len(pattern):
            return si == len(subject)
        char = pattern[pi]
        if char == "*":
            return any(walk(pi + 1, k) for k in range(si, len(subject) + 1))
        if si == len(subject):
            return False
        if char == "?":
            return walk(pi + 1, si + 1)
        if char == "[":
            parsed = _parse_class(pattern, pi)
            if parsed is not None:
                members, negated, after = parsed
                if _in_class(members, negated, subject[si]):
                    return walk(after, si + 1)
                return False
        return subject[si] == char and walk(pi + 1, si + 1)

    return walk(0, 0)
