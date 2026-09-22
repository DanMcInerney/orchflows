"""Explicit native host adapters; unsupported hosts never substitute another."""


# Trials default to cheaper models; --model/--effort override.
DEFAULTS = {'claude': ('claude-sonnet-5', 'high'), 'codex': ('gpt-5.6-luna', 'xhigh')}

# Concurrent harness sessions (--jobs). Hosts cap children per session (Claude runs up to 20
# subagents; Codex agents.max_threads), not sessions per account, so the harness bounds the total.
# A target session plus its children is about four agents: at most three children ran at once in
# 54 Codex Luna targets on 2026-09-22, and case requests allow six in all. Audits delegate nothing.
# Five sessions therefore stay near 20 agents, what one Claude session may already run.
JOBS = 5


def requested(name, model=None, effort=None):
    """The model and effort every session requests; another model drops the default effort."""
    default_model, default_effort = DEFAULTS.get(name, (None, None))
    return model or default_model, effort or (default_effort if model in (None, default_model) else None)


def get_host(name, executable=None, model=None, effort=None):
    """Model and effort replace the user's configured values for every session."""
    model, effort = requested(name, model, effort)
    if name == 'claude':
        from hosts.claude import Claude
        return Claude(executable, model, effort)
    if name == 'codex':
        from hosts.codex import Codex
        return Codex(executable, model, effort)
    raise ValueError(f'No exercised launch adapter for {name}')
