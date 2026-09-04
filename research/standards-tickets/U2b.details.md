Unit U2b: the resolver

Spec: research/standards-spec-2026-09-04.md. Read section 0, section 2, and section 3 U1 and U2 -- this unit is the seam between them. Decisions are closed: where one looks wrong, report the observation in `## Report` and continue.

This unit is not in the spec. The driver added it at the wave-2 join, from the defect U2 reported and the spec's section 4 denied was possible. Read that denial -- "U1 and U2 are disjoint" -- as the thing that hid this work, not as a rule you are breaking.

Why: the collapse has two halves and the spec assigned one. U2 deleted the cells table from all eight items and moved `adapter` into frontmatter. The code that reads a cells table is `scripts/packs_support.py`, which is U1's file, and U1's brief said it "adds the walk and nothing else". So at the wave-2 tip nothing resolves at all: `tests/test_packs.py` raises `pack signature missing cell(s): adapter, craft` from `_parse_rows` thirteen times, reached through `resolve_pack` -> `_resolved`. Every shipped item is now the collapsed shape and the resolver still demands the retired one.

Change, the shape. `PACK_CELLS`, `_CELL_SET`, `_CELL_ROW_RE`, `_parse_rows`, `_typed_cells`, `_declared_cell` and `_read_references` exist to read a two-row table and the second file its `craft` cell named. Neither exists now. Read `adapter` from frontmatter instead, and refuse a manifest that still carries a `| Cell | Binding |` table -- that is the retired shape and a silent acceptance of it is how a half-migrated item survives. One fact, one reader: `tickets_adapters.declared_adapter` already reads that field at that spelling, so decide which of the two owns the reading and make the other call it rather than leaving two regexes for one field.

Change, the digest. `contracts/standard.md` states it: SHA-256 over the standard's directory tree, pinned at issue and re-derived at every door. `_resolved` today digests an identity of the resolver version, the name, the typed cells and the base64 bytes of every referenced file -- an identity built out of the two things that just stopped existing. Make it the directory tree: every file under the standard's directory, its path relative to that directory and its bytes, in a stable order, so that adding a file, deleting one or changing a byte all move the digest. Keep the resolver version in the identity, because a resolver that reads differently should not agree with itself across the change.

`_signature_digest()` is the third consequence, and the quiet one. It hashes `rings.lib_root()/contracts/pack-signature.md`, which U0 deleted, and `is_file()` is false, so it now returns `None` and the library's own well-formedness contract silently left the identity it was put there to bind. Point it at `contracts/standard.md`, the file that replaced it, and prove the binding still bites with a check that changes a byte of that contract and sees the digest move. A test that passes because a `None` compares equal to a `None` is the failure this paragraph exists to prevent.

Do this under the OLD module and directory names. Items are still in `packs/` and `sheets/`, the modules are still `packs.py` and `packs_support.py`, and U3 renames all of it afterwards. Do not rename a module, a flag, a directory or a finding code, and do not move a file: a rename racing a content change is the collision the wave order exists to avoid, and this unit exists because that ordering already failed once.

Yours: `scripts/packs_support.py`, `scripts/packs.py`, `tests/test_packs.py`. `tests/test_packs.py` asserts the retired shape in thirteen places -- rewrite each to the collapsed one rather than deleting it, and where a test's whole subject was the second file, say so in `## Report` and say what replaced it. Where a file outside those three goes red on your change, fix it minimally and list it; where a fix would be large, report it instead.

Not yours: the two deleted contracts' inbound links, which are U3's, and the item content, which is U2's and has landed. `tools/regen.py` could not run at U1's base because it crashed on the deleted contract; check whether it runs now, and say either way.

The tree you cut from is not green and you cannot make it green. Eight modules fail at your base. Thirteen of the failures in `tests/test_packs.py` are yours; the rest, in `test_doclint`, `test_validate`, `test_validator`, `test_ticket_protocol`, `test_cell_linter`, `test_dispatch_launch_lines` and `test_dispatch_launch_command`, name a deleted contract or a term U3 has not swept yet. Take the baseline reading yourself before you change anything, save it to a file, and close on the difference: a red you added is yours and a red you inherited is not.

Done: `uv run --no-project python tools/run_required.py`

The mechanical `done` that `land` runs is that same command; run it yourself before closing. If it exits 1, redirect it to a file and grep `FAILED MODULE` -- a tail of a red run shows a `0 failures, 0 errors` summary line and looks green.

Close `limited`, naming it, if the directory-tree digest cannot replace the identity digest without changing a pin this run itself holds open.

Report: every file touched with its line delta, the failing and passing readings for the digest checks, which reader owns the `adapter` field and which one calls it, what `_signature_digest` hashed before and after with the reading that proves it bites, the baseline and candidate failing-module lists side by side, and any deviation from these Details with the observation that forced it.
