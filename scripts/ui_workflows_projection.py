"""Phase-A boundary for the current Workflows compatibility payload."""

# Workflows still uses the runs route in Phase A. The facade must not
# register a second owner for that method/path pair.
ROUTE_SPECS = ()
