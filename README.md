# orchflows-light

Composable native workflow skills and plain Markdown quality standards for Codex and Claude Code. The host runs agents; orchflows supplies delegation and review guidance. Small skills compose into larger workflows using the same `SKILL.md` format.

| Skill | Action |
| --- | --- |
| [delegate-work](skills/delegate-work/SKILL.md) | Ask a fresh child to make a result. |
| [delegate-review](skills/delegate-review/SKILL.md) | Ask a fresh child who did not make it to review without fixing. |
| [make-and-review](skills/make-and-review/SKILL.md) | Make, review, and allow one repair pass. |
| [compare-approaches](skills/compare-approaches/SKILL.md) | Develop alternatives and compare their actual results. |
| [parallel-build](skills/parallel-build/SKILL.md) | Make separable pieces concurrently, then join and review them. |
| [build-workflow](skills/build-workflow/SKILL.md) | Author a workflow, try it, and refine it from observed behavior. |
| [setup-library](skills/setup-library/SKILL.md) | Initialize a portable user library and local Python runtime. |
| [record-run](skills/record-run/SKILL.md) | Record one workflow run and its actual summary. |

## Set up your library

From a complete copy of this package, use Python 3.11 or newer:

```sh
python3 /absolute/path/to/orchflows-light/scripts/orchflows.py setup --example social-search
```

On Windows, use your Python 3.11+ interpreter in place of `python3`. Setup creates `~/.orchflows`, its Python venv, a managed core copy, and an editable copy of the example. It initializes a Git repository when Git is available, without committing or publishing. Existing user files are preserved. Set `ORCHFLOWS_HOME` or pass `--home` to choose another home.

```text
~/.orchflows/
├── config.toml                      portable core identity
├── libraries/
│   └── social-search/               editable native package
│       ├── plugin.json
│       ├── README.md
│       └── skills/                  helpers and workflows together
├── logs/YYYY-MM/<run>/
│   ├── run.json                     compact usage record
│   ├── summary.md                   outcome and limitations
│   ├── raw/                         optional, ignored
│   └── artifacts/                   optional, ignored
├── .agents/plugins/marketplace.json Codex catalog
├── .claude-plugin/marketplace.json  Claude catalog
└── .local/                          ignored, recreated per computer
    ├── config.toml
    ├── runtime/                     Python venv
    └── packages/orchflows-light/    managed core
```

Commit editable libraries, portable configuration, catalogs and selected summaries to your own dotfiles repository. Recreate `.local/` after cloning on another computer. A venv contains machine-specific interpreter paths and is not portable. [Home setup, restoration and logging](docs/home-library.md) explains the commands and preservation rules.

## Load in your host

Setup creates native catalogs; registering them is a separate native host step. For **Codex**:

```sh
codex plugin marketplace add /absolute/path/to/.orchflows
codex plugin add orchflows-light@orchflows-home
codex plugin add social-search@orchflows-home
```

Start a new session. In CLI/IDE, select a skill with `/skills` or `$social-search:social-search`; use the app's skill picker. If an older orchflows plugin is installed from another marketplace, use one enabled core installation to avoid duplicate names.

For **Claude Code**:

```sh
claude plugin marketplace add /absolute/path/to/.orchflows
claude plugin install orchflows-light@orchflows-home --scope user
claude plugin install social-search@orchflows-home --scope user
```

Start a new session and use `/social-search:social-search`. Both hosts cache installed packages. Edit your home library, then refresh/reinstall the native plugin and start a fresh session to load changes. [Native host details](docs/native-hosts.md) covers source paths, development installs and capability limits. [Codex plugins](https://developers.openai.com/plugins/build/plugins), [Claude plugins](https://code.claude.com/docs/en/plugins).

## Compose a workflow

Ask `build-workflow` to create a reusable workflow and give it a bounded example to try. It defaults to your home library, such as `~/.orchflows/libraries/personal/skills/prepare-proposal/SKILL.md`. An explicit project or repository destination takes precedence.

A library is a complete native package. Put small capabilities and larger orchestrators together under `skills/`; place scripts, references and assets beside their owning skill. Load another skill in the current context by default. Delegate when the workflow calls for an independent worker or reviewer.

Use relative links within a library, resolved from the loaded file. Across libraries, use package identity and the home resolver, then pass concrete resolved files to children. Do not assume a source checkout or a particular current directory. This is ordinary instruction composition, with a small path/setup helper; it adds no agent runtime or workflow language.

The `social-search` example package demonstrates the pattern:

```text
social-search → choose sources
               → source workflows in parallel
                   search-reddit / search-youtube / search-site
                     → delegate-work → evidence
               → gather all results
               → rank-evidence → delegate-review → cited assessment
```

Each source workflow owns one work-agent launch; the coordinator starts independent searches before gathering their results. One fresh reviewer assesses the collected evidence and returns a ranked, cited answer. There are no source reviews or review/collection loops. `search-site` accepts any named site; `rank-evidence` also reviews independently supplied evidence. `prepare-evidence` provides a shared handoff inside each worker, without another agent. Source profiles add only site-specific guidance.

Native tools are sufficient for search. The separate `research-acquire` example offers optional bounded acquisition and resume; install it with `setup --example research-acquire` when needed. Its scripts own those mechanics without adding them to the workflow instructions.

The repo example and its initial home copy contain the same files. The home copy becomes yours to edit; later setup runs do not overwrite it. In a source checkout, browse `example-workflows/README.md`. After setup, use `resolve social-search --resource README.md` through the installed CLI to find the package guide and its trial instructions.

## Standards

Choose only useful quality lenses: [Code](standards/code.md), [Research](standards/research.md), [Writing](standards/writing.md), [Visual design](standards/visual-design.md), and [Data analysis](standards/data-analysis.md). Pass chosen files to makers and reviewers. [API code](standards/code/api.md) specializes Code; pass its parent too.

A root standard earns a file when it adds a recurring, independent quality lens. A specialized standard adds recurring specificity within that lens. Keep one-off criteria in the prompt and tool mechanics in skills or references. Standards are ordinary prose, with no precedence engine. The example's evidence format belongs to its `prepare-evidence` skill; Research and Writing supply broader quality criteria.
