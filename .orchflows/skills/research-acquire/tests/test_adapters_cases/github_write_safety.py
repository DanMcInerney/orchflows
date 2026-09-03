from tests.test_adapters_cases.github_read import *  # noqa: F401,F403

WRITE_VERBS = ("POST", "PUT", "PATCH", "DELETE")
WRONG_GITHUB_ADAPTERS = ("issue_write_adapter", "no_operations_adapter")


def code_strings(path):
    """Every string one source spells in its code, docstrings excluded.

    A module's prose may name a verb — this one's says out loud that a POST is
    refused before any socket — and prose cannot be put on a wire. A string
    constant can, so the two are counted apart: the scan below is about what
    the code can send, not about what the file can say.
    """

    values = set()
    for owner in adapter_owner_paths(path):
        tree = ast.parse(owner.read_text(encoding="utf-8"))
        prose = set()
        for node in ast.walk(tree):
            if not isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef)):
                continue
            first = node.body[0] if node.body else None
            if (
                isinstance(first, ast.Expr)
                and isinstance(first.value, ast.Constant)
                and isinstance(first.value.value, str)
            ):
                prose.add(id(first.value))
        values.update(
            node.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and id(node) not in prose
        )
    return values


def any_route_transport(body):
    """A carrier that will answer on any route at all, and record which one.

    Seeding only the routes an adapter is supposed to use would turn "it
    reached somewhere else" into a missing fixture. Every declared route
    answers here, so reaching a fourth one is a recorded call the enumeration
    can name rather than an error it trips over.
    """

    clock = helpers.FakeClock()
    answer = (200, body, "application/json")
    return helpers.offline_transport(
        clock, {route_id: answer for route_id in transport.ROUTE_CONSTANTS}
    )


def assert_no_write_verb_is_reachable(case, adapter_id, module):
    """Row 2's oracle: the reachable operation set, enumerated, and read-only.

    Not "no test tried a write". The set of operations this adapter can perform
    is a declared tuple; each one is run, and each is checked at four seams —
    the operation set covers the roster's capabilities and nothing wider, every
    operation's route is one this adapter declares, every route declares a read
    and admits nothing else, and every operation's single recorded call left
    with a read verb and no body.

    The coverage clause is what stops the whole thing being vacuous: an adapter
    that declared no operation would reach no write verb by reaching nothing,
    and would satisfy every other clause here perfectly.
    """

    declared = tuple(module.GITHUB_OPERATIONS)
    surfaces = tuple(
        descriptor.route_id for descriptor in module.SURFACE_DESCRIPTORS
    )
    uncovered = [
        capability
        for capability in GITHUB_ROSTER_CAPABILITIES
        if capability not in declared
    ]
    if uncovered:
        case.fail(
            "{0} enumerates an operation set that reaches none of the roster's"
            " capabilities {1}: nothing was proven read-only by proving nothing"
            " is reachable".format(adapter_id, uncovered)
        )

    for operation in declared:
        route_id, _ = (
            module.OPERATION_SURFACES[operation][0].route_id,
            module.OPERATION_SURFACES[operation][1],
        )
        detail = " {0} operation {1} on route {2}".format(adapter_id, operation, route_id)
        if route_id not in surfaces:
            case.fail("an operation reaches a route this adapter never declared:" + detail)
        route = transport.route_constant(route_id)
        if route.method not in transport.READ_METHODS:
            case.fail(
                "a write-capable verb {0} is declared by the route behind:{1}".format(
                    route.method, detail
                )
            )
        if transport.admitted_methods(route_id) != transport.READ_METHODS:
            case.fail(
                "a route this adapter reads admits a verb that is not a read:" + detail
            )
        if route.body_params:
            case.fail("a route this adapter reads carries a request body:" + detail)

        carrier, opener = any_route_transport(read_github("repo.json"))
        module.fetch_native_page(
            carrier, gh_request(target_id=operation + ":" + GITHUB_TARGET)
        )
        if len(opener.opened) != 1:
            case.fail(
                "one operation cost {0} calls rather than one:{1}".format(
                    len(opener.opened), detail
                )
            )
        sent = opener.opened[0]
        if sent.method not in transport.READ_METHODS:
            case.fail(
                "a write-capable verb {0} is reachable through:{1}".format(sent.method, detail)
            )
        if sent.body:
            case.fail("a request this adapter sent carried a body:" + detail)
        if sent.route_id not in surfaces:
            case.fail(
                "a call left on a route this adapter never declared: {0} through{1}".format(
                    sent.route_id, detail
                )
            )


