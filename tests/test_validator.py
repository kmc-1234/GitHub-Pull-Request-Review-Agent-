from app.review.schemas import ReviewFinding, Severity
from app.review.validator import FindingValidator

FILES = [
    {
        "filename": "app/auth.py",
        "status": "modified",
        "patch": "@@ -40,3 +40,4 @@\n def check(token):\n+    return True\n     return bool(token)",
    }
]


def finding(line: int, confidence: float = 0.9, title: str = "Bug") -> ReviewFinding:
    return ReviewFinding(
        file_path="app/auth.py",
        line=line,
        title=title,
        description="The changed code is unsafe.",
        severity=Severity.high,
        category="security",
        confidence=confidence,
    )


def test_validator_keeps_only_changed_lines_above_threshold() -> None:
    validator = FindingValidator(FILES, min_confidence=0.8, max_comments=10)

    findings = validator.validate([finding(41), finding(42), finding(41, confidence=0.5)])

    assert [item.line for item in findings] == [41]


def test_validator_deduplicates_and_caps_findings() -> None:
    validator = FindingValidator(FILES, min_confidence=0.8, max_comments=1)

    findings = validator.validate([finding(41), finding(41), finding(41, title="Other bug")])

    assert len(findings) == 1
