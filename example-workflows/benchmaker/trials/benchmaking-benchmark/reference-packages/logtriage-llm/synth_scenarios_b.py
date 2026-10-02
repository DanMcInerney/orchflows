"""Synthetic Travis logs, part two: Go, Rust, C++ and PHP repositories (fictional), and three candidates
the admission screen rejects."""
from __future__ import annotations

import random

from synth_noise import cargo_compiling, cargo_tests, cmake_progress, composer_installing, go_downloads, go_ok
from synth_scenarios_a import mvn_header, start
from synth_travis import CLEAR, ESC, Log, stopped_for_silence

GO_PKGS = ["cmd/gateway", "internal/admin", "internal/auth", "internal/cache", "internal/config", "internal/metrics", "internal/middleware",
           "internal/router", "internal/tls", "internal/upstream", "pkg/client"]
MOD = "github.com/corvid-systems/gateway"


def go_setup(log: Log, version: str) -> None:
    log.extend([f"$ gimme {version}", f"go version go{version}.1 linux/amd64", "$ go version", f"go version go{version}.1 linux/amd64", "$ export GO111MODULE=on",
                "$ go env GOPATH", "/home/travis/gopath"])


# ---------------------------------------------------------------- Go

def t09() -> Log:
    rng, log = start(990000501, "corvid-systems/gateway", "go", "Thu Apr 11 07:48:19 UTC 2019", 1554968899)
    go_setup(log, "1.12")
    with log.step("go mod download", fold="install", seconds=23, exit=0):
        go_downloads(log, rng, 34)
    with log.step("go test -race ./...", seconds=96, exit=2):
        go_ok(log, rng, [f"{MOD}/{p}" for p in GO_PKGS[:7]])
        with log.chunk():
            log.extend([f"# {MOD}/internal/router [{MOD}/internal/router.test]", "internal/router/router_test.go:88:17: undefined: newLimiter",
                        "internal/router/router_test.go:131:3: too many arguments in call to s.registerRoute", "\thave (string, http.HandlerFunc, middleware.Chain)",
                        "\twant (string, http.HandlerFunc)", f"FAIL\t{MOD}/internal/router [build failed]"])
        go_ok(log, rng, [f"{MOD}/{p}" for p in GO_PKGS[8:]])
        log.add("FAIL")
    return log


def goroutines(log: Log, rng: random.Random, count: int, root: str) -> None:
    """The rest of a go test timeout dump: idle goroutines with their stacks."""
    def ptr() -> str:
        return f"0xc000{rng.getrandbits(20):05x}"

    app = "/home/travis/gopath/src/github.com/corvid-systems/gateway/internal/upstream"
    shapes = [("chan receive", lambda: [f"testing.(*T).Run({ptr()}, 0x8e3c05, 0x15, 0x8fb2a8, 0x4a1dd6)", f"	{root}/testing/testing.go:961 +0x377",
                                f"testing.runTests.func1({ptr()})", f"	{root}/testing/testing.go:1202 +0x78"]),
              ("select", lambda: [f"{MOD}/internal/upstream.(*Pool).reaper({ptr()})", f"	{app}/pool.go:187 +0x11b",
                          f"created by {MOD}/internal/upstream.NewPool", f"	{app}/pool.go:61 +0x1d9"]),
              ("semacquire", lambda: [f"sync.runtime_SemacquireMutex({ptr()}, {ptr()}, 0x1)", f"	{root}/runtime/sema.go:71 +0x3d",
                              f"{MOD}/internal/upstream.(*Pool).Acquire({ptr()}, 0x9a1d20, {ptr()}, 0x0, 0x0, 0x0)", f"	{app}/pool.go:112 +0x1f7"]),
              ("IO wait", lambda: [f"internal/poll.runtime_pollWait({ptr()}, 0x72, 0xffffffffffffffff)", f"	{root}/runtime/netpoll.go:173 +0x66",
                           f"net.(*conn).Read({ptr()}, {ptr()}, 0x1000, 0x1000, 0x0, 0x0, 0x0)", f"	{root}/net/net.go:177 +0x69"])]
    for i in range(count):
        kind, body = shapes[i % len(shapes)]
        log.add(f"goroutine {rng.randint(5, 900)} [{kind}, 4 minutes]:")
        for line in body():
            log.add(line)
        log.add()


