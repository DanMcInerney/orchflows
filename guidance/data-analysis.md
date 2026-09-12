# Data analysis

## Make

Define the question, unit of observation and population before calculating. Inspect data provenance, coverage, collection methods, units, missingness and duplicates. Check whether the available sample can support the proposed comparison; more rows do not cure selection bias.

Keep transformations traceable. Explain consequential exclusions, joins, imputations and aggregations. Verify join cardinality, denominators, date boundaries, unit conversions and weighting. Preserve enough source and method information to reproduce the result without relying on hidden manual steps.

Choose calculations and models suited to the data and assumptions. Separate descriptive associations from causal conclusions. Quantify uncertainty where meaningful and test sensitivity to choices that could change the answer. Present magnitudes and baselines alongside percentages; use precision the data can justify.

## Review

Recompute the central result or check it through an independent calculation. Trace a representative record through the transformations and reconcile counts or totals at important boundaries. Look for duplicated joins, missing groups, denominator changes, leakage and misleading aggregation.

Ask whether the conclusion survives plausible uncertainty and alternative assumptions. Check that charts and summaries describe the analyzed population and units accurately. Distinguish a reproducible calculation from a justified inference: either can fail while the other looks convincing.
