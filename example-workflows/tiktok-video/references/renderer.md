# Qualified rendering boundary

The private render-video method serves the production maker. It contains no
dispatch or review loop. The public tiktok-video workflow and private production
workflow own calls; their stamped standards own quality. The copied scaffold
owns artifact dependencies; this package's probe uses only Python's standard
library and the project's locked Node CLI. No package runtime npm install,
global FFmpeg, paid provider, or graph-layout library is required.

## Copy and render

Copy every file beside the [scaffold manifest](scaffold/package.json), including its dotfile and public/fonts,
to the video project's root. Run `npm ci --no-audit --no-fund` there. The committed
package-lock.json is the dependency identity; retain it in the produced project.
Use `node render.cjs 1 output/final.mp4` for the silent technical tracer or
`node render.cjs 30 output/final.mp4 mix.wav` when public/mix.wav is the final mix.
`npm run studio` provides local playback; output/final.mp4.png is a sampled still,
not a contact sheet or evidence of motion. Extend index.tsx into the approved
film; the sample two-node graphic is deliberately only a render boundary.

The renderer supports 1–120 seconds at 30 fps, rounding fractional durations to
the nearest frame. Animation derives from useCurrentFrame; a shared camera
transform preserves diagram identity across semantic zoom scales. Hold the
current focus long enough to read at phone size. Never use wall clocks, CSS
animations, random unseeded state, or a previous rendered frame as state.
Load local fonts before continuing render; use Remotion media primitives and
loading gates for asynchronously loaded captions/images. Seek through beginning,
transition midpoints and end, then inspect actual playback. Do not mistake a
static screenshot or a decoded file for settled motion/readability.

Render explicitly sets H264, yuv420p, BT.709 and AAC at 48kHz. Inspection must
confirm tv range and all three BT.709 tags: the prepared smoke's defaults had
reported full-range bt470bg. Do not remove a color check to accommodate defaults.
The observed encoder also needed explicit x264 VUI primaries/transfer flags;
render.cjs supplies them. The bundled FFmpeg omits the default wrapped_avframe
null encoder, so probe.py explicitly decodes to rawvideo/PCM in its null sink.

## Frozen tool and asset provenance

Qualified 2026-09-08 on Windows 11, Node 24.15.0 / npm 11.12.1. Direct Remotion
packages are 4.0.522, React/React DOM 19.2.8, Kokoro.js 1.2.1, and the directly
imported transformers package is 3.8.1. The scaffold lock
was reconciled from the prepared rendering lock plus that exact Kokoro pin:
naively merging the two locks conflicted at semver, tslib and yallist. npm
resolved transitive placement; actual clean npm ci and rendering are required
evidence. The qualified voice route uses transformers 3.8.1, phonemizer 1.2.1,
and onnxruntime-node 1.21.0. Future dependency additions require a recorded reason,
new lock and observed relevant execution, not a floating npx call.

[Browser provenance](scaffold/browser-provenance.json) freezes Chrome Headless
Shell 149.0.7790.0 win64 URL and the downloaded executable SHA256. render.cjs
verifies the executable before rendering. It uses Remotion's download or
REMOTION_BROWSER_EXECUTABLE pointing to the restored browser executable; keep
the browser's adjacent files intact. Its archive is outside npm lock integrity.
Other platforms/browsers are unqualified until separately observed and pinned;
this is no claim of portable bit-identical output.

[Font provenance](scaffold/font-provenance.json) pins the bundled Inter variable
font to an exact google/fonts commit and SHA256; its OFL license is beside the
font. Inter is newly frozen because the prepared smoke used host Arial. The
scaffold loads this local file and verifies its hash instead of relying on host
fonts. Respect OFL terms when redistributing/modifying fonts.

Remotion v4's installed LICENSE.md permits its enumerated free uses (individuals,
for-profit organizations up to three employees, nonprofits, noncommercial
evaluation); other entities require a Company License. User entity size and
production eligibility remain unresolved. Evaluation evidence does not grant
production eligibility. Do not purchase or silently upgrade. HyperFrames 0.8.31
is the researched Apache-2.0 alternative, not an observed fallback here.
The bundled FFmpeg n7.1 build includes GPL features; preserve applicable license
notices if redistributing binaries. Kokoro.js/model weights use Apache-2.0;
retain upstream notices and stock-voice provenance.

## Local voice, captions and sound

Reuse the prepared local q8 proof rather than rediscovering TTS installation.
[Model provenance](scaffold/model-provenance.json) lists exact-revision URLs,
relative restoration paths, byte counts and hashes for
onnx-community/Kokoro-82M-v1.0-ONNX revision
1939ad2a8e416c0acfeecc08a694d14ef25f2231. Restore those four assets under model/,
or copy and verify the prepared assets; they are intentionally not vendored in
the gallery. voice.mjs checks every hash and bundled af_heart.bin, disables
remote models/cache, and rejects application fetches. It uses CPU q8 at speed 1.
No voice clone, API key or runtime model revision parameter is involved.

