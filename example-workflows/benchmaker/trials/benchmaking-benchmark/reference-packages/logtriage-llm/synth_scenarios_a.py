"""Synthetic Travis logs, part one: Python, Java, JavaScript and Ruby repositories (fictional)."""
from __future__ import annotations

import random

from synth_noise import (bundler_using, jest_files, JEST_FAIL, maven_downloads, node_ids, pip_install,
                         pytest_lines)
from synth_travis import ESC, Log, checkout, colour, preamble


def start(build_id: int, repo: str, language: str, date: str, epoch: int, *, dist: str = "xenial") -> tuple[random.Random, Log]:
    rng = random.Random(build_id)
    log = Log(rng, epoch=epoch)
    preamble(log, rng, language=language, build_id=build_id, dist=dist, date=date)
    checkout(log, rng, repo)
    return rng, log


def py_setup(log: Log, version: str) -> None:
    log.add(f"$ source ~/virtualenv/python{version}/bin/activate")
    log.extend(["$ python --version", f"Python {version}.1", "$ pip --version",
                f"pip 18.1 from /home/travis/virtualenv/python{version}.1/lib/python{version}/site-packages/pip (python {version})"])


def mvn_header(log: Log) -> None:
    log.extend(["Apache Maven 3.6.0 (97c98ec64a1fdfee7767ce5ffb20918da4f719f3; 2018-10-24T18:41:47Z)", "Maven home: /usr/local/maven-3.6.0",
                "Java version: 1.8.0_201, vendor: Oracle Corporation, runtime: /usr/lib/jvm/java-8-oracle/jre",
                'Default locale: en_US, platform encoding: UTF-8', 'OS name: "linux", version: "4.15.0-1028-gcp", arch: "amd64", family: "unix"',
                "[INFO] Scanning for projects...", "[INFO] ", "[INFO] ------------------< io.tidewater.ledger:ledger-core >-------------------",
                "[INFO] Building ledger-core 2.7.0-SNAPSHOT", "[INFO] --------------------------------[ jar ]---------------------------------"])


# ---------------------------------------------------------------- Python

