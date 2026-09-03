---
name: fps-design
description: Stamp when the document being written is the design brief for a one-room first-person browser game.
packs: [orch-content-pack, orch-design-pack]
---

# fps-design

## Craft

A brief for a one-room first-person game fixes four things and leaves the
rest to the build. Each is a decision someone can disagree with, written so
a maker can execute it and a judge can read it off the running game.

- **The level, in measurements.** The room's extent in metres, the eye
  height, and every piece of blocking geometry by position and size. "A
  crypt" is a mood, not a level; a maker handed it invents the room and the
  judge has nothing to compare it against
  ([references/reference-brief.md](references/reference-brief.md)).
- **What blocks, and what it blocks.** Each wall, pillar or prop is named
  as blocking movement, blocking sight, or neither, and the room is closed:
  the player cannot leave it in any direction. The brief states the
  intended failure — the player walks into a wall and stops — because that
  is the sentence a probe can be written from.
- **Input, key by key.** Every control the player has, named by its
  physical key or button and by what it does, in a table. The mouse is a
  separate row, and the brief says what happens when the browser refuses
  the pointer lock: the game keeps playing on the keyboard and says so in
  the page ([references/reference-brief.md](references/reference-brief.md)).
- **Feel, as figures.** Move speed in metres per second, turn sensitivity,
  and the frame budget the build answers to. An adjective — "snappy",
  "weighty" — is not a target; the same adjective is met by two builds that
  play nothing alike.
- **What is out, named.** Everything a reader would reasonably expect and
  will not get: enemies, sound, saved progress, mobile support. An
  unstated absence is read as an omission by the maker and as a defect by
  the judge.
- **One vertical slice, not a plan.** The brief describes the state the
  player reaches on the first load: the page opens, the level starts, the
  player moves. Anything reachable only later belongs in a successor line
  at the end, not in the body.

## Lens

### doc

- Measurements: room extent, eye height and every blocking element carry
  numbers with units. An adjective in place of a figure is a finding.
- Blocking: each element is labelled as blocking movement, sight or
  neither, and the brief states the room is closed. Count the elements
  against the labels.
- Input: a table with one row per control, the mouse on its own row, and a
  stated behaviour when pointer lock is refused. A missing row is a
  finding.
- Feel: move speed, sensitivity and frame budget are figures with units.
- Exclusions: a section naming what is out. An empty one is a finding;
  silence about scope is not the same as nothing being out.
- Slice: every sentence in the body describes the first load. A sentence
  about a later entry belongs under the successor line.

### git

- The room the build ships matches the brief's measurements within the
  tolerance the brief states, read from the level's own source constants.
- Every blocking element the brief names exists and blocks what the brief
  said it blocks; the probe walks into one and the reported position
  stops.
- Every input row the brief names is bound in the running build, and the
  refused-pointer-lock behaviour the brief states is what the page does.
- The move speed and frame budget the brief fixed are the ones the build
  measures and the probe asserts, not different figures.
- Nothing the brief named as out is in the revision; a shipped extra is a
  finding against the brief or the build, and the judge says which.
