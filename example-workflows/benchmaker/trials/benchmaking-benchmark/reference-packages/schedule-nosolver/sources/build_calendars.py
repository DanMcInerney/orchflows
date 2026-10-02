"""Building blocks for synthetic scheduling instances: casts, work-hour templates, calendars and squeezing.

`synthesize.py` composes these into the committed offline instances. A cast is a team: people with a UTC offset, a
work-hours template and habits (lunch, stand-up). `squeeze` adds believable meetings for the required participants
until only a handful of valid starts remain, so a guess at a start almost never works.
"""
from datetime import datetime, time, timedelta, timezone

DAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
WEEK = ["Mon", "Tue", "Wed", "Thu", "Fri"]

HOURS = {
    "standard": [{"days": WEEK, "start": "09:00", "end": "17:00"}],
    "early": [{"days": WEEK, "start": "07:30", "end": "15:30"}],
    "late": [{"days": WEEK, "start": "10:30", "end": "19:00"}],
    "split": [{"days": WEEK, "start": "08:30", "end": "12:30"}, {"days": WEEK, "start": "14:00", "end": "18:00"}],
    "four-day": [{"days": ["Mon", "Tue", "Wed", "Thu"], "start": "09:00", "end": "17:30"}],
    "three-day": [{"days": ["Tue", "Wed", "Thu"], "start": "09:00", "end": "17:00"}],
    "part-time": [{"days": ["Tue", "Thu"], "start": "09:00", "end": "17:00"}, {"days": ["Wed"], "start": "09:00", "end": "13:00"}],
    "clinic": [{"days": WEEK, "start": "08:00", "end": "18:00"}, {"days": ["Sat"], "start": "09:00", "end": "13:00"}],
    "evening": [{"days": WEEK, "start": "14:00", "end": "24:00"}],
    "night": [{"days": ["Sun", "Mon", "Tue", "Wed", "Thu"], "start": "22:00", "end": "24:00"},
              {"days": WEEK, "start": "00:00", "end": "06:00"}],
    "flexible": [{"days": WEEK, "start": "07:00", "end": "11:30"}, {"days": WEEK, "start": "15:30", "end": "19:30"}],
}

CASTS = {
    "platform-eng": [("ana", "-07:00", "standard"), ("ben", "-04:00", "standard"), ("cho", "+01:00", "standard"),
                     ("dev", "+05:30", "late"), ("eli", "+09:00", "early"), ("fay", "+02:00", "standard")],
    "emea-sales": [("gus", "+01:00", "standard"), ("hana", "+02:00", "standard"), ("ivo", "+03:00", "standard"),
                   ("jo", "+04:00", "early"), ("kim", "+02:00", "split"), ("lee", "+00:00", "standard")],
    "design-studio": [("mia", "-03:00", "flexible"), ("ned", "+01:00", "part-time"), ("ola", "-06:00", "four-day"),
                      ("pia", "-05:00", "standard"), ("quin", "+01:00", "standard"), ("ria", "+05:45", "late")],
    "clinic-ops": [("sam", "+10:30", "clinic"), ("tia", "+10:30", "clinic"), ("uli", "+10:30", "evening"),
                   ("val", "+10:30", "split"), ("wes", "+10:30", "night"), ("xia", "+10:30", "standard")],
    "exec-office": [("yan", "-04:00", "standard"), ("zed", "-04:00", "late"), ("abe", "+01:00", "standard"),
                    ("bea", "+01:00", "early"), ("cal", "+08:00", "standard"), ("dax", "-07:00", "standard")],
    "field-teams": [("fox", "+11:00", "standard"), ("gil", "+13:00", "early"), ("hux", "+10:30", "standard"),
                    ("ian", "+09:30", "standard"), ("jax", "+08:00", "late"), ("kat", "+05:30", "standard")],
}

MONDAY = datetime(2026, 10, 5)


def zone(text):
    sign = -1 if text[0] == "-" else 1
    return timezone(sign * timedelta(hours=int(text[1:3]), minutes=int(text[4:6])))


def stamp(moment, tz=None):
    return (moment.astimezone(tz) if tz else moment).isoformat(timespec="minutes")


def local(day, clock, tz):
    """Aware datetime at local `clock` ("HH:MM") on date `day` in zone tz."""
    hours, minutes = clock.split(":")
    return datetime.combine(day, time(), tzinfo=tz) + timedelta(hours=int(hours), minutes=int(minutes))


def person(pid, template=None, **extra):
    name, off, hours = next(c for cast in CASTS.values() for c in cast if c[0] == pid)
    return {"id": name, "utc_offset": off, "work_hours": [dict(w) for w in HOURS[template or hours]], "busy": [], **extra}


def working_days(p, day):
    return [w for w in p["work_hours"] if DAYS[day.weekday()] in w["days"]]


def add_busy(p, start, end, utc=False):
    """Add [start, end) in the person's own offset, or as UTC when the calendar is an export in UTC."""
    tz = timezone.utc if utc else zone(p["utc_offset"])
    p["busy"].append({"start": stamp(start, tz), "end": stamp(end, tz)})


