"""Ordinary build output for synthetic logs: package fetching, compiling, passing tests.

Each function appends the lines a real tool prints around a failure; none of them states a failure. Words such
as `error` and `failure` appear only where real output holds them (a package named `error_prone_annotations`,
a test named `test_delivery_failure_is_retried`). Fetch and compile lines are distinct, as a real tool prints
each artifact once.
"""
from __future__ import annotations

import random

from synth_travis import ESC, Log, colour, hexes

JEST_PASS = f"{ESC}[0m{ESC}[7m{ESC}[1m{ESC}[32m PASS {ESC}[39m{ESC}[22m{ESC}[27m{ESC}[0m"
JEST_FAIL = f"{ESC}[0m{ESC}[7m{ESC}[1m{ESC}[31m FAIL {ESC}[39m{ESC}[22m{ESC}[27m{ESC}[0m"
SIZES = ("5.1 kB", "12 kB", "48 kB", "230 kB", "1.4 MB", "3.2 MB", "611 B", "92 kB")

MAVEN = ["org/apache/maven/plugins/maven-resources-plugin", "org/apache/maven/plugins/maven-compiler-plugin", "org/apache/maven/plugins/maven-surefire-plugin",
         "org/apache/maven/plugins/maven-jar-plugin", "org/apache/maven/plugins/maven-install-plugin", "org/apache/maven/plugins/maven-clean-plugin",
         "org/apache/maven/surefire/surefire-junit-platform", "org/apache/maven/surefire/surefire-api", "org/apache/maven/surefire/maven-surefire-common",
         "org/apache/maven/surefire/surefire-booter", "com/google/guava/guava", "com/google/errorprone/error_prone_annotations", "com/google/code/findbugs/jsr305",
         "org/checkerframework/checker-qual", "com/google/j2objc/j2objc-annotations", "org/slf4j/slf4j-api", "org/slf4j/jul-to-slf4j", "ch/qos/logback/logback-classic",
         "ch/qos/logback/logback-core", "com/fasterxml/jackson/core/jackson-databind", "com/fasterxml/jackson/core/jackson-core", "com/fasterxml/jackson/core/jackson-annotations",
         "com/fasterxml/jackson/datatype/jackson-datatype-jsr310", "org/apache/commons/commons-lang3", "commons-io/commons-io", "commons-codec/commons-codec",
         "org/apache/commons/commons-collections4", "org/codehaus/plexus/plexus-utils", "org/codehaus/plexus/plexus-interpolation", "org/codehaus/plexus/plexus-compiler-api",
         "junit/junit", "org/hamcrest/hamcrest-core", "org/junit/jupiter/junit-jupiter-api", "org/junit/jupiter/junit-jupiter-engine", "org/junit/platform/junit-platform-engine",
         "org/opentest4j/opentest4j", "org/apiguardian/apiguardian-api", "org/mockito/mockito-core", "net/bytebuddy/byte-buddy", "org/objenesis/objenesis",
         "org/hibernate/validator/hibernate-validator", "javax/validation/validation-api", "com/zaxxer/HikariCP", "org/postgresql/postgresql", "org/flywaydb/flyway-core",
         "org/jboss/logging/jboss-logging", "org/yaml/snakeyaml"]

GEMS = ["actioncable", "actionmailer", "actionpack", "actionview", "activejob", "activemodel", "activerecord", "activestorage", "activesupport", "addressable", "ast",
        "bcrypt", "bootsnap", "builder", "byebug", "capybara", "childprocess", "coderay", "concurrent-ruby", "connection_pool", "crass", "database_cleaner", "diff-lcs",
        "docile", "erubi", "execjs", "factory_bot", "faker", "faraday", "ffi", "globalid", "i18n", "jaro_winkler", "json", "jwt", "kaminari", "loofah", "mail", "marcel",
        "method_source", "mimemagic", "mini_mime", "mini_portile2", "minitest", "msgpack", "multi_json", "nio4r", "nokogiri", "oj", "parallel", "parser", "pg", "powerpack",
        "pry", "public_suffix", "puma", "rack", "rack-cors", "rack-test", "rails", "rails-dom-testing", "rails-html-sanitizer", "railties", "rainbow", "rake", "redis",
        "regexp_parser", "rspec-core", "rspec-expectations", "rspec-mocks", "rspec-rails", "rspec-support", "rubocop", "ruby-progressbar", "sidekiq", "simplecov",
        "sprockets", "thor", "thread_safe", "tzinfo", "unicode-display_width", "webmock", "websocket-driver", "websocket-extensions"]

