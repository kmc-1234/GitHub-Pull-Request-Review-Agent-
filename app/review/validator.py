import hashlib

from app.github.diff import FileDiff, parse_pull_request_files
from app.review.schemas import ReviewFinding

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


class FindingValidator:
    def __init__(self, files: list[dict], min_confidence: float, max_comments: int) -> None:
        self.diffs: dict[str, FileDiff] = parse_pull_request_files(files)
        self.min_confidence = min_confidence
        self.max_comments = max_comments

    def validate(self, findings: list[ReviewFinding]) -> list[ReviewFinding]:
        accepted: dict[str, ReviewFinding] = {}
        for finding in findings:
            diff = self.diffs.get(finding.file_path)
            if not diff or not diff.contains_line(finding.line):
                continue
            if finding.confidence < self.min_confidence:
                continue
            key = finding_fingerprint(finding)
            existing = accepted.get(key)
            if existing is None or _rank(finding) < _rank(existing):
                accepted[key] = finding

        ranked = sorted(
            accepted.values(),
            key=lambda item: (
                SEVERITY_ORDER[item.severity.value],
                -item.confidence,
                item.file_path,
                item.line,
            ),
        )
        return ranked[: self.max_comments]


def finding_fingerprint(finding: ReviewFinding) -> str:
    normalized = "|".join(
        [
            finding.file_path,
            str(finding.line),
            finding.title.strip().lower(),
            finding.category.strip().lower(),
        ]
    )
    return hashlib.sha256(normalized.encode()).hexdigest()


def _rank(finding: ReviewFinding) -> tuple[int, float]:
    return (SEVERITY_ORDER[finding.severity.value], -finding.confidence)
