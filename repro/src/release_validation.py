"""Validate the additive, text-only Hugging Face release candidate."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parents[2]
RELEASE = ROOT / "release"
SPACE = RELEASE / "space_candidate"
ARTIFACT_ROOT = ROOT / ".openresearch" / "artifacts"
ALLOWLIST = RELEASE / "hf_upload_allowlist.txt"
UPLOAD_MANIFEST = RELEASE / "hf_upload_manifest.sha256"
PROTECTED_MANIFEST = RELEASE / "protected-judged-manifest.sha256"
ALLOWED_VERDICTS = ["VERIFIED"] * 5 + ["FALSIFIED"]

SECRET_PATTERNS = (
    re.compile(r"hf_[A-Za-z0-9]{20,}"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"(?i)(?:api[_-]?key|access[_-]?token|secret)[\"']?\s*[:=]\s*[\"'][^\"']{8,}"),
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _manifest(path: Path) -> dict[str, str]:
    result = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        digest, relative = line.split(maxsplit=1)
        result[relative.strip()] = digest
    return result


def _walk_logbook(node: dict) -> list[str]:
    files = [node["file"]]
    for child in node.get("children", []):
        files.extend(_walk_logbook(child))
    return files


def main() -> None:
    allow_pairs = []
    for line in ALLOWLIST.read_text(encoding="utf-8").splitlines():
        local, remote = line.split("\t")
        remote_path = PurePosixPath(remote)
        if remote_path.is_absolute() or ".." in remote_path.parts:
            raise RuntimeError(f"unsafe remote path: {remote}")
        allow_pairs.append((local, remote))
    remote_paths = [remote for _, remote in allow_pairs]
    if len(remote_paths) != len(set(remote_paths)):
        raise RuntimeError("duplicate remote upload path")

    upload_manifest = _manifest(UPLOAD_MANIFEST)
    if set(upload_manifest) != set(remote_paths):
        raise RuntimeError("upload manifest and allowlist path sets differ")
    for local, remote in allow_pairs:
        local_path = ROOT / local
        if not local_path.is_file() or _sha(local_path) != upload_manifest[remote]:
            raise RuntimeError(f"upload hash mismatch: {local} -> {remote}")
        text = local_path.read_text(encoding="utf-8")
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                raise RuntimeError(f"secret-like text in upload: {local}")

    protected = _manifest(PROTECTED_MANIFEST)
    old_paths = set(protected)
    future_paths = old_paths | set(remote_paths)
    if not old_paths <= future_paths:
        raise RuntimeError("protected judged file set is not a subset")

    intentionally_changed = {"logbook.json"}
    local_old_text = {
        str(path.relative_to(SPACE))
        for path in SPACE.rglob("*")
        if path.is_file() and str(path.relative_to(SPACE)) in old_paths
    }
    preserved_hashes = []
    for relative in sorted(local_old_text - intentionally_changed):
        if _sha(SPACE / relative) != protected[relative]:
            raise RuntimeError(f"protected text changed: {relative}")
        preserved_hashes.append(relative)

    logbook = json.loads((SPACE / "logbook.json").read_text(encoding="utf-8"))
    if logbook.get("schema_version") != 1 or logbook.get("space_id") != "DineshAI/32NvV5zixD":
        raise RuntimeError("invalid logbook identity or schema")
    referenced_pages = _walk_logbook(logbook["root"])
    if any(page not in future_paths for page in referenced_pages):
        raise RuntimeError("logbook references a missing page")

    final = json.loads((ARTIFACT_ROOT / "final_verdict.json").read_text(encoding="utf-8"))
    verdicts = [row["verdict"] for row in final["results"]]
    if verdicts != ALLOWED_VERDICTS or not final.get("passed"):
        raise RuntimeError("release candidate verdict vector failed")
    for claim in range(1, 7):
        prefix = f"evidence/claim_{claim}/"
        required = {
            prefix + "claim_contract.json",
            prefix + "source_audit.md",
            prefix + "method.md",
            prefix + "limitations.md",
            prefix + "EVAL.md",
            prefix + "command.txt",
            prefix + "environment.json",
            prefix + "final_verdict.json",
            prefix + "independent_proof_checker_output.json",
            prefix + "negative_control_proof_output.json",
        }
        if not required <= set(remote_paths):
            raise RuntimeError(f"claim {claim} missing upload evidence")

    result = {
        "schema": "lion-protected-release-check-v1",
        "passed": True,
        "space_id": "DineshAI/32NvV5zixD",
        "protected_revision": "18c02b05d9b22408040b48f039a35274c1b06d6a",
        "protected_file_count": len(old_paths),
        "protected_file_set_is_subset": True,
        "protected_text_hashes_preserved": len(preserved_hashes),
        "intentionally_changed_existing_files": sorted(intentionally_changed),
        "remote_preserved_binary_files": sorted(path for path in old_paths if path.endswith(".png")),
        "upload_entries": len(allow_pairs),
        "future_logical_file_count": len(future_paths),
        "logbook_pages_resolved": len(referenced_pages),
        "verdicts": verdicts,
        "secret_scan_passed": True,
        "text_only_upload": True,
    }
    output = ARTIFACT_ROOT / "release_validation.json"
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("RELEASE_MACHINE_SUMMARY " + json.dumps(result, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
