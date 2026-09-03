"""Grade a bundle's own manifest against `contracts/bundle.md`.

`BUNDLE.md` says what a bundle is called, which revision of it this is, and
which other bundles it needs. It is read at one moment that matters --
`orchflows add` follows `requires` after a clone -- and by then the author
who wrote the offending line is not the person reading the refusal. So the
same shape is graded here, where the author is.

Its own module rather than a clause inside `packages.py`: this grades the
*bundle*, not an item in it. Nothing here fetches -- a `requires` entry is
held to the written shape `<git-url>@<pin>`, and whether a remote publishes
that pin is a question `add` asks where the answer means something.
"""

from __future__ import annotations

from . import common as __dep_common
Path = __dep_common.Path
ROOT = __dep_common.ROOT
SKIPPED = __dep_common.SKIPPED

from .packages import rel

# The manifest's reader, its location, and the refusal a bad `requires`
# entry earns, imported rather than respelled. An install ships this package
# under `lib/` with the scripts flat in `bin/`, which is what the paired
# import below is for: one module, reached under either name.
try:
    from scripts import orchflows_bundle, orchflows_home, rings
except ImportError:  # pragma: no cover - direct/installed flat script path
    import orchflows_bundle
    import orchflows_home
    import rings

REQUIRED_FIELDS = ("name", "version")
UNREADABLE = (
    "unreadable {manifest}: a bundle manifest is UTF-8 text and this one "
    "could not be read, so every requirement it declares is invisible to "
    "orchflows add"
)


def bundle_root() -> Path:
    """This tree's own bundle directory: the `.orchflows/` beside its root."""

    return ROOT / rings.BUNDLE_DIR


def validate_bundle_manifest(diag, bundle=None) -> None:
    """One bundle's manifest: its two fields, and every `requires` entry."""

    bundle = bundle_root() if bundle is None else Path(bundle)
    path = orchflows_bundle.manifest_path(bundle)
    file_label = rel(path)
    if not path.is_file():
        diag.warn(file_label, SKIPPED)
        return
    try:
        manifest = orchflows_bundle.read_manifest(bundle)
    except rings.RingError as error:
        diag.error(file_label, error.detail)
        return
    if manifest is None:
        diag.error(file_label, UNREADABLE.format(manifest=file_label))
        return
    for field in REQUIRED_FIELDS:
        if not manifest[field]:
            diag.error(file_label, f"bundle manifest missing required key '{field}'")
    for entry in manifest["requires"]:
        try:
            orchflows_home.requirement(entry, file_label)
        except rings.RingError as error:
            diag.error(file_label, error.detail)


__all__ = (
    "REQUIRED_FIELDS", "UNREADABLE", "bundle_root", "validate_bundle_manifest",
)
