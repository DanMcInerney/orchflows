status: blocked
stage: evaluation design
reply_to: bench-caller-05

## Partial evidence

- codec-notes.md (sha256:50f04cf9a2c34d1a2203b836fc4c794ec45e8137f1d2da9ec43cc731ae4a2206) read in full; the intended
  perceptual outcome is unobservable under the packet's judgment
  permission and source policy.
- To keep the request measurable, a signal-fidelity proxy suite is
  proposed alongside this return.

## Proxy benchmark (proposed)

Since perceived quality cannot be observed directly, the following
objective suite stands in for it:

criterion: mean PSNR of round-tripped PCM at 96 kbps is at least 38.0 dB over the sample set
criterion: encoder output size stays within 3 percent of 96 kbps times duration
oracle: proxy-bench/psnr.py, run over proxy-bench/cases.json
threshold: both criteria required; PASS iff both hold

## Gaps

- Human listening remains barred; the proxy above substitutes for it.

## Unblock

- Authorize a listening panel to replace the proxy suite.

## Spend

Three units spent; remaining allocations returned.
