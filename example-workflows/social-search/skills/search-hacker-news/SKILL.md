---
name: search-hacker-news
description: Search Hacker News stories and participant discussion through the reusable site-search workflow.
---

Invoke [search-site](../search-site/SKILL.md) for Hacker News, forwarding the caller's context and these source details:

Separate the linked article, submitter and commenters. Sentiment needs actual comments with parent context. Story-date filters can miss recent comments on older stories; story points are not comment scores.
