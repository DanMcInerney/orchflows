"""A core that reaches its adapters through a registry, written beside the tree.

Not a package module: nothing imports it, no discovery pattern matches it, and
it is never executed — the boundary scans read it as text. It exists so
`test_dependency_boundary` can be shown to reject the shape the spec forbids
rather than to match nothing at all.

Every line below is one of the things criterion 2 names. The adapter set is
built at run time instead of spelled, the module is resolved by string, the
call is reached by computed attribute, and the verb comes from the caller. An
exact search for `youtube_innertube` finds nothing here, which is the whole
defect: no reader and no language server can tell what this core can call.
"""

from __future__ import annotations

import importlib
import subprocess

import yt_dlp

REGISTRY = {}


def register(adapter_id):
    """A runtime registry, which is exactly what the literal branches are not."""

    REGISTRY[adapter_id] = importlib.import_module("super_research.adapters." + adapter_id)
    return REGISTRY[adapter_id]


def call_adapter(adapter_id, carrier, request, method="POST"):
    module = REGISTRY.get(adapter_id) or register(adapter_id)
    return getattr(module, "fetch_" + "native_page")(carrier, request, method)


def download(target):
    """A media surface and a shell, neither of which the package has.

    Both shell spellings, because they are two findings and not one: an argv
    list names the interpreter and never spells a command line, and a shell
    string is the command line. A scan that caught only one would report a
    clean module for the other.
    """

    subprocess.run(["/bin/sh", "-c", "yt-dlp " + target], check=False)
    subprocess.run("sh -c 'yt-dlp " + target + "'", shell=True, check=False)
    return yt_dlp.YoutubeDL({}).extract_info(target)