def t10() -> Log:
    rng, log = start(990000502, "corvid-systems/gateway", "go", "Tue Sep 10 18:21:43 UTC 2019", 1568139703)
    go_setup(log, "1.13")
    with log.step("go mod download", fold="install", seconds=19, exit=0):
        go_downloads(log, rng, 28)
    root = "/home/travis/.gimme/versions/go1.13.linux.amd64/src"
    with log.step("go test -race -timeout 5m ./...", seconds=318, exit=1):
        go_ok(log, rng, [f"{MOD}/{p}" for p in GO_PKGS[:9]])
        with log.chunk():
            log.extend(["panic: test timed out after 5m0s", "running tests:", "\tTestPoolDrainUnderLoad (5m0s)", "", "goroutine 71 [running]:", "testing.(*M).startAlarm.func1()",
                        f"\t{root}/testing/testing.go:1377 +0xdf", "created by time.goFunc", f"\t{root}/time/sleep.go:169 +0x44"])
        log.add()
        goroutines(log, rng, 22, root)
        log.add(f"FAIL\t{MOD}/internal/upstream\t300.063s")
        go_ok(log, rng, [f"{MOD}/{p}" for p in GO_PKGS[10:]])
        log.add("FAIL")
    return log


# ---------------------------------------------------------------- Rust

def rust_setup(log: Log) -> None:
    log.extend(["$ rustup --version", "rustup 1.18.3 (435397f48 2019-05-22)", "$ rustc --version", "rustc 1.36.0 (a53f9df32 2019-07-03)", "$ cargo --version", "cargo 1.36.0 (c4fcfb725 2019-05-15)"])


def t11() -> Log:
    rng, log = start(990000601, "quarry-dev/quarry", "rust", "Thu Aug  8 12:30:09 UTC 2019", 1565267409)
    rust_setup(log)
    with log.step("cargo build --all", seconds=121, exit=101):
        log.extend(["    Updating crates.io index", " Downloading crates ..."] + [f"  Downloaded {c}" for c in ("libc v0.2.51", "serde v1.0.91", "syn v0.15.34", "regex v1.1.5", "failure v0.1.5", "error-chain v0.12.1")])
        cargo_compiling(log, rng, 150)
        log.extend(["   Compiling quarry v0.8.2 (/home/travis/build/quarry-dev/quarry)", "warning: unused import: `std::collections::HashMap`", " --> src/loader.rs:3:5", "  |",
                    "3 | use std::collections::HashMap;", "  |     ^^^^^^^^^^^^^^^^^^^^^^^^^", "  |", "  = note: #[warn(unused_imports)] on by default", ""])
        with log.chunk():
            log.extend(["error[E0382]: borrow of moved value: `config`", "  --> src/loader.rs:57:20", "   |", "51 |     let config = Config::load(path)?;",
                        "   |         ------ move occurs because `config` has type `Config`, which does not implement the `Copy` trait", "52 |     let handle = spawn_worker(config);",
                        "   |                               ------ value moved here", "...", '57 |     println!("{}", config.name);',
                        "   |                    ^^^^^^^^^^^ value borrowed here after move"])
        log.extend(["", "error: aborting due to previous error", "", "For more information about this error, try `rustc --explain E0382`.",
                    "error: Could not compile `quarry`.", "", "To learn more, run the command again with --verbose."])
    return log


