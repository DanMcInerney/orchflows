# Synthetic offline instances

Travis CI build logs and labels in the layout of the LogChunks archive (`logs/<language>/<owner@repo>/failed/<build id>.log`,
`build-failure-reason/<language>/<owner@repo>.xml`). Everything here is invented: repositories, people, build ids and the
logs themselves, which imitate the byte format of real Travis logs (CRLF, ANSI sequences, `travis_fold` and `travis_time`
markers, carriage-return progress lines). Each label marks the lines a developer reads to understand the failure, as the
LogChunks labels do. `instances.json` records each log's failure family and why it is hard; three logs are candidates the
admission screen rejects. Regenerate with `python synthesize.py`.
