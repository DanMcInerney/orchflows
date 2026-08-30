# Code outline

## What a frozen code root carries

- Observable behavior at a seam, never the modules that will carry it.
- The failure paths the result must survive: an executor derives its first
  failing check from Goal alone, so an unstated path is an unchecked one.
- A pointer to the standards owner, and no test oracle at all.

## Worth asking at intake

- Which seam makes the outcome observable from outside the change?
- What must keep working that this change could plausibly break?
- Does a tracer slice exist that proves those seams before anything widens?
- Is the target repository, and its baseline revision, actually settled?

## Exemplar policy

Cite a module by path and revision, then list each property the imitation has
to carry: idiom, check style, layering. "Look like that file" lists none of
them, so it grants nothing.