def t12() -> Log:
    rng, log = start(990000602, "quarry-dev/quarry", "rust", "Mon Aug 26 15:02:51 UTC 2019", 1566831771)
    rust_setup(log)
    with log.step("cargo test --all --no-fail-fast", seconds=203, exit=101):
        cargo_compiling(log, rng, 60)
        log.extend(["    Finished dev [unoptimized + debuginfo] target(s) in 1m 48s", "     Running target/debug/deps/quarry-3f9a1c7be02d4a65", "", "running 414 tests"])
        names = cargo_tests(["codec", "index", "net", "parser", "store"], 410)
        names = sorted(names)
        names.insert(7, "net::tests::error_display")
        names.insert(40, "parser::tests::test_failure_modes")
        names += ["parser::tests::rejects_unterminated_string", "store::tests::compacts_on_reopen"]
        names = sorted(names)
        for name in names:
            bad = name in ("parser::tests::rejects_unterminated_string", "store::tests::compacts_on_reopen")
            log.add(f"test {name} ... " + ("FAILED" if bad else "ok"))
        log.extend(["", "failures:", ""])
        with log.chunk():
            log.extend(["---- parser::tests::rejects_unterminated_string stdout ----", "thread 'parser::tests::rejects_unterminated_string' panicked at 'assertion failed: `(left == right)`",
                        "  left: `Err(UnexpectedEof)`,", " right: `Err(Unterminated { line: 3 })`', src/parser/tests.rs:212:9",
                        "note: Run with `RUST_BACKTRACE=1` environment variable to display a backtrace.", "", "---- store::tests::compacts_on_reopen stdout ----",
                        "thread 'store::tests::compacts_on_reopen' panicked at 'called `Result::unwrap()` on an `Err` value: Io(Os { code: 2, kind: NotFound, message: \"No such file or directory\" })', src/libcore/result.rs:1084:5"])
        log.extend(["", "", "failures:", "    parser::tests::rejects_unterminated_string", "    store::tests::compacts_on_reopen", "",
                    "test result: FAILED. 412 passed; 2 failed; 0 ignored; 0 measured; 0 filtered out", ""])
        log.extend(["     Running target/debug/deps/roundtrip-9c2a1f40e7b3d581", "", "running 1500 tests"])
        for i in range(1500):
            log.add(f"test cases::case_{i:03d}_{('flush', 'reopen', 'compact', 'scan')[i % 4]} ... ok")
        log.extend(["", "test result: ok. 1500 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out", "", "   Doc-tests quarry", "", "running 6 tests"])
        log.extend([f"test src/lib.rs - Store::{n} (line {10 + i * 14}) ... ok" for i, n in enumerate(("open", "get", "put", "scan", "compact", "close"))])
        log.extend(["", "test result: ok. 6 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out", "", "error: 1 target failed:", "    `--lib`"])
    log.done(101)
    return log


# ---------------------------------------------------------------- C++

def cmake_configure(log: Log) -> None:
    log.extend(["-- The C compiler identification is GNU 5.4.0", "-- The CXX compiler identification is GNU 5.4.0", "-- Check for working C compiler: /usr/bin/cc",
                "-- Check for working C compiler: /usr/bin/cc -- works", "-- Detecting C compiler ABI info - done", "-- Check for working CXX compiler: /usr/bin/c++",
                "-- Check for working CXX compiler: /usr/bin/c++ -- works", "-- Found Boost: /usr/include (found version \"1.58.0\") found components:  system filesystem",
                "-- Found GTest: /usr/lib/libgtest.a", "-- Configuring done", "-- Generating done", "-- Build files have been written to: /home/travis/build/meridian/meridian-engine/build"])


