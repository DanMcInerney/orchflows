"""Explicit native host adapters; unsupported hosts never substitute another."""


def get_host(name, executable=None):
    if name == 'claude':
        from hosts.claude import Claude
        return Claude(executable)
    raise ValueError(f'No exercised launch adapter for {name}')
