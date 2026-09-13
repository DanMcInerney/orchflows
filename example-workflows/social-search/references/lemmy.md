# Public Lemmy access

Use the selected instance's API version. The [official versioned API documentation](https://join-lemmy.org/docs/contributors/04-api.html) distinguishes v3 and v4; query parameters and timestamp names differ. An instance URL is part of the caller's source scope, not a default discovery endpoint.

For a v0.19 instance exposing v3, these are public read operations:

```text
https://<instance>/api/v3/search?q=<encoded-query>&type_=Posts&sort=New&page=1&limit=<caller-cap>
https://<instance>/api/v3/comment/list?post_id=<local-post-id>&sort=New&limit=<caller-cap>
```

Inspect the returned post and comment objects, including `ap_id`, `published` and `updated`, and the accompanying creator and community objects. v3 search has no publication-window parameter: filter returned dates and bound pagination locally. Newest-first comment results can omit parents; retrieve needed context within the remaining read allowance and identify an incomplete sample.