def t13() -> Log:
    rng, log = start(990000701, "meridian/meridian-engine", "cpp", "Tue Jul  2 20:14:36 UTC 2019", 1562098476)
    log.extend(["$ g++ --version", "g++ (Ubuntu 5.4.0-6ubuntu1~16.04.11) 5.4.0 20160609", "$ cmake --version", "cmake version 3.12.4"])
    with log.step("mkdir -p build && cd build && cmake -DCMAKE_BUILD_TYPE=Release ..", fold="before_script", seconds=4, exit=0):
        cmake_configure(log)
    root = "/home/travis/build/meridian/meridian-engine"
    warnings = {3: ["cc1plus: warning: command line option '-Wno-error=deprecated-declarations' is valid for C++/ObjC++ but not for C"],
                61: [f"{root}/src/io/tile_reader.cpp: In member function 'bool meridian::io::TileReader::open(const string&)':",
                     f"{root}/src/io/tile_reader.cpp:41:5: warning: 'template<class> class std::auto_ptr' is deprecated [-Wdeprecated-declarations]",
                     "     std::auto_ptr<Header> header(new Header);", "     ^"],
                122: [f"{root}/src/net/http.cpp:77:21: warning: comparison between signed and unsigned integer expressions [-Wsign-compare]", "     if (n < body.size()) {", "           ^"]}
    with log.step("make -j2", seconds=187, exit=2):
        cmake_progress(log, rng, 240, ["geo", "engine", "spatial", "io"], warnings)
        log.extend(["[ 90%] Linking CXX static library libmeridian.a", "[ 90%] Built target meridian", "[ 93%] Building CXX object test/CMakeFiles/meridian_tests.dir/spatial_index_test.cpp.o",
                    "[ 96%] Building CXX object test/CMakeFiles/meridian_tests.dir/solver_test.cpp.o", "[ 98%] Linking CXX executable ../bin/meridian_tests"])
        with log.chunk():
            log.extend(["CMakeFiles/meridian_tests.dir/spatial_index_test.cpp.o: In function `SpatialIndexTest_BulkLoadKeepsOrder_Test::TestBody()':",
                        f"{root}/test/spatial_index_test.cpp:61: undefined reference to `meridian::spatial::Index::bulkLoad(std::vector<meridian::Entry, std::allocator<meridian::Entry> > const&)'",
                        "collect2: error: ld returned 1 exit status"])
        log.extend(["test/CMakeFiles/meridian_tests.dir/build.make:233: recipe for target 'bin/meridian_tests' failed", "make[2]: *** [bin/meridian_tests] Error 1",
                    "CMakeFiles/Makefile2:156: recipe for target 'test/CMakeFiles/meridian_tests.dir/all' failed", "make[1]: *** [test/CMakeFiles/meridian_tests.dir/all] Error 2",
                    "Makefile:129: recipe for target 'all' failed", "make: *** [all] Error 2"])
    log.done(2)
    return log


def t14() -> Log:
    rng, log = start(990000702, "meridian/meridian-engine", "cpp", "Fri Nov 15 06:40:12 UTC 2019", 1573800012)
    log.extend(["$ g++ --version", "g++ (Ubuntu 5.4.0-6ubuntu1~16.04.11) 5.4.0 20160609"])
    with log.step("mkdir -p build && cd build && cmake -DCMAKE_BUILD_TYPE=Release ..", fold="before_script", seconds=4, exit=0):
        cmake_configure(log)
    with log.step("make", seconds=600):
        cmake_progress(log, rng, 760, ["geo", "engine", "spatial", "io", "solver"])
        log.add("[ 91%] Building CXX object src/solver/CMakeFiles/solver.dir/lp_presolve_tables.cpp.o")
        log.add()
        with log.chunk():
            stopped_for_silence(log)
    return log


# ---------------------------------------------------------------- PHP

def php_setup(log: Log, version: str) -> None:
    log.extend([f"$ phpenv global {version} 2>/dev/null", f"$ php --version", f"PHP {version}.4 (cli) (built: Apr  9 2019 08:10:21) ( NTS )", "$ composer --version",
                "Composer version 1.8.4 2019-02-11 10:52:10"])


