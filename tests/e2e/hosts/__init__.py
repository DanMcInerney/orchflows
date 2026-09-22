"""Explicit native host adapters; unsupported hosts never substitute another."""


def get_host(name, executable=None, model=None, effort=None):
    """Model and effort, when given, replace the user's configured values for every session."""
    if name == 'claude':
        from hosts.claude import Claude
        return Claude(executable, model, effort)
    if name == 'codex':
        from hosts.codex import Codex
        return Codex(executable, model, effort)
    raise ValueError(f'No exercised launch adapter for {name}')
