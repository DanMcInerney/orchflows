# Meeting scheduling interface

An assistant is given one meeting request: who must attend, each person's work hours and busy time, optional rooms, constraints and a preference. It books one slot that satisfies every rule, or says that none exists.

A solver is an agent directory as defined in `interface/package.md`. A task's workspace contains `input.json` in its root; the solver writes `output.json` in the same place. A task conforms when its `input.json` follows this page and its instruction tells the solver to read `input.json` and write `output.json`. Anything not on this page does not affect correctness, and a task must not rely on it.

## input.json

```json
{"duration_minutes": 30, "granularity_minutes": 15,
 "window": {"start": "2026-10-05T07:00+00:00", "end": "2026-10-05T17:00+00:00"},
 "participants": [
   {"id": "ana", "utc_offset": "+02:00", "required": true,
    "work_hours": [{"days": ["Mon"], "start": "09:00", "end": "17:00"}],
    "busy": [{"start": "2026-10-05T09:00+02:00", "end": "2026-10-05T10:00+02:00"}]},
   {"id": "bo", "utc_offset": "-05:00",
    "work_hours": [{"days": ["Mon"], "start": "05:00", "end": "13:00"}], "busy": []}],
 "rooms": [],
 "constraints": [{"type": "not_before", "participant": "bo", "time": "06:30"}],
 "preference": "earliest"}
```

| Field | Meaning |
| --- | --- |
| `duration_minutes` | Meeting length, a positive integer. |
| `granularity_minutes` | Positive integer, default 15. |
| `window.start`, `window.end` | The meeting must lie inside `[start, end]`. |
| `participants[]` | Non-empty. Each has `id` (unique, non-empty string), `utc_offset` (`+HH:MM` or `-HH:MM`) and `work_hours[]`, all required; `required` (boolean, default true; at least one participant must be required); `busy[]` (`{start, end}` timestamps, default none). A `work_hours[]` entry is `{days, start, end}` with `days` from `Mon` to `Sun` and `start`, `end` as `HH:MM` local time (`end` may be `24:00`). |
| `rooms[]` | Optional. Each has `id` (unique, non-empty string) and `capacity` (integer); `features[]` (strings) and `busy[]` are optional. |
| `constraints[]` | Optional. Each has a `type` from the list below and a `participant` that is one of the ids (except `room_feature`). A task using any other type does not conform. |
| `preference` | `earliest`, `latest` or `any`. |

Unknown keys are ignored. Timestamps are ISO 8601 with an explicit offset, `YYYY-MM-DDTHH:MM` plus `+HH:MM`, `-HH:MM` or `Z`, on whole minutes. Offsets are fixed: there are no time-zone names and no daylight-saving changes.

## Rules

- **Instants.** Timestamps are compared as instants, never as text: `2026-10-05T13:30+02:00` and `2026-10-05T11:30+00:00` are the same time.
- **Slots.** A slot is the half-open interval `[start, start + duration_minutes)`. Valid starts are `window.start + k * granularity_minutes` for whole `k >= 0`, with the slot entirely inside the window (it may end exactly at `window.end`).
- **Busy time** is half-open. A slot conflicts with a busy interval when they share at least one minute; a slot that ends exactly when a busy interval starts, or starts exactly when it ends, does not conflict.
- **Work hours** apply in each participant's own `utc_offset`. The participant's working time is the union of the entries whose `days` contain the local weekday; every minute of the slot must be working time, and a participant with no entries never works.
- **Required participants.** Every required participant must be free, within work hours and satisfy their constraints. A participant with `required: false` never restricts the slot: their work hours, busy intervals and constraints are ignored.
- **Constraints**, evaluated in the named participant's local time and local dates:
  - `not_before` with `time` (`HH:MM`): the slot starts no earlier than `time` on the local date of its start.
  - `not_after` with `time`: the slot ends no later than `time` on the local date of its start.
  - `not_before` and `not_after` may carry `day` (`YYYY-MM-DD`, a local date) and then apply only to slots that start on that date.
  - `avoid_day` with `day`: the slot does not overlap that local calendar day.
  - `buffer_minutes` with `minutes`: every busy interval of the participant ends at least `minutes` before the slot starts or starts at least `minutes` after it ends.
  - `room_feature` with `feature`: the booked room has that feature.
- **Rooms.** When `rooms` is non-empty the output names a room that has no busy conflict with the slot, whose `capacity` is at least the number of required participants and that has every `room_feature` feature. Without rooms, `room` is ignored.
- **Preference.** `earliest` wants the valid slot with the earliest start, `latest` the latest start, `any` accepts every valid slot. The choice of room never affects optimality.
- **Infeasible.** When no valid slot exists the output is `{"infeasible": true, "explanation": "..."}` with a non-empty explanation. Claiming infeasibility while a valid slot exists is wrong.

## output.json

```json
{"start": "2026-10-05T11:30+00:00", "end": "2026-10-05T12:00+00:00"}
```

or `{"infeasible": true, "explanation": "..."}`. A UTF-8 JSON object. `start` and `end` are timestamps in any offset; with rooms, add `"room": "<room id>"`; unknown keys are ignored. When `infeasible` is true the other keys are ignored.

## What a task's checker must decide

- **Full success:** the output is a valid slot that is optimal for `preference`, or a correct infeasibility answer.
- **Valid but not optimal** (`earliest` or `latest` with another valid slot better): correct but suboptimal. A checker may award partial credit; it must not award full success.
- **Wrong:** a violated rule, a start off the grid, a duration other than `duration_minutes`, a missing room when rooms exist, an infeasibility answer without an explanation or while a valid slot exists, a slot for an infeasible request, or an unreadable output.

A checker must give the same verdict to outputs that name the same instants with different offsets, key order, whitespace or extra keys.
