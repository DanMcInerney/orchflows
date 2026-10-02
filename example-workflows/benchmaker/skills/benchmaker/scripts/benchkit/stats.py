"""Small-sample statistics for benchmark comparisons. Standard library only.

Cluster-level inference treats each cluster as one independent observation, so
tasks that share a source cannot inflate the evidence. Every procedure is exact
when its enumeration is small enough and otherwise a seeded Monte Carlo
approximation; results are deterministic for a given seed.
"""

import itertools
import math
import random

SIGN_FLIP_EXACT_MAX = 16
WILD_EXACT_MAX = 12

_ALTERNATIVES = {"two-sided": "two-sided", "greater": "greater", "one-sided": "greater", "less": "less"}


def check_alternative(name: str) -> str:
    """Canonical alternative ('two-sided', 'greater' or 'less'); raises ValueError otherwise."""
    try:
        return _ALTERNATIVES[name]
    except KeyError:
        raise ValueError(f"alternative must be one of {sorted(_ALTERNATIVES)}, got {name!r}") from None


def _signed_sums(values: list[float]) -> list[float]:
    """Every sum of the values under all 2**n sign assignments."""
    sums = [0.0]
    for v in values:
        sums = [s + v for s in sums] + [s - v for s in sums]
    return sums


def _random_signed_sum(values: list[float], rng: random.Random) -> float:
    bits = rng.getrandbits(len(values))
    return sum(v if bits >> i & 1 else -v for i, v in enumerate(values))


def _as_floats(values, what: str) -> list[float]:
    out = [float(v) for v in values]
    if not out:
        raise ValueError(f"{what} needs at least one value")
    if not all(math.isfinite(v) for v in out):
        raise ValueError(f"{what} must be finite")
    return out


def sign_flip_p(cluster_means: list[float], *, alternative: str = "two-sided", exact_max: int = SIGN_FLIP_EXACT_MAX,
                draws: int = 20000, seed: int = 0) -> float:
    """Sign-flip randomization p-value that the cluster values are centred on zero.

    The statistic is the sum of the values. Under the null each value is equally
    likely to carry either sign, so the reference distribution is the sum under
    all 2**G sign assignments (exact when G <= exact_max, else `draws` random
    assignments plus the observed one). `alternative` is "two-sided", "greater"
    (also "one-sided") or "less". Zeros are kept: they double the assignments
    without changing the sum, as the null requires.
    """
    x = _as_floats(cluster_means, "sign_flip_p")
    alt = check_alternative(alternative)
    obs = sum(x)
    tol = 1e-9 * (sum(abs(v) for v in x) or 1.0)

    def extreme(s: float) -> bool:
        if alt == "two-sided":
            return abs(s) >= abs(obs) - tol
        return s >= obs - tol if alt == "greater" else s <= obs + tol

    if len(x) <= exact_max:
        sums = _signed_sums(x)
        return sum(1 for s in sums if extreme(s)) / len(sums)
    rng = random.Random(seed)
    hits = 1 + sum(1 for _ in range(draws) if extreme(_random_signed_sum(x, rng)))
    return hits / (draws + 1)


def _quantile(sorted_values: list[float], q: float) -> float:
    """Inverse-CDF quantile: the smallest value whose empirical CDF reaches q."""
    index = math.ceil(q * len(sorted_values) - 1e-9) - 1
    return sorted_values[min(max(index, 0), len(sorted_values) - 1)]


def wild_cluster_ci(cluster_means: list[float], *, level: float = 0.95, exact_max: int = WILD_EXACT_MAX,
                    draws: int = 9999, seed: int = 0) -> tuple[float, float]:
    """Wild cluster bootstrap percentile interval for the mean of the cluster values.

    Each cluster's residual from the overall mean is multiplied by an independent
    Rademacher weight (+1 or -1); the interval is the mean plus the
    (1-level)/2 and 1-(1-level)/2 inverse-CDF quantiles of the reweighted mean
    residual. All 2**G weight vectors are enumerated when G <= exact_max, else
    `draws` are sampled. It is approximate and, with few clusters, can only
    reach as far as the mean absolute residual: read narrow intervals on a
    handful of clusters with care. Needs at least two clusters.
    """
    x = _as_floats(cluster_means, "wild_cluster_ci")
    if len(x) < 2:
        raise ValueError("wild_cluster_ci needs at least two clusters")
    if not 0.0 < level < 1.0:
        raise ValueError("level must be in (0, 1)")
    g = len(x)
    centre = sum(x) / g
    residuals = [v - centre for v in x]
    if g <= exact_max:
        reweighted = sorted(s / g for s in _signed_sums(residuals))
    else:
        rng = random.Random(seed)
        reweighted = sorted(_random_signed_sum(residuals, rng) / g for _ in range(draws))
    tail = (1.0 - level) / 2.0
    return centre + _quantile(reweighted, tail), centre + _quantile(reweighted, 1.0 - tail)


