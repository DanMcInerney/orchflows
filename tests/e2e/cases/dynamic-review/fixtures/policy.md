# Export authorization

Inputs are values decoded from JSON with the standard decoder. Custom Python objects and subclasses are outside this interface.

Allow export only when the role is exactly `owner` or `analyst`, authenticated is the boolean `True`, and suspended is the boolean `False`. Return the boolean `False` for every other combination, including unknown or missing roles and non-boolean authentication or suspension values. Truthy integers are not boolean authorization signals.
