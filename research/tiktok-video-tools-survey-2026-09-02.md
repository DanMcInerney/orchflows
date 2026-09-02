# Open-source toolchain survey: programmatic short-form vertical marketing video

Research packet behind `example-workflows/references/tiktok-video-pipeline.md`.
Surveyed 2026-09-02 by a web-research lane; star counts are as read from GitHub
repo pages or star-history that day and are approximate. Not a library owner:
the pipeline reference is what the workflow reads, this file is its evidence.

## 1. Composition / rendering engines

### Remotion — https://github.com/remotion-dev/remotion
- ~58.0k stars, TypeScript/React. **Not OSI open source**: source-available, free
  for individuals, non-profits, and companies with ≤3 employees; larger companies
  need a Company License ($25/seat/mo "Creators" or $0.01/render with $100/mo
  minimum for "Automators", i.e. any pipeline)
  ([license FAQ](https://www.remotion.dev/docs/license/faq),
  [pricing](https://www.remotion.dev/docs/license/pricing)).
- Steal: the frame-as-function-of-time model (`useCurrentFrame()`, `<Sequence>`,
  `<Series>`, `interpolate`) makes every animation deterministic and testable;
  `@remotion/captions` defines the cleanest caption data model in the ecosystem —
  a flat array of `{text, startMs, endMs, timestampMs, confidence}` tokens fed to
  `createTikTokStyleCaptions({combineTokensWithinMilliseconds,
  breakOnSilenceAfterMilliseconds})` returning
  `pages[{text, startMs, durationMs, tokens[{fromMs,toMs}]}]`; active-word
  highlighting compares playback time to `token.fromMs/toMs`
  ([docs](https://www.remotion.dev/docs/captions/create-tiktok-style-captions)).
  `@remotion/install-whisper-cpp` and `@remotion/whisper-web` normalise Whisper
  output into that shape. The official
  [template-tiktok](https://github.com/remotion-dev/template-tiktok) is the
  reference implementation of word-by-word TikTok captions;
  [remotion-dev/skills](https://github.com/remotion-dev/skills) packages
  captions/transitions/rendering guidance as agent skills.
- Weakness: licensing cost at company scale; Chromium rendering is CPU-heavy;
  React is mandatory.

### HyperFrames (HeyGen) — https://github.com/heygen-com/hyperframes
- ~43.6k stars, TypeScript, **Apache-2.0**. Plain `index.html` + CSS + data
  attributes for timing, animations through adapters (GSAP, CSS, Lottie,
  Three.js, WAAPI), frames captured deterministically via headless Chrome and
  encoded with FFmpeg.
- Steal: HTML as the composition format so any LLM authors it without a build
  step; the bundled agent skills with a router (`/product-launch-video`,
  `/faceless-explainer`, `/motion-graphics`) are the marketing-video taxonomy;
  targets 30–90 s clips.
- Weakness: young; animations must stay seekable (no wall-clock time) or frames
  drift; Lambda rendering adds deployment overhead; HeyGen-controlled roadmap.

### Motion Canvas — https://github.com/motion-canvas/motion-canvas
- ~19k stars, TypeScript, MIT. Generator-function animation with a live editor
  and audio-sync timeline. Steal: generator sequencing reads like a storyboard.
  Weakness: explainer/vector oriented, no headless render API in core, slower
  maintenance.

### Revideo — https://github.com/midrender/revideo
- ~4.0k stars, TypeScript, MIT. Motion Canvas fork with `renderVideo()` headless
  API, parallel workers, React `<Player/>` with dynamic inputs. Steal: preview
  and final render share one scene definition with typed inputs — the
  template-plus-variables model variant generation needs. Weakness: small
  community, commercial-product priorities, telemetry on by default.

### editly — https://github.com/mifi/editly
- ~5.5k stars, Node, MIT. Declarative JSON edit spec → ffmpeg, streaming.
  Steal: the JSON spec shape `{outPath, width, height, fps, defaults, clips[{duration,
  transition, layers[{type: video|image|title|subtitle|...}]}], audioTracks[],
  audioNorm}` — the simplest Creatomate-like model in OSS;
  [vidapi](https://github.com/moshehbenavraham/vidapi) wraps it as a self-hosted
  render API. Weakness: dormant for years (new maintainer, RC); no word-level
  caption layer; GL/canvas layers need headless GPU deps.

### Diffusion Studio core — https://github.com/diffusionstudio/core
- ~1.2k stars, TypeScript, MPL-2.0. Browser-only WebCodecs compositor. Steal: the
  hardware-accelerated render path and a CapCut-like caption API. Weakness: no
  server rendering.

### OpenCut — https://github.com/OpenCut-app/OpenCut
- ~88.4k stars, MIT. The "open-source CapCut"; a rewrite is in progress with a
  planned Editor API, plugin system, MCP server and headless batch rendering.
  Steal: watch its headless mode as the human-in-the-loop editor. Weakness:
  pre-release; nothing to build a pipeline on today.

### MoviePy — https://github.com/Zulko/moviepy
- ~14.9k stars, Python, MIT. Fastest way to prototype captions in Python;
  captacity and MoneyPrinter v1 build on it. Weakness: numpy round-trips make
  renders far slower than ffmpeg filtergraphs; v1→v2 breaks.

### ffmpeg wrappers
- [ffmpeg-python](https://github.com/kkroening/ffmpeg-python): ~11k stars,
  Apache-2.0, last release 2019 — frozen.
  [PyAV](https://github.com/PyAV-Org/PyAV) (~3.2k, BSD) is the maintained
  frame-level alternative. Winning pattern: generate the ffmpeg CLI string
  yourself.

## 2. AI short-video generators (topic → finished video)

### MoneyPrinterTurbo — https://github.com/harry0703/MoneyPrinterTurbo
- ~119.6k stars, Python, MIT. LLM script → search terms → Pexels/Pixabay/Coverr
  clips (or generated) → Edge TTS / Azure / ElevenLabs → subtitles from Whisper
  or TTS timestamps → ffmpeg assembly with BGM; 9:16 and 16:9, batch, CLI +
  WebUI + API + MCP.
- Steal: subtitle source = TTS timestamps first, Whisper as fallback; the
  search-terms step (LLM emits per-scene keywords beside the narration) is the
  data model everyone copies; config-as-preset export.
- Weakness: generic stock-footage-plus-robot-voice output; basic captions;
  Python 3.11 + 3 GB Whisper download.

### MoneyPrinter (v1) — https://github.com/FujiwaraChoki/MoneyPrinter
- ~13.9k stars, MIT. Ollama → Pexels → TikTok TTS/EdgeTTS → MoviePy →
  AssemblyAI; Postgres-backed restart-safe queue. V2 (~31.5k) is AGPL-3.0.
  Steal: the job queue.

### ShortGPT — https://github.com/RayVentura/ShortGPT
- ~7.9k stars, Python, MIT. Stepwise engines with TinyDB-persisted state so
  reruns skip done steps; an LLM-readable editing markup; translation/dubbing.
  Weakness: largely unmaintained, dated captions.

### NarratoAI — https://github.com/linyqh/NarratoAI
- ~11k stars, Python, MIT. Commentary over existing footage: VLM frame analysis
  → LLM screenplay → clip selection → TTS → subtitles. Steal: vision-model shot
  analysis as script input, so a script references what is on screen.

### short-video-maker — https://github.com/gyoridavid/short-video-maker
- ~1.3k stars, TypeScript, MIT. Remotion + Kokoro.js + whisper.cpp + Pexels +
  ffmpeg as MCP + REST. Scene model `{text, searchTerms}`; caption position,
  music mood, orientation, 28 Kokoro voices. Steal: the most modern near-keyless
  stack and the minimal scene schema. Weakness: English-only, Pexels-only, no own
  media.

### Faceless generators (illustrative)
- VUZA, Viral-Faceless-Shorts-Generator, SaarD00/AI-Youtube-Shorts-Generator:
  steal only the manual approval gate between script and render.

## 3. Auto-clippers (long video → shorts)

- [OpenShorts](https://github.com/mutonby/openshorts) (~3.8k, MIT): Gemini
  moment detection → MediaPipe + YOLOv8 face tracking with
  TRACK/GENERAL/SPLIT/SCREENCAST layouts → faster-whisper word subtitles;
  MCP + REST + webhooks. Steal: the layout-mode enum (SCREENCAST is what
  product-demo reframing needs).
- [AI-Youtube-Shorts-Generator](https://github.com/SamurAIGPT/AI-Youtube-Shorts-Generator)
  (~4.8k, MIT): rank → dedupe overlaps → top-N selection loop.
- [ClipsAI](https://github.com/ClipsAI/clipsai) (538, MIT): clean library API.
- [opensource-clipping](https://github.com/NaufalRizqullah/opensource-clipping)
  (85, MIT): the one small repo implementing ducking + b-roll + karaoke captions
  together.

## 4. Subtitles / captions

- [whisper.cpp](https://github.com/ggml-org/whisper.cpp) (~53.4k, MIT): `-ml 1`
  word timestamps, CPU-friendly; heuristic timing.
- [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (~25.2k, MIT):
  `word_timestamps=True`, Silero VAD, int8 CPU; default ASR for Python.
- [whisperX](https://github.com/m-bain/whisperX) (~23.8k, BSD-2): wav2vec2
  forced alignment (sub-100 ms words). Numerals and currency get no timestamps —
  pre-normalise the script to words.
- [captacity](https://github.com/unconv/captacity) (138, MIT): style dict (font,
  size, colour, stroke, shadow, `highlight_current_word`, `line_count`) — a
  caption theme schema.
- Rendering options: DOM captions (Remotion/HyperFrames); ASS/libass `\k`/`\kf`
  karaoke tags burned via `ffmpeg -vf "ass=captions.ass"` — no browser, 4–6
  words per page, 50–100 ms gaps between highlights
  ([guide](https://vidno.ai/blog/karaoke-style-word-highlight-captions)); PIL
  PNG overlays.

## 5. TTS

| Tool | Stars | License | Notes |
|---|---|---|---|
| [Kokoro](https://github.com/hexgrad/kokoro) | ~8.7k | Apache-2.0 | 82M params, 9 languages, CPU; no cloning; espeak-ng/misaki. Best default keyless voice. |
| [edge-tts](https://github.com/rany2/edge-tts) | ~11.8k | GPL-3.0 | Edge Read Aloud, `--write-subtitles` word boundaries; unofficial, ToS risk. |
| [Piper](https://github.com/OHF-Voice/piper1-gpl) | ~5.4k | GPL-3.0 | Fast CPU; robotic vs Kokoro. |
| [Chatterbox](https://github.com/resemble-ai/chatterbox) | ~26.2k | MIT | Turbo/Nano/Multilingual V3 (23+ langs); zero-shot cloning, `exaggeration` knob, watermark; blind test 65% preferred vs ElevenLabs ([source](https://findskill.ai/blog/best-open-source-tts-2026/)). |
| [Qwen3-TTS](https://github.com/QwenLM/Qwen3-TTS) | ~13.2k | Apache-2.0 | 10 langs, 3-s cloning, voice design from a description. |
| [Fish Speech](https://github.com/fishaudio/fish-speech) | ~32.5k | bespoke | check commercial terms. |
| [F5-TTS](https://github.com/SWivid/F5-TTS) | ~15.2k | MIT code, CC-BY-NC weights | non-commercial. |
| [OpenVoice](https://github.com/myshell-ai/OpenVoice) | ~37.4k | MIT | tone-colour converter over a base TTS. |
| [XTTS-v2 fork](https://github.com/idiap/coqui-ai-TTS) | ~2.3k | CPML weights | non-commercial; avoid. |
| ElevenLabs (hosted) | — | commercial | `/with-timestamps` returns character alignment ([API](https://elevenlabs.io/docs/api-reference/text-to-speech/convert-with-timestamps)). |

## 6. Stock, b-roll, generative

- [Pexels](https://www.pexels.com/api/documentation/): `/videos/search?orientation=portrait`,
  200 req/h, 20k/mo; attribution when possible.
  [Pixabay](https://pixabay.com/api/docs/): `orientation=vertical`, 100 req/min.
- Local generative video: [Wan 2.2](https://github.com/Wan-Video/Wan2.2) (~17.4k,
  Apache-2.0; TI2V-5B does 5 s 720p in under 9 min on a 24 GB card; later Wan
  versions are API-only); [LTX-2](https://github.com/Lightricks/LTX-2) (~9.3k,
  synchronised audio + video, ~66 GiB);
  [HunyuanVideo-1.5](https://github.com/Tencent-Hunyuan/HunyuanVideo-1.5);
  [CogVideoX-1.5](https://github.com/zai-org/CogVideo) (cheapest, ~3.6–5 GB int8);
  [Wan2GP](https://github.com/deepbeepmeep/Wan2GP) for 6 GB VRAM. Stills:
  [FLUX.2 klein 4B](https://github.com/black-forest-labs/flux2) (Apache-2.0).
- For marketing videos generative video is an accent (a 3–5 s hook shot), not the
  b-roll backbone.

## 7. Music

- Pixabay Music (no attribution, TikTok-ad OK), Free Music Archive (filter NC),
  Incompetech (CC-BY), YouTube Audio Library.
- Beat detection: `librosa.beat.beat_track` → `frames_to_time`
  ([docs](https://librosa.org/doc/0.11.0/generated/librosa.beat.beat_track.html)).
- Ducking: `[music][voice]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=300[duck];[voice][duck]amix=inputs=2`
  ([FFmpegLab](https://www.ffmpeglab.com/articles/ffmpeg-audio-mixing-amix-guide.html)),
  or a static `volume=0.15`.

## 8. Screen / product capture

- Playwright `recordVideo`: set `viewport` to 1080x1920 and `recordVideo.size`
  ([docs](https://playwright.dev/docs/videos)) — deterministic SaaS demo shots.
- [Screenity](https://github.com/alyssaxuu/screenity) (~18.7k, GPL-3.0) and OBS +
  [obs-websocket](https://github.com/obsproject/obs-websocket) for human-driven
  capture.

## 9. QA

- [PySceneDetect](https://github.com/Breakthrough/PySceneDetect) (~5.1k, BSD-3):
  verify b-roll has no internal cuts; cuts-per-10 s as a pacing metric.
- Loudness: two-pass `loudnorm` (`I=-14:TP=-1.5:LRA=11:print_format=json`, then
  feed `measured_*`)
  ([guide](https://dev.to/masonwritescode/two-pass-loudness-normalization-with-ffmpeg-loudnorm-the-right-way-1nm3)).
- Specs: 1080x1920, H.264 + AAC, 30 fps, 8–15 Mbps upload; 15–30 s highest
  engagement; safe zones top ~150–250 px, right ~120–240 px, bottom ~300–500 px
  ([Zeely](https://zeely.ai/blog/tiktok-safe-zones/),
  [Recharm](https://www.recharm.com/blog/tiktok-video-ad-specs)).

## 10. Synthesis

Convergent data model across the strong repos:

    Brief → Script{hook, beats[{narration, on_screen_text, visual_query|asset_ref, duration_hint}], cta}
          → Assets{per beat: file, source, licence, w×h, trimmed_range}
          → Voice{wav per beat + word_timestamps[]}
          → Captions{tokens[{text,startMs,endMs}] → pages[]}
          → Composition (typed template + inputs) → Render → QA report → Variants

Every stage writes a JSON artifact to a run directory so any stage is
re-runnable (ShortGPT's TinyDB idea, MoneyPrinter's queue idea).

| Stage | Zero-API-key path | Quality path |
|---|---|---|
| Brief → Script | Local LLM emitting the schema; hook ≤10 words; manual approval gate | Claude/GPT with the same schema; VLM pass over product footage |
| Assets | Own footage via Playwright at 1080x1920 + FLUX.2 klein stills; Pexels/Pixabay need a free key | Same plus 1–2 generative hook shots (Wan 2.2 / LTX-2 locally) |
| Voice | Kokoro | Chatterbox or Qwen3-TTS; ElevenLabs for brand voices |
| Captions | faster-whisper over the generated audio | whisperX alignment, or ElevenLabs timestamps |
| Composition | HyperFrames, or ASS karaoke burned by ffmpeg | Remotion where the licence fits; Revideo for MIT typed inputs |
| Render | ffmpeg libx264 crf 18–20, yuv420p, 30 fps, faststart, AAC 192k; sidechain ducking | Same; Lambda fan-out |
| QA | ffprobe, two-pass loudnorm, PySceneDetect pacing, caption bbox inside safe zone, hook text in frames 0–90, CTA in last 3 s, no silence >1.5 s | Add a VLM frame-grid review |
| Variants | Matrix over hook line × voice × music × caption theme; shared beats cached | Per-platform re-exports and per-language dubs |

Recommendation: HyperFrames (composition) + Kokoro (voice) +
faster-whisper/whisperX (word timing) + Pexels/Playwright (assets) + ffmpeg
(render, ducking, loudnorm) + PySceneDetect/ffprobe (QA), adopting
MoneyPrinterTurbo's `{narration, search_terms}` beat schema and Remotion's
caption token→pages model as interchange formats; Remotion only where its
licence fits; Chatterbox/ElevenLabs when the brief demands a branded voice.
