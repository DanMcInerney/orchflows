#!/usr/bin/env python3
"""Volume-tier order pricing in integer cents.

Bands are graduated, like tax brackets: the first 9 units bill at list
price, the next 40 units bill at 10% off, every unit past 49 bills at
25% off. Each band's subtotal is floored to the cent.
"""
from __future__ import annotations

import sys

BAND_ONE_UNITS = 9
BAND_TWO_UNITS = 40
BAND_TWO_PERCENT = 10
BAND_THREE_PERCENT = 25


def total_cents(units: int, unit_cents: int) -> int:
    """Order total in cents for `units` at list price `unit_cents`."""
    if units <= 0 or unit_cents <= 0:
        raise ValueError("units and unit_cents must be positive")
    if units > BAND_ONE_UNITS + BAND_TWO_UNITS:
        percent = BAND_THREE_PERCENT
    elif units > BAND_ONE_UNITS:
        percent = BAND_TWO_PERCENT
    else:
        percent = 0
    return (units * unit_cents * (100 - percent)) // 100


def main(argv) -> int:
    if len(argv) != 2:
        print("usage: pricing.py <units> <unit_cents>", file=sys.stderr)
        return 2
    print(total_cents(int(argv[0]), int(argv[1])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
