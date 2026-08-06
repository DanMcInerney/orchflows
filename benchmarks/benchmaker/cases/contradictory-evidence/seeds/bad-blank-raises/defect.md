Near-miss. Honors the settled side for the literal empty string and takes the
rejected side for a whitespace-only specification, which is the form a config
file actually produces (`listen_ports: " "`). Both documents agree that
whitespace around a token is ignored, so a blank specification names no ports
and settling the empty case settles this one with it. A benchmark that
transcribed the settled decision as the single case `parse_ports("") == []`
scores this variant clean; only one that carried the decision as a boundary --
no ports named, whatever the whitespace -- catches it. It also probes whether
a settled assumption was recorded as a rule or as one literal.
