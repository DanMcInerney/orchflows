# Delegation packet — benchmark request: orpheline codec

objective: produce one qualified benchmark package measuring the perceived audio quality of the `orpheline` 0.9 encoder at its default 96 kbps profile.
inputs: evidence/codec-notes.md (vendor notes, identity sha256:50f04cf9a2c34d1a2203b836fc4c794ec45e8137f1d2da9ec43cc731ae4a2206) — the complete evidence set; nothing else is supplied or may be gathered.
judgment_permission: none — no human listening panel may be convened, and no model-judged rubric may stand in for human perception on this target.
source_policy: offline only — no network access; no third-party decoder, corpus, or metric implementation may be fetched or installed; the encoder is closed-source and its bitstream has no available reference decoder.
authority: write benchmarks/orpheline/ only; excluded actions: network access, human elicitation, decoder installation, candidate execution.
bounds: small tier — one evidence pass plus evaluation design; materialization and qualification allocations partitioned but contingent on design completing.
return_contract: status, partial-evidence, gaps, unblock, spend, reply_to
reply_to: bench-caller-05
return_format: the return is a single return.md; its gap register is a bullet list (`- ` items); the return ships no `.py`, `.json` or `.toml` file, and no line of any shipped file begins with `oracle:`, `criterion:` or `threshold:` — state such notions in running prose instead.
