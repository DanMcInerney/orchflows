#!/bin/sh
# Bootstrap wrapper for install.py: resolves an interpreter
# (uv -> python3 -> python) and delegates, forwarding all arguments.
# Never hardcodes a bare python3/python without a PATH check first — see
# anthropics/claude-code#16131 for the Windows trap this avoids.
dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
target="$dir/install.py"
if command -v uv >/dev/null 2>&1; then
    exec uv run --no-project python "$target" "$@"
fi
if command -v python3 >/dev/null 2>&1; then
    exec python3 "$target" "$@"
fi
if command -v python >/dev/null 2>&1; then
    exec python "$target" "$@"
fi
echo "error: no python interpreter found (tried uv, python3, python)" >&2
exit 1
