"""Create, inspect, and remove cutcheck scratch trees."""

try:  # repository checkout
    from scripts import cutcheck_contract as _contract
except ImportError:  # installed flat script directory
    import cutcheck_contract as _contract
Path = _contract.Path
SCRATCH_NOT_REMOVED = _contract.SCRATCH_NOT_REMOVED
SCRATCH_PREFIX = _contract.SCRATCH_PREFIX
SYMLINK_IN_TREE = _contract.SYMLINK_IN_TREE
SYMLINK_MODE = _contract.SYMLINK_MODE
_TREE_STATE = _contract._TREE_STATE
re = _contract.re
shutil = _contract.shutil
sys = _contract.sys
tempfile = _contract.tempfile

try:  # repository checkout
    from scripts import cutcheck_state as _state
except ImportError:  # installed flat script directory
    import cutcheck_state as _state
_git = _state._git
_unread = _state._unread

def _scratch_root(worktree_root):
    """One invocation's private directory for the copies it grades in.

    The host's temp root, so the length of a scratch path is a fact about the
    host and never about the tree being graded. Placing it inside the target's
    own git storage put it beside the object store a local clone hardlinks
    from, which is faster and which made the tool unusable on Windows: a
    copy's paths are then the target's path plus a scratch directory plus a
    revision directory plus the deepest path in the revision, and a
    183-character worktree root took ``git clone`` past ``MAX_PATH`` on its own
    template copy -- which ``core.longpaths=true`` does not cover, so every
    invocation from that tree exited before grading anything. Speed gives way
    to running at all; the copy is still a clone, so it still carries history.

    ``worktree_root`` no longer decides where the copies land -- that is the
    whole of the change -- and stays as the argument the caller and the test
    harness both hold this seam by.

    ``None`` where the temp root will not take a directory; the caller has a
    ticket set it cannot grade and says so.
    """

    try:
        return Path(tempfile.mkdtemp(prefix=SCRATCH_PREFIX))
    except OSError:
        return None


def _remove_scratch_root(scratch_root):
    """Remove this invocation's copies, and say so when they will not go.

    ``ignore_errors=True`` here was a swallowed error in the tool whose whole
    subject is swallowed errors: each copy is a full clone, and a removal that
    quietly failed left one on disk per invocation with nothing said.

    Said rather than raised, never exit-setting, and on stderr. The report is
    about this tool's own hygiene: a leaked copy is no finding against the
    ticket set that was being read, and the `finally` this runs in precedes
    every finding printed, so the same line on stdout would prepend itself to
    a pinned verdict and move all of them at once on any host that leaks.
    """

    try:
        shutil.rmtree(str(scratch_root))
        return
    except OSError:
        # Git writes loose objects and packs `0o444` and hardlinks that mode
        # into every clone, so a strict removal meets it on every platform;
        # where a file with no write bit cannot be unlinked at all, as on
        # Windows, that alone would leak a copy per invocation. The mode is
        # git's statement about an object and never about whether this copy
        # may go, so clear it and try once more before calling the removal
        # refused. Only ever on the retry: the walk costs nothing on the path
        # that already succeeded.
        pass
    for path in [scratch_root] + sorted(scratch_root.rglob("*")):
        try:
            # A directory has to be enterable and writable to give up its
            # children; a file only has to be writable.
            path.chmod(path.stat().st_mode | (0o700 if path.is_dir() else 0o200))
        except OSError:
            pass
    try:
        shutil.rmtree(str(scratch_root))
    except OSError as exc:
        sys.stderr.write(
            "{}: {}: {}\n".format(SCRATCH_NOT_REMOVED, scratch_root, exc)
        )


