## Summary
Release 2.4 replaces the importer's row parser.
version = "2.4.0"

## Approach
Row width is validated first; parsing is a single pass.

## Risks
Consumers of the legacy queue must migrate first.