def t01() -> Log:
    rng, log = start(990000101, "harbor-labs/pyparcel", "python", "Mon Mar 25 16:43:24 UTC 2019", 1553532204)
    py_setup(log, "3.7")
    with log.step("pip install -r requirements-dev.txt", fold="install.1", seconds=41, exit=0):
        pip_install(log, rng, [("requests", "2.21.0"), ("pytest", "4.4.0"), ("pytest-cov", "2.6.1"), ("pytest-mock", "1.10.4"), ("attrs", "19.1.0"),
                               ("more-itertools", "7.0.0"), ("pluggy", "0.9.0"), ("py", "1.8.0"), ("coverage", "4.5.3"), ("six", "1.12.0"),
                               ("responses", "0.10.5"), ("freezegun", "0.3.11"), ("python-dateutil", "2.8.0"), ("cookies", "2.2.1")])
    with log.step("pip install -e .", fold="install.2", seconds=6, exit=0):
        log.extend(["Obtaining file:///home/travis/build/harbor-labs/pyparcel", "Installing collected packages: pyparcel",
                    "  Running setup.py develop for pyparcel", "Successfully installed pyparcel"])
    modules = {"test_address": 96, "test_carrier": 110, "test_customs": 64, "test_dimensions": 72, "test_label": 120,
               "test_manifest": 98, "test_rates": 130, "test_routing": 70, "test_tracking": 68, "test_webhook": 56}
    verbs = ["parse", "validate", "normalize", "format", "reject", "accept", "round", "convert", "merge", "sort", "filter", "serialize"]
    nouns = ["street_number", "postal_code", "country_alias", "weight_units", "label_size", "service_level", "insured_value", "customs_value",
             "tracking_code", "pickup_window", "manifest_totals", "address_line", "rate_quote", "dimension_units"]
    ids = node_ids(modules, verbs, nouns, {("test_address", 12): "test_invalid_zip_error_message", ("test_carrier", 31): "test_delivery_failure_is_retried",
                                           ("test_manifest", 61): "test_manifest_totals_use_decimal_rounding"})
    bad = ids.index("tests/test_manifest.py::test_manifest_totals_use_decimal_rounding")
    with log.step("pytest -v --cov=pyparcel", seconds=91, exit=1):
        log.extend(["============================= test session starts ==============================",
                    "platform linux -- Python 3.7.1, pytest-4.4.0, py-1.8.0, pluggy-0.9.0 -- /home/travis/virtualenv/python3.7.1/bin/python",
                    "cachedir: .pytest_cache", "rootdir: /home/travis/build/harbor-labs/pyparcel, inifile: setup.cfg",
                    "plugins: cov-2.6.1, mock-1.10.4", f"collecting ... collected {len(ids)} items", ""])
        pytest_lines(log, ids, failing=frozenset({bad}))
        log.add()
        log.add("=================================== FAILURES ===================================")
        with log.chunk():
            log.add(colour(colour("_________________ test_manifest_totals_use_decimal_rounding ____________________", "1"), "31"))
            log.extend(["", "make_manifest = <function make_manifest.<locals>.build at 0x7f2c6a1d8950>", "",
                        colour("    def test_manifest_totals_use_decimal_rounding(make_manifest):", "1"),
                        colour('        manifest = make_manifest(items=[("0.10", 3), ("0.20", 3)])', "1"),
                        colour('>       assert manifest.total == Decimal("0.90")', "1"),
                        f"{ESC}[1m{ESC}[31mE       AssertionError: assert Decimal('0.9000000000000000055511151231257827') == Decimal('0.90'){ESC}[0m",
                        f"{ESC}[1m{ESC}[31mE        +  where Decimal('0.9000000000000000055511151231257827') = <pyparcel.manifest.Manifest object at 0x7f2c6a1e1d68>.total{ESC}[0m",
                        f"{ESC}[1m{ESC}[31mE        +  and   Decimal('0.90') = Decimal('0.90'){ESC}[0m", "",
                        f"{ESC}[1m{ESC}[31mtests/test_manifest.py{ESC}[0m:57: AssertionError"])
        log.add(f"{ESC}[33m=============================== warnings summary ==============================={ESC}[0m")
        log.extend(["tests/test_label.py::test_label_png_has_300_dpi", "  /home/travis/virtualenv/python3.7.1/lib/python3.7/site-packages/PIL/Image.py:2800: DeprecationWarning: ",
                    "    'frombuffer' is deprecated", "", "-- Docs: https://docs.pytest.org/en/latest/warnings.html", ""])
        log.add("---------- coverage: platform linux, python 3.7.1-final-0 -----------")
        log.extend(["Name                            Stmts   Miss  Cover", "---------------------------------------------------"])
        for mod, stmts, miss in [("__init__", 12, 0), ("address", 188, 6), ("carrier/__init__", 41, 0), ("carrier/fedex", 214, 11), ("carrier/ups", 207, 9),
                                 ("carrier/usps", 176, 12), ("customs", 133, 5), ("dimensions", 88, 2), ("label", 241, 14), ("manifest", 152, 3),
                                 ("rates", 266, 7), ("routing", 119, 2), ("tracking", 98, 0), ("webhook", 85, 0)]:
            log.add(f"pyparcel/{mod}.py".ljust(32) + f"{stmts:5d}{miss:7d}{100 - miss * 100 // stmts:6d}%")
        log.extend(["---------------------------------------------------", "TOTAL                            2020     71    96%"])
        log.add(colour(colour(f"======== 1 failed, {len(ids) - 1} passed, 3 warnings in 91.20 seconds ========", "1"), "31"))
    with log.step("cat tests/output/last_run.log", seconds=0.1):
        for i in range(54):
            stamp = f"2019-03-25 17:{12 + i // 6:02d}:{(i * 7) % 60:02d},{rng.randint(100, 999)}"
            line = rng.choice(["DEBUG pyparcel.http: GET https://sandbox.carrier.test/v1/rates 200 ({:.3f}s)", "DEBUG pyparcel.http: POST https://sandbox.carrier.test/v1/labels 201 ({:.3f}s)",
                               "INFO pyparcel.manifest: closed manifest M-{:04d} with 3 items", "WARNING pyparcel.http: retrying after connection error (attempt 2/3) in {:.1f}s"])
            log.add(f"{stamp} " + (line.format(rng.uniform(0.05, 0.4)) if "{:." in line else line.format(rng.randint(1, 9999))))
    log.done(1)
    return log


def t02() -> Log:
    rng, log = start(990000102, "harbor-labs/pyparcel", "python", "Tue Dec  1 10:12:03 UTC 2020", 1606817523, dist="bionic")
    py_setup(log, "3.8")
    log.extend(["$ pip install -U pip", "Requirement already up-to-date: pip in /home/travis/virtualenv/python3.8.1/lib/python3.8/site-packages (20.3.1)"])
    with log.step("pip install -r requirements.txt", fold="install.1", seconds=312, exit=1, phase="install") as _:
        for name, version, size in [("boto3", "1.9.253", "128 kB"), ("botocore", "1.12.0", "4.9 MB"), ("requests", "2.25.0", "61 kB"), ("jsonschema", "3.2.0", "56 kB"),
                                    ("python-dateutil", "2.8.1", "227 kB"), ("pydantic", "1.7.3", "2.5 MB")]:
            log.add(f"Collecting {name}=={version}" if name in ("boto3", "botocore") else f"Collecting {name}")
            log.add(f"  Downloading {name}-{version}-py2.py3-none-any.whl ({size})")
        log.add(f"{' ' * 4}|{'█' * 32}| 128 kB 6.1 MB/s", "\r")
        log.extend(["Collecting jmespath<1.0.0,>=0.7.1", "  Using cached jmespath-0.10.0-py2.py3-none-any.whl (24 kB)", "Collecting s3transfer<0.3.0,>=0.2.0",
                    "  Using cached s3transfer-0.2.1-py2.py3-none-any.whl (70 kB)", "Collecting docutils<0.16,>=0.10",
                    "  Using cached docutils-0.15.2-py3-none-any.whl (547 kB)",
                    "INFO: pip is looking at multiple versions of boto3 to determine which version is compatible with other requirements. This could take a while.",
                    "INFO: pip is looking at multiple versions of s3transfer to determine which version is compatible with other requirements. This could take a while.",
                    "INFO: This is taking longer than usual. You might need to provide the dependency resolver with stricter constraints to reduce runtime. "
                    "If you want to abort this run, you can press Ctrl + C to do so. To improve how pip performs, tell us what happened here: https://pip.pypa.io/surveys/backtracking"])
        with log.chunk():
            log.extend(["ERROR: Cannot install -r requirements.txt (line 1) and botocore==1.12.0 because these package versions have conflicting dependencies.", "",
                        "The conflict is caused by:", "    The user requested botocore==1.12.0", "    boto3 1.9.253 depends on botocore<1.13.0 and >=1.12.253", "",
                        "To fix this you could try to:", "1. loosen the range of package versions you've specified",
                        "2. remove package versions to allow pip attempt to solve the dependency conflict", "",
                        "ERROR: ResolutionImpossible: for help visit https://pip.pypa.io/en/latest/user_guide/#fixing-conflicting-dependencies"])
    return log


