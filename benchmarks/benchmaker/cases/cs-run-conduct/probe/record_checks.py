"""Run-record checks rc.2 through rc.8 for the cs-run-conduct probe."""

import hashlib
import json
import re
from pathlib import Path


CASE_ROOT = Path(__file__).resolve().parent.parent
SHA64 = re.compile(r"^sha256:[0-9a-f]{64}$")
SHA_ANY = re.compile(r"sha256:[0-9a-f]{8,}")
FORBIDDEN_MARKERS = ("promotion:", "activation:", "comparison:")
FORBIDDEN_SKILLS = ("evolve", "skill-tournament")
LANE_TI = (
    "stated claims",
    "demand and failure record",
    "boundaries and refusals",
    "operator and harness",
    "change history",
)
LANE_FIELD = (
    "prior benchmarks",
    "comparable artifacts",
    "failure taxonomies",
    "oracle precedent",
    "gaming and contamination",
)
SYNTH_HEADINGS = (
    "construct definition",
    "claim register",
    "failure atlas",
    "prior-art register",
    "disagreement register",
    "gaps",
    "sourcing mode",
)
PACKET_FIELDS = (
    "packet",
    "skill",
    "objective",
    "inputs",
    "authority",
    "bounds",
    "return_contract",
    "reply_to",
)


def read(path):
    return path.read_text(encoding="utf-8", errors="replace")


def lines_of(path):
    return read(path).splitlines()


def parts_of(line):
    fields = {}
    for segment in line.split("|"):
        if ":" in segment:
            key, value = segment.split(":", 1)
            fields[key.strip()] = value.strip()
    return fields


def field_lines(lines, key):
    prefix = key + ":"
    return [
        line.strip()[len(prefix) :].strip()
        for line in lines
        if line.strip().startswith(prefix)
    ]


def headings_of(lines):
    return [line[3:].strip().lower() for line in lines if line.startswith("## ")]


def sha_lf(path):
    data = path.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


def check_acquire(record, failures):
    acquire = record / "acquire"
    lanes = (("lane-target-intent.md", LANE_TI), ("lane-field.md", LANE_FIELD))
    for name, required in lanes:
        path = acquire / name
        if not path.is_file():
            failures.append("rc.2: acquire lane '%s' is missing" % name)
            continue
        present = headings_of(lines_of(path))
        for heading in required:
            if heading not in present:
                failures.append("rc.2: %s lacks charter heading '%s'" % (name, heading))
    synth = acquire / "synthesis.md"
    synth_identity = None
    if not synth.is_file():
        failures.append("rc.2: no acquire/synthesis.md")
    else:
        slines = lines_of(synth)
        identities = [v for v in field_lines(slines, "identity") if SHA64.match(v)]
        if len(identities) != 1:
            failures.append(
                "rc.2: synthesis must declare exactly one sha256 identity, found %d"
                % len(identities)
            )
        else:
            synth_identity = identities[0]
        present = headings_of(slines)
        for heading in SYNTH_HEADINGS:
            if heading not in present:
                failures.append("rc.2: synthesis lacks charter artifact '%s'" % heading)
    exhibits = acquire / "exhibits.md"
    protected = acquire / "protected"
    if not protected.is_dir() or not any(p.is_file() for p in protected.rglob("*")):
        failures.append("rc.2: no protected-tier item under acquire/protected/")
    if exhibits.is_file() and protected.is_dir():
        blocks, current, fenced = [], [], False
        for line in lines_of(exhibits):
            if line.strip().startswith("```"):
                if fenced:
                    blocks.append("\n".join(current).strip())
                    current = []
                fenced = not fenced
            elif fenced:
                current.append(line)
        prot_texts = {
            p.relative_to(protected).as_posix(): read(p)
            for p in protected.rglob("*")
            if p.is_file()
        }
        for block in blocks:
            if len(block) < 20:
                continue
            for name, text in prot_texts.items():
                if block in text:
                    failures.append(
                        "rc.2: exhibit appears verbatim in protected item '%s'" % name
                    )
    elif not exhibits.is_file():
        failures.append("rc.2: no acquire/exhibits.md")
    saturation = acquire / "saturation.md"
    if not saturation.is_file():
        failures.append("rc.2: no acquire/saturation.md")
    else:
        slines = lines_of(saturation)
        notes = field_lines(slines, "saturation") + field_lines(slines, "gap")
        if not any(note.strip() for note in notes):
            failures.append("rc.2: saturation.md carries no saturation-or-gap note")
    return synth_identity


