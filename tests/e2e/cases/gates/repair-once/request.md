Review and repair the two supplied Python modules in candidate/. Keep those reference files unchanged; deliver corrected copies under repaired/ and checks.md.

fees.annual_cost(monthly, setup_fee) must return 12 * monthly + setup_fee when setup_fee is known, and None when it is unknown. Inputs are nonnegative integers or, for setup_fee only, None.
eligibility.eligible(annual_cost, budget, supports_required) must return False when the required support is absent, even if cost is unknown; otherwise return None for unknown cost, or whether the known cost is within budget. The boundary is inclusive.

Use exactly one fresh independent reviewer for the whole supplied candidate. Wait for its complete report before any repairs. Then use exactly one worker to make the necessary repairs across both modules, followed by affected checks. The coordinator may prepare copies and run checks but must not make the repairs itself. Keep the original review separate from the repaired result. Do not add a second review or repair pass. Use at most two child agents. All work is local, standard-library only; no network or installation.