def e1() -> Log:
    rng, log = start(990000103, "harbor-labs/pyparcel", "python", "Thu Mar 28 09:14:50 UTC 2019", 1553764490)
    py_setup(log, "3.7")
    with log.step("pip install -r requirements-dev.txt", fold="install.1", seconds=33, exit=0):
        pip_install(log, rng, [("mypy", "0.670"), ("mypy-extensions", "0.4.1"), ("typed-ast", "1.3.4"), ("requests", "2.21.0"), ("attrs", "19.1.0"), ("six", "1.12.0")])
    with log.step("pip install -e .", fold="install.2", seconds=5, exit=0):
        log.extend(["Obtaining file:///home/travis/build/harbor-labs/pyparcel", "Installing collected packages: pyparcel", "  Running setup.py develop for pyparcel", "Successfully installed pyparcel"])
    with log.step("mypy pyparcel", seconds=6, exit=1):
        with log.chunk():
            log.add('pyparcel/carrier/ups.py:214: error: Argument 1 to "quote" has incompatible type "str"; expected "int"')
        log.add("Found 1 error in 1 file (checked 41 source files)")
    log.done(1)
    return log


# ---------------------------------------------------------------- Java

def t03() -> Log:
    rng, log = start(990000201, "tidewater/ledger-core", "java", "Fri Mar  1 08:55:02 UTC 2019", 1551430502)
    log.extend(["$ jdk_switcher use oraclejdk8", "Switching to Oracle JDK8 (java-8-oracle), JAVA_HOME will be set to /usr/lib/jvm/java-8-oracle",
                "$ java -Xmx32m -version", 'java version "1.8.0_201"', "Java(TM) SE Runtime Environment (build 1.8.0_201-b09)",
                "$ javac -J-Xmx32m -version", "javac 1.8.0_201"])
    with log.step("mvn install -DskipTests=true -Dmaven.javadoc.skip=true -B -V", fold="install", seconds=72, exit=1, phase="install"):
        mvn_header(log)
        maven_downloads(log, rng, 700)
        log.extend(["[INFO] ", "[INFO] --- maven-resources-plugin:3.1.0:resources (default-resources) @ ledger-core ---",
                    "[INFO] Using 'UTF-8' encoding to copy filtered resources.", "[INFO] Copying 6 resources", "[INFO] ",
                    "[INFO] --- maven-compiler-plugin:3.8.0:compile (default-compile) @ ledger-core ---", "[INFO] Changes detected - recompiling the module!",
                    "[INFO] Compiling 214 source files to /home/travis/build/tidewater/ledger-core/target/classes",
                    "[WARNING] /home/travis/build/tidewater/ledger-core/src/main/java/io/tidewater/ledger/legacy/XmlExporter.java: Some input files use or override a deprecated API.",
                    "[WARNING] /home/travis/build/tidewater/ledger-core/src/main/java/io/tidewater/ledger/legacy/XmlExporter.java: Recompile with -Xlint:deprecation for details."])
        src = "/home/travis/build/tidewater/ledger-core/src/main/java/io/tidewater/ledger/posting/PostingEngine.java"
        with log.chunk():
            log.extend(["[INFO] -------------------------------------------------------------", "[ERROR] COMPILATION ERROR : ", "[INFO] -------------------------------------------------------------",
                        f"[ERROR] {src}:[88,37] cannot find symbol", "  symbol:   method withCurrency(java.util.Currency)", "  location: class io.tidewater.ledger.model.Money",
                        f"[ERROR] {src}:[104,21] incompatible types: java.lang.String cannot be converted to io.tidewater.ledger.model.AccountId",
                        "[INFO] 2 errors ", "[INFO] -------------------------------------------------------------"])
        log.extend(["[INFO] ------------------------------------------------------------------------", "[INFO] Reactor Summary for ledger 2.7.0-SNAPSHOT:", "[INFO] ",
                    "[INFO] ledger-api ........................................ SUCCESS [  9.114 s]", "[INFO] ledger-core ....................................... FAILURE [ 14.382 s]",
                    "[INFO] ledger-server ..................................... SKIPPED", "[INFO] ------------------------------------------------------------------------",
                    "[INFO] BUILD FAILURE", "[INFO] ------------------------------------------------------------------------", "[INFO] Total time:  01:12 min",
                    "[INFO] Finished at: 2019-03-01T08:57:41Z", "[INFO] ------------------------------------------------------------------------",
                    "[ERROR] Failed to execute goal org.apache.maven.plugins:maven-compiler-plugin:3.8.0:compile (default-compile) on project ledger-core: Compilation failure: Compilation failure: ",
                    f"[ERROR] {src}:[88,37] cannot find symbol", "[ERROR]   symbol:   method withCurrency(java.util.Currency)", "[ERROR]   location: class io.tidewater.ledger.model.Money",
                    f"[ERROR] {src}:[104,21] incompatible types: java.lang.String cannot be converted to io.tidewater.ledger.model.AccountId",
                    "[ERROR] -> [Help 1]", "[ERROR] ", "[ERROR] To see the full stack trace of the errors, re-run Maven with the -e switch.",
                    "[ERROR] Re-run Maven using the -X switch to enable full debug logging.", "[ERROR] ",
                    "[ERROR] For more information about the errors and possible solutions, please read the following articles:",
                    "[ERROR] [Help 1] http://cwiki.apache.org/confluence/display/MAVEN/MojoFailureException", "[ERROR] ",
                    "[ERROR] After correcting the problems, you can resume the build with the command", "[ERROR]   mvn <goals> -rf :ledger-core"])
    return log


