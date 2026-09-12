# Library context

Reuse supplied context. Otherwise establish it at the outermost entrypoint, including either leaf invoked alone. Resolve core primitives and `orchflows-light:docs/architecture.md`; its guidance-selection rule applies here. Relative links stay within their package; `library:resource` names another package.

Use available native skills or caller-supplied package roots. For a configured home, select the caller's home, then `ORCHFLOWS_HOME`, then the user's `.orchflows` directory. Its CLI is `.local/packages/orchflows-light/scripts/orchflows.py`; its Python is `.local/runtime/Scripts/python.exe` on Windows or `.local/runtime/bin/python` elsewhere. Any available Python 3.11+ can run the CLI:

```text
<python> <cli> resolve <library> --skill <name> --home <home>
<python> <cli> resolve <library> --resource <relative-path> --home <home>
```

Select independent `writing`, `visual-design` and `short-video` guidance; for marketing, select `short-video.marketing` as the video specialization. Include this library and any caller-supplied guidance names and package roots. Pass the resolved guidance paths, primitives, brief, assets and output locations through composed skills and children.

Choose unspecified creative settings for this brief. Use the caller's output directory or a task directory in its workspace, with separate locations for different films. Required missing skills, guidance or rendering capabilities are explicit blockers; missing playback/listening limits the review. An absent home runtime alone does not block native skills with resolved resources.
