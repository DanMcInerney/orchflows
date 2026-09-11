# Example libraries

Examples are portable user libraries, separate from the orchflows-light core plugin. Copy a complete package into an orchflows home with the core setup CLI; then use the native host's plugin registration and refresh flow to discover its skills.

| Library | Purpose | Try it |
| --- | --- | --- |
| [social-search](social-search/README.md) | Small search workflows composed into parallel source collection and one final evidence review. | [Two-source request](social-search/trials/request.md) and [acceptance criteria](social-search/trials/expected-behavior.md). |
| [research-acquire](research-acquire/README.md) | Optional bounded acquisition backend usable inside any research worker. | Offline fixture described in its package guide. |

Install any named example with `scripts/orchflows.py setup --example NAME`. Each library owns its dependencies and resources; acquisition code and fixtures stay in the optional acquisition package. Home configuration, runtimes and generated outputs belong outside this catalog.
