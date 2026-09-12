"""Offline harness for selected FxTwitter conversation reads."""

from __future__ import annotations

import unittest
from pathlib import Path

from super_research import adapters, transport
from super_research.adapters import x_fxtwitter
from tests import helpers

FIXTURE_DIR = Path(__file__).resolve().parent.parent / "fixtures"
FXTWITTER_DIR = FIXTURE_DIR / "x_fxtwitter"

FXTWITTER_ROUTE = transport.FXTWITTER_API_ROUTE

JSON_TYPE = "application/json"

X_ROOT_ID = "2088841930813690331"


def read_fixture(directory, name):
    return directory.joinpath(name).read_text(encoding="utf-8")


def discovery(query, **bounds):
    return adapters.AdapterRequest(step_id="s1-social", query=query, **bounds)


def hydration(target, **bounds):
    return adapters.AdapterRequest(step_id="s1-social", target_ids=(target,), **bounds)


def answered(module, route_id, body, request, status=200, content_type=JSON_TYPE):
    """Run one adapter over one canned answer; return its page and the opener."""

    clock = helpers.FakeClock()
    carrier, opener = helpers.offline_transport(
        clock, {route_id: (status, body, content_type)}
    )
    return (module.fetch_native_page(carrier, request), opener)


def fxtwitter_page(name, request, status=200, content_type=JSON_TYPE):
    return answered(
        x_fxtwitter, FXTWITTER_ROUTE, read_fixture(FXTWITTER_DIR, name), request, status,
        content_type,
    )
