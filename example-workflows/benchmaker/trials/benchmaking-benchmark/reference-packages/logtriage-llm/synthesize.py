"""Write the synthetic offline instances in the LogChunks layout.

    python synthesize.py [--out offline-instances]

The output is committed; this script reproduces it exactly (every log is seeded by its build id). Repositories,
people and build ids are invented. The logs follow the byte format of real Travis CI logs and the labels follow
the dataset's structure (`Log`, `Keywords`, `Category`, `Chunk`; chunk text without line numbers, escape
characters or `<`), so `generate.py` and the logtriage domain read them like the real archive.
"""
from __future__ import annotations

import argparse
import json
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

import synth_scenarios_a
import synth_scenarios_b

HERE = Path(__file__).resolve().parent

README = """# Synthetic offline instances

Travis CI build logs and labels in the layout of the LogChunks archive (`logs/<language>/<owner@repo>/failed/<build id>.log`,
`build-failure-reason/<language>/<owner@repo>.xml`). Everything here is invented: repositories, people, build ids and the
logs themselves, which imitate the byte format of real Travis logs (CRLF, ANSI sequences, `travis_fold` and `travis_time`
markers, carriage-return progress lines). Each label marks the lines a developer reads to understand the failure, as the
LogChunks labels do. `instances.json` records each log's failure family and why it is hard; three logs are candidates the
admission screen rejects. Regenerate with `python synthesize.py`.
"""


def build() -> list[dict]:
    rows = []
    for sc in synth_scenarios_a.SCENARIOS + synth_scenarios_b.SCENARIOS + synth_scenarios_b.REJECTED:
        log = sc["make"]()
        owner, name = sc["repo"].split("/")
        rows.append({**sc, "log_obj": log, "key": f"{sc['language']}/{owner}@{name}", "chunk": sc.get("label") or log.chunk_text()})
    return rows


def write(out: Path) -> list[str]:
    for part in ("logs", "build-failure-reason"):
        shutil.rmtree(out / part, ignore_errors=True)
    rows = build()
    meta, by_file = {}, {}
    for row in rows:
        path = f"{row['key']}/failed/{row['build']}.log"
        target = out / "logs" / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(row["log_obj"].bytes())
        by_file.setdefault(row["key"], []).append((path, row))
        meta[path] = {k: row[k] for k in ("family", "difficulty", "expert_minutes") if k in row} | {"realism": "synthetic"}
    for key, group in by_file.items():
        top = ET.Element("Examples")
        for path, row in group:
            node = ET.SubElement(top, "Example")
            for tag, value in (("Log", path), ("Keywords", row["keywords"]), ("Category", "0"), ("Chunk", row["chunk"])):
                ET.SubElement(node, tag).text = value
        ET.indent(top)
        target = out / "build-failure-reason" / f"{key}.xml"
        target.parent.mkdir(parents=True, exist_ok=True)
        ET.ElementTree(top).write(target, encoding="utf-8", xml_declaration=True)
    (out / "instances.json").write_text(json.dumps(meta, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    (out / "readme.md").write_text(README, encoding="utf-8", newline="\n")
    repos = sorted({f"{r['language']} {r['repo']}" for r in rows})
    (out / "repositories.txt").write_text("\n".join(repos), encoding="utf-8", newline="\n")
    return [p for group in by_file.values() for p, _ in group]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", default=str(HERE / "offline-instances"))
    out = Path(parser.parse_args().out)
    out.mkdir(parents=True, exist_ok=True)
    print(f"wrote {len(write(out))} logs under {out}")


if __name__ == "__main__":
    main()
