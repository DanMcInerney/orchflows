# Volume pricing guide

`pricing.py` prices one order line. Everything is integer cents; the
tool never returns a fraction.

    python pricing.py <units> <unit_cents>

## Bands

Bands are graduated — each unit bills at the rate of the band it falls
in, not at one rate for the whole order.

| units | band | rate |
| --- | --- | --- |
| 1-9 | starter | list price |
| 10-49 | volume | 10% off list |
| 50 and up | bulk | 25% off list |

Each band's subtotal is computed on that band's units alone and
floored to the cent (fractions of a cent are dropped, never rounded
up). The order total is the sum of the band subtotals.

## Worked examples

| units | unit cents | total cents |
| --- | --- | --- |
| 1 | 250 | 250 |
| 9 | 250 | 2250 |
| 10 | 250 | 2475 |
| 25 | 1000 | 23400 |
| 50 | 400 | 18300 |

Reading the third row: nine units bill at 250 (2250) and the tenth
unit bills at 10% off (225), so the order totals 2475.

## Errors

Zero or negative units, or a zero or negative list price, raise
`ValueError`.
