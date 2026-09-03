"""Grade a bundle's own manifest against `contracts/bundle.md`.

`BUNDLE.md` says what a bundle is called, which revision of it this is, and
which other bundles it needs. It is read at exactly one moment that matters
-- `orchflows add` follows `requires` after a clone -- and by then the
author who wrote the offending line is not the person reading the refusal.
So the same shape is graded here, where the author is: `tools/validate.py`
over this repository's own `.orchflows/BUNDLE.md`, and `orchflows check`
over the ring a person is standing in.

Its own module rather than a clause inside `packages.py` or `sheets.py`:
this grades the *bundle*, not an item in it -- one file per ring, above
every item directory. The seam is the file, so the growth goes sideways.

Nothing here fetches. A `requires` entry is held to the written shape
`<git-url>@<pin>`, which is `scripts/orchflows_home.py`'s pin law read
without a network: whether a remote publishes that pin as a tag is a
question about a remote, and `add` is where the answer means something.
"""

from __future__ import annotations

from . import common as __dep_common
Path = __dep_common.Path
ROOT = __dep_common.ROOT
SKIPPED = __dep_common.SKIPPED

from .packages import rel

# The manifest's reader, its location, and the refusal a bad `requires`
# entry earns, imported rather than respelled: a validator with its own
# parser or its own sentence would be a second owner of both.
#
# An install ships this package under `lib/` so `orchflows check` can run
# these checks over a ring, and the scripts it reads sit flat in `bin/`
# with no `scripts` package above them. The paired import is the tree's
# own idiom for that layout: one module, reached under either name.
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
    """One bundle's manifest: its two fields, and every `requires` entry.

    `bundle` is the bundle directory the manifest sits in -- `orchflows
    check` hands over the ring itself, because a ring *is* a bundle
    directory. Absent, it is this tree's own `.orchflows/`.

    A bundle without a manifest is a bundle with no requirements, which
    `contracts/bundle.md` states is a fact and never a refusal; it is still
    reported, in the compiler's own skipped wording, because finding nothing
    to check is not the same answer as finding nothing wrong.
    """

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
