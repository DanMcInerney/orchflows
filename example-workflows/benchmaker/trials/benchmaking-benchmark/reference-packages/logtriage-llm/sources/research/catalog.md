# Research catalog

Sources and scenarios behind the tasks. Retrieval dates are given where this build fetched or checked a source; entries marked "not re-fetched" come from the author's knowledge and are listed so a reviewer can check them.

## Sources

| Source | Used for | Reuse constraint | Checked |
| --- | --- | --- | --- |
| Brandt, Panichella, Beller (2020), *LogChunks: A Data Set for Build Log Analysis*, MSR 2020; data set at https://doi.org/10.5281/zenodo.3632351 (record https://zenodo.org/records/3632351) | Label semantics (a person marks the chunk of text that describes why the build failed); the log byte format (Travis raw logs: CRLF, ANSI sequences, `travis_fold` and `travis_time` markers, carriage-return progress lines); statistics: 797 logs, 80 repositories, 29 languages | CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/); attribute the authors when logs or labels are redistributed. The offline tasks include none of its logs | licence and archive structure checked 2026-10-01 by the metabench material step |
| Travis CI documentation, *Common Build Problems* (https://docs.travis-ci.com/user/common-build-problems/) | The messages Travis prints when a job is stopped: no output for ten minutes, the maximum job time | Public documentation; message text is quoted only as it appears in logs | not re-fetched |
| Beller, Gousios, Zaidman (2017), *Oops, my tests broke the build: An explorative analysis of Travis CI with GitHub*, MSR 2017 | Motivation for the failure families: broken builds are mostly failing tests, followed by other causes such as compilation and dependency problems | Paper | not re-fetched |
| Public documentation of the build tools whose output the tasks show: pytest, Apache Maven Surefire, Jest, RSpec, Go `testing`, Cargo and rustc, GCC and `ld`, CMake, PHPUnit and PHP_CodeSniffer, Composer, pip's resolver, npm 7, Bundler | The shape of each tool's failure report and its ordinary output | Public documentation | not re-fetched |
| Measurements of the LogChunks archive made for this work (the metabench logtriage domain report, 2026-10-01) | Realistic scale: median log 1,598 lines (87 KB, maximum 39,027 lines), median chunk 7 lines, about half of chunks end within the last 50 lines, 43 of 797 chunks occur more than once in their log | Derived counts | 2026-10-01 |

## Scenario catalog

Real triage work separates a reader who finds the cause from one who matches keywords. The patterns below recur in real logs and are what the tasks sample.

| Scenario | Why it is hard | Failure family |
| --- | --- | --- |
| One failing test among hundreds of passing lines | The cause is a short block between thousands of lines of passes; names of passing tests can contain `error` or `failure` | test-failure |
| Failure block far from the end | Coverage tables, warnings, a dumped debug log or more test binaries follow it | test-failure, compile-error |
| Compile or link error at the end of a long build | Warnings before it mention errors; build tools print cascading `Error 2` lines after it | compile-error |
| Resolver conflict reports | The cause is a multi-line report whose closing lines only say the command failed; some reports contain no error keyword | dependency-resolution |
| Stack dumps after a timeout | The cause is the first lines of a dump of hundreds of lines | timeout |
| Platform termination | The cause is a message from the CI platform after long silence, not tool output | timeout |
| Benign errors before the cause | A flaky test that passed on rerun, a `\|\| true` command that printed errors, a style check that does not fail the build | decoy-errors |
| The same report twice | Tools print a failure inline and again in a summary, or to two streams | test-failure, decoy-errors |

## Gaps

- No live research was done for this package; the sources above are the ones already known. Real logs of the scenarios above are available in LogChunks and enter the package through `generate.py --instances <dir>`.
- Other CI systems' log formats (GitHub Actions, GitLab) are not covered.

$coverage
