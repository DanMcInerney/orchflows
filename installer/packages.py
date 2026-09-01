"""Canonical package discovery, role rendering, and source identity."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from .foundation import HOST_ADAPTERS_DIR, PROFILE_ROLES, REPO_ROOT
from .hosts import GROK_EFFORTS, GROK_MODEL_CENSUS, load_host_adapters, load_role_profiles

# --- frontmatter parsing (adapters / prompts only need this much) ------


def split_frontmatter(text: str):
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].rstrip("\r\n") != "---":
        raise ValueError("missing frontmatter")
    end = None
    for i in range(1, len(lines)):
        if lines[i].rstrip("\r\n") == "---":
            end = i
            break
    if end is None:
        raise ValueError("unterminated frontmatter")
    return "".join(lines[: end + 1]), "".join(lines[end + 1 :])


def host_legal_frontmatter(
    frontmatter: str,
    host: str = "claude",
    adapter_dir: Path = HOST_ADAPTERS_DIR,
) -> str:
    """Host-legal adapter frontmatter and any declared native role binding."""
    spec = load_host_adapters(adapter_dir)[host]["frontmatter"]
    legal_keys = set(spec["legal_keys"])
    kept = [
        line
        for line in frontmatter.splitlines(keepends=True)
        if line.rstrip("\r\n") == "---"
        or line.partition(":")[0].strip() in legal_keys
    ]
    role = frontmatter_field(frontmatter, "role")
    if role in ("planner", "worker"):
        native = [
            f"{key}: {value.format(role=role)}\n"
            for key, value in spec.get("role_fields", {}).items()
        ]
        kept[-1:-1] = native
    return "".join(kept)


def frontmatter_field(frontmatter: str, key: str):
    for line in frontmatter.splitlines():
        line_key, sep, rest = line.partition(":")
        if sep and line_key.strip() == key:
            value = rest.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            return value
    return None


def discover_packages():
    """Every skill/pack package: ``skills/<sublayer>/orch-*`` and ``packs/orch-*``."""

    packages = []
    skills_root = REPO_ROOT / "skills"
    if skills_root.is_dir():
        for sublayer in sorted(p for p in skills_root.iterdir() if p.is_dir()):
            for pkg in sorted(p for p in sublayer.iterdir() if p.is_dir()):
                skill_md = pkg / "SKILL.md"
                if skill_md.is_file():
                    packages.append(skill_md)
    packs_root = REPO_ROOT / "packs"
    if packs_root.is_dir():
        for pkg in sorted(p for p in packs_root.iterdir() if p.is_dir()):
            skill_md = pkg / "SKILL.md"
            if skill_md.is_file():
                packages.append(skill_md)
    return packages


WORKFLOW_SKILL_FILE = "SKILL.md"
# Every workflow adapter is manual-invocation-only, whatever the source
# declares. A workflow's prose executes as orchestrator reasoning rather
# than inside a sealed child prompt (the lego design's A5 containment), so
# a host that fires one on its own reading of a description has opened that
# surface without anybody asking. The flag is forced here rather than
# trusted from frontmatter, because a ring workflow is authored outside
# this repository and cannot be required to remember it.
MANUAL_ONLY = "disable-model-invocation: true"


def discover_workflow_skills(root: Path = REPO_ROOT):
    """Every invocable workflow: a directory ``example-workflows/<name>/``
    whose ``SKILL.md`` is a workflow skill -- prose that calls bricks.

    Returns ``(directory, frontmatter, body)`` per workflow. A directory
    without that file, or one without frontmatter or a ``name``, is library
    data rather than a name surface and is skipped -- it still reaches the
    installed lib copy. ``example-workflows/references/`` is exactly that."""

    workflows = []
    comps_root = root / "example-workflows"
    if not comps_root.is_dir():
        return workflows
    for directory in sorted(p for p in comps_root.iterdir() if p.is_dir()):
        manifest = directory / WORKFLOW_SKILL_FILE
        if not manifest.is_file():
            continue
        try:
            frontmatter, body = split_frontmatter(manifest.read_text(encoding="utf-8"))
        except ValueError:
            continue
        if not frontmatter_field(frontmatter, "name"):
            continue
        workflows.append((directory, frontmatter, body))
    return workflows


def manual_only_frontmatter(frontmatter: str, host: str = "claude") -> str:
    """Host-legal adapter frontmatter with the manual-only flag guaranteed."""

    legal = host_legal_frontmatter(frontmatter, host)
    if MANUAL_ONLY.split(":")[0] in legal:
        return legal
    lines = legal.splitlines(keepends=True)
    lines[-1:-1] = [MANUAL_ONLY + "\n"]
    return "".join(lines)


def workflow_adapter_body(name: str, lib_workflow_dir: Path, frontmatter: str) -> str:
    """The Claude adapter stub's body for a workflow.

    A workflow is a skill whose prose calls bricks, so the adapter says
    exactly that and points at the one body: read it and invoke it. It is
    a pointer rather than an ``@``-include because the body's own relative
    links resolve against the library directory it lives in, not against
    the host surface this stub is written into."""

    return (
        f"`{name}` is a workflow skill: prose that opens a frame and calls\n"
        f"bricks. Its one body is {lib_workflow_dir / WORKFLOW_SKILL_FILE}.\n\n"
        "Read that file whole and invoke the skill by following it exactly:\n"
        "its Require names what the caller supplies, its call lines are the\n"
        "commands to run, and its Return is the close. A workflow is only\n"
        "ever invoked by name -- never on a host's own reading of this\n"
        "description.\n"
    )


# The fork-arrival clause: what a skill fork that arrives holding a
# contract and no launch prompt must do. Eighteen firings in one session
# proved the launch structurally cannot carry this rule -- a fork that
# arrives without one never reads one -- and rules/token-economy.md 11 priced the
# 22-contract sweep out of the skill bodies (tests/test_skill_fork_governance.py
# holds the clause's property ledger and that pricing's history). The
# adapter is upstream of the contract in a fork's load path, and the
# installer already renders behavioral dispatch law (ROLE_INSTRUCTIONS),
# so the clause lands on every rendered name surface of a role-bearing
# skill: one owner, zero skill-body words, no doclint pairing.
FORK_ARRIVAL_CLAUSE = (
    "Arriving without a launch prompt, refuse before reading anything: your "
    "refusal is your return, reaching your invoker through the invocation "
    "itself, never the coordinator. Acquire nothing, claim no name, derive "
    "no objective. Invoking a skill by name, forward your prompt or refuse."
)


def fork_arrival_preamble(role) -> str:
    """The clause paragraph a role-bearing name surface opens with.

    Only planner and worker adapters fork (`host_legal_frontmatter`), so
    only their surfaces can produce the prompt-less arrival the clause
    governs; a `role: none` surface runs in the invoking context and
    carries nothing extra."""

    if role in ("planner", "worker"):
        return FORK_ARRIVAL_CLAUSE + "\n\n"
    return ""


def claude_role_adapter_text(frontmatter: str, lib_skill_md: Path) -> str:
    """The installed Claude adapter: legal frontmatter, the fork-arrival
    clause where the adapter forks, then the ``@``-include of the one
    canonical body -- so the clause is the first body text a fork reads,
    before the contract the include pulls in."""

    role = frontmatter_field(frontmatter, "role")
    return host_legal_frontmatter(frontmatter) + fork_arrival_preamble(role) + f"@{lib_skill_md}\n"


def by_name_pointer_text(frontmatter: str, role, lib_skill_md: Path) -> str:
    """The flat ``by-name`` stub: the same clause-first shape for the one
    deterministic path an agent resolves a role-bearing name through."""

    return frontmatter + "\n" + fork_arrival_preamble(role) + f"Read {lib_skill_md} and follow it exactly.\n"


def codex_role_adapter_body(name: str, role: str, profile: dict, lib_skill_md: Path) -> str:
    """Explicit Codex dispatch gate for one role-bearing named skill."""

    if profile["role"] != role:
        raise ValueError(
            f"cannot render {name}: declared role {role} does not match "
            f"resolved profile role {profile['role']}"
        )
    binding = profile["codex"]
    return (
        f"`{name}` requires the matching role `orch-{role}`. If this context "
        f"is already that established child, read {lib_skill_md} and follow it exactly. Execute "
        "the exact named skill directly; never redispatch it. Otherwise root "
        f"must dispatch one child with agent_type `{binding['agent_type']}` and "
        f"fork_turns `{binding['fork_turns']}`, passing the "
        "emitted launch prompt and exact named skill; refuse execution when that "
        "matching role child is missing or mismatched; there is no inline "
        f"fallback.\n\n{FORK_ARRIVAL_CLAUSE}\n"
    )


# Every Grok text surface -- dispatch gate, legal frontmatter, skill file and
# `render_grok_agent` -- lives in installer/managed_text.py, not here beside
# its Claude and Codex siblings. Not a taxonomy choice: this file measured 483
# tracked-source lines before the Grok column arrived, and the group does not
# fit in what one-read size leaves.


def _role_description(name: str) -> str:
    """The routing fact and nothing else. It used to add "follow the role
    contract at <roles.md>": an imperative with no addressee, listed on
    every turn to every context holding the Agent tool -- children
    included -- while the dispatcher's law is already reached through
    rules/roles.md section 4 (contracts/work-item.md, contracts/dispatch.md)."""

    return f"Orchflows child role {name}."


# What a rendered role agent instructs, and all it instructs. It opened by
# sending every child of every role to read rules/roles.md before acting --
# 149 words loaded before the child had read its own ticket, whose own text
# already carries the clauses a child acts on (stay in scope; write the
# return into the durable artifact; deliver it by SendMessage). No rendered
# role agent file names roles.md anywhere (D-2).
ROLE_INSTRUCTIONS = (
    "Stay within delegated scope. Every record names your launch's dispatch id, "
    "seal, and assigned name; your first record is your acceptance. "
    "Execute the exact primary skill, or each exact member of a "
    "launch-stated ordered sequence, directly; never redispatch. Refuse a missing "
    "or mismatched role."
)

def render_codex_agent(name: str, profile: dict) -> str:
    binding = profile["codex"]
    lines = [
        f"name = {json.dumps(binding['agent_type'])}",
        f"description = {json.dumps(_role_description(name))}",
        f"developer_instructions = {json.dumps(ROLE_INSTRUCTIONS)}",
        f"model = {json.dumps(binding['model'])}",
        f"model_reasoning_effort = {json.dumps(binding['model_reasoning_effort'])}",
    ]
    if binding.get("service_tier"):
        lines.append(f"service_tier = {json.dumps(binding['service_tier'])}")
    return "\n".join(lines) + "\n"


def render_claude_agent(name: str, profile: dict) -> str:
    binding = profile["claude"]
    lines = [
        "---",
        f"name: {name}",
        f"description: {json.dumps(_role_description(name))}",
        f"model: {binding['model']}",
    ]
    if binding.get("effort"):
        lines.append(f"effort: {binding['effort']}")
    claude_transport = (
        " Write your contracted return into the dispatch's durable artifact, then "
        "deliver it or a pointer to it via SendMessage to your spawner as your final "
        "action - plain final text is not delivered to your caller."
    )
    lines.extend(["---", "", ROLE_INSTRUCTIONS + claude_transport])
    return "\n".join(lines) + "\n"


# --- managed marker blocks ----------------------------------------------


def template_markers(template_text: str):
    lines = [line.strip() for line in template_text.splitlines() if line.strip()]
    if not lines:
        raise ValueError("empty host-block template")
    return lines[0], lines[-1]


def resolved_python_interpreter() -> str:
    """The interpreter install.py verified itself running under
    (``sys.executable``). Refuses when the platform reports none rather than
    rendering a bare ``python`` into every command the host block hands an
    agent: on Windows that name is commonly the Store stub, so the fallback
    shipped a command that fails on first use."""

    if not sys.executable:
        raise ValueError(
            "this platform reports no sys.executable, so no interpreter path "
            "can be rendered into the host block; rerun install.py with an "
            "interpreter that reports one"
        )
    return sys.executable


def _git_dirs(repo_root: Path) -> tuple[Path, Path] | None:
    """``(git_dir, common_dir)`` for a checkout, or ``None`` when neither can
    be read. In an ordinary clone both are ``<root>/.git``. In a git worktree
    (``.git`` is a *file* holding ``gitdir: <path>``) HEAD lives in that
    gitdir while ``refs/`` and ``packed-refs`` live in the shared checkout the
    gitdir's ``commondir`` names — so the two differ, and reading HEAD's ref
    from the wrong one is why a worktree install used to record no commit."""

    marker = repo_root / ".git"
    if marker.is_dir():
        return marker, marker
    if not marker.is_file():
        return None
    try:
        pointer = marker.read_text(encoding="utf-8")
    except OSError:
        return None
    named = ""
    for line in pointer.splitlines():
        if line.startswith("gitdir:"):
            named = line.partition(":")[2].strip()
            break
    if not named:
        return None
    git_dir = Path(named)
    if not git_dir.is_absolute():
        git_dir = repo_root / git_dir
    common_file = git_dir / "commondir"
    common_dir = git_dir
    if common_file.is_file():
        try:
            common = Path(common_file.read_text(encoding="utf-8").strip())
        except OSError:
            return None
        if common.parts:
            common_dir = common if common.is_absolute() else git_dir / common
    return git_dir, common_dir


def resolve_source_commit(repo_root: Path = REPO_ROOT) -> str | None:
    """The git HEAD commit of the repo this installer runs from, read directly
    from ``.git`` (no subprocess, no dependency on ``git`` being on PATH).
    Handles both a clone and a worktree checkout (``_git_dirs``). Returns
    ``None`` whenever no checkout can be read — absent ``.git``, a gitdir
    pointer that does not parse, a ref that resolves to nothing, or any I/O
    error."""

    dirs = _git_dirs(repo_root)
    if dirs is None:
        return None
    git_dir, common_dir = dirs
    head_file = git_dir / "HEAD"
    if not head_file.is_file():
        return None
    try:
        content = head_file.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if not content:
        return None
    if not content.startswith("ref:"):
        return content
    ref = content.split(":", 1)[1].strip()
    for root in (git_dir, common_dir):
        ref_path = root / ref
        if ref_path.is_file():
            try:
                sha = ref_path.read_text(encoding="utf-8").strip()
            except OSError:
                return None
            return sha or None
    packed_refs = common_dir / "packed-refs"
    if not packed_refs.is_file():
        return None
    try:
        lines = packed_refs.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    for line in lines:
        if not line or line[0] in "#^":
            continue
        parts = line.split()
        if len(parts) == 2 and parts[1] == ref:
            return parts[0]
    return None


def source_commit_warning(commit: str | None, repo_root: Path = REPO_ROOT) -> str | None:
    """One line, when the receipt's ``source_commit`` is null, naming which
    read came up empty — otherwise a null reads as 'this installer has no such
    field' and the missing drift report looks like agreement."""

    if commit:
        return None
    dirs = _git_dirs(repo_root)
    if dirs is None:
        reason = f"no readable .git in {repo_root}"
    else:
        reason = f"HEAD in {dirs[0]} resolves to no commit"
    return f"warning: source commit unresolved ({reason}); the next install cannot report drift"


