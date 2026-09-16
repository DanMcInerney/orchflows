"""Authentication, invalid-request atomicity, and validation requirements."""

import time

from harness import CONFIG, assert_ids, require, signed_headers, status_is


def wrong_signature(s):
    body = b'{"attempt":"bad-signature"}'
    headers = signed_headers("alpha", "bad-then-good", body, secret="wrong-secret")
    status_is(s.request("POST", "/webhooks/alpha", body, headers), 401)
    require(s.page()["items"] == [], "bad signature inserted a row")
    status_is(s.post(event_id="bad-then-good", body=body), 201)


def cross_tenant_signature(s):
    body = b'{"cross":"tenant"}'
    headers = signed_headers("alpha", "cross", body)
    status_is(s.request("POST", "/webhooks/beta", body, headers), 401)
    require(s.page("alpha")["items"] == [] and s.page("beta")["items"] == [], "cross-tenant signature caused a write")
    status_is(s.post("beta", "cross", body), 201)


def replay_still_authenticated(s):
    body = b'{"retry":"original"}'
    status_is(s.post(event_id="retry", body=body), 201)
    before = s.page()
    status_is(s.post(event_id="retry", body=body, secret="forged"), 401)
    status_is(s.post(event_id="retry", body=body, timestamp=int(time.time()) - 360), 401)
    status_is(s.post(event_id="retry", body=b'{"changed":true}', secret="forged"), 401)
    require(s.page() == before, "unauthenticated retries changed the row")


def skew_window(s):
    now = int(time.time())
    for i, delta in enumerate([-290, 0, 290]):
        status_is(s.post(event_id=f"allowed-{i}", timestamp=now + delta), 201)
    before = s.page()
    for i, delta in enumerate([-360, 360]):
        status_is(s.post(event_id=f"outside-{i}", timestamp=now + delta), 401)
    require(s.page() == before, "out-of-window request inserted a row")


def malformed_post_headers(s):
    body = b'{"safe":true}'
    valid = signed_headers("alpha", "invalid-header", body)
    variants = []
    for key in valid:
        missing = dict(valid)
        missing.pop(key)
        variants.append(missing)
    now = str(int(time.time()))
    for timestamp in ["-1", "+" + now, "0" + now, now + ".0", "abc", ""]:
        variants.append(signed_headers("alpha", "invalid-header", body, timestamp=timestamp))
    for signature in ["A" * 64, "f" * 63, "g" * 64, ""]:
        variants.append(dict(valid, **{"X-Signature": signature}))
    for event_id in ["", "x" * 129]:
        variants.append(dict(valid, **{"X-Event-ID": event_id}))
    for headers in variants:
        status_is(s.request("POST", "/webhooks/alpha", body, headers), 400)
    require(s.page()["items"] == [], "malformed headers created state")
    status_is(s.post(event_id="invalid-header", body=body), 201)


def malformed_json_bodies(s):
    bodies = [b'{', b'[]', b'null', b'"string"', b'12', b'false', b'', b'{"bad":"\xff"}']
    for body in bodies:
        status_is(s.post(event_id="reusable-invalid", body=body), 400)
    require(s.page()["items"] == [], "malformed body created state")
    status_is(s.post(event_id="reusable-invalid", body=b'{"valid":true}'), 201)


def body_size(s):
    prefix, suffix = b'{"pad":"', b'"}'
    body = prefix + b'a' * (65536 - len(prefix) - len(suffix)) + suffix
    require(len(body) == 65536, "evaluator size fixture is invalid")
    status_is(s.post(event_id="at-limit", body=body), 201)
    too_large = prefix + b'a' * (65537 - len(prefix) - len(suffix)) + suffix
    status_is(s.post(event_id="over-limit", body=too_large), 413)
    assert_ids(s.page(), ["at-limit"])
    status_is(s.post(event_id="over-limit", body=b'{"now":"small"}'), 201)


def read_authorization(s):
    for headers in [{}, {"Authorization": "Bearer bad"}, {"Authorization": "Basic anything"}, {"Authorization": "Bearer"}, {"Authorization": "Bearer " + CONFIG["tenants"]["beta"]["token"]}]:
        status_is(s.request("GET", "/events/alpha", headers=headers), 401)
    status_is(s.get("alpha"), 200)
    status_is(s.get("beta"), 200)


