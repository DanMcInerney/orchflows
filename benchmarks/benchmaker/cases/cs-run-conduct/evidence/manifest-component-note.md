# Sealed-package component references — note

Supplements `record-schema.md` §package/. In the sealed package's
`manifest.json`, each of the six component references —
`evaluation_design`, `runnable_cases`, `runner`, `scoring`,
`provenance`, `qualification` — is an object of exactly this form:

    {"sha256": "sha256:<64-hex>", "locator": "<path relative to package/>"}

The digest field is the JSON key `sha256` and its value carries the
`sha256:` prefix; it is computed over the shipped bytes at the
locator. Where the cited manifest schema's prose describes a component
reference generically as an identity plus a locator, this package
family records that identity under the key `sha256` as above.
