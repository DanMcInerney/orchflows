# <<TITLE>>

<<REQUEST>>

You are working in the team's calendar folder, the current folder. The same request is in `request.json`. Book the meeting under the team's booking policy in `policy.md` by editing the calendar files, then write `result.json`.

## What is in the folder

- `request.json`: the meeting to book: `attendees`, `optional` invitees, `duration_minutes`, `granularity_minutes` (default 15), `window`, `preference` (`earliest`, `latest` or `any`), `priority` (`normal` or `urgent`) and `title`.
- `policy.md`: the rules every booking follows (`policy.json` holds the same rules for programs; do not edit either).
- `calendars/<person>.json`: one file per person, named by their id. It holds `utc_offset`, `work_hours` (`HH:MM` in the person's local time on the listed weekdays; `24:00` is midnight) and `events`, the entries `{"id", "title", "kind", "start", "end"}`. `kind` is `focus` for a focus block and anything else for an ordinary entry.
- `rooms/<room>.json`, when present: one file per room, with `capacity`, `features` and `events`.

## Recording the booking

- Add one new entry to the calendar file of every attendee and, when the folder has rooms, to the booked room's file: `{"id": "<new id>", "title": "<title>", "kind": "meeting", "start": "...", "end": "..."}`. Use one id that no entry in those files already has, the same in all of them; `start` and `end` are the booked slot, in any offset. Files of invited (optional) people may receive the same entry; no other file may change.
- Every existing entry must stay exactly as it is, and so must everything else in a file (`utc_offset`, `work_hours`, `capacity`, `features`). Do not delete or rewrite a file in a way that drops anything.
- Write `result.json`: `{"booked": {"start": "...", "end": "...", "room": "<room id>", "event_id": "<the id you used>"}}`, leaving out `room` when the folder has no rooms.
- If no valid time exists, change no file and write `{"infeasible": true, "explanation": "..."}` with a short explanation of what blocks every candidate. Never declare a request infeasible while a valid time exists.
