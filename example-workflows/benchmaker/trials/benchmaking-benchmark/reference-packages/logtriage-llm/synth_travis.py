"""Line-level builder for synthetic Travis CI logs, in the byte format of the LogChunks logs.

A log is a list of lines, each with its terminator, so a chunk is marked by line index and the delivered line
convention (CRLF, LF or CR ends a line) holds by construction. Travis markers (`travis_fold`, `travis_time`)
carry the `\\r\\x1b[0K` suffix real logs have, which makes the carriage return a line break of its own.
"""
from __future__ import annotations

import contextlib
import random
import re

ESC = "\x1b"
BREAK = re.compile(r"(\r\n|\n|\r)")
CLEAR = f"\r{ESC}[0K"


def colour(text: str, code: str) -> str:
    return f"{ESC}[{code}m{text}{ESC}[0m"


class Log:
    def __init__(self, rng: random.Random, *, epoch: int):
        self.rng = rng
        self.lines: list[list[str]] = []      # [content, terminator]
        self.chunks: list[tuple[int, int]] = []
        self.clock = epoch * 10**9            # nanoseconds, advanced by timed steps
        self._start = 0

    def add(self, text: str = "", term: str = "\r\n") -> None:
        """Append text; breaks inside it become lines of their own, `term` ends the last one."""
        parts = BREAK.split(text)
        for i in range(0, len(parts) - 1, 2):
            self.lines.append([parts[i], parts[i + 1]])
        self.lines.append([parts[-1], term])

    def extend(self, texts, term: str = "\r\n") -> None:
        for text in texts:
            self.add(text, term)

    @contextlib.contextmanager
    def chunk(self):
        """Mark the lines added inside the block as a labelled failure chunk."""
        start = len(self.lines)
        yield
        self.chunks.append((start, len(self.lines) - 1))

    def bytes(self) -> bytes:
        return "".join(c + t for c, t in self.lines).encode("utf-8")

    def chunk_text(self, index: int = 0) -> str:
        """The label text of a chunk as the dataset stores it: LF breaks, no escape characters, no `<`."""
        a, b = self.chunks[index]
        return "\n".join(c for c, _ in self.lines[a:b + 1]).replace(ESC, "").replace("<", "")

    def tid(self) -> str:
        return f"{self.rng.getrandbits(32):08x}"

    @contextlib.contextmanager
    def step(self, command: str, *, fold: str | None = None, seconds: float = 3.0, exit: int | None = None,
             phase: str | None = None):
        """One Travis command: markers, the `$` line, the body added inside the block, the closing timer.

        With `exit` the closing line carries Travis's verdict; a non-zero exit in an install or setup `phase`
        also stops the build.
        """
        ident = self.tid()
        opening = f"travis_fold:start:{fold}{CLEAR}" if fold else ""
        self.add(f"{opening}travis_time:start:{ident}{CLEAR}$ {command}")
        begin = self.clock
        yield ident
        self.clock = begin + int(seconds * 10**9)
        closing = f"travis_fold:end:{fold}{CLEAR}" if fold else ""
        verdict = "" if exit is None else CLEAR + _verdict(command, exit, phase)
        self.add(f"travis_time:end:{ident}:start={begin},finish={self.clock},duration={self.clock - begin}{CLEAR}{closing}{verdict}")
        if exit and phase:
            self.add()
            self.add("Your build has been stopped.")

    def done(self, code: int) -> None:
        self.add()
        self.add()
        self.add(f"Done. Your build exited with {code}.")


def _verdict(command: str, code: int, phase: str | None) -> str:
    if code and phase:
        return f'{ESC}[31;1mThe command "{command}" failed and exited with {code} during {ESC}[0m.'
    if code:
        return f'{ESC}[31;1mThe command "{command}" exited with {code}.{ESC}[0m'
    return f'{ESC}[32;1mThe command "{command}" exited with 0.{ESC}[0m'


def hexes(rng: random.Random, n: int) -> str:
    return "".join(rng.choice("0123456789abcdef") for _ in range(n))


def uuid(rng: random.Random) -> str:
    return "-".join(hexes(rng, k) for k in (8, 4, 4, 4, 12))


