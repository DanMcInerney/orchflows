#!/usr/bin/env python3
"""Public deterministic evidence boundary for the self-improve workflow.

collect --selection FILE; record --review ID --file FILE;
show --review ID; close --review ID --mode review|repair.
Exit 2 refuses invalid input/state; exit 3 means review complete, repair incomplete.
No command performs semantic diagnosis, dispatch, repair, installation or log edits.
"""
from __future__ import annotations

import argparse
import json
import sys
import sqlite3

from improve_common import EvidenceError, read_json, redact, safe_sink, selection
from improve_collect import collect
import improve_store


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    collect_command = commands.add_parser("collect")
    collect_command.add_argument("--selection", required=True)
    collect_command.add_argument("--disk-budget", type=int, default=2147483648)
    collect_command.add_argument("--record-budget", type=int, default=8388608)
    write = commands.add_parser("record")
    write.add_argument("--review", required=True)
    write.add_argument("--file", required=True)
    show = commands.add_parser("show")
    show.add_argument("--review", required=True)
    show.add_argument("--section", choices=("observations", "sources", "context", "gaps", "records"))
    show.add_argument("--offset", type=int, default=0)
    show.add_argument("--limit", type=int, default=100)
    close = commands.add_parser("close")
    close.add_argument("--review", required=True)
    close.add_argument("--mode", choices=("review", "repair"), required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "collect":
            frozen = selection(read_json(args.selection))
            safe_sink(frozen["sources"])
            result = improve_store.create(collect(frozen, args.disk_budget, args.record_budget))
        elif args.command == "record":
            result = improve_store.record(args.review, read_json(args.file))
        elif args.command == "show":
            result = improve_store.show(args.review, args.section, args.offset, args.limit)
        else:
            result = improve_store.close(args.review, args.mode)
        print(json.dumps(redact(result), sort_keys=True, ensure_ascii=True))
        return 3 if args.command == "close" and args.mode == "repair" and not result["repair_completed"] else 0
    except sqlite3.Error as exc:
        print(json.dumps({"kind": "evidence-refusal", "coverage": "partial", "error": redact(str(exc)),
                          "continuation": "restore spool storage and retry the same frozen selection; no complete collection claimed"}))
        return 2
    except (EvidenceError, OSError, KeyError, TypeError, ValueError) as exc:
        # OSError paths may themselves contain credentials. Never return raw inputs.
        print(json.dumps({"error": redact(str(exc)), "kind": "evidence-refusal"}, ensure_ascii=True))
        return 2


if __name__ == "__main__":
    sys.exit(main())
