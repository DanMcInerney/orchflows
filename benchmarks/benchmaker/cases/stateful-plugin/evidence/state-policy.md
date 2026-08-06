# Where the state lives

## One location, named by the caller

The file passed as `--state` holds the entire store. The tool keeps no other
persistent state: no cache beside the module, no file in the working
directory, no entry in the user's home or temp directory, no environment
variable. Deleting the state file returns the store to its initial condition
in full.

That property is what makes the tool safe to run twice: an operator who wants
a clean store removes one file, and a caller who wants two independent stores
passes two paths.

## Encoding

The state file's format is an implementation detail. Two builds that answer
every command identically are equivalent even if their state files differ
byte for byte, so nothing may depend on the file's encoding, key order, or
whitespace.

## What this asks of anything that exercises the tool

Any harness driving the store owns the state location it passes in and is
responsible for removing it afterwards. Two consecutive exercises from clean
state must be indistinguishable: same commands, same outputs, same exit codes.
A difference between the first exercise and the second is a defect in the
tool, not noise in the harness.
