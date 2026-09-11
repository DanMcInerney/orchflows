---
name: search-polymarket
description: Find and locally rank Polymarket contract and price evidence matched to a research question's exact outcome and horizon.
---

# Search Polymarket

Load and follow [search-site](../search-site/SKILL.md) in the current worker context, without spawning agents. Apply this profile to an ordinary research question or a caller's Polymarket assignment. Use the shared scope, public read-only default, bounds and evidence contract, returning locally ranked evidence in the assigned `results.md`.

- Match the exact market question, outcomes and forecast horizon, then inspect its resolution rules, threshold, deadline and resolution source. An event can contain several different contracts. A threshold touched at any time before a deadline does not answer an end-of-period direction or closing-value question.
- Preserve the exact contract wording, outcome labels and observed price strings alongside the original market URL and event relationship. Verify each outcome/price association from the actual page or response, including array ordering when applicable; never infer the pairing from proximity in a flattened page or search snippet. Keep any converted percentage separate and show its basis.
- Keep the observation time, market creation/update time, forecast deadline and resolution status distinct. A price observed now cannot establish odds at an earlier information cutoff; historical requests require evidence of the price at that time. Unavailable history is a gap, not permission to date a current price retrospectively.
- For active-market questions, verify current status and exclude resolved or closed markets from the active evidence set. Label any historical comparison separately. Do not infer active status solely from a search listing or a future date in the title.
- Preserve whether a quoted value is an outcome price, last trade, bid or ask, when stated. Include available liquidity, volume and spread context with its observation time and units; missing context limits interpretation. A thin market's price is evidence of that market, not a representative poll or a guaranteed probability.
- Inspect relevant sibling contracts when needed to understand the event, within the assigned bounds. Correlated thresholds, mutually exclusive outcomes and multiple contracts sharing one event are not independent corroboration. Rank by fit to the question and evidential substance, not by the most striking price.

If the shared workflow selects the optional bundled acquisition method, consult `prediction_markets` in its [adapter roster](../research-acquire/references/protocol.md#adapter-roster), using its Polymarket search, event and market reads. Inspect the returned rules and outcome/price fields; route availability does not establish their completeness or provide a historical price snapshot.
