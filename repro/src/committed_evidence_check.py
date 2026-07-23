"""Fail-closed integrity checks for the committed cumulative evidence pack."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_ROOT = ROOT / ".openresearch" / "artifacts"
RUN_COMMAND = "uv run --frozen python repro/src/verify_lion.py"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    manifest_path = ARTIFACT_ROOT / "sha256_manifest.json"
    manifest = _load(manifest_path)
    mismatches = []
    for relative, expected in manifest.items():
        path = ROOT / relative
        if not path.is_file() or _sha256(path) != expected:
            mismatches.append(relative)
    if mismatches:
        raise RuntimeError(f"committed evidence hash mismatch: {mismatches[:5]}")

    final = _load(ARTIFACT_ROOT / "final_verdict.json")
    expected_verdicts = ["VERIFIED"] * 5 + ["FALSIFIED"]
    observed_verdicts = [row["verdict"] for row in final["results"]]
    if (
        final.get("schema") != "lion-cumulative-verdict-v1"
        or final.get("run_command") != RUN_COMMAND
        or not final.get("passed")
        or observed_verdicts != expected_verdicts
    ):
        raise RuntimeError("committed final verdict contract failed")

    raw_rows = 0
    required_common = {
        "claim_contract.json",
        "source_audit.md",
        "method.md",
        "limitations.md",
        "EVAL.md",
        "command.txt",
        "environment.json",
        "final_verdict.json",
        "independent_proof_checker_output.json",
        "negative_control_proof_output.json",
    }
    for claim in range(1, 7):
        claim_dir = ARTIFACT_ROOT / f"claim_{claim}"
        missing = sorted(name for name in required_common if not (claim_dir / name).is_file())
        if missing:
            raise RuntimeError(f"claim {claim} missing required evidence: {missing}")
        if (claim_dir / "command.txt").read_text(encoding="utf-8").strip() != RUN_COMMAND:
            raise RuntimeError(f"claim {claim} command drift")
        for name in ("independent_proof_checker_output.json", "negative_control_proof_output.json"):
            if not _load(claim_dir / name).get("passed"):
                raise RuntimeError(f"claim {claim} failed {name}")

        if claim <= 5:
            for name in (
                "raw_empirical.csv",
                "empirical_summary.json",
                "independent_empirical_checker_output.json",
                "negative_control_empirical_output.json",
            ):
                if not (claim_dir / name).is_file():
                    raise RuntimeError(f"claim {claim} missing {name}")
            if _load(claim_dir / "empirical_summary.json").get("status") != "EMPIRICALLY_SUPPORTED":
                raise RuntimeError(f"claim {claim} empirical status failed")
            for name in (
                "independent_empirical_checker_output.json",
                "negative_control_empirical_output.json",
            ):
                if not _load(claim_dir / name).get("passed"):
                    raise RuntimeError(f"claim {claim} failed {name}")
            with (claim_dir / "raw_empirical.csv").open(newline="", encoding="utf-8") as handle:
                raw_rows += sum(1 for _ in csv.DictReader(handle))
        elif not (claim_dir / "raw_counterexample.json").is_file():
            raise RuntimeError("claim 6 counterexample evidence missing")

    if raw_rows != 1776:
        raise RuntimeError(f"expected 1776 empirical rows, found {raw_rows}")

    result = {
        "schema": "lion-committed-evidence-check-v1",
        "passed": True,
        "manifest_entries_verified": len(manifest),
        "artifact_files_present": sum(path.is_file() for path in ARTIFACT_ROOT.rglob("*")),
        "raw_empirical_rows": raw_rows,
        "verdicts": observed_verdicts,
        "run_command": RUN_COMMAND,
    }
    output = ARTIFACT_ROOT / "committed_evidence_checker_output.json"
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("COMMITTED_EVIDENCE_MACHINE_SUMMARY " + json.dumps(result, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
