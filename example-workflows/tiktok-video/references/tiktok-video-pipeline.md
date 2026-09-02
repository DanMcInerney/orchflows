# tiktok-video pipeline

The stack the `tiktok-video` workflow's render call builds, chosen on
2026-09-02 from the open-source tools that make short vertical video
today. Surveyed: Remotion, HyperFrames, Revideo, Motion Canvas, editly,
MoviePy, MoneyPrinterTurbo, ShortGPT, short-video-maker, NarratoAI,
OpenShorts, whisper.cpp, faster-whisper, whisperX, Kokoro, Chatterbox,
edge-tts, Pexels, Wan 2.2, LTX-2, PySceneDetect. The two designs worth
keeping from that survey are the beat schema every generator converged on
(one narration line beside its own visual query) and Remotion's caption
model (word tokens paged into short caption pages). Everything below is a
default the render call may deviate from when it reports why.

## Run directory

Every stage writes one JSON artifact under `runs/<slug>/`, so any stage
re-runs alone and a variant reuses every artifact its change does not
touch:

    brief.json      the research packet's claims the script drew on
    script.json     {hook, beats[{narration, on_screen, visual, seconds}], cta}
    assets.json     per beat: file, source, licence, w×h, trimmed range
    voice/          one WAV per beat plus words[{text, start_ms, end_ms}]
    captions.json   pages[{text, start_ms, duration_ms, tokens[]}]
    renders/        <variant>.mp4, <variant>.cover.jpg, <variant>.sheet.jpg
    probe.json      the spec probe's readings per render

## Stage choices

| stage | keyless path (`keys: none`) | quality path (a key named in `keys`) |
| --- | --- | --- |
| voice | Kokoro (Apache-2.0, CPU, no cloning) | Chatterbox Turbo or Multilingual (MIT, cloning, an `exaggeration` knob); ElevenLabs where a brand voice is mandated |
| word timing | faster-whisper `word_timestamps=True`, int8, over the generated voice | whisperX forced alignment; or ElevenLabs `/with-timestamps` grouped into words, no ASR pass |
| footage | the caller's own assets; Playwright `recordVideo` at 1080×1920 for product or site demos; FLUX.2 klein stills | Pexels or Pixabay portrait search by each beat's `visual`; one generated hook shot from Wan 2.2 or LTX-2 at most |
| composition | HyperFrames (Apache-2.0): one HTML file per variant, timing in data attributes, GSAP or CSS motion, frames captured headless | Remotion where its licence fits (free for individuals and teams of three; a company licence above that) |
| captions | ASS karaoke tags burned by ffmpeg when no browser is wanted | DOM captions in the composition: active token coloured and scaled |
| music | Pixabay Music or Free Music Archive, licence recorded in `assets.json` | same; a trending sound is the caller's to license, never fetched |
| render | ffmpeg `libx264 -crf 18 -preset medium -pix_fmt yuv420p -r 30 -movflags +faststart`, AAC 192k | same |

Licence traps the render call refuses: F5-TTS and XTTS weights are
non-commercial; Fish Speech carries its own terms; edge-tts is unofficial
and rate-limited. Kokoro, Chatterbox, Qwen3-TTS and OpenVoice are clean.

## Assembly rules

- Write the script's words out in full before voicing them — numerals and
  currency get no timestamps from the aligners.
- Page captions at four to six words, tokens combined within about a
  second of each other, a page break on any silence past 300 ms; hold at
  least 50 ms between active-token highlights so they read rather than
  strobe.
- Duck music under voice with `sidechaincompress` keyed on the voice
  track, or a flat `volume=0.15` where the mix is simple.
- Snap cuts to `librosa.beat.beat_track` beats when a track is present;
  reject any stock clip PySceneDetect finds an internal cut in.
- Normalise with two-pass `loudnorm` (measure, then apply the measured
  values) to the loudness and true-peak targets the rules state.
- Render the cover frame from the hook beat and a contact sheet of one
  frame per beat plus the CTA frame; the render judge reads the sheet
  first and the captures second.

## The spec probe

One command in the workspace, `probe`, read by the render call's `done`
and again by the frame's close. It exits non-zero on any reading outside
the rules' technical specification and writes `probe.json`. Over each
MP4 it reads, through ffprobe and ffmpeg: frame size, frame rate, video
and audio codec, duration against the requested `length`, integrated
loudness and true peak, silence longer than 1.5 s, the caption track or
burned captions present, and the cover frame's timestamp inside the
first second. It runs nothing that needs a key.

## Captures for the render judge

The render call stores, per variant, PNG captures at 0 s, 1 s, 3 s, the
first frame of every beat, and the final frame, each overlaid with the
rules' safe-zone rectangles. That set is the view identity list the
design pack's judge covers, and the only evidence it reads.
