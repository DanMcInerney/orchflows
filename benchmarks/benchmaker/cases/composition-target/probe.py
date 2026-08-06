#!/usr/bin/env python3
"""Case probe for composition-target. The case author's sanity oracle.

This is NOT the benchmark. It decides one question from the bytes of a
workflow file: does its artifact chain resolve? Every step is bound by
an invariant, every edge endpoint and carried artifact resolves to a
declared step, and the done check names the terminal artifact instead of
restating step status. Nothing here judges whether the pipeline is a
good pipeline.

Usage:  python probe.py [VARIANT_DIR]

VARIANT_DIR holds `workflow.md`. It arrives as the CASE_IMPL environment
variable, else as the positional argument, else defaults to the
reference variant `target/`. A relative path is resolved against the
current directory first, then against the case root, so the probe is
insensitive to where it is invoked from.

Exit 0 when every check passes; exit 1 with one failure per line.

Stdlib only. Python 3.9+.
"""

import os
import re
import sys
from pathlib import Path

CASE_ROOT = Path(__file__).resolve().parent
REFERENCE = CASE_ROOT / "target"

EM = "—"
ARROW = "→"

STEP = re.compile(
    r"^-\s+(?P<id>[a-z][a-z0-9-]*)\s+" + EM + r"\s+`(?P<unit>[^`]+)`"
    r"\s+" + EM + r"\s+produces\s+`(?P<artifact>[^`]+)`:\s*(?P<note>\S.*)$"
)
EDGE = re.compile(
    r"seq\s+(?P<src>[a-z][a-z0-9-]*)\s+" + ARROW + r"\s+(?P<dst>[a-z][a-z0-9-]*)"
    r"\s+" + EM + r"\s+carries\s+`(?P<artifact>[^`]+)`"
)
INVARIANT = re.compile(r"^-\s+(?P<step>[a-z][a-z0-9-]*)\s+" + EM + r"\s+(?P<clause>\S.*)$")
STATUS_RESTATEMENT = re.compile(
    r"(?i)\b(every|each|all)\s+steps?\b[^.]*\bstatus\b"
    r"|\bstatus\b[^.]*\b(complete|succeeded|passed)\b"
    r"|\b(every|each|all)\s+steps?\s+(returned|returns|reported|reports)\b"
)

ENTRIES = ("routed", "named", "scheduled")
INVARIANT_HEADER = "Invariants " + EM + " Never:"


def emit(message):
    """Print ASCII-safe, so a variant's bytes cannot break the console."""
    print(message.encode("ascii", "replace").decode("ascii"))


def resolve(argument):
    # CASE_IMPL outranks the positional: an adapter that sets it must never
    # be answered with the reference variant's verdict.
    argument = os.environ.get("CASE_IMPL") or argument
    if argument is None or argument == "{target}":
        return REFERENCE
    candidate = Path(argument)
    if candidate.is_absolute():
        return candidate
    for base in (Path.cwd(), CASE_ROOT):
        if (base / candidate).exists():
            return base / candidate
    return Path.cwd() / candidate


def bullets_after(lines, header):
    """The bullet block following a header line, up to the first blank."""
    if header not in lines:
        return None
    block = []
    for line in lines[lines.index(header) + 1:]:
        if not line.strip():
            break
        block.append(line)
    return block


def paragraph_from(lines, prefix):
    """The paragraph starting at the line with this prefix."""
    for index, line in enumerate(lines):
        if line.startswith(prefix):
            block = [line]
            for follower in lines[index + 1:]:
                if not follower.strip():
                    break
                block.append(follower)
            return " ".join(part.strip() for part in block)
    return None


def frontmatter(lines, failures):
    if not lines or lines[0].strip() != "---":
        failures.append("no frontmatter")
        return {}
    fields = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if ":" in line:
            key, value = line.split(":", 1)
            fields[key.strip()] = value.strip()
    for key in ("name", "description", "entry"):
        if not fields.get(key):
            failures.append("frontmatter declares no %s" % key)
    if len(fields.get("description", "")) > 140:
        failures.append(
            "description runs %d chars, bound is 140" % len(fields["description"])
        )
    entry = fields.get("entry")
    if entry and entry not in ENTRIES:
        failures.append("entry is %s, not one of %s" % (entry, "/".join(ENTRIES)))
    return fields


def parse_steps(lines, failures):
    block = bullets_after(lines, "Steps:")
    if block is None:
        failures.append("no Steps: block")
        return {}
    steps = {}
    for line in block:
        match = STEP.match(line.rstrip())
        if match is None:
            failures.append("step bullet is malformed: %s" % line.strip()[:60])
            continue
        if match.group("id") in steps:
            failures.append("step id %s is declared twice" % match.group("id"))
            continue
        steps[match.group("id")] = match.group("artifact")
    if len(steps) < 2:
        failures.append("workflow declares %d step(s), minimum is 2" % len(steps))
    artifacts = list(steps.values())
    for artifact in set(artifacts):
        if artifacts.count(artifact) > 1:
            failures.append("artifact %s is produced by more than one step" % artifact)
    return steps


