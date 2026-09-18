"""Run case-owned checks outside the target context; assertion failures are evidence."""
import argparse
import json
from pathlib import Path
import traceback

from common import load_hook, read_json, write_json


class MissingOutput(Exception):
    pass


class Checks:
    def __init__(self, root):
        self.root = Path(root)
        self.report = read_json(self.root / 'target.json')
        self.results = []

    def require(self, condition, requirement, evidence):
        self.results.append({'passed': bool(condition), 'requirement': requirement, 'evidence': evidence})

    def stage(self, name='target'):
        return self.root / 'stages' / name / 'workspace'

    def json(self, path):
        try:
            return read_json(path)
        except (FileNotFoundError, json.JSONDecodeError, UnicodeError) as error:
            self.require(False, 'Produce the required readable JSON output', str(path))
            raise MissingOutput(str(error)) from error


def run(root, hook):
    checks = Checks(root)
    gaps = []
    try:
        load_hook(hook).check(checks)
    except MissingOutput:
        pass
    except Exception:
        gaps.append(traceback.format_exc())
    result = {'checks': checks.results, 'gaps': gaps}
    write_json(Path(root) / 'checks.json', result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('root', type=Path)
    parser.add_argument('hook', type=Path)
    args = parser.parse_args()
    run(args.root, args.hook)
