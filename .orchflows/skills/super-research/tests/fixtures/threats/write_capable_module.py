"""A module that spells verbs no route in this package may reach.

Written beside the tree and never executed. It exists so the non-read-verb
scan is shown to discriminate: the package spells exactly one non-read verb,
in one module, inside the two closed sets `transport.py` declares, and a scan
that matched nothing would say the same thing about a module like this one.
"""

from __future__ import annotations

MUTATING_METHODS = ("PUT", "PATCH", "DELETE")
CREATE_METHOD = "POST"


def send(carrier, url, method=CREATE_METHOD, body=""):
    return carrier.request(method, url, body)
