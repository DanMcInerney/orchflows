"""Keyless-first acquisition core for the ``super-research`` skill.

Reliability bar: standard library only on the Python 3.9 floor, and no
I/O of any kind at import time. Every network touch is funnelled through
``super_research.transport``, which is the sole owner of route constants;
tests reach the seams by injecting an offline opener.
"""