def _scratch_tree(rev, worktree_root, scratch_root):
    """Clone ``rev`` beside the tree, so no oracle runs in the tree itself.

    A clone, not an extract: the copy carries its own history, so a git oracle
    reads the revision under test rather than walking up to whichever
    repository happens to enclose the copy. ``rev`` is resolved here, against
    the tree being graded, so the clone's own HEAD never decides what ``HEAD``
    meant. The clone keeps no remote: an oracle is ticket content, and ticket
    content is untrusted, so the scratch tree offers it no path to write back
    out of.

    ``core.symlinks=false`` is the third route out, and the only one the copy
    rather than the text can close. A committed symlink materialises as a file
    holding its target's path, so ``--output=link/PAYLOAD`` and
    ``-O link/orderfile`` -- both spelling a location inside the copy, both
    landing outside it -- fail on the copy's own filesystem instead. Written
    into the clone's config with ``--config`` and never with a global ``-c``:
    the checkout below is a separate process, and only what the config file
    holds reaches it. Windows already defaults to this, so setting it removes
    a divergence rather than adding one.

    ``core.longpaths=true`` for the same reason and by the same route. Where
    git enforces ``MAX_PATH`` the checkout below drops the entries it cannot
    write and still exits 0, so the copy arrives short of the revision it
    claims to hold and every oracle after it reads a tree missing files. Set
    here rather than asked of the host: a copy that silently omits part of the
    revision is a wrong reading on whichever host omits it.
    """

    tree = scratch_root / re.sub(r"[^A-Za-z0-9_.-]", "-", rev)
    if tree.is_dir():
        return tree
    resolved = _git(["rev-parse", rev + "^{commit}"], worktree_root)
    if resolved is None or resolved.returncode != 0:
        return None
    clone = [
        "clone",
        "--quiet",
        "--no-checkout",
        "--config",
        "core.symlinks=false",
        "--config",
        "core.longpaths=true",
        str(worktree_root),
        str(tree),
    ]
    steps = (
        (clone, scratch_root),
        (["checkout", "--quiet", "--detach", resolved.stdout.strip()], tree),
        (["remote", "remove", "origin"], tree),
    )
    for args, cwd in steps:
        proc = _git(args, cwd)
        if proc is None or proc.returncode != 0:
            shutil.rmtree(tree, ignore_errors=True)
            return None
    # Whatever the checkout arrived carrying is the copy's arrival state and no
    # span's doing. Recorded here so the first span graded is answerable for
    # the difference it made and for nothing else.
    _mutations(tree)
    return tree


def _mutations(tree):
    """Paths this copy holds that it did not hold at the previous reading.

    ``--ignored`` is the whole reading rather than a refinement of it. The leak
    this measures was found on disk as a `.pytest_cache/` directory, and this
    repository ignores that path, as every repository running pytest does: a
    bare ``git status --porcelain`` returns zero lines with the directory
    sitting in the copy, so the plain spelling is silently vacuous against the
    one leak that motivated the check. Ignored states what a reader wants kept
    out of a diff, and never what a sibling's oracle reads.

    A delta and not a census, because one copy grades span after span: the
    first writer would otherwise convict every span that followed it, and a
    checkout an eol rule or a filter left dirty would convict the first.
    """

    proc = _git(["status", "--porcelain", "--ignored"], tree)
    if proc is None or proc.returncode != 0:
        # No delta and no census: nobody looked. Returning the empty list
        # alone reads as "this span wrote nothing", which is the confinement
        # instrument answering for a reading it never made.
        _unread("git status in {} failed: confinement unmeasured".format(tree))
        return []
    # Porcelain v1 is two status columns, a space, then the path.
    seen = {line[3:] for line in proc.stdout.splitlines() if len(line) > 3}
    key = str(tree)
    fresh = seen - _TREE_STATE.get(key, frozenset())
    _TREE_STATE[key] = seen
    return sorted(fresh)


def _symlink_entries(tree):
    """Every path the graded revision records with git's ``120000`` mode.

    Read from the tree, never from the checkout: ``core.symlinks=false`` is
    what confines the copy, and it leaves the recorded mode exactly as
    committed, so this reads the same on Windows and POSIX and under any
    privilege. A tree carrying no history answers nothing -- the clone is what
    puts history there -- and the reading that failed says so rather than
    reading as a tree recording no symlink.
    """

    proc = _git(["ls-tree", "-r", "HEAD"], tree)
    if proc is None or proc.returncode != 0:
        _unread("ls-tree in {} failed: symlink entries unread".format(tree))
        return []
    return [
        line.partition("\t")[2]
        for line in proc.stdout.splitlines()
        if line.partition(" ")[0] == SYMLINK_MODE
    ]


def _symlink_findings(run, trees):
    """The instrument for ``rules/visibility.md`` §5's "No symlinks".

    One finding per path, named once however many graded trees record it: two
    revisions of one repository are one tree's worth of rule, not two.
    """

    paths = set()
    for tree in trees:
        if tree is not None:
            paths.update(_symlink_entries(tree))
    return [(run, 0, SYMLINK_IN_TREE, path) for path in sorted(paths)]


def _same_revision(rev, worktree_root):
    """Is ``rev`` the commit HEAD already points at?

    At cut time it is: nothing has landed, so every oracle that discriminates
    fails at the baseline and would fail again at HEAD. "Does this pass once
    the work lands" is unanswerable before the work lands, so the honest
    reading is to not ask -- the HEAD half is skipped and a baseline failure
    is clean unless the command could not run at all, which no landing work
    would change. Post-work the two differ and the full rule applies.
    """

    seen = set()
    for candidate in (rev, "HEAD"):
        proc = _git(["rev-parse", candidate + "^{commit}"], worktree_root)
        if proc is None or proc.returncode != 0:
            return False
        seen.add(proc.stdout.strip())
    return len(seen) == 1

__all__ = (
    '_scratch_root', '_remove_scratch_root', '_scratch_tree', '_mutations',
    '_symlink_entries', '_symlink_findings', '_same_revision',
)
