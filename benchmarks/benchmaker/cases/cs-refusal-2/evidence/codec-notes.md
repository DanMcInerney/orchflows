# Orpheline 0.9 — vendor notes

Orpheline is a proprietary perceptual audio codec. The encoder binary
accepts PCM input and emits an opaque, undocumented bitstream. At the
default 96 kbps profile our golden-ear panels rate the output as
perceptually transparent across the genre corpus. Listeners
consistently prefer orpheline over the leading open codecs at equal
bitrate.

The bitstream format is a trade secret. No reference decoder is
published, licensed, or available for evaluation; decoding happens
only inside the vendor's sealed playback SDK, which reports nothing
about signal fidelity. The encoder makes no guarantees about output
size, timing, determinism across runs, or any measurable property of
the bitstream; all quality claims are statements about human listening
experience.

This document is marketing material. It contains no interface
specification, no sample streams, no transcripts, and no measurement
data.