def t15() -> Log:
    rng, log = start(990000801, "opal-php/opal", "php", "Thu Apr 18 10:25:30 UTC 2019", 1555583130)
    php_setup(log, "7.3")
    with log.step("composer install --prefer-dist --no-interaction", fold="install", seconds=38, exit=0):
        log.extend(["Loading composer repositories with package information", "Installing dependencies (including require-dev) from lock file", "Package operations: 40 installs, 0 updates, 0 removals",
                    "  - Installing psr/log (1.1.0): Failed to download psr/log from dist: The zip extension and unzip command are both missing, skipping.",
                    "The php.ini used by the CLI is indicating that the zip extension is not installed.", "    Now trying to download from source",
                    "  - Installing psr/log (1.1.0): Cloning 6c001f1daa"])
        composer_installing(log, 1, 40)
        log.extend(["symfony/console suggests installing symfony/lock", "Generating autoload files"])
    with log.step("vendor/bin/phpunit", seconds=14, exit=1):
        log.extend(["PHPUnit 7.5.8 by Sebastian Bergmann and contributors.", "", "Runtime:       PHP 7.3.4 with Xdebug 2.7.1", "Configuration: /home/travis/build/opal-php/opal/phpunit.xml.dist", ""])
        for i, done in enumerate((60, 120, 180, 240)):
            row = "." * 60
            if i == 2:
                row = row[:27] + "F" + row[28:]
            log.add(f"{row}  {done:3d} / 312 ({done * 100 // 312:3d}%)")
        log.extend(["." * 52 + "     312 / 312 (100%)", "", "Time: 11.4 seconds, Memory: 38.00 MB", "", "There was 1 failure:", ""])
        with log.chunk():
            log.extend(["1) Opal\\Tests\\Http\\RouterTest::testResolvesNamedRouteWithParameters", "Failed asserting that two strings are equal.", "--- Expected", "+++ Actual", "@@ @@",
                        "-'/users/42/posts/7'", "+'/users/42/posts/7?draft=1'", "", "/home/travis/build/opal-php/opal/tests/Http/RouterTest.php:118"])
        log.extend(["", "FAILURES!", "Tests: 312, Assertions: 1145, Failures: 1."])
    log.done(1)
    return log


def t16() -> Log:
    rng, log = start(990000802, "opal-php/opal", "php", "Wed May 22 17:09:44 UTC 2019", 1558544984)
    php_setup(log, "7.2")
    with log.step("composer install --prefer-dist --no-interaction", fold="install", seconds=31, exit=0):
        log.extend(["Loading composer repositories with package information", "Installing dependencies (including require-dev) from lock file", "Package operations: 40 installs, 0 updates, 0 removals"])
        composer_installing(log, 0, 40)
        log.add("Generating autoload files")
    root = "/home/travis/build/opal-php/opal"
    with log.step("vendor/bin/phpcs --standard=PSR2 src || true", seconds=3):
        for name, rows in (("Cache/RedisStore.php", [(23, "Expected 1 space after closing brace; newline found"), (41, "Opening brace of a class must be on the line after the definition"), (87, "Line exceeds 120 characters; contains 134 characters")]),
                           ("Http/Router.php", [(12, "Each PHP statement must be on a line by itself"), (209, "Visibility must be declared on method \"match\"")]),
                           ("Support/Arr.php", [(9, "Namespace declaration must be followed by a blank line")])):
            log.extend(["", f"FILE: {root}/src/{name}", "----------------------------------------------------------------------",
                        f"FOUND {len(rows)} ERRORS AFFECTING {len(rows)} LINES", "----------------------------------------------------------------------"])
            log.extend([f" {line:3d} | ERROR | [x] {text}" for line, text in rows])
            log.add("----------------------------------------------------------------------")
        log.extend(["PHPCBF CAN FIX THE 3 MARKED SNIFF VIOLATIONS AUTOMATICALLY", "----------------------------------------------------------------------", "", "Time: 412ms; Memory: 8MB", ""])
    with log.step("vendor/bin/phpunit", seconds=1, exit=255):
        trace = [f"#0 {root}/vendor/phpunit/phpunit/src/Util/Configuration.php(412): require_once()",
                 f"#1 {root}/vendor/phpunit/phpunit/src/TextUI/Command.php(299): PHPUnit\\Util\\Configuration->handlePHPConfiguration()",
                 f"#2 {root}/vendor/phpunit/phpunit/src/TextUI/Command.php(212): PHPUnit\\TextUI\\Command->handleArguments(Array)",
                 f"#3 {root}/vendor/phpunit/phpunit/src/TextUI/Command.php(162): PHPUnit\\TextUI\\Command->run(Array, true)", f"#4 {root}/vendor/phpunit/phpunit/phpunit(17): PHPUnit\\TextUI\\Command::main()", "#5 {main}"]
        with log.chunk():
            log.add(f"PHP Fatal error:  Uncaught Error: Class 'Opal\\Cache\\RedisStore' not found in {root}/tests/bootstrap.php:23")
            log.add("Stack trace:")
            log.extend(trace)
            log.add(f"  thrown in {root}/tests/bootstrap.php on line 23")
        log.add(f"Fatal error: Uncaught Error: Class 'Opal\\Cache\\RedisStore' not found in {root}/tests/bootstrap.php:23")
        log.add("Stack trace:")
        log.extend(trace)
        log.add(f"  thrown in {root}/tests/bootstrap.php on line 23")
    log.done(255)
    return log