def source_commit_drift_message(old_receipt: dict | None, new_commit: str | None) -> str | None:
    """``None`` unless both receipts name a commit and they differ — first
    installs and unavailable commits are not drift."""

    old_commit = (old_receipt or {}).get("source_commit")
    if old_commit and new_commit and old_commit != new_commit:
        return f"source commit drift: {old_commit} -> {new_commit}"
    return None


def accepted_source_commit(
    current_commit: str | None, accepted_commit: str | None, *, mutating: bool = False
) -> str | None:
    """Require the checkout to be the one identity accepted by its gate.

    Only one final repository-global gate decides an installable tip, so a
    mutating installation must name the identity that gate accepted: omitting
    it there would make the finalization-gate-install path optional rather
    than enforced.  The read-only paths -- ``--dry-run``, doctor, uninstall --
    inspect a checkout rather than consume it, and may omit the identity.
    The value returned is the observed identity, never a caller-supplied
    value substituted for an unreadable checkout.
    """

    if accepted_commit is None:
        if mutating:
            raise ValueError(
                "a mutating installation requires the accepted composite-gate "
                "source identity; pass --accepted-source"
            )
        return current_commit
    if not isinstance(accepted_commit, str) or not accepted_commit.strip():
        raise ValueError("accepted source identity must be a non-empty commit")
    accepted = accepted_commit.strip()
    if current_commit is None:
        raise ValueError("accepted source identity cannot be checked: source commit is unresolved")
    if current_commit.lower() != accepted.lower():
        raise ValueError(
            "source identity is not the accepted composite-gate commit: "
            f"expected {accepted}, observed {current_commit}"
        )
    return current_commit
