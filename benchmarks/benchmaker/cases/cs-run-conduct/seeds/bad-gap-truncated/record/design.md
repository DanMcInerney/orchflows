# Frozen evaluation design (record copy)

identity: sha256:5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a
boundary-source: evidence/packet.md (the packet's intended outcome fixes the boundary; nothing here redefines it)
cases: ec-upper, ec-reverse, ec-exit

Selected cases cover upper, reverse/lower, and the exit-2 path;
scoring is byte-exact stdout plus exit code, unchanged at materialization.