GO_MODULES = ["github.com/pkg/errors v0.8.1", "github.com/gorilla/mux v1.7.1", "github.com/sirupsen/logrus v1.4.0", "golang.org/x/net v0.0.0-20190404232315-eb5bcb51f2a3",
              "github.com/prometheus/client_golang v0.9.2", "github.com/stretchr/testify v1.3.0", "github.com/davecgh/go-spew v1.1.1", "gopkg.in/yaml.v2 v2.2.2",
              "golang.org/x/sys v0.0.0-20190412213103-97732733099d", "github.com/hashicorp/golang-lru v0.5.1", "github.com/rs/cors v1.6.0", "google.golang.org/grpc v1.19.1",
              "github.com/golang/protobuf v1.3.1", "github.com/cespare/xxhash v1.1.0", "github.com/beorn7/perks v1.0.0", "github.com/matttproud/golang_protobuf_extensions v1.0.1",
              "github.com/prometheus/common v0.2.0", "github.com/prometheus/procfs v0.0.0-20190117184657-bf6a532e95b1", "github.com/pmezard/go-difflib v1.0.0",
              "github.com/konsorten/go-windows-terminal-sequences v1.0.1", "golang.org/x/text v0.3.0", "golang.org/x/crypto v0.0.0-20190308221718-c2843e01d9a2",
              "github.com/fsnotify/fsnotify v1.4.7", "github.com/spf13/cobra v0.0.3", "github.com/spf13/pflag v1.0.3", "github.com/inconshreveable/mousetrap v1.0.0",
              "github.com/google/uuid v1.1.1", "github.com/gorilla/handlers v1.4.0", "github.com/felixge/httpsnoop v1.0.0", "go.uber.org/atomic v1.3.2",
              "go.uber.org/multierr v1.1.0", "go.uber.org/zap v1.9.1", "github.com/lib/pq v1.0.0", "github.com/jmoiron/sqlx v1.2.0", "github.com/pelletier/go-toml v1.2.0",
              "github.com/mitchellh/mapstructure v1.1.2", "github.com/magiconair/properties v1.8.0", "github.com/hashicorp/hcl v1.0.0", "github.com/spf13/viper v1.3.2",
              "github.com/fatih/color v1.7.0"]

CRATES = ["libc", "cfg-if", "memchr", "lazy_static", "serde", "serde_derive", "proc-macro2", "quote", "syn", "unicode-xid", "byteorder", "log", "error-chain", "failure",
          "failure_derive", "thiserror", "regex", "regex-syntax", "aho-corasick", "thread_local", "rand", "rand_core", "bytes", "tokio", "mio", "futures", "num-traits", "itoa"]
CRATE_KINDS = ["core", "macros", "sys", "utils", "types", "traits"]