def read_auth_with_stored_rows(s):
    status_is(s.post("alpha", "private-a", b'{"secret":"alpha-payload"}'), 201)
    status_is(s.post("beta", "private-b", b'{"secret":"beta-payload"}'), 201)
    status_is(s.get("alpha", token=CONFIG["tenants"]["beta"]["token"]), 401)
    status_is(s.get("beta", token=CONFIG["tenants"]["alpha"]["token"]), 401)
    assert_ids(s.page("alpha"), ["private-a"])
    assert_ids(s.page("beta"), ["private-b"])


def query_validation(s):
    queries = ["?limit=0", "?limit=101", "?limit=-1", "?limit=1.5", "?limit=abc", "?limit=01", "?limit=", "?cursor=-1", "?cursor=1.5", "?cursor=abc", "?cursor=01", "?cursor=", "?cursor=+1", "?limit=2&limit=3", "?cursor=0&cursor=1", "?tenant=beta", "?unknown=1"]
    for query in queries:
        status_is(s.get(query=query), 400)
    require(s.page()["items"] == [], "query validation changed stored state")


def unknown_tenant_and_path(s):
    body = b'{"unknown":true}'
    headers = signed_headers("alpha", "unknown", body)
    status_is(s.request("POST", "/webhooks/unknown", body, headers), 404)
    status_is(s.request("GET", "/events/unknown", headers={"Authorization": "Bearer " + CONFIG["tenants"]["alpha"]["token"]}), 404)
    status_is(s.request("GET", "/not-a-route"), 404)
    status_is(s.request("POST", "/not-a-route", body, headers), 404)
    require(s.page()["items"] == [] and s.page("beta")["items"] == [], "unknown route created state")


def event_id_boundaries(s):
    for event_id in ["x", "z" * 128, "ID: with spaces / symbols?!"]:
        result = status_is(s.post(event_id=event_id), 201)
        require(result.get("event_id") == event_id, "accepted event ID was normalized")
    assert_ids(s.page(), ["x", "z" * 128, "ID: with spaces / symbols?!"])


def no_credential_disclosure(s):
    responses = [s.request("GET", "/health"), s.get("alpha"), s.get("alpha", token="wrong"), s.post(secret="wrong")]
    text = repr(responses)
    for tenant in CONFIG["tenants"].values():
        require(tenant["secret"] not in text and tenant["token"] not in text, "HTTP response disclosed a credential")


def content_length_validation(s):
    import http.client
    import json
    body = b'{"length":"checked"}'
    for length in [None, "-1", "abc", "1.5"]:
        conn = http.client.HTTPConnection(*s.address, timeout=8)
        try:
            conn.putrequest("POST", "/webhooks/alpha")
            for name, value in signed_headers("alpha", "length-test", body).items():
                conn.putheader(name, value)
            if length is not None:
                conn.putheader("Content-Length", length)
            conn.endheaders(body)
            response = conn.getresponse()
            status_is((response.status, json.loads(response.read())), 400)
        finally:
            conn.close()
    require(s.page()["items"] == [], "malformed Content-Length caused a write")
    status_is(s.post(event_id="length-test", body=body), 201)


CHECKS = [
    ("wrong_signature_no_effect_then_valid", "security", wrong_signature),
    ("cross_tenant_signature_rejected", "security", cross_tenant_signature),
    ("duplicates_and_conflicts_reauthenticate", "security", replay_still_authenticated),
    ("timestamp_past_and_future_window", "security", skew_window),
    ("malformed_required_headers_no_effect", "validation", malformed_post_headers),
    ("malformed_json_and_utf8_no_effect", "validation", malformed_json_bodies),
    ("body_65536_boundary_and_oversize_atomicity", "validation", body_size),
    ("missing_wrong_and_cross_tenant_read_tokens", "security", read_authorization),
    ("read_tokens_protect_stored_tenant_data", "security", read_auth_with_stored_rows),
    ("malformed_repeated_unknown_query", "validation", query_validation),
    ("unknown_tenants_and_routes", "validation", unknown_tenant_and_path),
    ("event_id_boundaries_and_fidelity", "data", event_id_boundaries),
    ("responses_do_not_disclose_credentials", "security", no_credential_disclosure),
    ("missing_and_malformed_content_length", "validation", content_length_validation),
]