def t04() -> Log:
    rng, log = start(990000202, "tidewater/ledger-core", "java", "Fri Jun 14 09:36:41 UTC 2019", 1560505001)
    log.extend(["$ jdk_switcher use oraclejdk8", "Switching to Oracle JDK8 (java-8-oracle), JAVA_HOME will be set to /usr/lib/jvm/java-8-oracle"])
    with log.step("mvn test -B -V", seconds=161, exit=1):
        mvn_header(log)
        maven_downloads(log, rng, 150)
        log.extend(["[INFO] ", "[INFO] --- maven-surefire-plugin:2.22.1:test (default-test) @ ledger-core ---", "[INFO] ",
                    "[INFO] -------------------------------------------------------", "[INFO]  T E S T S", "[INFO] -------------------------------------------------------"])
        by_area = {"account": ["AccountRepository", "AccountBalance", "AccountHierarchy", "AccountLimits", "AccountMerge"],
                   "audit": ["AuditTrail", "AuditExport", "AuditRedaction", "AuditRetention"], "cache": ["EvictionCache", "LedgerCache"],
                   "export": ["CsvExporter", "XmlExporter", "PdfExporter", "SwiftMessageWriter"], "fx": ["RateTable", "CrossRate", "RoundingMode", "CurrencyConversion"],
                   "ingest": ["BatchImporter", "StatementParser", "DuplicateDetector", "Mt940Reader"], "jobs": ["JobScheduler", "NightlyCloseJob", "RetryPolicy"],
                   "posting": ["PostingEngine", "PostingValidator", "EntryReversal", "JournalBatch", "Idempotency"],
                   "reports": ["TrialBalance", "AgedReceivables", "CashFlowStatement", "TaxSummary"], "rules": ["RuleCompiler", "RuleOrdering", "RuleSandbox"],
                   "security": ["TokenVerifier", "RoleCheck", "TenantIsolation"], "tax": ["VatCalculator", "ReverseCharge", "TaxPeriod"]}
        classes = [f"io.tidewater.ledger.{area}.{name}Test" for area, names in by_area.items() for name in names]
        for cls in classes:
            log.add(f"[INFO] Running {cls}")
            if cls.endswith("EvictionCacheTest"):
                log.extend([f"[ERROR] Tests run: 6, Failures: 1, Errors: 0, Skipped: 0, Time elapsed: 2.211 s <<< FAILURE! - in {cls}",
                            "[ERROR] evictsOldestWhenFull  Time elapsed: 0.054 s  <<< FAILURE!", "java.lang.AssertionError: expected:<a> but was:<b>",
                            "\tat org.junit.Assert.fail(Assert.java:88)", "\tat org.junit.Assert.failNotEquals(Assert.java:834)",
                            "\tat org.junit.Assert.assertEquals(Assert.java:118)", "\tat io.tidewater.ledger.cache.EvictionCacheTest.evictsOldestWhenFull(EvictionCacheTest.java:71)", "",
                            f"[INFO] Running {cls}", f"[WARNING] Tests run: 6, Failures: 0, Errors: 0, Skipped: 0, Flakes: 1, Time elapsed: 2.4 s - in {cls}"])
            elif cls.endswith("PostingEngineTest"):
                with log.chunk():
                    log.extend([f"[ERROR] Tests run: 9, Failures: 1, Errors: 0, Skipped: 0, Time elapsed: 0.412 s <<< FAILURE! - in {cls}",
                                "[ERROR] reversesCompoundEntries  Time elapsed: 0.031 s  <<< FAILURE!", "org.opentest4j.AssertionFailedError: expected: <120.00> but was: <119.99>",
                                "\tat org.junit.jupiter.api.AssertionUtils.fail(AssertionUtils.java:55)", "\tat org.junit.jupiter.api.AssertionUtils.failNotEqual(AssertionUtils.java:62)",
                                "\tat org.junit.jupiter.api.Assertions.assertEquals(Assertions.java:182)", "\tat org.junit.jupiter.api.Assertions.assertEquals(Assertions.java:177)",
                                "\tat io.tidewater.ledger.posting.PostingEngineTest.reversesCompoundEntries(PostingEngineTest.java:203)",
                                "\tat java.base/jdk.internal.reflect.NativeMethodAccessorImpl.invoke0(Native Method)",
                                "\tat java.base/java.lang.reflect.Method.invoke(Method.java:566)", ""])
            else:
                log.add(f"[INFO] Tests run: {rng.randint(3, 24)}, Failures: 0, Errors: 0, Skipped: {rng.choice((0, 0, 0, 1))}, Time elapsed: {rng.uniform(0.05, 3):.3f} s - in {cls}")
        log.extend(["[INFO] ", "[INFO] Results:", "[INFO] ", "[WARNING] Flakes: ", "[WARNING] io.tidewater.ledger.cache.EvictionCacheTest.evictsOldestWhenFull",
                    "[ERROR]   Run 1: EvictionCacheTest.evictsOldestWhenFull:71 expected:<a> but was:<b>", "[INFO]   Run 2: PASS", "[INFO] ", "[ERROR] Failures: ",
                    "[ERROR]   PostingEngineTest.reversesCompoundEntries:203 expected: <120.00> but was: <119.99>", "[INFO] ",
                    "[ERROR] Tests run: 187, Failures: 1, Errors: 0, Skipped: 2, Flakes: 1", "[INFO] ",
                    "[INFO] ------------------------------------------------------------------------", "[INFO] BUILD FAILURE", "[INFO] ------------------------------------------------------------------------",
                    "[INFO] Total time:  02:41 min", "[INFO] Finished at: 2019-06-14T09:42:18Z", "[INFO] ------------------------------------------------------------------------",
                    "[ERROR] Failed to execute goal org.apache.maven.plugins:maven-surefire-plugin:2.22.1:test (default-test) on project ledger-core: There are test failures.",
                    "[ERROR] ", "[ERROR] Please refer to /home/travis/build/tidewater/ledger-core/target/surefire-reports for the individual test results.",
                    "[ERROR] Please refer to dump files (if any exist) [date].dump, [date]-jvmRun[N].dump and [date].dumpstream.", "[ERROR] -> [Help 1]", "[ERROR] ",
                    "[ERROR] To see the full stack trace of the errors, re-run Maven with the -e switch.", "[ERROR] Re-run Maven using the -X switch to enable full debug logging.", "[ERROR] ",
                    "[ERROR] For more information about the errors and possible solutions, please read the following articles:",
                    "[ERROR] [Help 1] http://cwiki.apache.org/confluence/display/MAVEN/MojoFailureException"])
    log.done(1)
    return log


