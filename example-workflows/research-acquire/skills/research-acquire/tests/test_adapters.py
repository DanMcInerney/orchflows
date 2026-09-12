"""Retained adapter behavior and shared fixture helpers."""

from __future__ import annotations

import ast
import importlib.util
import json
import locale
import unittest
import urllib.parse
import urllib.request
from pathlib import Path
from unittest import mock

from super_research import adapters, cache, normalize, runner, schema, transport
from super_research.adapters import fake, github_rest, hacker_news, reddit_archive, rss_atom
from tests import helpers, test_pipeline
from tests.test_transport import ROUTE_OWNING_MODULES


TEST_DIR = Path(__file__).resolve().parent
# T02's captive-portal body, read rather than copied: an adapter inherits
# interception typing from the protocol, and the proof has to be the same
# measured body the transport suite uses or it proves something else.
TRANSPORT_FIXTURE_DIR = TEST_DIR / "fixtures" / "transport"
PACKAGE_DIR = TEST_DIR.parent / "scripts" / "super_research"
ADAPTER_DIR = PACKAGE_DIR / "adapters"

# The 2026-08-10 probes (X): every field the syndication row records this route
# returning for each of its 100 timeline entries.

PROFILE_REQUEST = adapters.AdapterRequest(step_id="s1-x", target_ids=("simonw",))






def adapters_named(path, own_id):
    """Every adapter id one source names that is not its own."""

    source = adapter_owner_source(path)
    return sorted(
        adapter_id
        for adapter_id in runner.ADAPTER_IDS
        if adapter_id != own_id and adapter_id in source
    )


def adapter_owner_paths(path):
    """One adapter module: every source that owns its behavior."""

    return (path,)


def adapter_owner_source(path):
    """The source read as one logical adapter owner, never as dispatch modules."""

    return path.read_text(encoding="utf-8")




def load_adapter_fixture(name, directory=None):
    """Load one adapter written beside the tree, by path.

    These are not package modules: nothing in the package imports them and no
    discovery pattern matches them. They exist so the oracle below can be shown
    to reject a wrong result, without mutating the tree under test.
    """

    spec = importlib.util.spec_from_file_location(
        "adapter_fixture_" + name,
        directory / (name + ".py"),
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module






def adapter_page(module, status, body, content_type="text/html", request=None):
    """Run one adapter over one canned response; return its page and the opener."""

    clock = helpers.FakeClock()
    carrier, opener = helpers.offline_transport(
        clock, {module.DESCRIPTOR.route_id: (status, body, content_type)}
    )
    return (
        module.fetch_native_page(carrier, PROFILE_REQUEST if request is None else request),
        opener,
    )


class FakeHTTPResponse:
    """The little of an http response that ``urlopen_read`` reads."""

    def __init__(self, status, body, content_type, url=""):
        self.status = status
        self.url = url
        self.headers = {"Content-Type": content_type}
        self._body = body.encode("utf-8")

    def read(self, limit):
        return self._body[:limit]

    def __enter__(self):
        return self

    def __exit__(self, *exception):
        return False









def counts_of(record):
    """One record's metrics by name, on whichever side of normalize it sits.

    A native record carries pairs and an artifact record carries snapshots. The
    roster row is the same row either way, and reading it at both ends is how
    "the route reaches its capability" stops being a claim about an
    intermediate value.
    """

    named = {}
    for metric in record.engagement:
        if isinstance(metric, schema.EngagementSnapshot):
            named[metric.metric_name] = metric.value
        else:
            named[metric[0]] = metric[1]
    return named

def assert_one_answer_costs_one_call(case, adapter_id, rows, run, routes):
    """Row 3's oracle: one bounded call in, exactly one page out, on one route.

    ``run`` answers one case with the page an adapter produced and the opener
    that saw what left. Two adapters here read two origins each, so "one page
    per call" is not only about pagination and retries: an adapter that
    answered a search by also reading the item it found would be two reads
    charged to one page, on two budgets, with one observation time — and the
    core, which owns pacing and sequence, would never see the second.
    """

    for row in rows:
        name = row["case_name"]
        page, opener = run(row)
        detail = " {0} case {1}".format(adapter_id, name)
        if not isinstance(page, adapters.NativePage):
            case.fail("an answer was not one NativePage:" + detail)
        if len(opener.opened) != 1:
            case.fail(
                "one answer cost {0} calls rather than one:{1}".format(
                    len(opener.opened), detail
                )
            )
        if opener.opened[0].route_id != page.route_id:
            case.fail(
                "the page names route {0} and the call went to {1}:{2}".format(
                    page.route_id, opener.opened[0].route_id, detail
                )
            )
        if page.route_id not in routes:
            case.fail(
                "an answer came back on a route this adapter never declared: {0}{1}".format(
                    page.route_id, detail
                )
            )

def attribute_pairs(record, name):
    """Every value one record carries under one attribute name, in its own order."""

    return tuple(value for carried, value in record.attributes if carried == name)

def as_a_last_page(body):
    """One capture with the next-page claim it makes dropped."""

    for claim, replacement in (('"nbPages": 50', '"nbPages": 1'),):
        if claim in body:
            return body.replace(claim, replacement)
    raise AssertionError("this capture states no next page to drop")

def names_read(path, name):
    """How many times one source reads a name, its own definition excluded.

    A constant a module declares and never reads is a statement that the module
    has seen the thing and does not act on it. That is exactly what
    ``NAVIGATION_CHROME`` is for, and a count is the only way to check it from
    outside — a string scan would count the module's own prose.

    Both ways of reaching it are counted: bare, as the declaring module would,
    and through its module, as anything else would. A scan that counted only
    the first would pass any module that imported the constant instead.
    """

    read = 0
    for owner in adapter_owner_paths(path):
        for node in ast.walk(ast.parse(owner.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Name) and node.id == name:
                read += 1 if isinstance(node.ctx, ast.Load) else 0
            elif isinstance(node, ast.Attribute) and node.attr == name:
                read += 1
    return read

# Test classes stay discoverable through this structural facade.
from tests.test_adapters_cases.hacker_news_github_routes import *  # noqa: F401,F403
from tests.test_adapters_cases.hacker_news_read import *  # noqa: F401,F403
from tests.test_adapters_cases.hacker_news_claims import *  # noqa: F401,F403
from tests.test_adapters_cases.github_read import *  # noqa: F401,F403
from tests.test_adapters_cases.github_write_safety import *  # noqa: F401,F403
from tests.test_adapters_cases.hacker_news_github_calls import *  # noqa: F401,F403
from tests.test_adapters_cases.hacker_news_github_ttl import *  # noqa: F401,F403
from tests.test_adapters_cases.hacker_news_github_artifact import *  # noqa: F401,F403
from tests.test_adapters_cases.feed_page_routes import *  # noqa: F401,F403
from tests.test_adapters_cases.rss_atom import *  # noqa: F401,F403
from tests.test_adapters_cases.feed_page_calls_and_ttl import *  # noqa: F401,F403
from tests.test_adapters_cases.feed_page_artifact import *  # noqa: F401,F403
from tests.test_adapters_cases.unrecognized_and_roster import *  # noqa: F401,F403
from tests.test_adapters_cases.fake_attributes import *  # noqa: F401,F403
