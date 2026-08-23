"""Support modules for ``tools/run_required.py``.

The facade owns the command plan, the phases and the exit mapping; these
modules own the two things that must be exactly right for a memo to be
honest -- what the working tree currently is, and where a verdict for that
tree is allowed to be stored.
"""
