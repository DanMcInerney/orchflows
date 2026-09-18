---
name: invoice-packet
description: Prepare a checked internal invoice and a public summary from an existing invoice and its source.
disable-model-invocation: true
---

Apply the supplied core's docs/architecture.md. Inputs are an invoice, source data, a required check command and output paths. Apply [verified-invoice](../verified-invoice/SKILL.md) to the existing invoice and use its returned invoice for a public summary under [public guidance](../../guidance/public.md). Return the invoice, independent review, check evidence, public summary and any gaps. This workflow has one verification stage and no extra review of the summary.