# ---------------------------------------------------------------- JavaScript

def nvm_setup(log: Log, node: str, npm: str) -> None:
    log.add(f"$ nvm install {node.split('.')[0]}")
    log.add(f"Downloading and installing node v{node}...")
    log.add(f"Downloading https://nodejs.org/dist/v{node}/node-v{node}-linux-x64.tar.xz...")
    log.add("#" * 8 + " " * 60 + "11.4%\r" + "#" * 44 + " " * 24 + "62.0%\r" + "#" * 70 + "100.0%")
    log.add(f"Computing checksum with sha256sum\nChecksums matched!\nNow using node v{node} (npm v{npm})")
    log.extend(["$ node --version", f"v{node}", "$ npm --version", npm])


def t05() -> Log:
    rng, log = start(990000301, "kestrel-io/kestrel-ui", "node_js", "Tue Oct  8 13:20:17 UTC 2019", 1570540817)
    nvm_setup(log, "10.16.3", "6.9.0")
    with log.step("npm ci", fold="install", seconds=44, exit=0):
        log.extend(["npm WARN deprecated request@2.88.0: request has been deprecated, see https://github.com/request/request/issues/3142",
                    "npm WARN deprecated core-js@2.6.9: core-js@<3 is no longer maintained and not recommended for usage due to the number of issues.",
                    "npm WARN optional SKIPPING OPTIONAL DEPENDENCY: fsevents@1.2.9 (node_modules/fsevents)",
                    'npm WARN notsup SKIPPING OPTIONAL DEPENDENCY: Unsupported platform for fsevents@1.2.9: wanted {"os":"darwin","arch":"any"} (current: {"os":"linux","arch":"x64"})',
                    "added 1428 packages in 41.213s"])
    with log.step("npm test", seconds=48, exit=1):
        log.extend(["", "> kestrel-ui@3.4.0 test /home/travis/build/kestrel-io/kestrel-ui", "> jest --ci --verbose", ""])
        areas = ["Accordion", "Alert", "Avatar", "Badge", "Breadcrumb", "Button", "Card", "Checkbox", "Dropdown", "Form", "Grid", "Icon", "Input", "Modal", "Pagination",
                 "Popover", "Radio", "Select", "Slider", "Spinner", "Switch", "Tabs", "Tag", "Toast", "Tooltip", "Tree"]
        jest_files(log, rng, areas[:9], 7, 9)
        log.extend(["  console.error node_modules/react-dom/cjs/react-dom.development.js:530", '    Warning: Each child in a list should have a unique "key" prop.', "",
                    "    Check the render method of `Menu`. See https://fb.me/react-warning-keys for more information.", "        in li (created by Menu)",
                    "        in Menu (created by Select)", "        in Select", ""])
        jest_files(log, rng, areas[9:], 7, len(areas[9:]))
        failing = "src/datatable/DataTable.test.js"
        suites = len(areas) + 9
        details = ["  ● DataTable › renders sticky header when scrolled", "", "    expect(received).toMatchSnapshot()", "",
                   "    Snapshot name: `DataTable renders sticky header when scrolled 1`", "", f"    {ESC}[32m- Snapshot{ESC}[39m", f"    {ESC}[31m+ Received{ESC}[39m", "",
                   "    @@ -1,9 +1,9 @@", "      <div", '        className="data-table"', "      >", "        <table>", "    -     <thead",
                   '    -       className="sticky"', "    +     <thead", '    +       className="sticky sticky--scrolled"', "        >", "          <tr>", "",
                   "      56 |     wrapper.find('.data-table').simulate('scroll', { target: { scrollTop: 120 } });", "      57 |     wrapper.update();",
                   "    > 58 |     expect(wrapper.html()).toMatchSnapshot();", "         |                            ^", "      59 |   });", "      60 | });", "",
                   "      at Object.<anonymous> (src/datatable/DataTable.test.js:58:28)", ""]
        log.add(f"{JEST_FAIL} {failing} (3.912s)")
        log.extend(["  DataTable", f"    {ESC}[32m✓{ESC}[39m {ESC}[2mrenders without crashing (21ms){ESC}[22m",
                    f"    {ESC}[31m✕{ESC}[39m {ESC}[2mrenders sticky header when scrolled (38ms){ESC}[22m",
                    f"    {ESC}[32m✓{ESC}[39m {ESC}[2msorts by the clicked column (17ms){ESC}[22m", ""])
        with log.chunk():
            log.extend(details[:-1])
        log.add()
        later = ["Calendar", "Carousel", "Chip", "Divider", "Drawer", "Menu", "Rating", "Skeleton", "Stepper"]
        jest_files(log, rng, later, 7, len(later))
        log.extend(["Summary of all failing tests", f"{JEST_FAIL} {failing} (3.912s)"])
        with log.chunk():
            log.extend(details[:-1])
        log.extend(["", "Snapshot Summary", " › 1 snapshot failed from 1 test suite. Inspect your code changes or run `npm test -- -u` to update them.", "",
                    f"Test Suites: 1 failed, {suites} passed, {suites + 1} total", f"Tests:       1 failed, {suites * 7 + 2} passed, {suites * 7 + 3} total", "Snapshots:   1 failed, 41 passed, 42 total", "Time:        48.311s",
                    "Ran all test suites.", "npm ERR! Test failed.  See above for more details."])
    log.done(1)
    return log


