"""Immutable review ledger with exclusive locking and checked predecessors."""
from __future__ import annotations

import json
import hashlib
import sqlite3
import os
import uuid
from contextlib import closing, contextmanager
from pathlib import Path

from improve_spool import Rows, encoded
from improve_common import EvidenceError, canonical, digest, read_json, redact, safe_sink
from improve_lifecycle import close_probe, projection, require, validate


def review_path(review):
    require(isinstance(review, str) and len(review) == 32 and all(c in "0123456789abcdef" for c in review), "invalid review identity")
    return safe_sink() / "reviews" / review


def atomic(path, value):
    temporary = path.with_name("." + path.name + "." + uuid.uuid4().hex)
    try:
        with temporary.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(canonical(value) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(str(temporary), str(path))
    finally:
        if temporary.exists():
            temporary.unlink()


@contextmanager
def locked(path):
    lock = path / ".write-lock"
    try:
        descriptor = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        raise EvidenceError("review busy; retry after writer finishes; abandoned lock requires operator inspection") from None
    try:
        os.write(descriptor, str(os.getpid()).encode())
        os.close(descriptor)
        yield
    finally:
        lock.unlink()


def create(bundle):
    root = safe_sink(bundle["selection"]["sources"])
    review = uuid.uuid4().hex
    path = root / "reviews" / review
    path.mkdir(parents=True, exist_ok=False)
    (path / "records").mkdir()
    hasher = hashlib.sha256()
    with (path / "bundle.json").open("wb") as stream:
        for chunk in encoded(bundle):
            data = chunk.encode("utf-8")
            stream.write(data)
            hasher.update(data)
    revision = hasher.hexdigest()
    counts = {}
    with closing(sqlite3.connect(path / "pages.sqlite")) as pages, pages:
        pages.execute("CREATE TABLE pages (section TEXT, position INTEGER, body TEXT, digest TEXT, PRIMARY KEY(section,position))")
        for section, key in (("observations", "observations"), ("sources", "sources"),
                             ("context", "structural_context"), ("gaps", "gaps")):
            counts[section] = len(bundle[key])
            for index, item in enumerate(bundle[key]):
                body = "".join(encoded(item))
                pages.execute("INSERT INTO pages VALUES (?,?,?,?)", (section, index, body, hashlib.sha256(body.encode()).hexdigest()))
    summary = {"review": review, "bundle": str(path / "bundle.json"), "revision": revision,
               "coverage": bundle["coverage"], "selection": bundle["selection"],
               "occurrence_identity": bundle.get("occurrence_identity", "legacy; attribution may be ambiguous"),
               "gap_count": counts["gaps"], "counts": counts, "acquisition": bundle.get("acquisition"),
               "pages": {section: {"section": section, "offset": 0} for section in counts}}
    atomic(path / "summary.json", summary)
    return summary



def load(review):
    path = review_path(review)
    bundle = read_json(path / "bundle.json")
    safe_sink(bundle["selection"]["sources"])
    revision = digest(bundle)
    records = []
    for file in sorted((path / "records").glob("*.json")):
        envelope = read_json(file)
        entry = envelope["record"]
        require(entry["predecessor"] == revision, "corrupt ledger predecessor")
        require(envelope["revision"] == digest(entry), "corrupt ledger record digest")
        validate(entry, bundle, records)
        records.append(entry)
        revision = envelope["revision"]
    return bundle, records, revision


def record(review, raw):
    # Redact before comparison and persistence; original source bytes are never copied.
    entry = redact(raw)
    require(isinstance(entry, dict), "record must be an object")
    path = review_path(review)
    if not path.is_dir():
        raise EvidenceError("review not found")
    with locked(path):
        bundle, records, revision = load(review)
        for existing in records:
            if existing["id"] == entry.get("id"):
                require(canonical(existing) == canonical(entry), "same ID with different content")
                return {"record": existing["id"], "revision": digest(existing), "head": revision, "idempotent": True}
        require(entry.get("predecessor") == revision, "stale predecessor; show current revision before retry")
        if entry.get("kind") == "prior_proposal":
            require(entry.get("source_review") != review, "prior proposal must name another review")
            prior_bundle, prior_records, prior_revision = load(entry["source_review"])
            require(entry.get("source_revision") == prior_revision, "stale prior review revision")
            prior = projection(prior_bundle, prior_records)
            original = prior["proposals"].get(entry["id"])
            require(original is not None and entry.get("proposal") == original, "prior proposal differs from original evidence")
            require(entry.get("stage") == prior["states"][entry["id"]], "prior lifecycle differs from original")
            require(entry.get("original_incidents") == {i: prior["incidents"][i] for i in original["incidents"]}, "original incident provenance differs")
        validate(entry, bundle, records)
        envelope = {"record": entry, "revision": digest(entry)}
        atomic(path / "records" / ("%08d.json" % (len(records) + 1)), envelope)
        return {"record": entry["id"], "revision": envelope["revision"], "idempotent": False}


def show(review, section=None, offset=0, limit=100):
    if section is not None and section != "records" and (review_path(review) / "summary.json").is_file():
        require(type(offset) is int and offset >= 0 and type(limit) is int and 1 <= limit <= 1000, "page requires offset >= 0 and limit 1..1000")
        path = review_path(review)
        summary = read_json(path / "summary.json")
        safe_sink(summary["selection"]["sources"])
        require(section in summary["counts"], "unknown page section")
        items = []
        with closing(sqlite3.connect("file:" + path.joinpath("pages.sqlite").as_posix() + "?mode=ro", uri=True)) as pages:
            for body, expected in pages.execute("SELECT body,digest FROM pages WHERE section=? AND position>=? ORDER BY position LIMIT ?", (section, offset, limit)):
                require(hashlib.sha256(body.encode()).hexdigest() == expected, "corrupt evidence page")
                items.append(json.loads(body))
        total = summary["counts"][section]
        revision = summary["revision"]
        for file in sorted((path / "records").glob("*.json")):
            envelope = read_json(file)
            require(envelope["record"]["predecessor"] == revision and envelope["revision"] == digest(envelope["record"]), "corrupt ledger predecessor")
            revision = envelope["revision"]
        return {"review": review, "revision": revision, "selection": summary["selection"],
                "coverage": summary["coverage"], "gap_count": summary["gap_count"],
                "section": section, "offset": offset, "total": total, "items": items,
                "next_offset": offset + limit if offset + limit < total else None,
                "page_is_collection": False}
    bundle, records, revision = load(review)
    if section is not None:
        require(type(offset) is int and offset >= 0 and type(limit) is int and 1 <= limit <= 1000, "page requires offset >= 0 and limit 1..1000")
        if section == "observations":
            items = bundle["observations"]
        elif section == "sources":
            items = bundle["sources"]
        elif section == "context":
            items = bundle["structural_context"]
        elif section == "gaps":
            items = bundle["gaps"]
        elif section == "records":
            items = records
        else:
            raise EvidenceError("unknown page section")
        return {"review": review, "revision": revision, "selection": bundle["selection"],
                "coverage": bundle["coverage"], "gap_count": len(bundle["gaps"]),
                "section": section, "offset": offset, "total": len(items),
                "items": items[offset:offset + limit],
                "next_offset": offset + limit if offset + limit < len(items) else None,
                "page_is_collection": False}
    return {"review": review, "revision": revision, "bundle": bundle, "records": records,
            "projection": projection(bundle, records)}


def close(review, mode):
    bundle, records, revision = load(review)
    require(mode in {"review", "repair"}, "close mode must be review|repair")
    if mode == "repair":
        require(bundle["selection"]["mode"] == "repair", "frozen selection is review mode")
    result = close_probe(bundle, records, mode)
    return dict(result, review=review, revision=revision)
