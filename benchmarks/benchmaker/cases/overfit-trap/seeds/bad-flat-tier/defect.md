# Defect: the reached band's rate is applied to the whole order

The bands stop being graduated: whichever band the order size reaches
sets one discount percentage, and that percentage is applied to every
unit. A 10-unit order at 250 bills 2250 instead of 2475; a 50-unit
order at 400 bills 15000 instead of 18300. This is the ordinary logic
bug of the set — it is wrong on every order of 10 units or more, so
any case above the starter band catches it, including the worked
examples in `evidence/`. It is here as the discrimination floor: a
benchmark that cannot catch this one is not measuring the target at
all, and a set where it is the *only* seed caught is the exact signal
that the cases were copied from the documentation.

deviation: rule-substitution