def check_joins(record, synth_identity, design_identity, failures):
    joins_path = record / "joins.md"
    if not joins_path.is_file():
        failures.append("rc.3: no record/joins.md")
        return
    joins = {}
    for line in lines_of(joins_path):
        stripped = line.strip()
        if not stripped.startswith("join:"):
            continue
        fields = parts_of(stripped)
        edge = tuple(part.strip() for part in fields.get("join", "").split("->"))
        if len(edge) != 2:
            failures.append("rc.3: malformed join line: %s" % stripped[:60])
            continue
        frozen, consumed = fields.get("frozen", ""), fields.get("consumed", "")
        joins[edge] = (frozen, consumed)
        if not SHA64.match(frozen) or not SHA64.match(consumed):
            failures.append("rc.3: join %s->%s carries a malformed identity" % edge)
        elif frozen != consumed:
            failures.append(
                "rc.3: join %s->%s consumes an identity other than the frozen one" % edge
            )
    for edge in (
        ("acquire-spec", "acquire"),
        ("acquire", "design"),
        ("design", "materialize"),
    ):
        if edge not in joins:
            failures.append("rc.3: required join %s->%s is missing" % edge)
    if synth_identity and ("acquire", "design") in joins:
        if joins[("acquire", "design")][0] != synth_identity:
            failures.append("rc.3: design consumes an identity other than the frozen synthesis")
    if design_identity and ("design", "materialize") in joins:
        if joins[("design", "materialize")][0] != design_identity:
            failures.append(
                "rc.3: materialize consumes an identity other than the frozen design"
            )


def load_packets(record, failures):
    packets_dir = record / "packets"
    packets = {}
    if not packets_dir.is_dir():
        failures.append("rc.4: no record/packets/ directory")
        return packets
    for path in sorted(packets_dir.glob("*.md")):
        plines = lines_of(path)
        fields = {}
        for key in PACKET_FIELDS + ("pack", "spec"):
            fields[key] = field_lines(plines, key)
        packets[path.name] = fields
    if not packets:
        failures.append("rc.4: record/packets/ holds no packet")
    return packets


def check_packets(packets, caller_bounds, failures):
    skills = []
    for name, fields in packets.items():
        for key in PACKET_FIELDS:
            if not any(value.strip() for value in fields[key]):
                failures.append("rc.4: packet '%s' lacks a nonempty '%s'" % (name, key))
        bounds = (fields["bounds"] or [""])[0].strip()
        if caller_bounds and bounds == caller_bounds:
            failures.append(
                "rc.4: packet '%s' carries the caller bound verbatim, not a stage allocation"
                % name
            )
        skills.extend(fields["skill"])
    for required in ("orch-spec", "orch-deliver", "orch-eval-design"):
        if required not in skills:
            failures.append("rc.4: no internal call with skill '%s' is recorded" % required)


def check_provenance_sources(impl, manifest, failures):
    """rc.5: the package attests the same bytes the record attests."""

    if not isinstance(manifest, dict):
        return
    ref = manifest.get("provenance")
    if not (isinstance(ref, dict) and isinstance(ref.get("locator"), str)):
        return
    path = (impl / "package" / ref["locator"]).resolve()
    if not path.is_file():
        return
    try:
        provenance = json.loads(read(path))
    except ValueError as error:
        failures.append("rc.5: provenance component does not parse: %s" % error)
        return
    sources = provenance.get("sources")
    if not isinstance(sources, list):
        failures.append("rc.5: provenance states no 'sources' list of attested files")
        return
    for entry in sources:
        if not isinstance(entry, dict):
            failures.append("rc.5: a provenance source is not an object")
            continue
        named = str(entry.get("file") or "")
        digest = str(entry.get("sha256") or "")
        source = CASE_ROOT / named
        if not named or not digest:
            failures.append("rc.5: a provenance source names no file or no digest")
        elif not source.is_file():
            failures.append("rc.5: provenance attests '%s', which the case does not supply" % named)
        elif digest[len("sha256:") :] != sha_lf(source):
            failures.append(
                "rc.5: provenance digest for '%s' does not match the case evidence" % named
            )


def check_never(impl, record, packets, manifest, failures):
    check_provenance_sources(impl, manifest, failures)
    case_evidence = CASE_ROOT / "evidence"
    evidence_path = record / "evidence.md"
    if not evidence_path.is_file():
        failures.append("rc.5: no record/evidence.md attesting consumed evidence")
    else:
        attested = {}
        for value in field_lines(lines_of(evidence_path), "evidence"):
            tokens = value.split()
            if len(tokens) == 2 and tokens[1].startswith("sha256:"):
                attested[tokens[0]] = tokens[1][len("sha256:") :]
        for name in ("packet.md", "record-schema.md"):
            if name not in attested:
                failures.append("rc.5: evidence.md attests no digest for '%s'" % name)
            elif attested[name] != sha_lf(case_evidence / name):
                failures.append(
                    "rc.5: attested digest for '%s' does not match the case evidence" % name
                )
    for path in sorted(record.rglob("*.md")):
        for line in lines_of(path):
            lowered = line.strip().lower()
            if lowered.startswith(FORBIDDEN_MARKERS):
                failures.append(
                    "rc.5: never-marker '%s' in %s"
                    % (lowered.split(":", 1)[0], path.relative_to(record).as_posix())
                )
    for name, fields in packets.items():
        for skill in fields["skill"]:
            if skill.strip() in FORBIDDEN_SKILLS:
                failures.append(
                    "rc.5: packet '%s' dispatches forbidden skill '%s'"
                    % (name, skill.strip())
                )


