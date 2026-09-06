# 1. Defects and usable bootstrap

## Goal

A clean checkout installs through the documented no-flag path. An operator may assert the exact source commit, and a mismatch refuses before writes. Public standard resolution and ticket pinning report the same tree identity. Ticket help exposes each standard option and kind once.

This stage makes the current `do`/`judge`/`land` path sufficient to qualify later stages. It adds no new workflow, gate record, or installation coordinator.

## Owners and changes

`installer/packages.py` and `install.py` make `--accepted-source` optional on mutating installs. When supplied, it must be non-empty, the checkout commit must be readable, and the values must match case-insensitively. When omitted, installation makes no assertion and records the observed source commit, including `null` when it cannot resolve one. Help and documentation say plainly that the flag asserts checkout identity; it does not attest that tests passed, that the tree is clean, or that no run is active. Existing wrapper argument forwarding stays unchanged.

`standards_support` and `tickets_pins` share one canonical standard tree-digest calculation and record shape. The public `standards.py resolve` output uses the same digest a ticket pins. Necessary legacy ticket reads remain, but no public command publishes another digest for the same standard tree. `docs/standard-authoring.md` points authors to the canonical resolver and describes the identity it covers.

`tickets_mint.py`, `tickets_commands.py`, and related help generation remove the second parse of `--standard`, duplicate usage fragments, the duplicate `standard` member in `PINNED_KINDS`, and the repeated help alternative. Repeatable standards remain supported.

Focused tests cover no-flag install, explicit matching and mismatching assertions, unresolved source with an explicit assertion, receipt identity, identical resolver/pin digests, repeated standards, and generated help. Preserve uninstall, doctor, dry-run, and old-ticket reads.

## Exclusions

Do not scan all projects for open frames from the installer, add a mandatory census, invent an accepted-gate record, or import the ticket runtime into installation. Do not reinstall beneath running children. Example-workflow defects and obsolete command references are handled only through the general package checker in stage 3; this stage does not edit the gallery.

## Observable proof

First reproduce the current no-flag refusal and the two digest values. After the change, a disposable user install without `--accepted-source` succeeds and records the checkout commit; the same install with the matching full commit succeeds; a different commit refuses before the plan is applied. Resolve one standard through the public resolver, mint a ticket with it, and assert equal digest and directory identity. Check that `do --help` and the top-level kind help show one repeatable standard option.

For source-based qualification, use a stable checkout and the existing lifecycle:

```text
tickets.py do <run> --standard orch-code --goal-file <goal> --workspace <checkout>
# invoke the emitted launch, record its result, then:
tickets.py land <run> <ticket>
tickets.py judge <run> --standard orch-code --goal-file <review> --artifacts git:<landed-tip>
# invoke the judge launch, record findings, then land/close as the current help directs
```

Run the outside probe from that checkout and record `git rev-parse HEAD` as the accepted source for integration. Supplying `--accepted-source <recorded-head>` is useful as a final identity assertion, but it does not replace the checks. Retain the previous source identity and receipt so an operator can reinstall it if the new runtime fails.

The slice is ready to integrate when its focused installer, standard-resolution, ticket-pin, and help tests pass. A source-backed integration test exercises the `do`/`judge`/`land` path and an outside probe; durable live-host artifact and findings lines are recorded only when a host is actually available.