def t06() -> Log:
    rng, log = start(990000302, "kestrel-io/kestrel-ui", "node_js", "Thu Dec  3 11:12:31 UTC 2020", 1607001151, dist="bionic")
    nvm_setup(log, "15.14.0", "7.7.6")
    with log.step("npm install", fold="install", seconds=9, exit=1, phase="install"):
        with log.chunk():
            log.extend(["npm ERR! code ERESOLVE", "npm ERR! ERESOLVE unable to resolve dependency tree", "npm ERR! ", "npm ERR! While resolving: kestrel-ui@3.4.0",
                        "npm ERR! Found: react@17.0.2", "npm ERR! node_modules/react", 'npm ERR!   react@"^17.0.2" from the root project',
                        'npm ERR!   peer react@">=16.8.0" from @kestrel-io/theme@2.1.0', "npm ERR!   node_modules/@kestrel-io/theme",
                        'npm ERR!     @kestrel-io/theme@"^2.1.0" from the root project', "npm ERR! ", "npm ERR! Could not resolve dependency:",
                        'npm ERR! peer react@"^18.0.0" from react-aria-hooks@4.0.1', "npm ERR! node_modules/react-aria-hooks",
                        'npm ERR!   react-aria-hooks@"^4.0.1" from the root project', "npm ERR! ", "npm ERR! Fix the upstream dependency conflict, or retry",
                        "npm ERR! this command with --force, or --legacy-peer-deps", "npm ERR! to accept an incorrect (and potentially broken) dependency resolution.",
                        "npm ERR! ", "npm ERR! See /home/travis/.npm/eresolve-report.txt for a full report."])
        log.extend(["", "npm ERR! A complete log of this run can be found in:", "npm ERR!     /home/travis/.npm/_logs/2020-12-03T11_12_31_912Z-debug.log"])
    return log


