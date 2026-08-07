## Summary
Release 2.4 hardens the importer and removes the legacy queue.
version = "2.4.0"

## Approach
The importer now validates row width before parsing.

## Risks
Legacy queue consumers must migrate before upgrading.

## Rollout
Staged over two weeks behind the import-v2 flag.
