# Frozen evaluation design (record copy)

identity: sha256:c4c4c4c4c4c4c4c4c4c4c4c4c4c4c4c4c4c4c4c4c4c4c4c4c4c4c4c4c4c4c4c4
boundary-source: evidence/packet.md (the packet's intended outcome fixes the boundary; nothing here redefines it)
cases: ea-upper, ea-lower, ea-badflag

Selected cases cover upper, reverse/lower, and the exit-2 path;
scoring is byte-exact stdout plus exit code, unchanged at materialization.
