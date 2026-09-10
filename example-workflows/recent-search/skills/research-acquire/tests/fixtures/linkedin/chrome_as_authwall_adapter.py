"""A wrong result kept beside the tree: navigation chrome read as an authwall.

This is the adapter this ticket exists to not write, and the one the
superseded spec would have produced. It sees "Sign in to" and "Join now" in
the page, concludes that LinkedIn is refusing, and hands back `auth_required`
— off a 200 response carrying a complete ld+json Person block. A caller then
records a keyless route as credentialed, and the platform drops back out of
the roster on exactly the assumption the measurement overturned.

It reads the shipped adapter's own declared chrome constant, which the shipped
adapter declares and never reads. That is the difference between the two
modules, and it is the whole difference: every other branch is delegated, so
the oracle's rejection is attributable to this one and to nothing else.

Loaded by path, part of no package, never imported by the tree under test.
"""

from super_research.adapters import build_native_page, fetch_one_page, linkedin_public

DESCRIPTOR = linkedin_public.DESCRIPTOR


def _page_from(response, slug):
    lowered = response.body.lower()
    if any(marker in lowered for marker in linkedin_public.NAVIGATION_CHROME):
        return build_native_page(
            DESCRIPTOR,
            (),
            observed_at=response.observed_at,
            native_order=linkedin_public.NATIVE_ORDER,
            warnings=("the page asks the reader to sign in",),
            outcome="failed",
            loss=(linkedin_public.AUTH_REQUIRED,),
        )
    return linkedin_public._page_from(response, slug)


def fetch_native_page(carrier, request):
    slug = linkedin_public.slug_of(request)

    def parse(response):
        return _page_from(response, slug)

    return fetch_one_page(
        DESCRIPTOR,
        carrier,
        params={"slug": slug},
        parse=parse,
        native_order=linkedin_public.NATIVE_ORDER,
    )
