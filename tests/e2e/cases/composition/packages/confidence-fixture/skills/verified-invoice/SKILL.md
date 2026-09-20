---
name: verified-invoice
description: Review an existing invoice against source data, with at most one repair and the caller's required checks.
disable-model-invocation: true
---

Apply `shared:review-revise-once` to the supplied invoice, source, check command and output paths with [internal guidance](../../guidance/internal.md). Repairs are limited to actual invoice errors. Return its delivered invoice, original review, checks and unresolved findings.