def check_gaps(record, manifest, failures):
    gaps_path = record / "gaps.md"
    if not gaps_path.is_file():
        failures.append("rc.6: no record/gaps.md")
        return
    manifest_gaps = manifest.get("gaps") if isinstance(manifest, dict) else None
    manifest_gaps = manifest_gaps if isinstance(manifest_gaps, list) else []
    for line in lines_of(gaps_path):
        stripped = line.strip()
        if not stripped.startswith("gap:"):
            continue
        fields = parts_of(stripped)
        if fields.get("stage") == "design":
            gap_id = fields.get("gap", "")
            if gap_id and gap_id not in manifest_gaps:
                failures.append(
                    "rc.6: design-stage gap '%s' is absent from the manifest gaps" % gap_id
                )


def check_design(record, impl, packets, failures):
    design_path = record / "design.md"
    if not design_path.is_file():
        failures.append("rc.7: no record/design.md")
        return None
    dlines = lines_of(design_path)
    identities = [v for v in field_lines(dlines, "identity") if SHA64.match(v)]
    identity = identities[0] if len(identities) == 1 else None
    if identity is None:
        failures.append("rc.7: design.md declares no single sha256 identity")
    sources = field_lines(dlines, "boundary-source")
    if not any("packet.md" in value for value in sources):
        failures.append("rc.7: design.md does not cite the packet for its boundary")
    case_lines = field_lines(dlines, "cases")
    designed = set()
    for value in case_lines:
        designed.update(item.strip() for item in value.split(",") if item.strip())
    cases_path = impl / "package" / "cases" / "cases.json"
    if cases_path.is_file():
        try:
            data = json.loads(read(cases_path))
        except ValueError:
            failures.append("rc.7: package cases.json does not parse")
        else:
            case_list = data.get("cases", []) if isinstance(data, dict) else None
            if not isinstance(case_list, list) or not all(
                isinstance(case, dict) for case in case_list
            ):
                failures.append(
                    "rc.7: package cases.json is not an object carrying a list of case objects"
                )
            else:
                materialized = {case.get("id") for case in case_list}
                if designed != materialized:
                    failures.append(
                        "rc.7: design case list %s differs from the materialized set %s"
                        % (sorted(designed), sorted(materialized))
                    )
    else:
        failures.append("rc.7: no package/cases/cases.json to compare the design selection against")
    by_id = {}
    for name, fields in packets.items():
        for pid in fields["packet"]:
            by_id[pid.strip()] = (name, fields)
    for name, fields in packets.items():
        skill = (fields["skill"] or [""])[0].strip()
        if skill == "orch-spec" and len(fields["pack"]) != 1:
            failures.append(
                "rc.7: spec packet '%s' carries %d pack stamps, law is exactly one"
                % (name, len(fields["pack"]))
            )
        if skill == "orch-deliver":
            spec_refs = [v.strip() for v in fields["spec"] if v.strip()]
            if len(spec_refs) != 1 or spec_refs[0] not in by_id:
                failures.append("rc.7: deliver packet '%s' names no recorded spec packet" % name)
                continue
            spec_fields = by_id[spec_refs[0]][1]
            if len(fields["pack"]) != 1 or fields["pack"] != spec_fields["pack"]:
                failures.append(
                    "rc.7: deliver packet '%s' does not preserve its spec's pack stamp" % name
                )
    return identity


def check_schema_citation(record, failures):
    citations = 0
    for path in sorted(record.rglob("*.md")):
        for line in lines_of(path):
            stripped = line.strip()
            if stripped.startswith("manifest-schema:"):
                if SHA_ANY.search(stripped):
                    citations += 1
                else:
                    failures.append("rc.8: manifest-schema citation carries no identity")
    if citations != 1:
        failures.append(
            "rc.8: manifest schema cited %d times; law is exactly once at open" % citations
        )


def caller_bounds_line():
    packet = CASE_ROOT / "evidence" / "packet.md"
    if not packet.is_file():
        return ""
    values = field_lines(lines_of(packet), "bounds")
    return values[0].strip() if values else ""


def check_record(impl, record, manifest, failures):
    """Append every rc.2–rc.8 failure while preserving their original order."""

    synth_identity = check_acquire(record, failures)
    packets = load_packets(record, failures)
    check_packets(packets, caller_bounds_line(), failures)
    check_never(impl, record, packets, manifest, failures)
    check_gaps(record, manifest, failures)
    design_identity = check_design(record, impl, packets, failures)
    check_joins(record, synth_identity, design_identity, failures)
    check_schema_citation(record, failures)
