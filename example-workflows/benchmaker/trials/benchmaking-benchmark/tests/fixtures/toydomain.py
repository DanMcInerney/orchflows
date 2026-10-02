"""A toy domain matching the kit's package-mini fixture: sum the numbers of input.json into output.json.

It implements the metabench hook protocol with the smallest possible rules, so the runtime tests need no real
domain. `metabench.registry` loads it by file path (`MetaTask.domain_file`).
"""
import json
from pathlib import Path

NAME = "toy"
INPUT, OUTPUT = "input.json", "output.json"
DEFECTS = {}
HEURISTICS = {}


def recognize(workspace, prompt=""):
    try:
        numbers = json.loads((Path(workspace) / INPUT).read_text(encoding="utf-8"))["numbers"]
    except (OSError, ValueError, KeyError, TypeError):
        return None
    return {"numbers": numbers} if isinstance(numbers, list) and all(type(n) is int for n in numbers) else None


def _dump(value, **options):
    return {OUTPUT: json.dumps(value, **options).encode("utf-8")}


def solve(instance):
    return [_dump({"sum": sum(instance["numbers"])})]


def check(instance, files):
    try:
        value = json.loads(files[OUTPUT].decode("utf-8"))["sum"]
    except (KeyError, ValueError, TypeError, AttributeError):
        return {"label": "unparseable", "reasons": ["output.json is missing or has no sum"]}
    if isinstance(value, (int, float)) and not isinstance(value, bool) and value == sum(instance["numbers"]):
        return {"label": "valid", "reasons": []}
    return {"label": "invalid", "reasons": [f"sum {value!r} is wrong"]}


def apply(workspace, files):
    for name, data in files.items():
        (Path(workspace) / name).write_bytes(data)


DEFECTS["off_by_one"] = lambda instance, rng: _dump({"sum": sum(instance["numbers"]) + 1})
DEFECTS["drop_last"] = lambda instance, rng: _dump({"sum": sum(instance["numbers"][:-1])})
HEURISTICS["first_number"] = lambda workspace, prompt="": _dump({"sum": (recognize(workspace) or {"numbers": [0]})["numbers"][0]})


def labeled(instance):
    total = sum(instance["numbers"])
    return [
        {"files": _dump({"sum": total}), "label": "valid", "kind": "canonical"},
        {"files": _dump({"sum": total}, indent=2), "label": "valid", "kind": "whitespace-variant"},
        {"files": _dump({"sum": float(total)}), "label": "valid", "kind": "float-variant"},
        {"files": _dump({"sum": total, "note": "extra"}), "label": "valid", "kind": "extra-key-variant"},
        {"files": _dump({"sum": total + 1}), "label": "invalid", "kind": "off-by-one"},
        {"files": _dump({"sum": str(total)}), "label": "invalid", "kind": "string-sum"},
        {"files": _dump({"total": total}), "label": "invalid", "kind": "wrong-key"},
        {"files": {OUTPUT: b"The sum is the total of the numbers."}, "label": "invalid", "kind": "prose"},
    ]
