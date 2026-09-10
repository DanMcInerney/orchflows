"""Durable local receipts and read reservations for one fixed acquisition plan.

A started step without a verified receipt is uncertain, never automatically
replayed. Atomic receipt publication precedes completion, so interruption after
publication reuses the result. An OS lock prevents concurrent invocations and
is released by the OS on process death. Thread locking protects parallel lanes.
"""

from contextlib import contextmanager
import hashlib
import json
import math
import os
from pathlib import Path
import threading
import time

from acquire_plan import digest
from super_research import pacing, transport


class CheckpointError(ValueError):
    """A checkpoint is incompatible, corrupt, locked, or uncertain."""


def read_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (ValueError, OSError) as error:
        raise CheckpointError("cannot read checkpoint/input: " + str(path)) from error


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, ensure_ascii=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def package_identity(package):
    """Normalized contained package bytes, not the dispatcher's pin algorithm."""
    rows = []
    for path in sorted(Path(package).rglob("*")):
        if "__pycache__" in path.parts or path.suffix in (".pyc", ".pyo") or not path.is_file():
            continue
        if path.is_symlink():
            raise CheckpointError("package identity refuses symlink: " + str(path))
        content = path.read_bytes().replace(b"\r\n", b"\n")
        rows.append((path.relative_to(package).as_posix(), hashlib.sha256(content).hexdigest()))
    return digest({"algorithm": "recent-search-package-v1", "files": rows})


@contextmanager
def exclusive(directory):
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / ".lock").open("a+b") as lock:
        lock.seek(0)
        if os.name == "nt":
            import msvcrt
            if lock.read(1) == b"":
                lock.write(b"0")
                lock.flush()
            lock.seek(0)
            try:
                msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as error:
                raise CheckpointError("checkpoint is in use") from error
        else:
            import fcntl
            try:
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as error:
                raise CheckpointError("checkpoint is in use") from error
        try:
            yield
        finally:
            if os.name == "nt":
                lock.seek(0)
                msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


class Store:
    def __init__(self, directory, identity, plan):
        self.directory = directory
        self.path = directory / "checkpoint.json"
        self.lock = threading.RLock()
        self.limits = plan["limits"]
        self.as_of = plan["as_of"]
        if not self.path.exists() and any((directory / name).exists() for name in (
                "steps", "packet.json", "candidates.json", "summary.json", "selection.json")):
            raise CheckpointError("checkpoint missing for existing evidence; no replay authorized")
        self.state = read_json(self.path) if self.path.exists() else {
            "identity": identity, "steps": {}, "requests": [], "selection": None,
            "spent_seconds": 0.0, "pacing": None, "refused_origins": []}
        if not isinstance(self.state, dict) or self.state.get("identity") != identity:
            raise CheckpointError("plan/package identity changed; use a separate evidence directory")
        required = {"identity", "steps", "requests", "selection", "spent_seconds", "pacing", "refused_origins"}
        if (set(self.state) != required or not isinstance(self.state["steps"], dict)
                or not isinstance(self.state["requests"], list)
                or not isinstance(self.state["refused_origins"], list)
                or not isinstance(self.state["spent_seconds"], (int, float))):
            raise CheckpointError("malformed checkpoint state")
        self.save()
        # Verify every completed receipt before any additional read, even if
        # the caller only asks for the discovery checkpoint.
        for name, entry in self.state["steps"].items():
            if (not isinstance(entry, dict) or set(entry) != {"state", "input"}
                    or entry["state"] not in ("started", "complete")):
                raise CheckpointError("malformed step state: " + name)
            self.receipt(name, entry["input"])

    def save(self):
        atomic_json(self.path, self.state)

    def receipt_path(self, name):
        return self.directory / "steps" / (hashlib.sha256(name.encode()).hexdigest() + ".json")

    def receipt(self, name, identity):
        entry = self.state["steps"].get(name)
        if entry is None:
            return None
        if entry["input"] != identity:
            raise CheckpointError("step identity changed: " + name)
        path = self.receipt_path(name)
        if not path.exists():
            if entry["state"] == "complete":
                raise CheckpointError("completed step receipt missing: " + name)
            return None
        value = read_json(path)
        if (not isinstance(value, dict) or value.get("input") != identity
                or value.get("sha256") != digest(value.get("result"))
                or not isinstance(value.get("result"), dict)):
            raise CheckpointError("step receipt failed verification: " + name)
        return value["result"]

    def begin(self, name, identity):
        with self.lock:
            held = self.receipt(name, identity)
            if held is not None:
                if self.state["steps"][name]["state"] != "complete":
                    self.state["steps"][name]["state"] = "complete"
                    self.save()
                return held
            if name in self.state["steps"]:
                raise CheckpointError("uncertain interrupted step; no replay authorized: " + name)
            self.state["steps"][name] = {"state": "started", "input": identity}
            self.save()
            return None

    def finish(self, name, identity, result):
        with self.lock:
            atomic_json(self.receipt_path(name), {
                "input": identity, "sha256": digest(result), "result": result})
            self.state["steps"][name]["state"] = "complete"
            self.save()

    def bind_selection(self, selection):
        with self.lock:
            held = self.state["selection"]
            if held is not None and held != selection:
                raise CheckpointError("selection changed after hydration was bound")
            self.state["selection"] = selection
            self.save()


