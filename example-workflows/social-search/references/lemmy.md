# Public Lemmy access

Use the selected instance's API version; [official documentation](https://join-lemmy.org/docs/contributors/04-api.html) distinguishes v3/v4 parameters and timestamps. The instance URL belongs to caller scope, not a default discovery endpoint.

Public reads for v0.19 instances exposing v3:

```text
https://<instance>/api/v3/search?q=<encoded-query>&type_=Posts&sort=New&page=1&limit=<caller-cap>
https://<instance>/api/v3/comment/list?post_id=<local-post-id>&sort=New&limit=<caller-cap>
```

Inspect post/comment `ap_id`, `published` and `updated`, plus creator/community objects. v3 search lacks a publication-window parameter: filter dates and bound pagination locally. Newest-first comments may omit parents; retrieve context within remaining reads and label incomplete samples.
