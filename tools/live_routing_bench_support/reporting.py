"""Summary computation and table formatting for the routing benchmark."""

from __future__ import annotations

from tools.live_routing_bench_support.grading import ERROR, UNROUTED, route_class


def _rate(counts: dict) -> float:
    """Misroutes over the sessions that ran.

    A session that failed before it could route is neither a route nor a
    misroute, so it leaves the rate rather than entering its numerator --
    otherwise the rate measures how often the CLI was reachable, which is
    not the question the README's decision rule asks.
    """

    ran = counts["n"] - counts["errors"]
    return round((ran - counts["matched"]) / ran, 4) if ran > 0 else 0.0


def summarize(records, max_budget_usd: float | None = None) -> dict:
    summary: dict = {}
    for record in records:
        bucket = summary.setdefault(
            record["adapter_set"],
            {"n": 0, "matched": 0, "unrouted": 0, "errors": 0, "cost_usd": 0.0, "by_class": {}},
        )
        by_class = bucket["by_class"].setdefault(
            route_class(record["expected"]),
            {"n": 0, "matched": 0, "unrouted": 0, "errors": 0},
        )
        for counts in (bucket, by_class):
            counts["n"] += 1
            counts["matched"] += 1 if record["match"] else 0
            counts["unrouted"] += 1 if record["observed"] == UNROUTED else 0
            counts["errors"] += 1 if record["observed"] == ERROR else 0
        bucket["cost_usd"] = round(bucket["cost_usd"] + (record.get("cost_usd") or 0.0), 6)
    spent = sum(bucket["cost_usd"] for bucket in summary.values())
    for bucket in summary.values():
        bucket["misroute_rate"] = _rate(bucket)
        for by_class in bucket["by_class"].values():
            by_class["misroute_rate"] = _rate(by_class)
        if max_budget_usd is not None:
            bucket["max_budget_usd"] = max_budget_usd
            bucket["budget_stopped"] = spent >= max_budget_usd
    return summary


def format_table(summary: dict) -> str:
    lines = [
        f"{'adapter set':<12} {'n':>4} {'matched':>8} {'misroute':>9} "
        f"{'unrouted':>9} {'errors':>7}  by class"
    ]
    for adapter_set in sorted(summary):
        bucket = summary[adapter_set]
        by_class = " ".join(
            f"{name}={counts['matched']}/{counts['n']}"
            for name, counts in sorted(bucket["by_class"].items())
        )
        lines.append(
            f"{adapter_set:<12} {bucket['n']:>4} {bucket['matched']:>8} "
            f"{bucket['misroute_rate']:>9.3f} {bucket['unrouted']:>9} "
            f"{bucket['errors']:>7}  {by_class}"
        )
    return "\n".join(lines)
