"""Read the frozen case declarations used by measurement rows."""

from .common import CASE_KEYS, TOML_SCALAR


class CaseSchemaError(Exception):
    """The case does not declare, readably, what its row is checked against."""


def case_keys(cases_dir, case_id):
    """The angle/size/exec_bound a case declares, or a refusal.

    This intentionally reads only the single-line basic-string subset used
    by the frozen case set. Refusing an unreadable declaration keeps the
    comparisons from silently turning themselves off.
    """
    path = cases_dir / case_id / "case.toml"
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as error:
        raise CaseSchemaError("cannot read %s: %s" % (path, error))
    found = {}
    for line in text.splitlines():
        match = TOML_SCALAR.match(line.strip())
        if match:
            found[match.group(1)] = match.group(2)
    absent = [key for key in CASE_KEYS if key not in found]
    if absent:
        raise CaseSchemaError(
            "%s states no %s as a single-line basic string"
            % (path, ", ".join("'%s'" % key for key in absent))
        )
    return found
