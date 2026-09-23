# Library context

Require core `orchflows` (`orchflows:orch-work`, `orchflows:orch-review`) and apply its `docs/architecture.md`. Load `orchflows:orch-work` first: its package root holds core `docs/` and `guidance/`.

Collection guidance is `research.search-site` plus each assigned site's specialization: `.hacker-news`, `.reddit`, `.github`, `.x`, `.youtube`, `.polymarket`, `.feeds`, `.lemmy` or `.web`. Unfamiliar sites use `research.search-site` alone. Assessment guidance is `research.search-site` and `writing`. Preserve caller guidance and library order.

Collectors read sources through native search and fetch tools, and through the shell for the direct HTTP and `yt-dlp` routes in [public access](access.md). A missing route limits coverage; missing core primitives or delegation block dependent work.
