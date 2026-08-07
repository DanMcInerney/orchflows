# changelog generator — document-domain specification

The emitted changelog is a human-audience Markdown document. Every
constraint below is deterministically checkable.

## Structure

- The first line is exactly `# Changelog`.
- Sections appear in this fixed order, each present only when it has
  at least one entry:
  1. `## Features` — the `feat` commits.
  2. `## Fixes` — the `fix` commits.
  3. `## Documentation` — the `docs` commits.
- Section headings are exactly level two (`## `), never any other
  level, and use exactly the three names above.
- Each heading is preceded by exactly one blank line.
- Every entry line is `- ` followed by the commit subject with its
  first character uppercased. Subjects are otherwise unaltered.
- Every line of the document is one of: the title line, a section
  heading, an entry line, or a blank line. The generator adds no
  prose of its own.

## Voice

- Audience voice is impersonal release notes. The words `we`, `our`
  and `awesome` (case-insensitive, whole words) must not appear
  anywhere in the document.
- The document ends with a single trailing newline.
