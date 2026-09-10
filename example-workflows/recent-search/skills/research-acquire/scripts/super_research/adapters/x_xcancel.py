"""K3 X search and selected status reads through xcancel's public Nitter HTML.

Markup is source-derived, not a captured successful xcancel response. Both
2026-09-10 live probes returned a browser challenge. This parser never runs
that challenge, imports cookies, retries, switches hosts or follows links.
Pagination and server-side time filtering remain unverified.
"""
from __future__ import annotations

import re
from dataclasses import replace
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Tuple
from urllib.parse import urlsplit

from .. import schema, transport
from . import AdapterDescriptor, AdapterRequest, NativeRecord, build_native_page, fetch_one_page

DESCRIPTOR = AdapterDescriptor(
    adapter_id="x_xcancel", adapter_version="1", access_class="K3",
    route_id=transport.XCANCEL_SEARCH_ROUTE, platform="x",
    native_identity_namespace="x", representation_kind="native",
    operator_identity="xcancel", standing_loss=("third_party_archive",),
    reply_count_metric="icon-comment",
)
STATUS_DESCRIPTOR = replace(DESCRIPTOR, route_id=transport.XCANCEL_STATUS_ROUTE)
SURFACE_DESCRIPTORS = (DESCRIPTOR, STATUS_DESCRIPTOR)
STATUS_PATH = r"/([A-Za-z0-9_]{1,15})/status/([0-9]+)"
STATUS_TARGET = r"([A-Za-z0-9_]{1,15})/([0-9]+)"
METRICS = ("icon-comment", "icon-retweet", "icon-heart", "icon-views")
VOID_TAGS = {"br", "img", "input", "meta", "link", "hr", "source", "wbr"}


def operation_for(request: AdapterRequest) -> Tuple[str, str]:
    named = request.target_ids[0] if request.target_ids else request.query
    operation, separator, argument = named.partition(":")
    if separator and operation in ("search", "status"):
        return operation, argument
    return ("status" if request.target_ids else "search"), named


def _instant(text):
    for pattern in (schema.INSTANT_FORMAT, "%b %d, %Y · %I:%M %p UTC", "%b %d, %Y · %I:%M %p %Z"):
        try:
            return datetime.strptime(text, pattern).replace(tzinfo=timezone.utc).strftime(schema.INSTANT_FORMAT)
        except ValueError:
            pass
    return ""