def fill_calendar(rng, p, first_day, days, per_day, habits, utc=False, avoid=()):
    """Meetings, lunch, stand-up and the odd absence on the person's working days; `avoid` keeps spans clear."""
    tz = zone(p["utc_offset"])
    for n in range(days + 2):
        day = first_day + timedelta(days=n - 1)
        spans = working_days(p, day)
        if not spans:
            continue
        slots = []
        if "standup" in habits and rng.random() < 0.8:
            slots.append((local(day, spans[0]["start"], tz) + timedelta(minutes=30), 15))
        if "lunch" in habits and rng.random() < 0.8 and spans[0]["end"] > "13:00":
            slots.append((local(day, rng.choice(["12:00", "12:30"]), tz), 60))
        for _ in range(rng.randint(*per_day)):
            w = rng.choice(spans)
            lo = int((local(day, w["start"], tz) - local(day, "00:00", tz)).total_seconds() // 60)
            hi = int((local(day, w["end"], tz) - local(day, "00:00", tz)).total_seconds() // 60)
            length = rng.choice([30, 30, 45, 60, 60, 90])
            if hi - lo <= length:
                continue
            begin = lo + 15 * rng.randrange(0, (hi - lo - length) // 15 + 1)
            slots.append((local(day, "00:00", tz) + timedelta(minutes=begin), length))
        for begin, length in slots:
            end = begin + timedelta(minutes=length)
            if not any(begin < b and a < end for a, b in avoid):
                add_busy(p, begin, end, utc)
    p["busy"].sort(key=lambda b: datetime.fromisoformat(b["start"]))


def time_off(rng, p, day, tz=None):
    """A whole working day away, expressed as the person's calendar would."""
    tz = tz or zone(p["utc_offset"])
    add_busy(p, local(day, "00:00", tz), local(day, "00:00", tz) + timedelta(days=1))


def rooms(*specs):
    return [{"id": i, "capacity": c, "features": list(f), "busy": []} for i, c, f in specs]


def fill_rooms(rng, inst, first_day, days, per_day=(1, 3), avoid=()):
    tz = datetime.fromisoformat(inst["window"]["start"]).tzinfo
    for r in inst["rooms"]:
        for n in range(days):
            day = first_day + timedelta(days=n)
            for _ in range(rng.randint(*per_day)):
                begin = local(day, "00:00", tz) + timedelta(minutes=60 * rng.randint(8, 16) + 15 * rng.randint(0, 3))
                end = begin + timedelta(minutes=rng.choice([30, 60, 90, 120]))
                if not any(begin < b and a < end for a, b in avoid):
                    r["busy"].append({"start": stamp(begin), "end": stamp(end)})
        r["busy"].sort(key=lambda b: datetime.fromisoformat(b["start"]))


def squeeze(rng, oracle, inst, ceiling, keep=(), tries=400):
    """Add meetings for required participants until at most `ceiling` valid starts remain; never touch the starts in `keep`.

    Returns the final list of valid starts. A block that would remove every valid start, or a kept one, is undone."""
    model = oracle.read(inst)
    starts = [s for s, _ in oracle.valid_starts(inst)]
    required = [p for p in inst["participants"] if p.get("required", True)]
    by_id = {p["id"]: p for p in model["people"]}
    step = inst.get("granularity_minutes", 15)
    for _ in range(tries):
        if len(starts) <= ceiling:
            break
        target = rng.choice([s for s in starts if s not in keep] or starts)
        owner = rng.choice(required)
        tz = zone(owner["utc_offset"])
        length = rng.choice([30, 45, 60, 90])
        local_begin = target.astimezone(tz) - timedelta(minutes=step * rng.randint(0, max(0, length // step - 1)))
        begin = local_begin.replace(minute=local_begin.minute - local_begin.minute % 15, second=0, microsecond=0)
        end = begin + timedelta(minutes=length)
        add_busy(owner, begin, end)
        by_id[owner["id"]]["busy"].append((begin, end))
        remaining = [s for s in starts if oracle.blocked(by_id[owner["id"]], s, s + model["duration"]) is None]
        if not remaining or any(k not in remaining for k in keep):
            owner["busy"].pop()
            by_id[owner["id"]]["busy"].pop()
            continue
        starts = remaining
    owner_busy_sort(inst)
    return starts


def owner_busy_sort(inst):
    for p in inst["participants"]:
        p["busy"].sort(key=lambda b: datetime.fromisoformat(b["start"]))


def window(start, days, tz, extra_minutes=0):
    return {"start": stamp(start, zone(tz) if isinstance(tz, str) else tz),
            "end": stamp(start + timedelta(days=days, minutes=extra_minutes), zone(tz) if isinstance(tz, str) else tz)}


def grid_size(inst):
    lo, hi = datetime.fromisoformat(inst["window"]["start"]), datetime.fromisoformat(inst["window"]["end"])
    return int((hi - lo - timedelta(minutes=inst["duration_minutes"])) / timedelta(minutes=inst.get("granularity_minutes", 15))) + 1


