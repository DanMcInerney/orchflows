"""Ladder members: the oracle that, with probability q per attempt, produces a wrong answer instead.

The wrong answer is drawn from the domain's defects (its diagnostic ones excluded) and kept only when the domain's
checker says it is wrong on this instance, so a rung's expected score falls as q rises by construction.
"""
import random

GOOD = ("valid", "correct-infeasible")


def wrong(verdict: dict) -> bool:
    return verdict.get("label") not in GOOD


def draw(domain, instance, q: float, rng: random.Random):
    """(files, applied): the output and the defect that produced it, or None when the oracle's answer was kept."""
    best = domain.solve(instance)[0]
    if rng.random() >= q:
        return best, None
    diagnostic = set(getattr(domain, "DIAGNOSTIC", ()))
    names = [n for n in sorted(getattr(domain, "DEFECTS", {})) if n not in diagnostic]
    rng.shuffle(names)
    for name in names:
        files = domain.DEFECTS[name](instance, rng)
        if wrong(domain.check(instance, files)):
            return files, name
    return best, None
