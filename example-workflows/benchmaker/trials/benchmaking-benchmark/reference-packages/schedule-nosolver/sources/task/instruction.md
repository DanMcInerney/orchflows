# <<TITLE>>

<<REQUEST>>

Read `input.json` in the current folder and write your answer to `output.json` in the same folder.

## How to read `input.json`

- `duration_minutes` is the meeting length and `granularity_minutes` (default 15) the step between possible starts. The meeting is the half-open interval from its start up to, not including, its end. Its start must be `window.start` plus a whole number of steps, and the whole meeting must lie inside `window` (it may end exactly at `window.end`).
- Each participant has a `utc_offset`, `work_hours` and `busy` intervals. Work hours are `HH:MM` in that participant's own local time on the listed weekdays (`24:00` is midnight); working time is the union of all entries for a local weekday, so it can continue across midnight. Every minute of the meeting must be working time for each required participant.
- `busy` intervals are half-open too: a meeting that ends exactly when a busy interval starts, or starts exactly when it ends, does not conflict. Timestamps carry explicit offsets and are different spellings of the same instants when they name the same moment; offsets are fixed, with no daylight saving.
- A participant with `"required": false` never restricts the meeting: ignore their work hours, busy intervals and constraints. Every other participant is required.
- `constraints` apply to the named required participant, in that participant's local time and local dates. `not_before` with `time`: the meeting starts no earlier than `time` on the local date it starts. `not_after` with `time`: it ends no later than `time` on the local date it starts. Both may carry a `day` (a local date) and then apply only to meetings that start on that date. `avoid_day` with `day`: the meeting must not overlap that local calendar day at all. `buffer_minutes` with `minutes`: every busy interval of that participant must end at least that many minutes before the meeting starts or start at least that many minutes after it ends. `room_feature` with `feature`: the booked room must have that feature.
- If `rooms` is not empty, book a room that is free for the whole meeting, whose `capacity` is at least the number of required participants and that has every `room_feature` feature. Rooms have their own `busy` intervals.
- `preference` is `earliest`, `latest` or `any`: book the valid start that is earliest or latest, or any valid start.

## What to write

A JSON object in `output.json`:

```json
{"start": "2026-10-05T11:30+00:00", "end": "2026-10-05T12:00+00:00", "room": "r1"}
```

`start` and `end` are ISO 8601 timestamps with an offset, in any offset, on whole minutes. Include `room` only when `input.json` lists rooms. If no meeting satisfies every rule, write `{"infeasible": true, "explanation": "..."}` with a short explanation of why nothing fits; never declare a request infeasible while a valid meeting exists.