class BoundedRead:
    """Wrap the transport opener beneath the ordinary paced/cache governor.

    The request cap counts outbound opener attempts, including guest activation;
    urllib redirect hops remain inside that transport operation. Reservations
    are durable before I/O, so a crash cannot silently reclaim spent allowance.
    Refused origins and the governor's reserved budget state survive resume.
    """
    def __init__(self, store, opener, now, clock=time.monotonic, sleep=time.sleep):
        self.store, self.opener, self.now = store, opener, now
        self.clock, self.sleep, self.started = clock, sleep, clock()
        self.prior = store.state["spent_seconds"]
        self.local = threading.local()

    def pacing_state(self):
        held = self.store.state["pacing"]
        if held is None:
            if self.store.state["requests"]:
                raise CheckpointError("pacing state missing for reserved reads")
            return None
        if (not isinstance(held, dict) or set(held) != {"saved_at", "state"}
                or type(held["saved_at"]) not in (int, float) or not math.isfinite(held["saved_at"])
                or not isinstance(held["state"], dict)
                or set(held["state"]) != {"arrival_us", "blocked_until_us"}):
            raise CheckpointError("malformed pacing checkpoint")
        elapsed = max(0, round((time.time() - held["saved_at"]) * pacing.US_PER_SECOND))
        result = {}
        for name, values in held["state"].items():
            if (not isinstance(values, dict) or any(not isinstance(key, str) or type(value) is not int
                                                    for key, value in values.items())):
                raise CheckpointError("malformed pacing budget state")
            result[name] = {key: value - elapsed for key, value in values.items()}
        return result

    def save_pacing(self, state):
        with self.store.lock:
            self.store.state["pacing"] = {"saved_at": time.time(), "state": state}
            self.store.save()

    def decline_step(self, step_id):
        with self.store.lock:
            for request in self.store.state["requests"]:
                if request["step_id"] == step_id and request["origin"] not in self.store.state["refused_origins"]:
                    self.store.state["refused_origins"].append(request["origin"])
            self.store.save()

    def check_time(self, wait=0):
        spent = self.prior + self.clock() - self.started
        if spent + wait >= self.store.limits["max_seconds"]:
            raise transport.TransportError("plan elapsed-time budget exhausted")
        if self.now() > self.store.as_of:
            raise transport.TransportError("observation horizon expired; no new reads")

    def wait(self, seconds):
        self.check_time(seconds)
        self.sleep(seconds)

    def __call__(self, request):
        origin = transport.origin_key(request)
        with self.store.lock:
            if origin in self.store.state["refused_origins"]:
                raise transport.TransportError("origin refused earlier in this plan; no further read")
        with self.store.lock:
            self.check_time()
            if len(self.store.state["requests"]) >= self.store.limits["max_requests"]:
                raise transport.TransportError("plan request cap exhausted")
            position = len(self.store.state["requests"])
            self.store.state["requests"].append({"route_id": request.route_id,
                "url": request.url, "started_at": self.now(), "state": "reserved",
                "origin": origin, "step_id": self.local.step_id})
            self.store.save()
        began = self.clock()
        try:
            answered = self.opener(request)
        except BaseException:
            # The unacknowledged reservation stays uncertain. Never retry it.
            raise
        with self.store.lock:
            entry = self.store.state["requests"][position]
            entry.update(state="answered", status=answered[0], duration_seconds=self.clock() - began)
            if answered[0] in (401, 403, 429) or transport.rate_refused(answered[0], answered[1]):
                self.store.state["refused_origins"].append(origin)
            self.store.state["spent_seconds"] = self.prior + self.clock() - self.started
            self.store.save()
        return answered
