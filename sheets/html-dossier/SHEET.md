---
name: html-dossier
description: Stamp when the deliverable is one self-contained HTML dossier that opens offline and cites every claim in-file.
packs: [orch-content-pack, orch-design-pack]
---

# html-dossier

## Craft

The dossier is one file a reader opens from disk, years later, with no
network and no server. That single constraint decides most of what follows.

- **One file.** Styles, scripts, fonts and images live inside it, inline or
  as `data:` URIs. No `<link>`, no `src` carrying a scheme, no `@import`,
  no remote font, no analytics pixel. A dependency the reader has to fetch
  is a dependency the reader will one day not have.
- **Answer first.** The question's answer opens the page, above the
  evidence that supports it. The evidence is the reason to believe the
  answer, not the route to finding it.
- **Legible in both themes.** The full palette is defined once in `:root`
  and only the tokens that change are redefined under
  `prefers-color-scheme: dark`; `body` carries an explicit background. A
  colour whose only definition sits inside the dark block is a colour the
  light reader does not get.
- **Numerals are tabular.** Figures, tables and durations set
  `font-variant-numeric: tabular-nums`, so digits in a column line up and a
  reader can compare two rows by eye.
- **A sources section, and citations that reach it.** The dossier ends with
  one entry per source: its title, its date, and the locator the record
  itself carried. Every citation in the body is a same-page link to its
  entry, so no claim sends the reader off the page to be checked.
- **Carry the source's own string.** A locator or a figure re-typed from
  memory looks authoritative and is a guess; a number re-rounded is a
  second number. Quote a community voice verbatim with its author and its
  count.
- **Name what is missing and what disagrees.** Every typed loss appears on
  the page as a loss - a refusal rendered as an absence is how a dossier
  whose failures were all reported still misleads. Where two sources inside
  the window contradict, both are shown and neither is averaged away.

## Lens

### doc

- Offline: the file opens from the filesystem with nothing missing - no
  `<link>`, no `src` with a scheme, no `@import`, no remote font remains in
  it. One external reference is a blocking finding.
- Captions: every figure, table and chart carries a caption naming what it
  shows, its source and its date.
- Citations: every claim in the body links to an entry in the sources
  section inside this same file; an entry no citation reaches, and a
  citation reaching no entry, are both findings.
- Themes: the page is readable at both `prefers-color-scheme` values, and
  no token is defined only inside the dark block.
- Numerals: figures and tables render with tabular numerals.
- Fidelity: sampled locators, figures and quotations match the source
  records exactly, with the author and count each quotation was given.
- Losses and contradictions: each typed loss is stated as a loss, and each
  contradiction inside the window is shown unresolved rather than picked.