Put short original phrases in phrases.json; `npm run voice` writes WAV chunks
and public/captions.json with source text, sample count/rate, sample-derived
start/end seconds and hashes. Schedule chunks and phrase captions from this
one timeline, converting seconds to display frames only at render time. Include
intentional gaps in both clocks if editing pauses. Keep actual chunk waveforms
and text for audition; low-energy silence detection is not word alignment.
The generator's short-chunk guard reduces truncation risk but cannot establish
missing-word absence. Audition every phrase and compare with the script.

For one second, choose a readable single idea; voice may be explicitly omitted.
For 120 seconds, budget distinct explanatory beats and measured pauses. Neither
duration should be a stretched 30-second composition. Word highlighting requires
a separately qualified forced aligner; never distribute a phrase's time evenly
over words and call that alignment.

Use original synthesized sound or licensed music with recorded authorship/source,
license and asset hashes. A test sine is original technical audio, not a fitting
soundtrack. Mix a continuous delivery bed with voice foreground, deliberate
ducking and fades. Inspect decoded integrated loudness and true peak after AAC
encoding; the reference production target is -16 LUFS +/-2, true peak <= -1 dBTP.
Pass other approved settings explicitly to the probe. A listening-capable
reviewer must judge intelligibility, pronunciation, musical fit and sync;
waveform statistics, captions and text cannot prove heard quality.

## Outside output probe

From the disposable project root, with the unchanged accepted package in its
project bundle, use the workflow environment interpreter:

    <orchflows env workflow tiktok-video> .orchflows/workflows/tiktok-video/scripts/probe.py --project . --video output/final.mp4 --seconds 30

This denotes the interpreter returned by `orchflows env workflow tiktok-video`,
not a literal shell executable. On the qualified host it is the verified Python
interpreter. Probe defaults are 30fps, required audio, -16 LUFS +/-2 and -1 dBTP.
For an approved silent artifact add `--audio optional`; any present audio still
undergoes codec/timing/loudness checks. Use `--fps`, `--lufs`, `--lufs-tolerance`
and `--true-peak` only for explicit production settings.

The probe checks one 1080x1920 H264 stream, pixel/color tags, frame rate, decoded
frame count and video duration within one frame. It runs FFprobe count_frames
and full FFmpeg decode with fatal decoder errors, then measures audio. AAC can
pad its stream/container: compare video duration to the requested duration;
permit audio difference of two AAC packets plus one video frame. This is not
permission for narration drift. Absent/corrupt/malformed/wrong-size/wrong-duration
outputs return nonzero JSON errors. Each tool invocation has a 300-second timeout.
The probe intentionally does not certify visible burned captions or aesthetics.

Before reporting success, preserve nonzero absent/corrupt readings and a zero
reading on the actual output, along with file hash, command exits and independent
visual/audio findings. Foundation's 1s rendered tracer and cheap 120s endpoint
fixture are technical checks only. The actual named workflow, 30s polished film,
120s/1s creative quality, listening and independent acceptance belong to later
admission/production; retain these gaps until observed.

## Foundation observations, 2026-09-08

Run 20260908-video-creator, ticket B1.1.1.2 under frame B1.1.1 exercised this
copied scaffold in a disposable project. It did not invoke the finished public
workflow; that package and its independent admission did not yet exist.
Maker pins were orch-code
8049030d7cef517e5d6dbc09a1ece092c43841521cd76665022132bded12ddf6 and
orch-workflow-authoring
6ab4a4dee535a7f0ddcde8682049dac84499245f13aeaba1bb82b7b80a1258a0.
No independent foundation judgment is implied; the joined gate owns it.

| Observed boundary | Exit / reading |
| --- | --- |
| Copied scaffold clean npm ci | 0 |
| 1s Remotion portrait tracer | 0; 30 rendered/decoded frames |
| Absent / corrupt file probe | 1 / 1 |
| Actual 1s decoded audio/video probe | 0; -16.12 LUFS, -15.29 dBTP |
| 120s repeated-still technical fixture | Encode 0, probe 0; 3600 decoded frames, -16.05 LUFS, -10.11 dBTP |
| Wrong 540x960 size / requested 2s on 1s output | 1 / 1 |
| Local q8 phrase generation / decoded WAV | 0 / 0; 62,400 samples at 24kHz, 2.6s |
| Silent render; required / optional audio probe | 0; 1 / 0 |

The midpoint PNG was directly inspected: readable Make/Check nodes, arrow and
tracer labels on a portrait canvas. This is not continuous playback or heard
audio evidence. The 120s fixture repeats that rendered still and a measured
original test tone; it does not exercise a full 3600-frame Remotion production,
long-zoom craft, narration pacing or endpoint creative quality. Six deterministic
probe tests cover additional malformed metadata, missing audio, bad color/fps/
codec, AAC padding versus drift, timeout, silent/clipped/off-target signal and
toolchain-pin failures. These mocks do not replace the observed decode above.

The initial TSX build failed, the first colorSpace-only output lacked H264
transfer/primaries, and the first null decode lacked an enabled output encoder.
All produced nonzero readings before the documented fixes. Exact argv, exits,
timings, hashes and logs are retained in the ticket Report's evidence note;
render/voice output remains auditionable in that candidate's reserved scratch.
