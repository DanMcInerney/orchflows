"""Shared fixtures and behavioral oracles for the partitioned pipeline suite."""

from __future__ import annotations

import dataclasses
import email.utils
import importlib.util
import json
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

from super_research import adapters, cache, normalize, probes, runner, schema, transport
from super_research.adapters import fake, reddit_archive, web_search
from tests import helpers


TESTS_DIR = Path(__file__).resolve().parent.parent
FIXTURE_DIR = TESTS_DIR / "fixtures" / "pipeline"
PACKAGE_DIR = TESTS_DIR.parent / "scripts" / "super_research"
LATER_ADAPTER = TESTS_DIR / "fixtures" / "transport" / "minimal_adapter.py"
TRACER_FIXTURE_DIR = TESTS_DIR / "fixtures" / "tracer"

SHIPPED_ADAPTERS = (web_search, reddit_archive, fake)
ADAPTERS_WITH_ROTATING_IDENTIFIERS = ("x_guest", "youtube_innertube")

REDDIT_FEED_ROUTE = "reddit_feed"
GITHUB_REST_ROUTE = "github_rest"
REDDIT_FEED_BUDGET = runner.RouteBudget(
    min_interval_ms=30000, burst=1, cooldown_ms=30000
)
GITHUB_REST_BUDGET = runner.RouteBudget(
    min_interval_ms=60000, burst=60, cooldown_ms=3600000
)
SEEDED_BUDGETS = {
    REDDIT_FEED_ROUTE: REDDIT_FEED_BUDGET,
    GITHUB_REST_ROUTE: GITHUB_REST_BUDGET,
}

OK_JSON = (200, '{"data": []}', "application/json")
RATE_LIMITED_ANSWER = (transport.RATE_LIMITED_STATUS, "slow down", "text/plain")
US_PER_MS = 1000
US_PER_SECOND = 1000000
STATED_WAIT_SECONDS = 900
SECONDARY_LIMIT_BODY = (
    '{"message": "You have exceeded a secondary rate limit. Please wait a few'
    ' minutes before you try again."}'
)
FORBIDDEN_BODY = '{"message": "Must have admin rights to Repository."}'
UNREADABLE_STATED_INTERVALS = (
    "", "   ", "soon", "-5", "9.5", "1e3", "²", "Tue, 32 Foo 2026 25:99:99 GMT"
)
EMPTY_PAGE_BODY = (200, '{"data": [], "records": []}', "application/json")
PROBE_REQUEST = adapters.AdapterRequest(
    step_id="s-probe", query="probe", target_ids=("1abc234",)
)

REDDIT_THREAD_LOCATOR = (
    "https://www.reddit.com/r/LocalLLaMA/comments/1abc234/"
    "what_is_the_best_local_model_right_now/"
)
DISCOVERY_STEP = {
    "step_id": "s1-discover",
    "kind": "discovery",
    "adapter_id": "web_search",
    "query": "site:reddit.com best local model",
    "max_items": 6,
}
HYDRATION_STEP = {
    "step_id": "s2-hydrate",
    "kind": "hydration",
    "adapter_id": "reddit_archive",
    "prior_step_id": "s1-discover",
    "selected_hits": [
        {"discovery_locator": REDDIT_THREAD_LOCATOR, "target_id": "1abc234"}
    ],
    "max_items": 6,
}
DISCOVERY_MANIFEST = {
    "schema_version": 2,
    "manifest_id": "pipeline-discover",
    "mode": "staged",
    "as_of": "2026-08-10T00:00:00Z",
    "steps": [DISCOVERY_STEP],
}
TWO_STEP_MANIFEST = {
    "schema_version": 2,
    "manifest_id": "pipeline-two-step",
    "mode": "staged",
    "as_of": "2026-08-10T00:00:00Z",
    "steps": [DISCOVERY_STEP, HYDRATION_STEP],
}
FUSED_MANIFEST = dict(TWO_STEP_MANIFEST, manifest_id="pipeline-fused", mode="fused")
STAGED_HYDRATION_MANIFEST = {
    "schema_version": 2,
    "manifest_id": "pipeline-hydrate",
    "mode": "staged",
    "as_of": "2026-08-10T00:00:00Z",
    "steps": [dict(HYDRATION_STEP, prior_step_id="")],
}
REPEAT_ROUTES = (transport.DDG_HTML_ROUTE, transport.ARCTIC_SHIFT_POSTS_ROUTE)
ROUTE_LATENCIES = {
    transport.DDG_HTML_ROUTE: helpers.DEFAULT_LATENCY_SECONDS,
    transport.ARCTIC_SHIFT_POSTS_ROUTE: 1.5,
}


