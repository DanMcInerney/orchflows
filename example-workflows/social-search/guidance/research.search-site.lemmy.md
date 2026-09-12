# Lemmy

## Make

Search the selected instance using its public API; see [Lemmy access](../references/lemmy.md) for version-specific operations. Its view contains local material and federated material known to that instance, not all of Lemmy.

Keep the serving instance separate from the originating community and author. Deduplicate federated copies by the post or comment's canonical `ap_id`, not instance-local numeric IDs. Preserve publication and update times separately. Read comments with their parent context for participant claims; a post's body, linked article, score or comment count does not establish what commenters said.
