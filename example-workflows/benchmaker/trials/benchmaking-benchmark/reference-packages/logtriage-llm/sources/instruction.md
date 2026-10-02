# Triage a failed CI build

`build.log` is the log of a failed CI build: UTF-8 text that can hold ANSI colour sequences and carriage returns. A developer will read the lines you pick instead of the whole log. Find the lines that show why the build failed and write `triage.json` in the working directory:

```json
{"failure_lines": [212, 231], "summary": "test_render_table_width fails an assertion about table width."}
```

- `failure_lines` is `[first, last]`: integers, 1-based, both lines included, `first <= last`, both inside `build.log`. A line ends at CRLF, LF or CR, and a final line break does not start another line. Number the lines yourself.
- Choose one contiguous range holding the output a developer would read first to understand the failure, such as the failing test with its assertion output, the compiler error with its location, or the failing command with its error message, and little else. Setup output, warnings that did not fail the build and output printed after the failure belong in the range only when they explain it.
- `summary` is one or two plain-text sentences for the failure notification. It is not graded, and other keys are ignored.
- `triage.json` holds only the JSON object.

Grading compares `failure_lines` with the lines a person marked as the failure in this log; if the marked output occurs more than once in the log, any occurrence counts. The range is correct when it holds at least 80% of the marked lines and at least 80% of its own lines are marked lines or lie within two lines of one; credit is the average of those two shares. A range with less than a quarter of its lines on or within two lines of the failure earns nothing, so naming the whole log or a long stretch around the failure does not help. A missing or invalid file earns nothing.
