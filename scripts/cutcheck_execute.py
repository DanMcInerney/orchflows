"""Execute and discriminate cutcheck oracle commands."""

try:  # repository checkout
    from scripts import cutcheck_contract as _contract
except ImportError:  # installed flat script directory
    import cutcheck_contract as _contract
ALREADY_PASSES = _contract.ALREADY_PASSES
COMMAND_TIMEOUT = _contract.COMMAND_TIMEOUT
FAILS_BOTH_REVISIONS = _contract.FAILS_BOTH_REVISIONS
NO_HITS_BOTH_REVISIONS = _contract.NO_HITS_BOTH_REVISIONS
NO_MATCH = _contract.NO_MATCH
SEARCH_HEADS = _contract.SEARCH_HEADS
TIMED_OUT = _contract.TIMED_OUT
UNRUNNABLE = _contract.UNRUNNABLE
UNRUNNABLE_ORACLE = _contract.UNRUNNABLE_ORACLE
_EXIT_CACHE = _contract._EXIT_CACHE
_MUTATED = _contract._MUTATED
shlex = _contract.shlex
subprocess = _contract.subprocess

try:  # repository checkout
    from scripts import cutcheck_scratch as _scratch
except ImportError:  # installed flat script directory
    import cutcheck_scratch as _scratch
_mutations = _scratch._mutations

try:  # repository checkout
    from scripts import cutcheck_search as _search
except ImportError:  # installed flat script directory
    import cutcheck_search as _search
_search_exit = _search._search_exit

try:  # repository checkout
    from scripts import cutcheck_state as _state
except ImportError:  # installed flat script directory
    import cutcheck_state as _state
_unread = _state._unread

def _exit_code(command, tree):
    """This command's exit status in this tree, run once however often asked.

    A scratch tree is a copy built for one invocation and thrown away with it,
    and the cache is a speed change rather than a meaning change exactly while
    ``(command, tree)`` reads the same every time: one ticket set states the
    same invariant oracle in item after item, and a suite is a slow read.

    That sameness is measured now rather than assumed. ``_run_once`` reads the
    copy's status after every span it runs, so a span that wrote into the copy
    is reported as ``unconfined-oracle`` instead of silently deciding what the
    next reader of this cache sees. Measured, not proven: the reading covers
    the working tree, so a write into ``.git``, or one an interpreter's
    ``sys.pycache_prefix`` sends to a cache directory outside the copy, is a
    change no status can see.
    """

    key = (command, str(tree))
    if key in _EXIT_CACHE:
        return _EXIT_CACHE[key]
    _EXIT_CACHE[key] = code = _run_once(command, tree)
    return code


def _run_once(command, tree):
    try:
        argv = shlex.split(command)
    except ValueError:
        return None
    if not argv:
        return None
    if argv[0] in SEARCH_HEADS:
        # Answered here and never spawned, so it writes nothing and there is
        # nothing for `_mutations` to report.
        return _search_exit(argv, tree)
    try:
        proc = subprocess.run(
            argv,
            cwd=str(tree),
            # Discarded, never decoded: the exit status is the whole reading,
            # and an oracle in a tree with history prints whatever it likes --
            # `git archive` prints a tar. Text mode made one such span fatal to
            # the invocation, and the report it was one line of.
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=COMMAND_TIMEOUT,
        )
        code = proc.returncode
    except subprocess.TimeoutExpired:
        # A span that ran out of time still ran, and still wrote whatever it
        # had written by the time it was killed.
        code = TIMED_OUT
    except OSError:
        # Nothing started, so there is nothing for it to have written.
        return UNRUNNABLE
    _MUTATED.extend(_mutations(tree))
    return code



def _discrimination(command, baseline_tree, head_tree):
    """The class this oracle fails as, or None when it discriminates.

    An oracle discriminates when it fails at the baseline and passes once the
    work has landed, so HEAD is only consulted after the baseline read fails.
    A baseline read that could not run at all is revision-independent -- no
    work makes an absent command exist -- so it is reported without asking
    HEAD, and at cut time, where there is no HEAD half to ask, it is reported
    all the same. Neither half's non-reading is a failure: a read that timed
    out or could not run decided nothing, and is reported as deciding nothing
    whichever half produced it.

    A half that produced no reading at all -- a command no tokeniser could
    split into an argv -- returns the same None as an oracle that
    discriminates, and names itself through ``_unread`` so the two are told
    apart in the report. ``head_tree`` being None is not that case: it is cut
    time, where the HEAD half is skipped by design and a failed clone has
    already stopped the run.
    """

    at_baseline = _exit_code(command, baseline_tree)
    if at_baseline is None:
        _unread("baseline reading decided nothing: {}".format(command))
        return None
    if at_baseline == 0:
        return ALREADY_PASSES
    if at_baseline in (UNRUNNABLE, TIMED_OUT):
        return UNRUNNABLE_ORACLE
    if head_tree is None:
        return None
    at_head = _exit_code(command, head_tree)
    if at_head is None:
        _unread("HEAD reading decided nothing: {}".format(command))
        return None
    if at_head == 0:
        return None
    if at_head in (UNRUNNABLE, TIMED_OUT):
        # The same reading the baseline half already refuses to call a failure.
        # A command that never returned, or that nothing could run, produced no
        # verdict at HEAD; "fails at both revisions" claims one. An oracle that
        # discriminates perfectly reads as one that never discriminates, and
        # the timeout that says so is the likeliest reading of all -- a suite
        # outgrowing COMMAND_TIMEOUT is the ordinary way here.
        return UNRUNNABLE_ORACLE
    searching = command.split(" ", 1)[0] in SEARCH_HEADS
    if searching and at_baseline == NO_MATCH and at_head == NO_MATCH:
        return NO_HITS_BOTH_REVISIONS
    return FAILS_BOTH_REVISIONS

__all__ = (
    '_exit_code', '_run_once', '_discrimination',
)
