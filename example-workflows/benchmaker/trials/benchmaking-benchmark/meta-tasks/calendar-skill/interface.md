# Team calendar booking interface

An agent books one meeting for a team by editing the calendar files in its workspace. The workspace holds the request, the team's booking policy and one file per person and room. The agent adds the meeting to the right calendars, or says that no valid time exists.

An agent is an agent directory as defined in `interface/package.md`. A task's workspace holds the files below; its instruction, which is the agent's prompt, tells the agent to book the meeting in `request.json` under `policy.md` and to write `result.json`. A task conforms when its workspace follows this page. Anything not on this page does not affect correctness, and a task must not rely on it.

## Workspace

```text
request.json              the meeting to book
policy.json, policy.md    the booking rules; policy.md is rendered from policy.json and says the same
calendars/<person>.json   one file per person; the file name without .json is the person's id
rooms/<room>.json         optional, one file per room; the file name without .json is the room's id
result.json               written by the agent
```

### request.json

```json
{"title": "Q4 planning", "attendees": ["ana", "bo"], "optional": ["dee"],
 "duration_minutes": 60, "granularity_minutes": 15,
 "window": {"start": "2026-10-05T09:00+00:00", "end": "2026-10-09T17:00+00:00"},
 "preference": "earliest", "priority": "normal"}
```

| Field | Meaning |
| --- | --- |
| `attendees` | Non-empty list of person ids who must attend. |
| `optional` | Person ids invited but not required; default none. Disjoint from `attendees`. |
| `duration_minutes` | Meeting length, a positive integer. |
| `granularity_minutes` | Positive integer, default 15. |
| `window.start`, `window.end` | The meeting must lie inside `[start, end]`. |
| `preference` | `earliest`, `latest` or `any`. |
| `priority` | `normal` (default) or `urgent`. |
| `title` | Optional text for the new entries. |

Every id in `attendees` and `optional` has a file in `calendars/`.

### calendars/\<person\>.json and rooms/\<room\>.json

```json
{"utc_offset": "+02:00",
 "work_hours": [{"days": ["Mon", "Tue", "Wed", "Thu", "Fri"], "start": "09:00", "end": "17:00"}],
 "events": [{"id": "ev-1", "title": "Standup", "kind": "meeting",
             "start": "2026-10-05T09:00+02:00", "end": "2026-10-05T09:30+02:00"},
            {"id": "ev-2", "title": "Focus: design", "kind": "focus",
             "start": "2026-10-05T13:00+02:00", "end": "2026-10-05T15:00+02:00"}]}
```

A room file holds `capacity` (integer), `features` (strings, optional) and `events` instead of `utc_offset` and `work_hours`.

- `utc_offset` is `+HH:MM` or `-HH:MM`. A `work_hours[]` entry is `{days, start, end}` with `days` from `Mon` to `Sun` and `start`, `end` as `HH:MM` local time (`end` may be `24:00`).
- Each entry has a unique non-empty string `id`, `start` and `end`, and optionally `title` and `kind`. `kind` is free text; `focus` marks a focus block and any other value is an ordinary entry. Entries end after they start.

### policy.json

```json
{"rules": [{"type": "buffer_minutes", "minutes": 15},
           {"type": "focus_blocks", "urgent_may_override": true},
           {"type": "room_feature", "min_attendees": 4, "feature": "video"}]}
```

A rule type that is absent does not apply. `buffer_minutes` and `focus_blocks` appear at most once; `room_feature` may appear several times. A policy with another rule type does not conform.

Timestamps are ISO 8601 with an explicit offset, `YYYY-MM-DDTHH:MM` plus `+HH:MM`, `-HH:MM` or `Z`, on whole minutes. Offsets are fixed: there are no time-zone names and no daylight-saving changes. Unknown keys are ignored.

## Rules

- **Instants.** Timestamps are compared as instants, never as text: `2026-10-05T13:30+02:00` and `2026-10-05T11:30+00:00` are the same time.
- **Slots.** A slot is the half-open interval `[start, start + duration_minutes)`. Valid starts are `window.start + k * granularity_minutes` for whole `k >= 0`, with the slot entirely inside the window (it may end exactly at `window.end`).
- **Busy time.** Every entry of a person or room is busy time, half-open. A slot conflicts with an entry when they share at least one minute; a slot that ends exactly when an entry starts, or starts exactly when it ends, does not conflict.
- **Work hours** apply in each person's own `utc_offset`. A person's working time is the union of the `work_hours` entries whose `days` contain the local weekday; every minute of the slot must be working time, and a person with no entries never works.
- **Required attendees.** Every person in `attendees` must be within work hours and free. A person in `optional` never restricts the slot: their work hours and entries are ignored.
- **Rooms.** When `rooms/` holds files the booking names a room that has no entry conflicting with the slot, whose `capacity` is at least the number of `attendees`, and that satisfies the applicable `room_feature` rules. Without rooms, no room is booked.
- **`buffer_minutes`.** For each person in `attendees`, every entry of that person ends at least `minutes` before the slot starts or starts at least `minutes` after it ends.
- **`focus_blocks`.** Entries of kind `focus` are busy time like any other. With `urgent_may_override` true and `priority` `urgent`, the focus entries of every person are ignored entirely: they neither conflict with the slot nor count for `buffer_minutes`.
- **`room_feature`.** When at least `min_attendees` people are in `attendees` (default 1), the booked room's `features` include `feature`.
- **Preference.** `earliest` wants the valid slot with the earliest start, `latest` the latest start, `any` accepts every valid slot. The choice of room never affects optimality.
- **Infeasible.** When no valid slot exists the answer is infeasible. Claiming infeasibility while a valid slot exists is wrong.

## Recording a booking

A booking changes the files and writes `result.json`:

- Add one new entry `{"id": "<event_id>", "title": "...", "kind": "meeting", "start": "...", "end": "..."}` to the calendar of each person in `attendees` and to the booked room's file. The `id` is not used by any entry already in the file; `start` and `end` are the slot, in any offset. The files of people in `optional` may receive the same entry too. No other file changes.
- Every existing entry stays: same `id`, `title`, `kind`, instants and other fields. Files keep their `utc_offset`, `work_hours`, `capacity` and `features`, and no file is deleted. The order of entries does not matter.
- Write `result.json` as `{"booked": {"start": "...", "end": "...", "room": "birch", "event_id": "bk-1"}}`, with `room` only when rooms exist and `event_id` the id used in the files. For an infeasible request write `{"infeasible": true, "explanation": "..."}` with a non-empty explanation and change no file.

A UTF-8 JSON file; `start` and `end` are timestamps in any offset; unknown keys are ignored.

## What a task's checker must decide

- **Full success:** the booking is a valid slot that is optimal for `preference`, every file holds it as described, no existing entry was changed, and `result.json` agrees with the files; or the request is infeasible, the answer says so and no file gained an entry.
- **Valid but not optimal** (`earliest` or `latest` with another valid slot better): correct but suboptimal. A checker may award partial credit; it must not award full success.
- **Wrong:** a violated rule, a start off the grid, a duration other than `duration_minutes`, a missing or unknown room when rooms exist, a booking missing from a required attendee's file or the room's file, `result.json` disagreeing with the files, an infeasibility answer without an explanation or while a valid slot exists, a slot for an infeasible request, or an unreadable `result.json`.
- **Critical failure:** an existing entry that was changed or removed, a changed or deleted calendar or room file, or `result.json` reporting a booking that no file holds. A critical failure is never full success, whatever else is right.

A checker must give the same verdict to outputs that name the same instants with different offsets, key order, whitespace or extra keys.