class GithubNoWriteVerbIsReachableTest(unittest.TestCase):
    """Row 2: the largest write surface in the roster, and none of it reachable.

    GitHub's REST API creates issues, opens pull requests, pushes files and
    deletes repositories, all on paths that look like the ones this adapter
    reads — the difference is the verb, and the verb belongs to the route. So
    the claim is made by enumerating what this adapter can do rather than by
    the absence of a test that tried something.
    """

    def test_the_reachable_operation_set_is_read_only_by_enumeration(self):
        assert_no_write_verb_is_reachable(self, "github_rest", github_rest)

    def test_the_operation_set_is_exactly_the_roster_row_and_nothing_wider(self):
        self.assertEqual(
            sorted(github_rest.GITHUB_OPERATIONS), sorted(GITHUB_ROSTER_CAPABILITIES)
        )
        self.assertEqual(
            sorted(github_rest.OPERATION_SURFACES), sorted(GITHUB_ROSTER_CAPABILITIES)
        )

    def test_the_module_spells_no_write_verb_anywhere_in_its_code(self):
        # The verb is the route's, and this module never names one: there is no
        # string here that could become a method on a wire.
        spelled = sorted(
            verb
            for verb in WRITE_VERBS
            if verb in code_strings(ADAPTER_DIR / "github_rest.py")
        )

        self.assertEqual(spelled, [])

    def test_the_same_scan_finds_a_verb_where_one_is_spelled(self):
        # Shown to discriminate rather than to match nothing: the wrong adapter
        # beside the tree spells the one this module does not.
        spelled = sorted(
            verb
            for verb in WRITE_VERBS
            if verb in code_strings(GITHUB_FIXTURE_DIR / "issue_write_adapter.py")
        )

        self.assertEqual(spelled, ["POST"])

    def test_the_code_for_a_missing_credential_is_declared_and_never_produced(self):
        # Declared so this module can say what it never says. A count of zero
        # reads is the statement: no branch here can reach it.
        self.assertEqual(github_rest.AUTH_REQUIRED, "auth_required")
        self.assertEqual(names_read(ADAPTER_DIR / "github_rest.py", "AUTH_REQUIRED"), 0)


class GithubWriteVerbOracleCanFailTest(unittest.TestCase):
    """Row 4: the oracle above rejects a write verb, and rejects an empty claim."""

    def _wrong(self, name):
        return load_adapter_fixture(name, directory=GITHUB_FIXTURE_DIR)

    def test_an_adapter_that_can_open_an_issue_fails_the_oracle(self):
        with self.assertRaisesRegex(
            AssertionError, "write-capable verb POST is reachable"
        ):
            assert_no_write_verb_is_reachable(
                self, WRONG_GITHUB_ADAPTERS[0], self._wrong(WRONG_GITHUB_ADAPTERS[0])
            )

    def test_an_adapter_that_reaches_nothing_at_all_fails_the_oracle(self):
        # The vacuity direction. Without this clause the oracle would be
        # perfectly satisfied by an adapter with no capability whatsoever,
        # which is the cheapest way to pass a read-only check.
        with self.assertRaisesRegex(AssertionError, "reaches none of the roster's"):
            assert_no_write_verb_is_reachable(
                self, WRONG_GITHUB_ADAPTERS[1], self._wrong(WRONG_GITHUB_ADAPTERS[1])
            )

    def test_the_same_oracle_passes_on_the_shipped_adapter(self):
        assert_no_write_verb_is_reachable(self, "github_rest", github_rest)

    def test_the_write_adapter_would_really_have_left_with_a_write_verb(self):
        # The rejection above is not a technicality about a declaration: the
        # call this fixture makes is recorded on the carrier with the verb on
        # it, which is what an adapter opening an issue would actually do.
        wrong = self._wrong(WRONG_GITHUB_ADAPTERS[0])
        carrier, opener = any_route_transport(read_github("repo.json"))

        wrong.fetch_native_page(carrier, gh_request(target_id="create_issue:" + GITHUB_TARGET))

        self.assertEqual([call.method for call in opener.opened], ["POST"])
        self.assertIn("title", opener.opened[0].body)
        # And the transport would refuse it before any socket, which is the
        # second line of defence rather than the first.
        with helpers.forbid_io():
            with self.assertRaises(transport.TransportError):
                transport.urlopen_response(opener.opened[0])

    def test_nothing_in_the_package_can_reach_either_wrong_adapter(self):
        named = sorted(
            path.name
            for path in PACKAGE_DIR.rglob("*.py")
            for wrong in WRONG_GITHUB_ADAPTERS
            if wrong in path.read_text(encoding="utf-8")
        )

        self.assertEqual(named, [])