def kendall_tau_b(x: list[float], y: list[float]) -> float:
    """Kendall's tau-b rank correlation, correcting for ties in either list.

    (concordant - discordant) / sqrt((pairs - ties_x) * (pairs - ties_y)).
    Returns nan when either list is constant (undefined).
    """
    if len(x) != len(y):
        raise ValueError("x and y must have the same length")
    concordant = discordant = ties_x = ties_y = 0
    for i, j in itertools.combinations(range(len(x)), 2):
        dx, dy = x[i] - x[j], y[i] - y[j]
        if dx == 0:
            ties_x += 1
        if dy == 0:
            ties_y += 1
        if dx and dy:
            if (dx > 0) == (dy > 0):
                concordant += 1
            else:
                discordant += 1
    pairs = len(x) * (len(x) - 1) // 2
    denominator = math.sqrt((pairs - ties_x) * (pairs - ties_y))
    return (concordant - discordant) / denominator if denominator else math.nan


def pair_accuracy(scores: dict[str, float], known: list[tuple[str, str]]) -> float:
    """Share of known (higher, lower) pairs the scores order correctly; ties count 0.5.

    A pair whose member has no score (missing or None) is skipped. Returns nan
    when no pair can be scored.
    """
    credit = []
    for higher, lower in known:
        hi, lo = scores.get(higher), scores.get(lower)
        if hi is None or lo is None:
            continue
        credit.append(1.0 if hi > lo else 0.5 if hi == lo else 0.0)
    return sum(credit) / len(credit) if credit else math.nan


def order_null_p(members: list[str], known: list[tuple[str, str]], observed: float, *,
                 exact_max: int = 9, draws: int = 100000, seed: int = 0) -> float:
    """Probability that a uniformly random strict ranking matches the known pairs at least as well.

    The null orders the members that appear in `known` uniformly at random and
    scores it as `pair_accuracy` does (a random strict ranking has no ties).
    The p-value is the share of rankings whose accuracy is >= `observed`:
    exact by enumerating all permutations when at most `exact_max` members are
    involved, else (1 + hits) / (draws + 1) over random permutations.
    """
    involved = sorted({name for pair in known for name in pair})
    unknown = [name for name in involved if name not in members]
    if unknown:
        raise ValueError(f"known pairs name members not in the member list: {unknown}")
    if not known:
        raise ValueError("order_null_p needs at least one known pair")
    index = {name: i for i, name in enumerate(involved)}
    pairs = [(index[h], index[l]) for h, l in known]
    need = observed * len(pairs) - 1e-9
    n = len(involved)
    if n <= exact_max:
        total = hits = 0
        for ranks in itertools.permutations(range(n)):
            total += 1
            if sum(ranks[h] > ranks[l] for h, l in pairs) >= need:
                hits += 1
        return hits / total
    rng = random.Random(seed)
    ranks = list(range(n))
    hits = 1
    for _ in range(draws):
        rng.shuffle(ranks)
        if sum(ranks[h] > ranks[l] for h, l in pairs) >= need:
            hits += 1
    return hits / (draws + 1)


def _binom_terms(n: int, p: float, lo: int, hi: int) -> float:
    """P(lo <= X <= hi) for X ~ Binomial(n, p), summed in log space so large n is safe."""
    if p <= 0.0:
        return 1.0 if lo <= 0 <= hi else 0.0
    if p >= 1.0:
        return 1.0 if lo <= n <= hi else 0.0
    log_p, log_q, log_n = math.log(p), math.log1p(-p), math.lgamma(n + 1)
    return math.fsum(
        math.exp(log_n - math.lgamma(j + 1) - math.lgamma(n - j + 1) + j * log_p + (n - j) * log_q)
        for j in range(max(lo, 0), min(hi, n) + 1))


def clopper_pearson(k: int, n: int, level: float) -> tuple[float, float]:
    """Exact two-sided binomial confidence interval for k successes in n trials.

    Each tail holds (1 - level) / 2; the bounds are found by bisection on the
    binomial CDF. The one-sided bound at confidence c is the matching side with
    level = 2c - 1: `clopper_pearson(0, 5, 0.8)[1]` is 0.369, the 90% one-sided
    upper bound. n = 0 gives (0.0, 1.0).
    """
    if not 0 <= k <= n:
        raise ValueError("need 0 <= k <= n")
    if not 0.0 < level < 1.0:
        raise ValueError("level must be in (0, 1)")
    tail = (1.0 - level) / 2.0

    def solve(f, increasing: bool) -> float:
        lo, hi = 0.0, 1.0
        for _ in range(80):
            mid = (lo + hi) / 2.0
            if (f(mid) < tail) == increasing:
                lo = mid
            else:
                hi = mid
        return (lo + hi) / 2.0

    # lower: P(X >= k | p) rises with p; upper: P(X <= k | p) falls with p
    lower = 0.0 if k == 0 else solve(lambda p: _binom_terms(n, p, k, n), True)
    upper = 1.0 if k == n else solve(lambda p: _binom_terms(n, p, 0, k), False)
    return lower, upper
