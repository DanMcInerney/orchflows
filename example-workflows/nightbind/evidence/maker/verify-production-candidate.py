"""Read-only runtime integrity check; writes only closeout evidence manifests."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[2]
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))
def files_under(path):
    return sorted(p for p in path.rglob("*") if p.is_file() and not any(x in ("node_modules", "__pycache__") for x in p.parts) and not p.name.endswith(".blend1"))

created = datetime.now(timezone.utc).isoformat()
results = []
source_sets = []
for build_id, output in [("release-c09f13cac8e9", "dist"), ("qa-c09f13cac8e9", "test-dist")]:
    manifest = read(root / f"evidence/builds/{build_id}.json")
    mismatches = [entry["path"] for entry in manifest["source"] + manifest["built"] if not (root / entry["path"]).is_file() or sha(root / entry["path"]) != entry["sha256"]]
    actual_source = []
    for directory in ["src", "scripts", "tests", "public", "assets/source"]:
        actual_source.extend(files_under(root / directory))
    actual_source.extend(root / name for name in ["index.html", "asset-preview.html", "package.json", "package-lock.json", "vite.config.js"])
    source_paths = {p.relative_to(root).as_posix() for p in actual_source}
    declared_source = {entry["path"] for entry in manifest["source"]}
    actual_output = {p.relative_to(root).as_posix() for p in files_under(root / output)}
    declared_output = {entry["path"] for entry in manifest["built"]}
    source_difference = sorted(source_paths ^ declared_source)
    output_difference = sorted(actual_output ^ declared_output)
    javascript = "".join(p.read_text(encoding="utf-8") for p in files_under(root / output) if p.suffix == ".js")
    audit = {"adapterPresent": "__gameTest" in javascript, "fixturesPresent": "boss-danger" in javascript}
    expected_diagnostics = output == "test-dist"
    digest = hashlib.sha256(json.dumps(manifest["source"], separators=(",", ":")).encode()).hexdigest()[:12]
    assert build_id.endswith(digest), "source digest changed"
    assert not mismatches and not source_difference and not output_difference, "file integrity mismatch"
    assert all(value == expected_diagnostics for value in audit.values()), "diagnostics isolation mismatch"
    source_sets.append(manifest["source"])
    results.append({"build": build_id, "sourceFiles": len(manifest["source"]), "outputFiles": len(manifest["built"]), "hashMismatches": mismatches, "sourcePathDifference": source_difference, "outputPathDifference": output_difference, "diagnosticAudit": audit, "manifest": f"evidence/builds/{build_id}.json", "manifestSha256": sha(root / f"evidence/builds/{build_id}.json")})
assert source_sets[0] == source_sets[1], "release and test source differ"
asset_manifest = root / "public/models/manifest.json"
expected_asset_sha = "b943f7fca7efc58f225fdf6f7add960a1bf71218943df84274434e6628e00f66"
assert sha(asset_manifest) == expected_asset_sha
archive_root = root / "evidence/builds/core-220cfa39951c-runtime"
archive = read(archive_root / "archive.json")
archive_mismatches = [entry["path"] for entry in archive["files"] if sha(archive_root / entry["path"].removeprefix("dist/")) != entry["sha256"]]
assert not archive_mismatches
verification = {"checkedAt": created, "method": "Read-only file hashing, path-set comparison and compiled diagnostics audit; no rebuild or replay", "commonSource": "source-c09f13cac8e9", "sameSourceAcrossBuilds": True, "builds": results, "assetManifestSha256": expected_asset_sha, "archivedCore": {"build": archive["build"], "filesChecked": len(archive["files"]), "mismatches": archive_mismatches}, "result": "PASS"}
verification_path = root / "evidence/builds/production-final-verification.json"
verification_path.write_text(json.dumps(verification, indent=2) + "\n", encoding="utf-8")
handoff_paths = ["README.md", ".gitignore", "notes/production-qa.md", "notes/performance.md", "notes/production-qa-plan.md", "notes/production-step14.md", "notes/core-baseline.md", "notes/core-review.md", "notes/core-playtest.md", "notes/asset-brief.md", "notes/art-direction.md", "notes/assets.md", "notes/caller-production-play.md", "notes/caller-step14.md", "notes/request.md", "notes/acceptance.md", "notes/capabilities.md", "evidence/assets/delivery-inventory.json", "evidence/maker/production-wave9-recalculation.json", "evidence/maker/analyze-production-performance.py", "evidence/maker/verify-production-candidate.py", "evidence/caller/dusk-run/attempt2-performance-summary.json", "evidence/caller/dusk-run/attempt2-wave9-frames.json", "evidence/caller/dusk-run/performance-metadata-after-retry.json", "evidence/caller/dusk-run/repeated-retries.json", "evidence/caller/fresh-origin-load.json", "evidence/caller/integrated-load-recovery.json", "evidence/builds/production-final-verification.json"]
glbs = list((root / "public/models").glob("*.glb"))
candidate = {"status": "READY for final independent review; maker/caller QA complete", "frozenAt": created, "release": {"id": results[0]["build"], "url": "http://127.0.0.1:4191/", "manifest": results[0]["manifest"], "manifestSha256": results[0]["manifestSha256"]}, "assistedTest": {"id": results[1]["build"], "url": "http://127.0.0.1:4193/", "manifest": results[1]["manifest"], "manifestSha256": results[1]["manifestSha256"]}, "sourceIdentity": "source-c09f13cac8e9", "assets": {"manifest": "public/models/manifest.json", "sha256": expected_asset_sha, "glbCount": len(glbs), "glbBytes": sum(p.stat().st_size for p in glbs), "editableBlenderCount": len(list((root / "assets/source").glob("*.blend"))), "report": "notes/assets.md"}, "verification": "evidence/builds/production-final-verification.json", "handoffDocuments": [{"path": path, "sha256": sha(root / path)} for path in handoff_paths], "evidenceScope": "Source/build manifests enumerate every current production source, asset and compiled file. Handoff document hashes snapshot this checkpoint. Historical screenshots/state are linked in the reports; this is not an assertion that every past evidence file belongs to the final build.", "limits": ["1280x720 DPR1 Intel/D3D11 observed; other viewport/device matrix unverified", "Ordinary Dusk/Eclipse final run uses public pauses; Solar/Worldcoil final forms observed assisted", "Audible quality, deliberate blur and graphics context loss unverified", "Startup is local warm/fresh-origin readiness, not clean-profile/network/GPU-cold timing", "Final independent review pending; game/assets remain frozen"]}
(root / "evidence/builds/production-candidate.json").write_text(json.dumps(candidate, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"result": "PASS", "builds": results, "assetManifestSha256": expected_asset_sha, "archivedCoreFiles": len(archive["files"]), "handoffDocuments": len(handoff_paths)}, indent=2))
