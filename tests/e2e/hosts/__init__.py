"""Explicit native host adapters; unsupported hosts never substitute another."""


# Trials default to cheaper models; --model/--effort override.
DEFAULTS = {'claude': ('claude-sonnet-5', 'high'), 'codex': ('gpt-5.6-luna', 'xhigh')}


def get_host(name, executable=None, model=None, effort=None):
    """Model and effort replace the user's configured values for every session."""
    default_model, default_effort = DEFAULTS.get(name, (None, None))
    model, effort = model or default_model, effort or (default_effort if model in (None, default_model) else None)
    if name == 'claude':
        from hosts.claude import Claude
        return Claude(executable, model, effort)
    if name == 'codex':
        from hosts.codex import Codex
        return Codex(executable, model, effort)
    raise ValueError(f'No exercised launch adapter for {name}')