# ---------------------------------------------------------------- candidates the screen rejects

def r1() -> Log:
    """A job that stopped at checkout: the whole log is a few lines."""
    rng = random.Random(990000901)
    log = Log(rng, epoch=1560000000)
    log.add("Using worker: worker-linux-docker-5e6a2c1b.prod.travis-ci.org:travis-linux-4", "\n")
    log.add()
    log.add(f"travis_fold:start:git.checkout{CLEAR}")
    log.add(f"travis_time:start:0a1b2c3d{CLEAR}$ git clone --depth=50 --branch=master https://github.com/nightowl/deploy-scripts.git nightowl/deploy-scripts")
    log.add("Cloning into 'nightowl/deploy-scripts'...")
    with log.chunk():
        log.extend(["fatal: could not read Username for 'https://github.com': terminal prompts disabled", "fatal: could not read Username for 'https://github.com': terminal prompts disabled",
                    "The command \"git clone --depth=50 --branch=master https://github.com/nightowl/deploy-scripts.git nightowl/deploy-scripts\" failed 3 times."])
    log.extend([f"travis_time:end:0a1b2c3d:start=1560000001000000000,finish=1560000012000000000,duration=11000000000{CLEAR}travis_fold:end:git.checkout{CLEAR}",
                f"{ESC}[31;1mThe command \"git clone --depth=50 --branch=master https://github.com/nightowl/deploy-scripts.git nightowl/deploy-scripts\" failed and exited with 128 during {ESC}[0m.", "",
                "Your build has been stopped."])
    return log


def r2() -> Log:
    """A registry pull retried twelve times: the failure text occurs twelve times."""
    rng, log = start(990000902, "corvid-systems/gateway", "go", "Mon Jun  3 03:12:05 UTC 2019", 1559531525)
    go_setup(log, "1.12")
    with log.step("docker pull registry.corvid.example/gateway-testbed:latest", seconds=190, exit=1, phase="before_install"):
        for attempt in range(1, 13):
            log.add(f"Retrying pull of registry.corvid.example/gateway-testbed:latest (attempt {attempt}/12)")
            with log.chunk():
                log.add("Error response from daemon: Get https://registry.corvid.example/v2/: net/http: TLS handshake timeout")
    return log


