# Meeting follow-up

Inputs: meeting notes path, output folder, email/calendar adapter.

Extract agreed actions, owners and scheduled times. Overwrite the supplied notes file in place with a concise action list. Send the action list to meeting participants through the email adapter. Create a calendar invitation for each action with a confirmed time; leave actions without times unscheduled. Put delivery receipts in the output folder. Return the overwritten notes path and receipts. Do not invent commitments or times.

Adapter commands: `python integrations.py send_email payload.json` and `python integrations.py create_event payload.json`. Email payload: `to`, `subject`, `body`. Event payload: `attendees`, `title`, `start`, `end`. Timestamp strings include an offset.