def e2() -> Log:
    rng, log = start(990000303, "kestrel-io/kestrel-ui", "node_js", "Tue Oct  8 13:26:40 UTC 2019", 1570541200)
    nvm_setup(log, "10.16.3", "6.9.0")
    with log.step("npm ci", fold="install", seconds=43, exit=0):
        log.extend(["npm WARN deprecated request@2.88.0: request has been deprecated, see https://github.com/request/request/issues/3142",
                    "npm WARN optional SKIPPING OPTIONAL DEPENDENCY: fsevents@1.2.9 (node_modules/fsevents)", "added 1428 packages in 40.118s"])
    root = "/home/travis/build/kestrel-io/kestrel-ui"
    with log.step("npm run lint", seconds=11, exit=1):
        log.extend(["", "> kestrel-ui@3.4.0 lint " + root, "> eslint src --max-warnings=0", ""])
        with log.chunk():
            log.extend([f"{root}/src/utils/format.js", "  14:7  error  'unusedLocale' is assigned a value but never used  no-unused-vars"])
        log.extend(["", "✖ 1 problem (1 error, 0 warnings)", "", "npm ERR! code ELIFECYCLE", "npm ERR! errno 1", "npm ERR! kestrel-ui@3.4.0 lint: `eslint src --max-warnings=0`",
                    "npm ERR! Exit status 1", "npm ERR! ", "npm ERR! Failed at the kestrel-ui@3.4.0 lint script.",
                    "npm ERR! This is probably not a problem with npm. There is likely additional logging output above.", "", "npm ERR! A complete log of this run can be found in:",
                    "npm ERR!     /home/travis/.npm/_logs/2019-10-08T13_26_52_911Z-debug.log"])
    log.done(1)
    return log


# ---------------------------------------------------------------- Ruby

def rvm_setup(log: Log, ruby: str) -> None:
    log.extend([f"$ rvm use {ruby} --install --binary --fuzzy", f"Using /home/travis/.rvm/gems/ruby-{ruby}", "$ ruby --version",
                f"ruby {ruby}p105 (2018-10-18 revision 65156) [x86_64-linux]", "$ rvm --version", "rvm 1.29.7 (latest) by Michal Papis, Piotr Kuczynski, Wayne E. Seguin [https://rvm.io]",
                "$ bundle --version", "Bundler version 2.0.1"])


def t07() -> Log:
    rng, log = start(990000401, "fernwood/fernwood-api", "ruby", "Wed Apr 10 14:02:55 UTC 2019", 1554904975)
    rvm_setup(log, "2.5.3")
    log.add("$ gem --version\n3.0.3")
    with log.step("bundle install --jobs=3 --retry=3", fold="install", seconds=118, exit=0):
        log.add("Fetching gem metadata from https://rubygems.org/..........")
        count = bundler_using(log, rng, 80)
        log.extend([f"Bundle complete! {count // 3} Gemfile dependencies, {count} gems now installed.", "Use `bundle info [gemname]` to see where a bundled gem is installed."])
    with log.step("psql -c 'create role fernwood superuser login;' -U postgres || true", seconds=0.3):
        log.add('ERROR:  role "fernwood" already exists')
    with log.step("bundle exec rake db:create db:schema:load", seconds=14, exit=0):
        log.extend(["Created database 'fernwood_test'", '-- enable_extension("plpgsql")', f"   -> {rng.uniform(0.005, 0.03):.4f}s"])
        tables = ["tenants", "users", "memberships", "api_keys", "webhooks", "webhook_deliveries", "delivery_attempts", "events", "event_payloads", "invoices", "invoice_lines",
                  "plans", "subscriptions", "audit_entries", "feature_flags", "rate_limits", "sessions", "tokens", "audit_exports", "notification_preferences", "templates",
                  "template_versions", "integrations", "integration_credentials", "jobs", "job_runs", "tags", "taggings", "attachments", "comments"]
        for table in tables:
            log.extend([f'-- create_table("{table}", {{:force=>:cascade}})', f"   -> {rng.uniform(0.004, 0.05):.4f}s"])
        for table in tables[1:12]:
            log.extend([f'-- add_foreign_key("{table}", "tenants")', f"   -> {rng.uniform(0.002, 0.02):.4f}s"])
    with log.step("bundle exec rspec", seconds=134, exit=1):
        log.extend(["Run options: exclude {:slow=>true}", "", "Randomized with seed 41807"])
        for i in range(6):
            dots = "".join(rng.choice(".........................*") for _ in range(196))
            if i == 2:
                dots = dots[:80] + "F" + dots[81:]
            if i == 4:
                dots = dots[:120] + "F" + dots[121:]
            log.add(dots)
            if i % 2 == 1:
                log.add("W, [2019-04-10T14:09:11.482 #2891]  WARN -- : retrying webhook delivery after connection error (attempt 1/3)")
        log.extend(["", "Failures:", ""])
        sig = "/home/travis/.rvm/gems/ruby-2.5.3/gems/rspec-core-3.8.0/lib/rspec/core"
        with log.chunk():
            log.extend(["  1) Api::V2::WebhooksController POST /v2/webhooks/deliver signs the payload with the tenant secret",
                        "     Failure/Error: expect(response.headers['X-Fernwood-Signature']).to eq(expected_signature)", "",
                        '       expected: "sha256=3f1c9ab0d2c2"', '            got: "sha256=9a0e4477d1b7"', "", "       (compared using ==)",
                        "     # ./spec/requests/api/v2/webhooks_spec.rb:48:in `block (4 levels) in <top (required)>'",
                        "     # ./spec/support/tenant_context.rb:12:in `block (3 levels) in <top (required)>'", f"     # {sig}/example.rb:254:in `instance_exec'", "",
                        "  2) Api::V2::WebhooksController POST /v2/webhooks/deliver records the delivery attempt",
                        "     Failure/Error: expect(delivery.attempts.count).to eq(1)", "", "       expected: 1", "            got: 0", "", "       (compared using ==)",
                        "     # ./spec/requests/api/v2/webhooks_spec.rb:61:in `block (4 levels) in <top (required)>'",
                        "     # ./spec/support/tenant_context.rb:12:in `block (3 levels) in <top (required)>'"])
        log.extend(["", "Finished in 2 minutes 14.5 seconds (files took 7.31 seconds to load)", "1204 examples, 2 failures, 1 pending", "", "Failed examples:", "",
                    "rspec ./spec/requests/api/v2/webhooks_spec.rb:44 # Api::V2::WebhooksController POST /v2/webhooks/deliver signs the payload with the tenant secret",
                    "rspec ./spec/requests/api/v2/webhooks_spec.rb:59 # Api::V2::WebhooksController POST /v2/webhooks/deliver records the delivery attempt", "",
                    "Randomized with seed 41807", ""])
    log.done(1)
    return log


