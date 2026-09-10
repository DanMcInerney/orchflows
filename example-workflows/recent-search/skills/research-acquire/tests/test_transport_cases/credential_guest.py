"""Guest credential minting cases."""

from .common import *
from .policy_support import *
from .request_cases import *

class GuestMintIsOnePacedRecordedCallTest(unittest.TestCase):
    """The mint is one recorded, paced call on whatever opener was injected.

    It used to run inside ``urlopen_read``, below every seam: invisible to the
    call log, unreachable by an injected opener, and outside every budget. It
    now runs at the governor, which is the only place all three are true at
    once — a carrier cannot put a request inside a budget, because the carrier
    is what the governor paces.

    The store is module-level, so every test here clears it: ordering would
    otherwise decide which of them minted.
    """

    def setUp(self):
        transport.GUEST_TOKENS.clear()
        self.addCleanup(transport.GUEST_TOKENS.clear)

    def guest_carrier(self, activation=ACTIVATION_ANSWER, read=GUEST_READ_ANSWER):
        """The carrier a run actually gets: the governor over a recording transport."""

        clock = helpers.FakeClock()
        carrier, opener = helpers.offline_transport(clock, {
            transport.X_GUEST_ACTIVATE_ROUTE: activation,
            transport.X_GUEST_GRAPHQL_ROUTE: read,
        })
        governor = runner.RateGovernor(carrier, clock=clock.monotonic, sleep=clock.sleep)
        return governor, carrier, opener

    def test_the_activation_is_in_the_call_log_ahead_of_the_read_it_authorizes(self):
        governor, carrier, _ = self.guest_carrier()

        governor.fetch(guest_read_request())

        self.assertEqual(
            [call.route_id for call in carrier.calls],
            [transport.X_GUEST_ACTIVATE_ROUTE, transport.X_GUEST_GRAPHQL_ROUTE],
        )

    def test_the_injected_opener_answers_the_activation_and_urllib_never_does(self):
        governor, _, opener = self.guest_carrier()

        # Bypassing the injected opener means reaching urllib, which this guard
        # turns into an assertion failure rather than an egress.
        with forbid_io():
            governor.fetch(guest_read_request())

        self.assertEqual(
            [request.route_id for request in opener.opened],
            [transport.X_GUEST_ACTIVATE_ROUTE, transport.X_GUEST_GRAPHQL_ROUTE],
        )
        self.assertEqual(
            transport.GUEST_TOKENS._tokens,
            {transport.X_GUEST_ACTIVATE_ROUTE: MINTED_GUEST_TOKEN},
        )

    def test_the_activation_is_charged_against_its_own_routes_budget(self):
        # The governor's log is what it charged, and it is a different list
        # from the carrier's: a request in `calls` but not in `log` is one the
        # scheduler never saw and no budget ever covered.
        governor, _, _ = self.guest_carrier()

        governor.fetch(guest_read_request())

        self.assertEqual(
            [read.route_id for read in governor.log],
            [transport.X_GUEST_ACTIVATE_ROUTE, transport.X_GUEST_GRAPHQL_ROUTE],
        )
        self.assertEqual(
            runner.route_budgets()[transport.X_GUEST_ACTIVATE_ROUTE],
            runner.budget_of(x_guest.ACTIVATION_DESCRIPTOR),
        )

    def test_a_second_activation_would_wait_out_the_interval_its_route_declares(self):
        # The point of a budget is the wait it can impose. One mint per process
        # means the second activation never happens on its own, so the ceiling
        # is proven by asking the governor to spend the route twice.
        governor, _, _ = self.guest_carrier()
        interval_us = (
            runner.route_budgets()[transport.X_GUEST_ACTIVATE_ROUTE].min_interval_ms
            * runner.US_PER_MS
        )

        with helpers.forbid_sleep():
            governor.fetch(guest_read_request())
            governor.fetch(
                transport.build_transport_request(transport.X_GUEST_ACTIVATE_ROUTE)
            )

        activations = [
            read for read in governor.log
            if read.route_id == transport.X_GUEST_ACTIVATE_ROUTE
        ]
        self.assertEqual(len(activations), 2)
        self.assertGreater(interval_us, 0)
        self.assertEqual(activations[1].at_us - activations[0].at_us, interval_us)

    def test_a_bare_transport_mints_nothing_and_the_read_goes_out_unauthorized(self):
        # 4b. A caller reaches an unpaced origin only by building a carrier and
        # handing it in, which `run_scheduled` already calls an act rather than
        # a default. The mint is now inside that same choice: no governor, no
        # activation — and the read that needed one goes out without it, so the
        # origin's own refusal is what the run records.
        clock = helpers.FakeClock()
        carrier, opener = helpers.offline_transport(clock, {
            transport.X_GUEST_ACTIVATE_ROUTE: ACTIVATION_ANSWER,
            transport.X_GUEST_GRAPHQL_ROUTE: (401, "unauthorized", "application/json"),
        })

        response = carrier.fetch(guest_read_request())

        self.assertEqual([call.route_id for call in carrier.calls], [transport.X_GUEST_GRAPHQL_ROUTE])
        self.assertEqual(
            [request.route_id for request in opener.opened], [transport.X_GUEST_GRAPHQL_ROUTE]
        )
        # No invented token, and the refusal is the origin's own — not a local
        # error and not a retry.
        self.assertEqual(transport.GUEST_TOKENS._tokens, {})
        self.assertEqual(response.status, 401)
        self.assertEqual(response.channel_verdict, transport.ORIGIN_FAILURE)

    def test_the_bare_carrier_consequence_is_stated_where_the_mint_is_documented(self):
        # 4b's second half. The behaviour is proven above; this is the claim
        # that a reader meets it without running the suite. Both places that
        # document the mint must name the un-minted outcome, so deleting it
        # from either one fails here rather than quietly leaving a reader to
        # assume every carrier mints.
        for owner in (pacing.RateGovernor._mint_for, transport.mint_guest_token):
            with self.subTest(documented=owner.__qualname__):
                stated = inspect.getdoc(owner)

                self.assertIn("unauthorized", stated)

    def test_the_token_is_minted_once_and_the_store_answers_every_later_read(self):
        governor, carrier, _ = self.guest_carrier()

        governor.fetch(guest_read_request())
        governor.fetch(guest_read_request())

        self.assertEqual(
            [call.route_id for call in carrier.calls],
            [
                transport.X_GUEST_ACTIVATE_ROUTE,
                transport.X_GUEST_GRAPHQL_ROUTE,
                transport.X_GUEST_GRAPHQL_ROUTE,
            ],
        )

    def test_a_route_declaring_no_activation_route_mints_nothing(self):
        clock = helpers.FakeClock()
        carrier, _ = helpers.offline_transport(
            clock, {transport.DDG_HTML_ROUTE: GUEST_READ_ANSWER}
        )
        governor = runner.RateGovernor(carrier, clock=clock.monotonic, sleep=clock.sleep)

        governor.fetch(
            transport.build_transport_request(transport.DDG_HTML_ROUTE, {"q": "probe"})
        )

        self.assertEqual([call.route_id for call in carrier.calls], [transport.DDG_HTML_ROUTE])
        self.assertEqual(transport.GUEST_TOKENS._tokens, {})

    def test_an_activation_the_opener_refuses_outright_yields_no_token(self):
        # The opener raises rather than answering, so the read that needed a
        # token goes out without one and the origin's own 401 is what the run
        # records — never an invented token.
        clock = helpers.FakeClock()
        carrier, _ = helpers.offline_transport(
            clock,
            {transport.X_GUEST_GRAPHQL_ROUTE: (401, "unauthorized", "application/json")},
        )
        governor = runner.RateGovernor(carrier, clock=clock.monotonic, sleep=clock.sleep)

        response = governor.fetch(guest_read_request())

        self.assertEqual(
            transport.GUEST_TOKENS._tokens, {transport.X_GUEST_ACTIVATE_ROUTE: ""}
        )
        self.assertEqual(response.status, 401)

    def test_a_refused_mint_sends_the_read_unauthorized_and_is_never_retried(self):
        # The rule :func:`mint_guest_token` states, now under test: a mint that
        # produced nothing is not turned into a second activation, and the
        # origin's own 401 is what the run records. A refusal re-attempted per
        # read would spend two requests on every one the origin already refused.
        governor, carrier, _ = self.guest_carrier(
            activation=(403, "forbidden", "text/plain"),
            read=(401, "unauthorized", "application/json"),
        )

        first = governor.fetch(guest_read_request())
        second = governor.fetch(guest_read_request())

        self.assertEqual(
            transport.GUEST_TOKENS._tokens, {transport.X_GUEST_ACTIVATE_ROUTE: ""}
        )
        self.assertEqual(
            [call.route_id for call in carrier.calls],
            [
                transport.X_GUEST_ACTIVATE_ROUTE,
                transport.X_GUEST_GRAPHQL_ROUTE,
                transport.X_GUEST_GRAPHQL_ROUTE,
            ],
        )
        self.assertEqual((first.status, second.status), (401, 401))

    def test_an_activation_route_that_named_a_token_route_cannot_recurse(self):
        # Minting at the governor is re-entrant: the activation is itself a
        # paced fetch. Nothing in the table declares this today, so the guard is
        # proven against a table that does.
        looping = dict(transport.ROUTE_CONSTANTS)
        looping[transport.X_GUEST_ACTIVATE_ROUTE] = dataclasses.replace(
            looping[transport.X_GUEST_ACTIVATE_ROUTE],
            token_route_id=transport.X_GUEST_ACTIVATE_ROUTE,
        )
        governor, carrier, _ = self.guest_carrier()

        with mock.patch.object(transport, "ROUTE_CONSTANTS", looping):
            governor.fetch(guest_read_request())

        self.assertEqual(
            [call.route_id for call in carrier.calls],
            [transport.X_GUEST_ACTIVATE_ROUTE, transport.X_GUEST_GRAPHQL_ROUTE],
        )

    def test_a_read_a_run_already_remembers_costs_no_activation(self):
        # The mint is on the miss path, where pacing lives: a token buys an
        # origin read, and a cache hit reaches no origin. Minting for one would
        # spend a request the run had already decided not to make.
        clock = helpers.FakeClock()
        carrier, _ = helpers.offline_transport(clock, {
            transport.X_GUEST_ACTIVATE_ROUTE: ACTIVATION_ANSWER,
            transport.X_GUEST_GRAPHQL_ROUTE: GUEST_READ_ANSWER,
        })
        governor = runner.RateGovernor(
            carrier,
            run_cache=cache.RunCache(clock=clock.monotonic),
            clock=clock.monotonic,
            sleep=clock.sleep,
        )

        governor.fetch(guest_read_request())
        transport.GUEST_TOKENS.clear()
        governor.fetch(guest_read_request())

        self.assertEqual([serve.cache_hit for serve in governor.serves], [False, True])
        self.assertEqual(transport.GUEST_TOKENS._tokens, {})

    def test_the_opener_attaches_what_the_governor_minted_and_mints_nothing_itself(self):
        governor, _, _ = self.guest_carrier()
        governor.fetch(guest_read_request())

        # Under the guard on purpose: a lookup that still minted would reach
        # urllib here, and a store the governor filled needs no network.
        with forbid_io():
            held = transport.tokened_headers((), transport.X_GUEST_ACTIVATE_ROUTE)
            transport.GUEST_TOKENS.clear()
            empty = transport.tokened_headers((), transport.X_GUEST_ACTIVATE_ROUTE)

        self.assertEqual(held, ((transport.GUEST_TOKEN_HEADER, MINTED_GUEST_TOKEN),))
        self.assertEqual(empty, ())

    def test_the_minted_token_reaches_no_call_no_response_and_no_environment(self):
        governor, carrier, opener = self.guest_carrier()

        # The guard is half the claim: no file was written because none could be.
        with forbid_io():
            response = governor.fetch(guest_read_request())

        # A token really was minted, so the four claims below are about
        # something rather than about nothing.
        self.assertEqual(
            transport.GUEST_TOKENS._tokens,
            {transport.X_GUEST_ACTIVATE_ROUTE: MINTED_GUEST_TOKEN},
        )
        self.assertNotIn(MINTED_GUEST_TOKEN, repr(carrier.calls))
        self.assertNotIn(MINTED_GUEST_TOKEN, repr(opener.opened))
        self.assertNotIn(MINTED_GUEST_TOKEN, repr(response))
        self.assertEqual(
            [name for name, value in os.environ.items() if MINTED_GUEST_TOKEN in value], []
        )

    def test_exactly_one_site_in_the_package_mints(self):
        self.assertEqual(minting_sites(), ["pacing.py:RateGovernor._mint_for"])

    def test_the_minting_site_scan_notices_a_site_it_was_not_told_about(self):
        # The scan is shown to discriminate rather than to match nothing at all.
        found = set()

        sites_calling(
            ast.parse(
                "class Rogue:\n"
                "    def read(self):\n"
                "        return mint_guest_token(self.fetch, 'r')\n"
            ),
            (),
            "rogue.py",
            found,
        )

        self.assertEqual(sorted(found), ["rogue.py:Rogue.read"])
