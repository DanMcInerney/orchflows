"""Explicit native host adapters; unsupported hosts never substitute another."""


def get_host(name, executable=None):
    if name == 'claude':
        from hosts.claude import Claude
        return Claude(executable)
    if name == 'codex':
        from hosts.codex import Codex
        return Codex(executable)
    raise ValueError(f'No exercised launch adapter for {name}')
