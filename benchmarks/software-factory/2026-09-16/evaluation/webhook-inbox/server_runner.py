"""Evaluator-only subprocess adapter for the published server factory."""

import argparse
import importlib.util
import json
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True)
    parser.add_argument("--db", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--ready", required=True)
    args = parser.parse_args()
    project = Path(args.project).resolve()
    sys.path.insert(0, str(project))
    spec = importlib.util.spec_from_file_location("inbox", project / "inbox.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["inbox"] = module
    spec.loader.exec_module(module)
    server = module.create_server(args.db, args.config, host="127.0.0.1", port=0)
    host, port = server.server_address[:2]
    ready = Path(args.ready)
    staged = ready.with_suffix(".pending")
    staged.write_text(json.dumps({"host": host, "port": port}), encoding="utf-8")
    staged.replace(ready)
    try:
        server.serve_forever()
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
