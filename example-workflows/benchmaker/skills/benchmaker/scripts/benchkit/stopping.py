"""Sequential stopping for repeated attempts on one item. Standard library only."""

from .stats import clopper_pearson


def decide(successes: int, attempts: int, *, low: float, high: float, level: float = 0.9,
           max_attempts: int) -> str:
    """Whether to keep repeating an item, judged against the target band [low, high].

    Computes the exact two-sided Clopper-Pearson interval for `successes` of
    `attempts` at `level` (each tail (1 - level) / 2) and compares it with the
    band:

    - 'below': the whole interval lies under `low`.
    - 'above': the whole interval lies over `high`.
    - 'inside': the whole interval lies within [low, high].
    - 'exhausted': none of those, and `max_attempts` is reached.
    - 'continue': none of those, and more attempts remain.

    Decisive outcomes are returned even at `max_attempts`. Checking after each
    attempt and stopping on a decisive result is a sequential procedure, so the
    realized error rate of 'below'/'above' exceeds the nominal one; use a
    higher level when a wrong stop is costly.
    """
    if not 0.0 <= low <= high <= 1.0:
        raise ValueError("need 0 <= low <= high <= 1")
    if not 0 <= successes <= attempts:
        raise ValueError("need 0 <= successes <= attempts")
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")
    if attempts:
        lower, upper = clopper_pearson(successes, attempts, level)
        if upper < low:
            return "below"
        if lower > high:
            return "above"
        if lower >= low and upper <= high:
            return "inside"
    return "exhausted" if attempts >= max_attempts else "continue"