def probe_request_for(adapter_id):
    probe = probes.probe_for(adapter_id)
    if probe is None:
        return PROBE_REQUEST
    # A probe that declares its own window is an adapter whose smoke reads
    # windowed, and one of them (`wikimedia_pageviews`) has no windowless
    # shape at all: what its own smoke asks it includes the bound.
    window_start = "2026-08-01T00:00:00Z" if probe.window_days else ""
    if probe.kind == "discovery":
        return adapters.AdapterRequest(
            step_id="s-probe", query=probe.target, window_start=window_start
        )
    return adapters.AdapterRequest(
        step_id="s-probe", target_ids=(probe.target,), window_start=window_start
    )


def tracer_responses():
    return {
        transport.DDG_HTML_ROUTE: (
            200,
            TRACER_FIXTURE_DIR.joinpath("ddg_html_results.html").read_text(encoding="utf-8"),
            "text/html",
        ),
        transport.ARCTIC_SHIFT_POSTS_ROUTE: (
            200,
            TRACER_FIXTURE_DIR.joinpath("arctic_shift_posts_ids.json").read_text(
                encoding="utf-8"
            ),
            "application/json",
        ),
    }


def probe_request(route_id, index=0):
    return transport.TransportRequest(
        route_id=route_id,
        method="GET",
        url="probe://{0}/{1}".format(route_id, index),
        headers=(("User-Agent", transport.USER_AGENT), ("Accept", "application/json")),
    )


def paced_governor(clock, responses, latencies=None, budgets=None, governor_class=None):
    carrier, opener = helpers.offline_transport(clock, responses, latencies=latencies)
    governor = (runner.RateGovernor if governor_class is None else governor_class)(
        carrier,
        budgets=SEEDED_BUDGETS if budgets is None else budgets,
        clock=clock.monotonic,
        sleep=clock.sleep,
    )
    return governor, opener


def answer_stating(route_id, index, status, body, headers, content_type="text/plain"):
    return (status, body, content_type, probe_request(route_id, index).url, headers)


def moment_after(seconds):
    started = datetime.strptime(helpers.FROZEN_START, helpers.STAMP_FORMAT).replace(
        tzinfo=timezone.utc
    )
    return started + timedelta(seconds=seconds)


def http_date_after(seconds):
    return email.utils.format_datetime(moment_after(seconds), usegmt=True)


def epoch_after(seconds):
    return str(int(moment_after(seconds).timestamp()))


def cooldown_us(governor, index=0):
    refusal = governor.log[index]
    return governor.log[index + 1].at_us - (refusal.at_us + refusal.duration_us)


def load_module_beside_the_tree(path):
    spec = importlib.util.spec_from_file_location("pipeline_fixture_" + path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def adapter_page(module, clock, answers):
    carrier, opener = helpers.offline_transport(
        clock, {module.DESCRIPTOR.route_id: answers}
    )
    return module.fetch_native_page(carrier, PROBE_REQUEST), opener


def package_sources():
    return sorted(PACKAGE_DIR.rglob("*.py"))


def adapter_sources():
    return sorted(
        path
        for path in (PACKAGE_DIR / "adapters").rglob("*.py")
        if path.name != "__init__.py"
    )


def sources_naming(names, paths):
    return sorted(
        (path.name, name)
        for path in paths
        for name in names
        if name in path.read_text(encoding="utf-8")
    )


def assert_rate_budget_respected(case, governor, budgets):
    if not governor.log:
        raise AssertionError("no origin read was made, so no budget was exercised")

    theoretical = {}
    blocked_until = {}
    for read in governor.log:
        budget = budgets.get(read.route_id)
        if budget is None:
            raise AssertionError(
                "route {0} was read with no declared budget".format(read.route_id)
            )
        interval_us = budget.min_interval_ms * US_PER_MS
        allowance_us = (budget.burst - 1) * interval_us
        arrival = theoretical.get(read.route_id)
        earliest = blocked_until.get(read.route_id, 0)
        if arrival is not None:
            earliest = max(earliest, arrival - allowance_us)
        if read.at_us < earliest:
            raise AssertionError(
                "a read outran its route's declared budget: {0} was read at {1} us,"
                " admissible at {2} us under {3}".format(
                    read.route_id, read.at_us, earliest, budget
                )
            )
        theoretical[read.route_id] = (
            max(read.at_us if arrival is None else arrival, read.at_us) + interval_us
        )
        if read.status == transport.RATE_LIMITED_STATUS:
            blocked_until[read.route_id] = (
                read.at_us + read.duration_us + budget.cooldown_ms * US_PER_MS
            )

    identities = sorted(
        {
            value
            for request in governor.calls
            for name, value in request.headers
            if name.lower() == "user-agent"
        }
    )
    if identities != [transport.USER_AGENT]:
        raise AssertionError(
            "the identity changed between reads, which is evasion rather than"
            " respect: {0}".format(identities)
        )


CONCURRENCY_MODULES = (
    "asyncio", "concurrent", "multiprocessing", "threading", "_thread"
)
