# tiktok-video rules

The craft every call in the `tiktok-video` workflow reads: what a TikTok
marketing video has to be for the platform's own data to favour it, stated
as checks. Sources are TikTok's Creative Codes, its creative best-practice
help article, its conversion study over auction ads, and the in-feed ad
specification, read 2026-09-02; marketer benchmarks are marked as such.
The script judge reads §§1–4 and §8; the render judge §§5–7 and §9; the
spec probe reads only §7.

## 1. The hook, 0–3 s

TikTok's structure code is hook, body, close, and its help article puts
the offer inside the first three seconds and holds attention through the
first six; ninety percent of ad recall lands in those six. The viewer's
decision falls between one and three seconds, and TikTok's own hook metric
is the two-second view.

- A hook is spoken, on screen and visual at once. Its text is eight words
  or fewer; its visual stimulus — a face meeting the lens, the product in
  motion, or the result shown first — is in frame by one second.
- Archetypes a script names and a judge recognises: pattern interrupt,
  result first, direct address or POV, bold or contrarian claim, curiosity
  question, qualified "stop scrolling if", text tease with an open loop.
  A pattern interrupt disconnected from the body wins the first second
  and loses completion; the result-first open holds three-second
  retention best (marketer studies).
- Nothing opens on a logo, slate, title card, black frame or silence.

## 2. Structure by length

TikTok's conversion study: 21–34 s ads lifted conversion 280 percent over
shorter and longer; multiple scenes lifted it 38 percent; text on screen
inside seven seconds, 43 percent. Cold audiences fall off sharply past
60 s; the paid-policy ceiling is 60 s, so 61–120 s is for explainers,
tutorials, founder stories and retargeting only, and only when `goal`
says so.

| length | use | beats | scenes | voice words |
| --- | --- | --- | --- | --- |
| 6 s | awareness bumper, reminder | hook visual + text; one benefit with the product; brand + CTA | 2–3 | ≤ 15 |
| 15 s | awareness, impulse, install | hook 0–2; context 2–5; demo 5–12; CTA 12–15 | 5–8 cuts | 28–42 |
| 30 s | conversion, the default | hook 0–3; problem 3–10; solution and proof 10–25; CTA and offer 25–30 | ≥ 5 scenes, 10–15 cuts | 60–84 |
| 60 s | consideration, mechanism, comparison | as 30 s with story 13–28 and proof 48–55; re-hook near 20 s and 40 s | 20–35 cuts | 130–160 |
| 120 s | explainer, tutorial, warm retarget | three chapters each opened by a text re-hook; payoff before 60 s; CTA teased near 40 s, closed 110–120 s | ≥ 40 cuts | 250–300 |

Defaults when `length` is a band: conversion 21–34 s, awareness 9–15 s.
Body shots run 1.5–3 s; no shot exceeds 5 s without a punch-in, a caption
change or a b-roll insert; every video past 30 s re-hooks every 15–20 s.

## 3. Script formulas

A script names one formula and its beats fall inside the table above:
problem–agitate–solution–proof–CTA; attention–interest–desire–action;
problem–solution–demo–CTA, the default ad shape; before–after–bridge,
after shown first; the numbered list, one scene per item; tutorial,
outcome promised then steps then result; testimonial or skeptic, low
expectation then surprise then invitation. Each beat carries its
narration, its on-screen text, its visual and its seconds; the product or
offer is visible or named by three seconds and on screen for at least
thirty percent of the runtime.

## 4. The close

Text CTAs lifted conversion 152 percent and CTA cards lifted recall 45
percent in TikTok's study. The close is the last three to five seconds:
a spoken line and a two-or-three-word on-screen action verb that matches
the button label TikTok offers (Shop Now, Learn More, Sign Up, Download,
Order Now, Book Now). No "swipe up", no drawn button, no induced gesture —
policy rejects them — and "link in bio" only for a Spark ad, where a
profile exists to tap. Specific beats vague: "free to try, link below"
over "check it out".

## 5. The frame

- Canvas 9:16 at 1080×1920. Vertical lifted conversion 91 percent over
  letterboxed; 720p and above, 312 percent.
- Safe box: x 60–940, y 200–1436. The top 200 px carries the tabs and the
  sponsored mark, the right 140 px the action column, the bottom 484 px
  the account, caption, sound and button. No text or key visual lands
  outside the box; a violation costs about a fifth of completion (marketer
  data over 170k posts).
- Backgrounds behind the UI regions are never white or transparent; the
  UI is white.
- Hierarchy: hook text upper-centre for 0–3 s; benefit callouts
  lower-centre from 3 s; CTA bottom-centre inside the box for the last
  seconds. Brand marks appear only after the hook.
- Native beats polished for cold audiences: TikTok-first creative earns
  3.3× the action. Handheld or selfie framing, natural light, in-app text
  style, jump and zoom cuts; polish is for warm and premium.
- No static stretch past one second without motion or audio; static
  frames stay under half the runtime; no third-party watermark, blurred
  or otherwise.

## 6. Captions

Word-by-word or one-to-three-word pop captions in a bold sans-serif —
TikTok Sans is open source, Montserrat or Inter serve — white with a
black stroke or a highlight colour, lower-middle, never over a face. Cap
height 48 px or more at 1080 wide, stroke or shadow 4 px or more, one to
seven words a chunk, one to three seconds a chunk, at most ten words a
second, breaks at speech pauses. Burn captions in: the platform's own
caption can be hidden and cannot be styled.

## 7. Technical specification

MP4, H.264 video and AAC audio at 48 kHz and 192 kbps or better;
1080×1920; 30 fps, 60 only where motion demands; 6–12 Mbps; under 500 MB.
Duration inside `length`, and inside 5–60 s unless `goal` licenses more.
An audio track is mandatory: voice at −14 LUFS integrated, −1 dBTP true
peak; music 18–25 dB under the voice while it speaks; voice at 140–160
words a minute; no silence past 1.5 s except one deliberate beat before
the CTA. The first frame is the cover: subject and hook text inside the
centre block, not a black or transition frame.

## 8. Variants

Hold the body and swap only the first three seconds: three hook variants
per body, each a different archetype, and a six-second cutdown of the
strongest. The manifest names each variant's archetype and the readings a
marketer takes — two-second and six-second view rates, views at each
quarter, average play time. A near-vertical drop inside 1–3 s is a hook
failure; a good hook losing half by the midpoint is a body failure.

## 9. Render judge findings that block

A blocking finding is one of: any text or key visual outside the safe
box; caption cap height under 48 px or no stroke; a logo, slate or static
frame inside the first three seconds; hook text absent by one second; the
product absent past three seconds; no CTA text in the last five seconds
or a CTA that contradicts the button; a white or transparent UI region;
a watermark; a shot past five seconds with nothing changing. Other
findings are weighed against the goal, not blocking.
