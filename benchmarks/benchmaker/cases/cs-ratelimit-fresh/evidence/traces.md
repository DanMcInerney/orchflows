# exhibited call/response traces — fixed scripted-clock timelines

Both timelines were captured against the vendor limiter with an
injected scripted clock. `t` is the injected clock's reading in
seconds; the clock advances only where the timeline says so. These are
the only exhibited concrete runs.

## Timeline T1 — rate=2.0, burst=6

    t=0.0    acquire(4)  -> True
    advance clock by 1.0
    t=1.0    acquire(4)  -> True
    t=1.0    acquire(1)  -> False
    advance clock by 44.0
    t=45.0   acquire(6)  -> True

Timeline T1 spans 45.0 seconds of clock time.

## Timeline T2 — rate=2.0, burst=6

    t=0.0    acquire(6)  -> True
    t=0.0    acquire(1)  -> False
    advance clock by 0.5
    t=0.5    acquire(1)  -> True
    advance clock by 74.5
    t=75.0   acquire(5)  -> True

Timeline T2 spans 75.0 seconds of clock time.

Together the exhibited timelines cover 120.0 seconds of clock time; a
harness that replays them against a real clock cannot finish quickly.
