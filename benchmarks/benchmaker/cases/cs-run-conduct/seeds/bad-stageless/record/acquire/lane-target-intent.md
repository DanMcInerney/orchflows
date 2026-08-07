# Lane: target intent

## stated claims

- the CLI transforms one argv line per flag; stdout only.

## demand and failure record

- users report flag typos exiting 0 in v1.0; fixed v1.1.

## boundaries and refusals

- no stdin mode is claimed; no locale guarantee is made.

## operator and harness

- outcome observed through argv/stdout/exit code alone.

## change history

- v1.1 hardened unknown-flag handling to exit 2.
