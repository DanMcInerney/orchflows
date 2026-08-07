# Worked example

From the case directory:

    uv run --no-project python target/rank.py --weights evidence/records/weights.json \
        evidence/records/alpha.json evidence/records/beta.json evidence/records/omega.json

Exact stdout (LF endings), exit 0:

    rank 1: beta score 5
    rank 2: alpha score 4
    margin 1/2: 1
    excluded: omega required-fail: r1

alpha scores 1 + 3 = 4 (r1, c1), beta scores 1 + 2 + 2 = 5 (r1, c2,
c3). omega would have scored 7 — the highest — but fails the required
case `r1`, so it is excluded from the ranking, not ranked low. The
same three records in any argument order produce these same bytes.
