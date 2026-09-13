# Production capabilities

Checked 2026-09-13 in this Windows workspace before game implementation.

- Reused the disposable tool probe from the earlier workflow trial at `C:/Users/danhm/tmp/orchflows-game-trial-20260912/probe`; its game scaffold is not reused.
- Node 24.15.0 / npm 11.12.1 are available. Vite production preview served the built Three.js r186 probe on 127.0.0.1:4179.
- Blender 5.2.1 LTS successfully reran `export_probe.py`, saved editable `probe.blend` and exported `public/probe.glb`. The existing identical probe GLB rendered through Three.js in the in-app browser.
- Confirmed the newly exported GLB and served `dist/probe.glb` have identical SHA-256 `3f5b851f4b6fa3eca0ea3e3eea6a7a97536fce8ee346edfcbe45a51c7f42bb11`.
- Browser observed GLB ready. An ordinary ArrowRight press produced keydown and keyup and moved x from 0 to 0.18. Cruise right advanced continuously to x=3; Stop released it; camera orbit and Pause controls operated. A rendered screenshot was captured and inspected.
- The browser adapter exposes single key presses, not a physical held-key API. Use ordinary click-to-move for sustained game movement, keyboard support for people, and a separate visible development panel for diagnostic stepping/scenarios. Read-only page evaluation is only for observations.
- Initial browser runtime setup timed out; retrying the supported setup succeeded. Each worker must use its own tab and read the browser skill/runtime documentation.
- Audio is not yet verified; verify generated audio interaction during production if included. This probe establishes rendering/input/export, not game performance or physical device coverage.
- Windows reports NVIDIA GeForce RTX 5090 Laptop GPU (driver 32.0.16.1062) and Intel Graphics (32.0.101.6733). This inventory does not establish which adapter the browser uses; record its actual WebGL backend with gameplay measurements.
- While the frozen core was under independent review, a disposable Blender source-render probe also passed: Blender 5.2.1 opened the earlier probe `.blend`, rendered a 384×384 Cycles CPU image at 16 samples, and saved it successfully. Caller opened and inspected the image. Script/image are in `C:/Users/danhm/tmp/orchflows-game-validation-20260913/`. This establishes the source contact-render route ahead of asset production; no game model was produced or altered.
