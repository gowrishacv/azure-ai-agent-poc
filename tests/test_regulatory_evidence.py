import json
from pathlib import Path

from scripts.regulatory_evidence import (
    evaluate_check,
    evaluate_controls,
    load_control_sets,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def test_repository_controls_have_no_critical_failures() -> None:
    controls = load_control_sets(REPOSITORY_ROOT / "compliance" / "controls")

    report = evaluate_controls(REPOSITORY_ROOT, controls)

    assert report["summary"]["critical_failures"] == 0
    assert report["summary"]["manual_reviews_required"] == 2
    assert report["summary"]["result"] == "pass_with_review"


def test_missing_critical_evidence_fails(tmp_path: Path) -> None:
    check = {
        "id": "TEST-1",
        "description": "Required evidence exists.",
        "severity": "critical",
        "kind": "file_exists",
        "path": "missing.tf",
    }

    result = evaluate_check(tmp_path, check)

    assert result["status"] == "fail"
    assert result["evidence"]["sha256"] is None


def test_control_files_use_official_sources() -> None:
    for path in (REPOSITORY_ROOT / "compliance" / "controls").glob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["official_source"].startswith("https://eur-lex.europa.eu/")
