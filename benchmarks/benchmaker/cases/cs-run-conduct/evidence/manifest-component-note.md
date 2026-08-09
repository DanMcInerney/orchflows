# Package component references — note

Supplements `record-schema.md` §package/. In the package's
`manifest.json`, each of the six component references —
`evaluation_design`, `runnable_cases`, `runner`, `scoring`,
`provenance`, `qualification` — is an object of exactly this form:

    {"locator": "<path relative to package/>"}

The locator is the whole reference: it resolves over the shipped bytes,
and a component that moves is a component whose locator moves with it.
Nothing beside it records what those bytes were.