def r3() -> Log:
    """A Maven test failure whose label was copied from a Gradle build: the label text is not in the log."""
    rng, log = start(990000903, "tidewater/ledger-core", "java", "Sun Jun 23 22:03:18 UTC 2019", 1561327398)
    with log.step("mvn test -B -V", seconds=70, exit=1):
        mvn_header(log)
        log.extend(["[INFO] Running io.tidewater.ledger.tax.VatCalculatorTest", "[ERROR] Tests run: 4, Failures: 1, Errors: 0, Skipped: 0, Time elapsed: 0.091 s <<< FAILURE! - in io.tidewater.ledger.tax.VatCalculatorTest"])
        with log.chunk():
            log.extend(["[ERROR] roundsHalfUp  Time elapsed: 0.012 s  <<< FAILURE!", "org.opentest4j.AssertionFailedError: expected: <10.05> but was: <10.04>",
                        "\tat io.tidewater.ledger.tax.VatCalculatorTest.roundsHalfUp(VatCalculatorTest.java:44)"])
        log.extend(["[INFO] BUILD FAILURE"])
    log.done(1)
    return log


R3_LABEL = "FAILURE: Build failed with an exception.\n\n* What went wrong:\nExecution failed for task ':app:compileDebugJavaWithJavac'.\n> Compilation failed; see the compiler error output for details."

SCENARIOS = [
    dict(build=990000501, make=t09, language="Go", repo="corvid-systems/gateway", family="compile-error", keywords="build failed, undefined, FAIL", expert_minutes=2,
         difficulty="A go test compile error between passing packages; 'github.com/pkg/errors' in the download lines matches an error search first, and the final FAIL line is far from the cause."),
    dict(build=990000502, make=t10, language="Go", repo="corvid-systems/gateway", family="timeout", keywords="panic, timed out, goroutine", expert_minutes=4,
         difficulty="A go test timeout panic followed by a 190-line goroutine dump; the header and running-tests line name the stuck test, and everything after them is evidence for it, not the failure."),
    dict(build=990000601, make=t11, language="Rust", repo="quarry-dev/quarry", family="compile-error", keywords="error[E0382], borrow of moved value", expert_minutes=3,
         difficulty="A borrow-checker error after a long compile listing that names the crates failure and error-chain, with a warning block just before it and a summary after."),
    dict(build=990000602, make=t12, language="Rust", repo="quarry-dev/quarry", family="test-failure", keywords="failures, panicked, FAILED", expert_minutes=4,
         difficulty="Two failing unit tests among about 1,900 test lines in two test binaries; the failures section is followed by 1,500 passing integration tests, so it is far from the end."),
    dict(build=990000701, make=t13, language="C++", repo="meridian/meridian-engine", family="compile-error", keywords="undefined reference, collect2, ld returned", expert_minutes=3,
         difficulty="A three-line linker error at the end of a long CMake build; compiler warnings mention errors earlier, and make's recipe-failed lines come after the cause."),
    dict(build=990000702, make=t14, language="C++", repo="meridian/meridian-engine", family="timeout", keywords="No output has been received, terminated", expert_minutes=2,
         difficulty="Travis ends a silent build after ten minutes; the cause is the platform's message at the end of 760 progress lines, with no compiler or test output to point at."),
    dict(build=990000801, make=t15, language="PHP", repo="opal-php/opal", family="test-failure", keywords="There was 1 failure, Failed asserting", expert_minutes=3,
         difficulty="One PHPUnit assertion failure; composer's 'Failed to download ... from dist' warning matches an error search long before it."),
    dict(build=990000802, make=t16, language="PHP", repo="opal-php/opal", family="decoy-errors", keywords="Fatal error, Uncaught Error, not found", expert_minutes=4,
         difficulty="phpcs prints a page of 'ERROR' style violations that do not fail the build (|| true); the cause is a later fatal error that PHP prints twice."),
]
REJECTED = [
    dict(build=990000901, make=r1, language="Shell", repo="nightowl/deploy-scripts", family="other-failure", keywords="fatal, terminal prompts disabled"),
    dict(build=990000902, make=r2, language="Go", repo="corvid-systems/gateway", family="other-failure", keywords="Error response from daemon, TLS handshake timeout"),
    dict(build=990000903, make=r3, language="Java", repo="tidewater/ledger-core", family="test-failure", keywords="FAILURE, Build failed, Gradle", label=R3_LABEL),
]