def parse_edges(lines, failures):
    line = next((one for one in lines if one.startswith("Edges:")), None)
    if line is None:
        failures.append("no Edges: line")
        return []
    edges = []
    for fragment in line[len("Edges:"):].split(";"):
        if not fragment.strip():
            continue
        match = EDGE.search(fragment)
        if match is None:
            failures.append("edge is malformed: %s" % fragment.strip()[:60])
            continue
        edges.append((match.group("src"), match.group("dst"), match.group("artifact")))
    return edges


def check_chain(steps, edges, failures):
    """Edges must form one chain over every step, carrying real artifacts."""
    for src, dst, artifact in edges:
        for endpoint in (src, dst):
            if endpoint not in steps:
                failures.append("edge names undeclared step %s" % endpoint)
        if src in steps and artifact != steps[src]:
            failures.append(
                "edge %s to %s carries %s, but %s produces %s"
                % (src, dst, artifact, src, steps[src])
            )
    if not steps:
        return None
    if len(edges) != len(steps) - 1:
        failures.append(
            "%d edge(s) over %d step(s); a chain needs %d"
            % (len(edges), len(steps), len(steps) - 1)
        )
    outgoing, incoming = {}, {}
    for src, dst, _ in edges:
        outgoing.setdefault(src, []).append(dst)
        incoming.setdefault(dst, []).append(src)
    for node, targets in outgoing.items():
        if len(targets) > 1:
            failures.append("step %s has %d successors; a chain allows one" % (node, len(targets)))
    for node, sources in incoming.items():
        if len(sources) > 1:
            failures.append("step %s has %d predecessors; a chain allows one" % (node, len(sources)))
    heads = [node for node in steps if node not in incoming]
    tails = [node for node in steps if node not in outgoing]
    if len(heads) != 1 or len(tails) != 1:
        failures.append(
            "chain has %d start(s) and %d end(s); it needs one of each"
            % (len(heads), len(tails))
        )
        return None
    walked, node = [], heads[0]
    while node is not None and node not in walked:
        walked.append(node)
        successors = outgoing.get(node, [])
        node = successors[0] if successors else None
    unreached = sorted(set(steps) - set(walked))
    if unreached:
        failures.append("step(s) off the chain: %s" % ", ".join(unreached))
        return None
    return tails[0]


def check_invariants(lines, steps, failures):
    block = bullets_after(lines, INVARIANT_HEADER)
    if block is None:
        failures.append("no Invariants Never: block")
        return
    bound = set()
    for line in block:
        match = INVARIANT.match(line.rstrip())
        if match is None:
            failures.append("invariant bullet is malformed: %s" % line.strip()[:60])
            continue
        if match.group("step") not in steps:
            failures.append("invariant binds undeclared step %s" % match.group("step"))
            continue
        bound.add(match.group("step"))
    unbound = sorted(set(steps) - bound)
    if unbound:
        failures.append("step(s) bound by no invariant: %s" % ", ".join(unbound))


def check_done(lines, steps, terminal, failures):
    done = paragraph_from(lines, "Done check:")
    if done is None:
        failures.append("no Done check: line")
        return
    body = done[len("Done check:"):].strip()
    if not body:
        failures.append("Done check: is empty")
        return
    if STATUS_RESTATEMENT.search(body):
        failures.append("done check restates step status instead of checking output")
    if terminal is None:
        return
    if steps[terminal] not in body:
        failures.append(
            "done check names no terminal artifact; %s produces %s"
            % (terminal, steps[terminal])
        )


def check_return(lines, failures):
    line = next((one for one in lines if one.startswith("Return:")), None)
    if line is None:
        failures.append("no Return: line")
    elif not line[len("Return:"):].strip().startswith("status, result"):
        failures.append("Return: does not lead with status, result")


def check(variant):
    failures = []
    path = variant / "workflow.md"
    if not path.is_file():
        return ["missing file: workflow.md"]
    lines = path.read_text(encoding="utf-8").splitlines()

    frontmatter(lines, failures)
    if not any(one.startswith("Require:") and one[len("Require:"):].strip() for one in lines):
        failures.append("no Require: line")
    steps = parse_steps(lines, failures)
    edges = parse_edges(lines, failures)
    terminal = check_chain(steps, edges, failures) if steps else None
    check_invariants(lines, steps, failures)
    check_done(lines, steps, terminal, failures)
    check_return(lines, failures)
    return failures


def main(argv):
    if len(argv) > 2:
        emit("usage: probe.py [VARIANT_DIR]")
        return 2
    variant = resolve(argv[1] if len(argv) == 2 else None)
    if not variant.is_dir():
        emit("no such variant directory: %s" % variant)
        return 2
    failures = check(variant)
    for failure in failures:
        emit("FAIL %s: %s" % (variant.name, failure))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