class _Tweets(HTMLParser):
    """Collect direct tweet fields while keeping quote cards and chrome out."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.rows = []
        self.row = None
        self.root_depth = 0
        self.closed_timelines = 0
        self.malformed = False
        self.more = False
        self.empty = False
        self.title = ""

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = set((attrs.get("class") or "").split())
        ancestors = set().union(*(entry[1] for entry in self.stack)) if self.stack else set()
        quoted = bool({"quote", "quote-link", "quote-big"} & (classes | ancestors))
        inside = "timeline" in ancestors and not quoted
        if "show-more" in classes and inside:
            self.more = True
        if "timeline-none" in classes and inside and self.row is None:
            self.empty = True
        if "timeline-item" in classes and not quoted and not inside:
            self.malformed = True
        if "timeline-item" in classes and inside and self.row is None:
            self.row = {"path": "", "author": "", "body": "", "time": "", "stats": []}
            self.root_depth = len(self.stack)
        if self.row is not None and not quoted:
            if tag == "a" and ("tweet-link" in classes or "tweet-date" in ancestors):
                href = attrs.get("href") or ""
                parsed = urlsplit(href)
                # Only the relative status path this HTML surface declares.
                if not parsed.scheme and not parsed.netloc and re.fullmatch(STATUS_PATH, parsed.path):
                    self.row["path"] = parsed.path
                    if "tweet-date" in ancestors:
                        self.row["time"] = attrs.get("title") or ""
            if "tweet-stat" in classes:
                self.row["stats"].append(["", ""])
            metric = next((name for name in METRICS if name in classes), "")
            if metric and self.row["stats"] and "tweet-stat" in ancestors:
                self.row["stats"][-1][0] = metric
        if tag not in VOID_TAGS:
            self.stack.append((tag, classes))

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                removed = self.stack[index:]
                if index != len(self.stack) - 1 and any("timeline" in entry[1] for entry in self.stack):
                    self.malformed = True
                self.closed_timelines += sum("timeline" in entry[1] for entry in removed)
                del self.stack[index:]
                if self.row is not None and len(self.stack) <= self.root_depth:
                    self.rows.append(self.row)
                    self.row = None
                return

    def handle_data(self, data):
        if any(tag == "title" for tag, _ in self.stack):
            self.title += data
        if self.row is None:
            return
        classes = set().union(*(entry[1] for entry in self.stack))
        if classes & {"quote", "quote-link", "quote-big"} or any(tag in ("script", "style") for tag, _ in self.stack):
            return
        if "tweet-content" in classes:
            self.row["body"] += data
        elif "username" in classes:
            self.row["author"] += data
        elif "tweet-stat" in classes and self.row["stats"]:
            self.row["stats"][-1][1] += data


def _record(row, position):
    path = re.fullmatch(STATUS_PATH, row["path"])
    if path is None:
        return None
    counts = []
    attributes = []
    for name, raw in row["stats"]:
        if not name:
            continue
        spelling = raw.strip()
        if re.fullmatch(r"(?:[0-9]+|[0-9]{1,3}(?:,[0-9]{3})+)", spelling):
            value = int(spelling.replace(",", ""))
            if value <= 2 ** 63 - 1:
                counts.append((name, value))
        elif spelling:
            attributes.append((name, spelling))
    published = _instant(row["time"])
    body = row["body"].strip()
    author = row["author"].strip().lstrip("@")
    loss = DESCRIPTOR.standing_loss
    if not published or not body or not author:
        loss += ("field_omitted",)
    return NativeRecord(
        canonical_content_kind="post", canonical_locator=transport.X_SITE_ORIGIN + row["path"],
        native_item_id=path[2], body=body, author=author, published_at=published,
        engagement=tuple(counts), attributes=tuple(attributes), native_position=position, loss=loss,
    )


def _page(response, descriptor, selected=""):
    def answer(records=(), outcome="failed", loss=(), warnings=()):
        return build_native_page(descriptor, tuple(records), observed_at=response.observed_at,
                                 native_order="xcancel_page_order", outcome=outcome, loss=loss, warnings=warnings)
    parser = _Tweets()
    parser.feed(response.body)
    parser.close()
    if "verifying your browser" in parser.title.lower() or "anubis_challenge" in response.body.lower():
        return answer(outcome="refused", loss=("attestation_required",),
                      warnings=("xcancel browser challenge; no challenge execution or alternate route attempted",))
    if response.status != 200:
        return answer(loss=("http_status",), warnings=("xcancel HTTP {0}".format(response.status),))
    records = tuple(record for position, row in enumerate(parser.rows)
                    for record in (_record(row, position),) if record is not None
                    and (not selected or row["path"] == selected))
    unread = (parser.malformed or parser.row is not None
              or any("timeline" in classes for _, classes in parser.stack)
              or any(not row["path"] for row in parser.rows))
    if records:
        losses = (("schema_drift",) if unread else ()) + (("recall_window_partial",) if parser.more else ())
        return answer(records, "partial" if unread else "ok", losses,
                      ("Pagination and search window filtering are unverified; one page only",))
    if not selected and parser.closed_timelines and parser.empty and not parser.rows and not unread:
        return answer(outcome="empty")
    return answer(loss=("schema_drift",), warnings=("No readable requested status or recognized empty timeline",))


def fetch_native_page(carrier, request):
    operation, argument = operation_for(request)
    selected = ""
    if operation == "status":
        parsed = urlsplit(argument)
        if parsed.scheme == "https" and parsed.netloc == urlsplit(transport.X_SITE_ORIGIN).netloc and not parsed.query and not parsed.fragment:
            matched = re.fullmatch(STATUS_PATH, parsed.path)
        else:
            matched = re.fullmatch(STATUS_TARGET, argument)
        if matched is None:
            return build_native_page(STATUS_DESCRIPTOR, (), outcome="refused", loss=("unselected_target",),
                                     warnings=("status target must be handle/numeric-id or a canonical X status URL",))
        descriptor = STATUS_DESCRIPTOR
        params = {"handle": matched[1], "collection": "status", "id": matched[2]}
        selected = "/{0}/status/{1}".format(matched[1], matched[2])
    else:
        descriptor = DESCRIPTOR
        params = {"f": "tweets", "q": argument}
    return fetch_one_page(descriptor, carrier, params=params,
                          parse=lambda response: _page(response, descriptor, selected),
                          native_order="xcancel_page_order")