def preamble(log: Log, rng: random.Random, *, language: str, build_id: int, dist: str = "xenial",
             date: str = "Mon Mar 25 16:43:24 UTC 2019", extras: tuple[str, ...] = ()) -> None:
    """Worker and system information, as the first lines of every Travis job log."""
    gce = rng.randint(1, 24)
    log.add(f"travis_fold:start:worker_info{CLEAR}{colour('Worker information', '33;1')}", "\n")
    log.add(f"hostname: {uuid(rng)}@1.production-2-worker-org-gce-{gce:02d}vf", "\n")
    log.add(f"version: v6.2.0 https://github.com/travis-ci/worker/tree/{hexes(rng, 40)}", "\n")
    log.add(f"instance: travis-job-{uuid(rng)} travis-ci-sardonyx-{dist}-1553530528-f909ac5 (via amqp)", "\n")
    log.add(f"startup: {rng.randint(4, 9)}.{rng.randint(100000000, 999999999)}s", "\n")
    log.add(f"travis_fold:end:worker_info{CLEAR}travis_fold:start:system_info{CLEAR}{colour('Build system information', '33;1')}")
    log.extend([f"Build language: {language}", "Build group: stable", f"Build dist: {dist}", f"Build id: {build_id}",
                f"Job id: {build_id + 1}", "Runtime kernel version: 4.15.0-1028-gcp", "travis-build version: 544249267"])
    sections = [("Build image provisioning date and time", [date]),
                ("Operating System Details", ["Distributor ID:\tUbuntu", "Description:\tUbuntu 16.04.6 LTS", "Release:\t16.04", "Codename:\txenial"]),
                ("Cookbooks Version", ["42e42e4 https://github.com/travis-ci/travis-cookbooks/tree/42e42e4"]),
                ("git version", ["git version 2.21.0"]),
                ("bash version", ["GNU bash, version 4.3.48(1)-release (x86_64-pc-linux-gnu)"]),
                ("gcc version", ["gcc (Ubuntu 5.4.0-6ubuntu1~16.04.11) 5.4.0 20160609"]),
                ("docker version", ["Client:", " Version:           18.06.0-ce", " API version:       1.38", " Go version:        go1.10.3",
                                    "", "Server:", " Engine:", "  Version:          18.06.0-ce"]),
                ("clang version", ["clang version 7.0.0 (tags/RELEASE_700/final)"]),
                ("cmake version", ["cmake version 3.12.4"]),
                ("mysql version", ["mysql  Ver 14.14 Distrib 5.7.25, for Linux (x86_64) using  EditLine wrapper"]),
                ("openssl version", ["OpenSSL 1.0.2g  1 Mar 2016"]),
                ("postgresql client version", ["psql (PostgreSQL) 10.7 (Ubuntu 10.7-1.pgdg16.04+1)"]),
                ("default ruby version", ["ruby 2.5.3p105 (2018-10-18 revision 65156) [x86_64-linux]"]),
                ("Pre-installed PostgreSQL versions", ["9.4.21", "9.5.16", "9.6.12"]),
                ("Pre-installed Go versions", ["1.11.1"]),
                ("mvn version", ["Apache Maven 3.6.0 (97c98ec64a1fdfee7767ce5ffb20918da4f719f3; 2018-10-24T18:41:47Z)"]),
                ("Pre-installed Node.js versions", ["v10.15.3", "v11.0.0", "v6.17.0", "v8.12.0", "v8.15.1"]),
                ("composer --version", ["Composer version 1.8.4 2019-02-11 10:52:10"]),
                ("Pre-installed Ruby versions", ["ruby-2.3.8", "ruby-2.4.5", "ruby-2.5.3"])]
    for title, body in sections:
        log.add(f"{ESC}[34m{ESC}[1m{title}{ESC}[0m")
        log.extend(body)
    log.extend(extras)
    log.add(f"travis_fold:end:system_info{CLEAR}", "\n")


def checkout(log: Log, rng: random.Random, repo: str, *, branch: str = "master") -> None:
    sha = hexes(rng, 40)
    with log.step(f"git clone --depth=50 --branch={branch} https://github.com/{repo}.git {repo}", fold="git.checkout", seconds=2.1):
        log.add(f"Cloning into '{repo}'...")
        objects = rng.randint(1800, 9000)
        log.add(f"remote: Enumerating objects: {objects}, done.\rremote: Counting objects:  50% ({objects // 2}/{objects})\r"
                f"remote: Counting objects: 100% ({objects}/{objects}), done.\rremote: Compressing objects: 100% ({objects // 3}/{objects // 3}), done.")
        log.add(f"remote: Total {objects} (delta {objects // 4}), reused {objects - 90} (delta {objects // 4}), pack-reused 0\r"
                f"Receiving objects: 100% ({objects}/{objects}), {rng.randint(2, 40)}.{rng.randint(10, 99)} MiB | 18.31 MiB/s, done.\r"
                f"Resolving deltas: 100% ({objects // 4}/{objects // 4}), done.")
    log.add(f"$ cd {repo}")
    log.add(f"$ git checkout -qf {sha}")


def stopped_for_silence(log: Log) -> None:
    """The Travis message for a job that printed nothing for ten minutes."""
    log.add("No output has been received in the last 10m0s, this potentially indicates a stalled build or something wrong with the build itself.")
    log.add("Check the details on how to adjust your build configuration on: https://docs.travis-ci.com/user/common-build-problems/#build-times-out-because-no-output-was-received")
    log.add()
    log.add("The build has been terminated")
