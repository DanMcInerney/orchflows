---
name: booking-rules
description: Book a meeting into the team's calendar files under the booking policy. Use when asked to schedule, book or find a time for a meeting by editing the calendars/ and rooms/ files of a workspace that has request.json and policy.md.
---

# Booking rules

How the calendar team books a meeting. `policy.md` in the workspace is the policy; this skill is how we apply it.

## The workspace

- `request.json`: attendees, optional invitees, duration, window, granularity, preference and priority.
- `calendars/<person>.json` and `rooms/<room>.json`: the entries of each person and room. A calendar also holds the person's `utc_offset` and `work_hours`; a room holds its `capacity` and `features`.
- `policy.json` holds the rules and `policy.md` is generated from it. Read `policy.md`; never edit either.

## Rules we apply

- Every required attendee must be inside their work hours, in their own `utc_offset`, and free. Optional invitees never restrict the time.
- Start times lie on the request's granularity grid, counted from the start of the window, and the meeting ends inside the window.
- **Buffers.** `buffer_minutes` in `policy.json` is a gap: keep at least that many minutes between the new meeting and every other entry on each required attendee's calendar, on both sides.
- With rooms, book one that is free for the whole meeting and seats every required attendee.
- Honour `preference`: the earliest or the latest valid start; `any` takes any valid start.

## Recording the booking

Add one new entry with a unique id to each required attendee's calendar and to the room's file. Leave every existing entry exactly as it is. Then write `result.json` as `{"booked": {"start", "end", "room", "event_id"}}`, or `{"infeasible": true, "explanation": "..."}` when no valid start exists, and book nothing.

## Helper

`scripts/free_slots.py` in this skill's directory lists candidate starts, earliest first, with the rooms free and large enough for each:

```
python free_slots.py --workspace . --limit 10
python free_slots.py --workspace . --latest
```

It applies the busy, work-hours, grid and buffer rules above. It is a starting point, not the whole policy.

## Not covered

- **Room features.** A `room_feature` rule in `policy.json` requires a feature when enough people attend. The helper lists rooms by capacity and availability only; check `features` in the room files yourself.
- **Focus-block exceptions.** The helper treats focus entries (`"kind": "focus"`) like any other busy time. When the policy lets an urgent request book over focus blocks, work that out yourself.
