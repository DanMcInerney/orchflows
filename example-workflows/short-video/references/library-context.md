# Library context

Reuse supplied context. Otherwise resolve dependencies once at the outermost entrypoint, then pass absolute paths, the brief and output locations through every invocation and child. Relative links resolve within their owning package; `library:resource` denotes another package, never a sibling directory.

Use available native skills or caller-supplied package roots. For a configured home, select the caller's home, then `ORCHFLOWS_HOME`, then the user's `.orchflows` directory. Its CLI is `.local/packages/orchflows-light/scripts/orchflows.py`; its Python is `.local/runtime/Scripts/python.exe` on Windows or `.local/runtime/bin/python` elsewhere. Any available Python 3.11+ can run the CLI:

```text
<python> <cli> resolve <library> --skill <name> --home <home>
<python> <cli> resolve <library> --resource <relative-path> --home <home>
```

Resolve needed `orchflows-light` primitives and resources, plus caller-supplied profile dependencies. Start with [Short video](../standards/short-video.md); add [Marketing](../standards/short-video/marketing.md) for marketing and any caller standards. Follow every `Extends:` transitively and pass each distinct standard once to maker and reviewer. Core parents are `standards/writing.md` and `standards/visual-design.md`.

Choose unspecified creative settings for this brief. Use the caller's output directory or a task directory in its workspace, with separate locations for different films. Required missing skills, standards or rendering capabilities are explicit blockers; missing playback/listening limits the review. An absent home runtime alone does not block native skills with resolved resources. Children inherit this context without repeating resolution.