COMPOSER = ["psr/log (1.1.0)", "symfony/polyfill-mbstring (v1.11.0)", "symfony/console (v4.2.5)", "psr/container (1.0.0)", "symfony/debug (v4.2.5)", "monolog/monolog (1.24.0)",
            "guzzlehttp/psr7 (1.5.2)", "guzzlehttp/guzzle (6.3.3)", "guzzlehttp/promises (v1.3.1)", "doctrine/inflector (v1.3.0)", "doctrine/lexer (1.0.1)",
            "nesbot/carbon (2.17.1)", "phpunit/php-token-stream (3.0.1)", "phpunit/php-text-template (1.2.1)", "phpunit/php-file-iterator (2.0.2)", "phpunit/php-code-coverage (6.1.4)",
            "phpunit/phpunit-mock-objects (6.1.2)", "phpunit/phpunit (7.5.8)", "sebastian/diff (3.0.2)", "sebastian/comparator (3.0.2)", "sebastian/exporter (3.1.0)",
            "sebastian/environment (4.2.1)", "sebastian/recursion-context (3.0.0)", "sebastian/global-state (2.0.0)", "sebastian/object-enumerator (3.0.3)",
            "sebastian/resource-operations (2.0.1)", "sebastian/version (2.0.1)", "myclabs/deep-copy (1.8.1)", "phpspec/prophecy (1.8.0)", "webmozart/assert (1.4.0)",
            "phar-io/manifest (1.0.3)", "phar-io/version (2.0.1)", "theseer/tokenizer (1.1.2)", "squizlabs/php_codesniffer (3.4.1)", "symfony/yaml (v4.2.5)",
            "symfony/finder (v4.2.5)", "symfony/filesystem (v4.2.5)", "symfony/translation (v4.2.5)", "vlucas/phpdotenv (v3.3.3)", "ramsey/uuid (3.8.0)"]


def pip_install(log: Log, rng: random.Random, packages: list[tuple[str, str]]) -> None:
    for name, version in packages:
        log.add(f"Collecting {name}=={version}")
        log.add(f"  Using cached https://files.pythonhosted.org/packages/{hexes(rng, 2)}/{hexes(rng, 2)}/{hexes(rng, 60)}/{name}-{version}-py2.py3-none-any.whl ({rng.randint(12, 900)}kB)")
    log.add("Installing collected packages: " + ", ".join(name for name, _ in packages))
    log.add("Successfully installed " + " ".join(f"{name}-{version}" for name, version in packages))


def pytest_lines(log: Log, tests: list[str], *, failing: frozenset[int] = frozenset()) -> None:
    """One `-v` line per test with the running percentage; indexes in `failing` print FAILED."""
    total = len(tests)
    for i, node in enumerate(tests):
        word = colour("FAILED", "31") if i in failing else colour("PASSED", "32")
        pad = max(1, 79 - len(node) - 14)
        log.add(f"{node} {word}{ESC}[36m{' ' * pad}[{(i + 1) * 100 // total:3d}%]{ESC}[0m")


def node_ids(modules: dict[str, int], verbs: list[str], nouns: list[str],
             rename: dict[tuple[str, int], str] | None = None) -> list[str]:
    """pytest node ids, modules in alphabetical order; `rename` replaces the test at (module, position)."""
    ids = []
    for module in sorted(modules):
        for i in range(modules[module]):
            name = (rename or {}).get((module, i)) or f"test_{verbs[i % len(verbs)]}_{nouns[(i // len(verbs) + i) % len(nouns)]}"
            tag = f"[{('fedex', 'ups', 'dhl', 'usps')[i % 4]}-{('us', 'ca', 'de', 'gb')[i // 4 % 4]}]" if i % 5 == 4 else ""
            ids.append(f"tests/{module}.py::{name}{tag}")
    return ids


def maven_downloads(log: Log, rng: random.Random, n: int) -> None:
    """n fetches, each artifact once (a pom or a jar), with sizes and speeds."""
    for i in range(n):
        path = MAVEN[i % len(MAVEN)]
        round_ = i // len(MAVEN)
        version = f"{1 + round_ // 6}.{round_ % 6}.{(i * 7) % 10}"
        artifact = path.rsplit("/", 1)[1]
        url = f"https://repo.maven.apache.org/maven2/{path}/{version}/{artifact}-{version}.{'pom' if i % 2 else 'jar'}"
        log.add(f"[INFO] Downloading from central: {url}")
        log.add(f"[INFO] Downloaded from central: {url} ({rng.choice(SIZES)} at {rng.randint(40, 900)} kB/s)")


