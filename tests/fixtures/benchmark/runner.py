"""Deterministic runner and independent qualifier for the benchmark fixture."""

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path


REFERENCE_FIELDS = (
    "evaluation_design",
    "runnable_cases",
    "runner",
    "scoring",
    "provenance",
    "qualification",
)
PRESEAL_FIELDS = REFERENCE_FIELDS[:-1]
REQUIRED_QUALIFICATION_CRITERIA = {
    "oracle_failability",
    "coverage",
    "discrimination",
    "reproducibility",
    "redundancy",
    "provenance",
    "execution_cost",
}


def canonical_json(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def sha256_bytes(value):
    return f"sha256:{hashlib.sha256(value).hexdigest()}"


def sha256_identity(path):
    return sha256_bytes(path.read_bytes())


def benchmark_identity(manifest):
    payload = dict(manifest)
    payload.pop("benchmark_identity")
    return sha256_bytes(canonical_json(payload).encode("utf-8"))


def evidence_identity(evidence):
    payload = {key: value for key, value in evidence.items() if key != "identity"}
    return sha256_bytes(canonical_json(payload).encode("utf-8"))


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_reference(root, reference):
    identity = reference["identity"]
    if not identity.startswith("sha256:"):
        raise ValueError("component identity is not a sha256 digest")
    path = (root / reference["locator"]).resolve()
    path.relative_to(root)
    if not path.is_file():
        raise ValueError(f"missing reference: {reference['locator']}")
    if sha256_identity(path) != identity:
        raise ValueError(f"identity mismatch: {reference['locator']}")
    return path


def execute_candidate(candidate_path, payload, timeout):
    try:
        completed = subprocess.run(
            [sys.executable, str(candidate_path)],
            input=canonical_json(payload),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return None, "candidate timed out"
    if completed.returncode != 0:
        return None, f"candidate exit {completed.returncode}"
    try:
        return json.loads(completed.stdout), ""
    except json.JSONDecodeError:
        return None, "candidate output was not JSON"


def validate_components(manifest, design, case_set, scoring, provenance):
    if design["scoring_identity"] != scoring["scoring_identity"]:
        raise ValueError("design and scoring identities differ")
    if design["aggregation"] != scoring["aggregation"]:
        raise ValueError("design and scoring aggregation differ")
    aggregation = scoring["aggregation"]
    if aggregation != {
        "operator": "all_required_status",
        "status": scoring["required_status"],
    }:
        raise ValueError("unsupported scoring aggregation")
    if scoring["ranking_eligibility"] != {"operator": "aggregation_passes"}:
        raise ValueError("unsupported ranking eligibility")
    if set(scoring["per_case"]) != {"PASS", "FAIL", "UNVERIFIED"}:
        raise ValueError("per-case scoring statuses are incomplete")
    if any(
        not isinstance(value, (int, float))
        for value in scoring["per_case"].values()
    ):
        raise ValueError("per-case scores must be numeric")

    cases = case_set["cases"]
    case_identities = [case["case_identity"] for case in cases]
    if len(case_identities) != len(set(case_identities)):
        raise ValueError("duplicate runnable case identity")
    if set(case_identities) != set(design["case_specifications"]):
        raise ValueError("design and runnable case identities differ")
    case_coverage = {
        dimension for case in cases for dimension in case["coverage"]
    }
    if case_coverage != set(design["intended_coverage"]):
        raise ValueError("design and runnable case coverage differ")
    if set(case_identities) != set(provenance["case_sources"]):
        raise ValueError("case provenance map is incomplete")
    source_identities = {source["identity"] for source in provenance["sources"]}
    if source_identities != set(design["source_identities"]):
        raise ValueError("design and provenance source identities differ")
    for case in cases:
        sources = set(provenance["case_sources"][case["case_identity"]])
        if not sources or sources != set(case["covered_evidence"]):
            raise ValueError("case provenance identities differ")
        if not sources <= source_identities:
            raise ValueError("case provenance source is unresolved")

    expected = design["expected_execution_cost"]
    manifest_cost = manifest["expected_cost"]
    if (
        manifest_cost["case_count"] != expected["case_count"]
        or manifest_cost["candidate_processes_per_replay"]
        != expected["candidate_processes"]
        or manifest_cost["per_case_timeout_seconds"]
        != expected["per_case_timeout_seconds"]
        or len(cases) != expected["case_count"]
    ):
        raise ValueError("declared execution cost differs from the design")


def evaluate_candidate(candidate_path, case_set, scoring, provenance, timeout):
    cases = []
    covered_evidence = set()
    for case in case_set["cases"]:
        observed, error = execute_candidate(candidate_path, case["input"], timeout)
        verdict = "PASS" if not error and observed == case["expected"] else "FAIL"
        covered_evidence.add(case["case_identity"])
        covered_evidence.update(case["covered_evidence"])
        covered_evidence.update(provenance["case_sources"][case["case_identity"]])
        cases.append(
            {
                "case_identity": case["case_identity"],
                "verdict": verdict,
                "oracle_class": case["oracle_class"],
                "observed": observed,
                "error": error,
            }
        )

    required_results = [
        result
        for case, result in zip(case_set["cases"], cases)
        if case["required"]
    ]
    if not required_results:
        raise ValueError("benchmark has no required case")
    aggregation_passes = all(
        result["verdict"] == scoring["required_status"]
        for result in required_results
    )
    verdict = scoring["required_status"] if aggregation_passes else "FAIL"
    score = sum(scoring["per_case"][result["verdict"]] for result in cases) / len(
        cases
    )
    return {
        "candidate_identity": sha256_identity(candidate_path),
        "verdict": verdict,
        "score": score,
        "eligible_for_ranking": aggregation_passes,
        "cases": cases,
        "covered_evidence": sorted(covered_evidence),
    }


def verify_qualification(
    root, manifest, design, case_set, scoring, provenance, qualification
):
    calibration = qualification["calibration_candidates"]
    known_good = resolve_reference(root, calibration["known_good"])
    known_bad = resolve_reference(root, calibration["known_bad"])
    timeout = manifest["expected_cost"]["per_case_timeout_seconds"]
    good_first = evaluate_candidate(
        known_good, case_set, scoring, provenance, timeout
    )
    good_second = evaluate_candidate(
        known_good, case_set, scoring, provenance, timeout
    )
    bad = evaluate_candidate(known_bad, case_set, scoring, provenance, timeout)

    if good_first["verdict"] != "PASS" or bad["verdict"] != "FAIL":
        raise ValueError("qualification discrimination failed")
    if bad["eligible_for_ranking"]:
        raise ValueError("qualification failability failed")
    if good_first != good_second:
        raise ValueError("qualification reproducibility failed")

    case_coverage = {
        case["case_identity"]: set(case["coverage"])
        for case in case_set["cases"]
    }
    unique_coverage = {}
    for case_identity, coverage in case_coverage.items():
        other_coverage = set().union(
            *(
                other
                for other_identity, other in case_coverage.items()
                if other_identity != case_identity
            )
        )
        unique = sorted(coverage - other_coverage)
        if not unique:
            raise ValueError("qualification redundancy failed")
        unique_coverage[case_identity] = unique

    covers = {
        name: manifest[name]["identity"] for name in PRESEAL_FIELDS
    }
    covers["known_good"] = calibration["known_good"]["identity"]
    covers["known_bad"] = calibration["known_bad"]["identity"]
    expected = {
        "oracle_failability": {
            "covers": [covers["runner"], covers["runnable_cases"], covers["scoring"], covers["known_bad"]],
            "observation": {
                "known_bad_verdict": bad["verdict"],
                "eligible_for_ranking": bad["eligible_for_ranking"],
            },
        },
        "coverage": {
            "covers": [covers["evaluation_design"], covers["runnable_cases"]],
            "observation": {
                "case_count": len(case_set["cases"]),
                "covered_dimensions": sorted(design["intended_coverage"]),
            },
        },
        "discrimination": {
            "covers": [covers["runner"], covers["runnable_cases"], covers["scoring"], covers["known_good"], covers["known_bad"]],
            "observation": {
                "known_good_verdict": good_first["verdict"],
                "known_bad_verdict": bad["verdict"],
            },
        },
        "reproducibility": {
            "covers": [covers["runner"], covers["runnable_cases"], covers["scoring"], covers["known_good"]],
            "observation": {"identical_replays": good_first == good_second},
        },
        "redundancy": {
            "covers": [covers["evaluation_design"], covers["runnable_cases"]],
            "observation": {"unique_coverage": unique_coverage},
        },
        "provenance": {
            "covers": [covers["evaluation_design"], covers["runnable_cases"], covers["provenance"]],
            "observation": {"case_sources": provenance["case_sources"]},
        },
        "execution_cost": {
            "covers": [covers["evaluation_design"], covers["runnable_cases"], covers["runner"]],
            "observation": {
                "replays": 3,
                "candidate_processes": 3 * len(case_set["cases"]),
                "per_case_timeout_seconds": timeout,
            },
        },
    }

    entries = {
        entry["criterion"]: entry
        for entry in qualification["entries"]
        if entry["required"]
    }
    if set(entries) != REQUIRED_QUALIFICATION_CRITERIA:
        raise ValueError("qualification criterion set is incomplete")
    for criterion, expected_entry in expected.items():
        entry = entries[criterion]
        expected_covers = sorted(expected_entry["covers"])
        if (
            entry["verdict"] != "PASS"
            or entry["oracle_class"] != "deterministic"
            or sorted(entry["covers"]) != expected_covers
        ):
            raise ValueError(f"qualification {criterion} verdict is invalid")
        evidence = entry["evidence"]
        if (
            evidence["observation"] != expected_entry["observation"]
            or sorted(evidence["provenance"]) != expected_covers
            or evidence["identity"] != evidence_identity(evidence)
        ):
            raise ValueError(f"qualification {criterion} evidence is invalid")

    spend = expected["execution_cost"]["observation"]
    if qualification["actual_qualification_spend"] != {
        "replays": spend["replays"],
        "candidate_processes": spend["candidate_processes"],
    }:
        raise ValueError("qualification spend is invalid")
    if (
        qualification["overall_verdict"] != "PASS"
        or qualification["weakest_oracle_class"] != "deterministic"
    ):
        raise ValueError("qualification overall verdict is invalid")

    optimization = next(
        entry
        for entry in qualification["entries"]
        if entry["criterion"] == "optimization_resistance"
    )
    if manifest["protected_evidence"]["candidate_inaccessible_check"] is None:
        if optimization["required"] or optimization["verdict"] != "UNVERIFIED":
            raise ValueError("optimization resistance must remain UNVERIFIED")
    if optimization["evidence"]["identity"] != evidence_identity(
        optimization["evidence"]
    ):
        raise ValueError("optimization-resistance evidence is invalid")


def replay(manifest_path, candidate_path):
    manifest_path = manifest_path.resolve()
    candidate_path = candidate_path.resolve()
    root = manifest_path.parent.resolve()
    manifest = load_json(manifest_path)
    if manifest["benchmark_identity"] != benchmark_identity(manifest):
        raise ValueError("benchmark identity mismatch")
    references = {
        name: resolve_reference(root, manifest[name]) for name in REFERENCE_FIELDS
    }
    if references["runner"] != Path(__file__).resolve():
        raise ValueError("manifest runner does not resolve to this file")

    design = load_json(references["evaluation_design"])
    case_set = load_json(references["runnable_cases"])
    scoring = load_json(references["scoring"])
    provenance = load_json(references["provenance"])
    qualification = load_json(references["qualification"])
    validate_components(manifest, design, case_set, scoring, provenance)
    verify_qualification(
        root, manifest, design, case_set, scoring, provenance, qualification
    )

    result = evaluate_candidate(
        candidate_path,
        case_set,
        scoring,
        provenance,
        manifest["expected_cost"]["per_case_timeout_seconds"],
    )
    evidence_payload = {
        "benchmark_identity": manifest["benchmark_identity"],
        "evaluation_design_identity": manifest["evaluation_design"]["identity"],
        "runner_identity": manifest["runner"]["identity"],
        "candidate_identity": result["candidate_identity"],
        "cases": result["cases"],
        "covered_evidence": result["covered_evidence"],
    }
    return {
        "benchmark_identity": manifest["benchmark_identity"],
        "evaluation_design_identity": manifest["evaluation_design"]["identity"],
        "runner_identity": manifest["runner"]["identity"],
        "candidate_identity": result["candidate_identity"],
        "verdict": result["verdict"],
        "oracle_class": "deterministic",
        "score": result["score"],
        "eligible_for_ranking": result["eligible_for_ranking"],
        "cases": result["cases"],
        "covered_evidence": result["covered_evidence"],
        "evidence_identity": sha256_bytes(
            canonical_json(evidence_payload).encode("utf-8")
        ),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--candidate", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = replay(args.manifest, args.candidate)
    except (
        OSError,
        ValueError,
        KeyError,
        StopIteration,
        TypeError,
        json.JSONDecodeError,
    ) as error:
        print(str(error), file=sys.stderr)
        return 2
    print(canonical_json(result))
    return 0 if result["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
