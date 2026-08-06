# Cache rollout digest

The cache went from 5% to full traffic on 2026-03-02 [S1], and p99 read latency dropped from 412 ms to 96 ms [S2].
Cache hosts cost $1,840 a month against a $5,200 fall in origin database spend [S4].
A stale-key bug served outdated prices to 0.3% of sessions for 26 minutes that day [S3].
Nothing tracked stale-key age, which is the open follow-up [S5].
