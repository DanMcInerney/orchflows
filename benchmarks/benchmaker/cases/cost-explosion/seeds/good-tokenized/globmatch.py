"""Glob-style pattern matching against a whole subject string.

Same language as the reference, compiled to a token list and matched by
a single forward scan that backtracks to the last ``*``. Behaviourally
equivalent to the reference; structurally unrelated to it.

Pattern language:

    *       any run of characters, including the empty run
    ?       exactly one character
    [set]   one character drawn from set
    [!set]  one character not drawn from set

Inside a set, ``x-y`` is a range inclusive of both endpoints, a ``]``
written first is a literal ``]``, and a ``-`` with no character after it
is a literal ``-``. An unterminated ``[`` is a literal ``[``. Every other
pattern character matches only itself.
"""

STAR = "star"
ANY = "any"
SET = "set"


def _parse_class(pattern, start):
    index = start + 1
    negated = False
    if index < len(pattern) and pattern[index] == "!":
        negated = True
        index += 1
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


def _tokenize(pattern):
    tokens = []
    index = 0
    while index < len(pattern):
        char = pattern[index]
        if char == "*":
            if not tokens or tokens[-1][0] != STAR:
                tokens.append((STAR, None, False))
            index += 1
            continue
        if char == "?":
            tokens.append((ANY, None, False))
            index += 1
            continue
        if char == "[":
            parsed = _parse_class(pattern, index)
            if parsed is not None:
                members, negated, after = parsed
                tokens.append((SET, members, negated))
                index = after
                continue
        tokens.append((SET, [(char, char)], False))
        index += 1
    return tokens


def _accepts(token, char):
    kind, members, negated = token
    if kind == ANY:
        return True
    hit = any(low <= char <= high for low, high in members)
    return hit != negated


def match(pattern, subject):
    """Return True when ``pattern`` matches the whole of ``subject``."""
    tokens = _tokenize(pattern)
    ti = si = 0
    star_ti = -1
    star_si = 0
    while si < len(subject):
        if ti < len(tokens) and tokens[ti][0] == STAR:
            star_ti = ti
            star_si = si
            ti += 1
        elif ti < len(tokens) and _accepts(tokens[ti], subject[si]):
            ti += 1
            si += 1
        elif star_ti >= 0:
            star_si += 1
            si = star_si
            ti = star_ti + 1
        else:
            return False
    while ti < len(tokens) and tokens[ti][0] == STAR:
        ti += 1
    return ti == len(tokens)
