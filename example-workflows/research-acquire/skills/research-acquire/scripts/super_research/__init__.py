"""Keyless-first acquisition core for the ``super-research`` skill.

Reliability bar: the Python 3.9 floor, nothing imported beyond the
standard library and what ``requirements.txt`` beside the item declares,
and no I/O of any kind at import time. Every network touch is funnelled through
``super_research.transport``, which re-exports the route constants
``super_research.routes`` declares and so stays the one address they are
reached at; tests reach the seams by injecting an offline opener.
"""