def t08() -> Log:
    rng, log = start(990000402, "fernwood/fernwood-api", "ruby", "Mon May 13 09:31:08 UTC 2019", 1557739868)
    rvm_setup(log, "2.5.3")
    with log.step("bundle install --jobs=3 --retry=3", fold="install", seconds=7, exit=1, phase="install"):
        log.add("Fetching gem metadata from https://rubygems.org/............")
        log.add("Fetching gem metadata from https://rubygems.org/.")
        log.add("Resolving dependencies...")
        with log.chunk():
            log.extend(['Bundler could not find compatible versions for gem "activesupport":', "  In Gemfile:", "    rails (~> 5.2.3) was resolved to 5.2.3, which depends on",
                        "      activesupport (= 5.2.3)", "", "    fernwood-auth (~> 0.9) was resolved to 0.9.1, which depends on", "      activesupport (>= 6.0)"])
    return log


SCENARIOS = [
    dict(build=990000101, make=t01, language="Python", repo="harbor-labs/pyparcel", family="test-failure", keywords="FAILURES, test_manifest, AssertionError", expert_minutes=3,
         difficulty="One failing pytest test in a verbose run of 884; the FAILURES section sits above a coverage table and a dumped debug log, and earlier passing test names contain 'error' and 'failure'."),
    dict(build=990000102, make=t02, language="Python", repo="harbor-labs/pyparcel", family="dependency-resolution", keywords="ERROR, ResolutionImpossible, conflict", expert_minutes=2,
         difficulty="A pip resolver conflict report buried after backtracking INFO text; the conflict names the cause, and the closing Travis lines only say the command failed."),
    dict(build=990000103, make=e1, language="Python", repo="harbor-labs/pyparcel", family="static-analysis", keywords="error, mypy, incompatible type", expert_minutes=1,
         difficulty="An easy case kept for scale: a single mypy error line, the only line with error-like words before mypy's own count line, so keyword search and a careful reader both land on it."),
    dict(build=990000201, make=t03, language="Java", repo="tidewater/ledger-core", family="compile-error", keywords="COMPILATION ERROR, cannot find symbol", expert_minutes=3,
         difficulty="A javac error block in Maven output with about 1,400 lines of downloads before it (artifact names such as error_prone_annotations) and the same errors repeated in the build summary."),
    dict(build=990000202, make=t04, language="Java", repo="tidewater/ledger-core", family="decoy-errors", keywords="FAILURE, AssertionFailedError, PostingEngineTest", expert_minutes=4,
         difficulty="A flaky test that failed once and passed on rerun prints a FAILURE trace long before the real assertion failure; the real failure is 40 lines of results and a build summary away from the end."),
    dict(build=990000301, make=t05, language="JavaScript", repo="kestrel-io/kestrel-ui", family="test-failure", keywords="FAIL, toMatchSnapshot, DataTable", expert_minutes=3,
         difficulty="A snapshot failure among 290 verbose jest results; console.error output from a passing suite comes first, and jest prints the failure twice, inline and in its summary."),
    dict(build=990000302, make=t06, language="JavaScript", repo="kestrel-io/kestrel-ui", family="dependency-resolution", keywords="ERESOLVE, peer, react", expert_minutes=2,
         difficulty="An npm 7 ERESOLVE report where every line is prefixed 'npm ERR!'; the cause is the peer dependency chain inside it, not the closing lines about the debug log."),
    dict(build=990000303, make=e2, language="JavaScript", repo="kestrel-io/kestrel-ui", family="static-analysis", keywords="error, eslint, no-unused-vars", expert_minutes=1,
         difficulty="An easy case kept for scale: one eslint violation with its file path; the first error-like line is the violation, but the closing npm ERR! lines also say the lint script failed."),
    dict(build=990000401, make=t07, language="Ruby", repo="fernwood/fernwood-api", family="decoy-errors", keywords="Failures, Failure/Error, rspec", expert_minutes=4,
         difficulty="A harmless 'ERROR: role already exists' from a before_script command precedes two rspec failures printed in one Failures section, with the failed-examples list after it."),
    dict(build=990000402, make=t08, language="Ruby", repo="fernwood/fernwood-api", family="dependency-resolution", keywords="Bundler could not find compatible versions", expert_minutes=2,
         difficulty="Bundler's conflict report has no error marker word, so a keyword search skips it; the log ends a few lines after it with only Travis's own failure lines."),
]
