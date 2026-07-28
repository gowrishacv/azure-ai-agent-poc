import json
from pathlib import Path

from scripts.regulatory_evidence import (
    evaluate_check,
    evaluate_controls,
    load_control_sets,
    render_markdown,
    scan_personal_data,
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


def test_personal_data_scan_reports_counts_without_values() -> None:
    scan = scan_personal_data(
        REPOSITORY_ROOT,
        ["tests/fixtures/synthetic-personal-data.txt"],
    )

    assert scan["status"] == "potential_personal_data_detected"
    assert scan["files_with_findings"] == 1
    assert scan["total_indicators"] == 5
    assert scan["indicator_types"] == {
        "customer_identifier": 1,
        "email_address": 1,
        "international_phone": 1,
        "ipv4_address": 1,
        "labelled_person_name": 1,
    }
    serialized = json.dumps(scan)
    assert "Example Person" not in serialized
    assert "ava.example@example.invalid" not in serialized
    assert "+49 30 5550 1234" not in serialized
    assert "192.0.2.42" not in serialized
    assert "CUST-123456" not in serialized


def test_markdown_report_does_not_include_detected_values() -> None:
    report = evaluate_controls(
        REPOSITORY_ROOT,
        load_control_sets(REPOSITORY_ROOT / "compliance" / "controls"),
    )
    report["personal_data_scan"] = scan_personal_data(
        REPOSITORY_ROOT,
        ["tests/fixtures/synthetic-personal-data.txt"],
    )
    report["ai_review"] = "Not requested."

    markdown = render_markdown(report)

    assert "potential_personal_data_detected" in markdown
    assert "email_address: 1" in markdown
    assert "labelled_person_name: 1" in markdown
    assert "ava.example@example.invalid" not in markdown