def jest_files(log: Log, rng: random.Random, areas: list[str], per_file: int, count: int, *, verbose: bool = True) -> list[str]:
    """PASS blocks with ticked tests; returns the file names used."""
    verbs = ["renders without crashing", "forwards the ref", "applies the variant class", "calls onChange once", "handles keyboard focus",
             "memoizes derived rows", "supports the disabled state", "formats numbers with the locale", "ignores unknown props", "cleans up listeners"]
    used = []
    for i in range(count):
        area = areas[i % len(areas)]
        name = f"src/{area.lower()}/{area}{'' if i < len(areas) else i // len(areas) + 1}.test.js"
        used.append(name)
        log.add(f"{JEST_PASS} {name} ({rng.uniform(0.6, 6.5):.3f}s)")
        if verbose:
            for verb in rng.sample(verbs, per_file):
                log.add(f"  {ESC}[32m✓{ESC}[39m {ESC}[2m{verb} ({rng.randint(1, 48)}ms){ESC}[22m")
    return used


def bundler_using(log: Log, rng: random.Random, n: int) -> int:
    """n distinct gems, each installed or reused once; returns how many were printed."""
    for name in rng.sample(GEMS, min(n, len(GEMS))):
        log.add(f"{rng.choice(('Using', 'Using', 'Installing'))} {name} {rng.randint(1, 6)}.{rng.randint(0, 9)}.{rng.randint(0, 12)}")
    return min(n, len(GEMS))


def go_downloads(log: Log, rng: random.Random, n: int) -> None:
    for module in GO_MODULES[:n]:
        log.add(f"go: downloading {module}")


def go_ok(log: Log, rng: random.Random, packages: list[str]) -> None:
    for pkg in packages:
        log.add(rng.choice((f"ok  \t{pkg}\t{rng.uniform(0.01, 3):.3f}s", f"ok  \t{pkg}\t{rng.uniform(0.01, 3):.3f}s", f"?   \t{pkg}\t[no test files]")))


def cargo_compiling(log: Log, rng: random.Random, n: int) -> None:
    for i in range(n):
        base = CRATES[i % len(CRATES)]
        name = base if i < len(CRATES) else f"{base}-{CRATE_KINDS[(i // len(CRATES) - 1) % len(CRATE_KINDS)]}"
        log.add(f"   Compiling {name} v{i // 40}.{(i * 3) % 20}.{(i * 7) % 12}")


def cargo_tests(modules: list[str], n: int) -> list[str]:
    verbs = ["parses", "rejects", "round_trips", "handles", "compacts", "orders", "reads", "writes", "flushes", "skips", "merges", "splits"]
    nouns = ["empty_input", "unicode_keys", "large_values", "nested_blocks", "truncated_header", "duplicate_keys", "bad_checksum", "short_reads",
             "trailing_newline", "negative_offsets", "wide_rows", "sorted_runs", "tombstones", "snapshots", "bloom_filter", "index_pages"]
    names, seen = [], set()
    for i in range(n):
        base = f"{modules[i % len(modules)]}::tests::{verbs[(i * 7) % len(verbs)]}_{nouns[(i * 5 + i // 16) % len(nouns)]}"
        name, k = base, 1
        while name in seen:
            k += 1
            name = f"{base}_{k}"
        seen.add(name)
        names.append(name)
    return names


def cmake_progress(log: Log, rng: random.Random, n: int, targets: list[str], warnings: dict[int, list[str]] | None = None) -> None:
    files = ["core/arena", "core/config", "geo/polygon", "geo/ring", "geo/bbox", "spatial/rtree", "spatial/quadtree", "spatial/index", "net/http",
             "net/pool", "io/tile_reader", "io/tile_writer", "solver/lp_presolve", "solver/simplex", "solver/branch", "util/strings", "util/logging"]
    for i in range(n):
        pct = min(99, (i + 1) * 100 // (n + 1))
        target = targets[i % len(targets)]
        source = files[(i * 3) % len(files)] + (f"_{i // len(files)}" if i >= len(files) else "")
        log.add(f"[{pct:3d}%] Building CXX object src/CMakeFiles/{target}.dir/{source}.cpp.o")
        for extra in (warnings or {}).get(i, []):
            log.add(extra)


def composer_installing(log: Log, start: int, stop: int) -> None:
    for package in COMPOSER[start:stop]:
        log.add(f"  - Installing {package}: Loading from cache")
