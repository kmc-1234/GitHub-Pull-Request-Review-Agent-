from app.core.metrics import PUBLISHED_FINDINGS
from app.github.client import GitHubClient
from app.github.diff import parse_pull_request_files
from app.review.schemas import ReviewFinding
from app.review.validator import finding_fingerprint


class ReviewPublisher:
    def __init__(self, github: GitHubClient) -> None:
        self.github = github

    def publish(
        self,
        repo: str,
        pr_number: int,
        commit_id: str,
        findings: list[ReviewFinding],
        summary: str,
        decision: str,
    ) -> int:
        files = self.github.list_pull_request_files(repo, pr_number)
        diffs = parse_pull_request_files(files)
        existing_markers = {
            marker
            for comment in self.github.list_review_comments(repo, pr_number)
            if (marker := _extract_marker(comment.get("body", "")))
        }
        comments = []
        published_findings = []
        for finding in findings:
            fingerprint = finding_fingerprint(finding)
            if fingerprint in existing_markers:
                continue
            diff = diffs.get(finding.file_path)
            position = diff.position_for_line(finding.line) if diff else None
            if position is None:
                continue
            comments.append(
                {
                    "path": finding.file_path,
                    "position": position,
                    "body": _format_finding(finding, fingerprint),
                }
            )
            published_findings.append(finding)
        event = "REQUEST_CHANGES" if decision == "REQUEST_CHANGES" and comments else "COMMENT"
        self.github.create_review(repo, pr_number, commit_id, summary, event, comments)
        for finding in published_findings:
            PUBLISHED_FINDINGS.labels(severity=finding.severity.value).inc()
        return len(comments)


def _format_finding(finding: ReviewFinding, fingerprint: str) -> str:
    lines = [
        f"**{finding.title}**",
        "",
        finding.description,
        "",
        f"Severity: `{finding.severity.value}` | Confidence: `{finding.confidence:.2f}` "
        f"| Category: `{finding.category}`",
    ]
    if finding.suggestion:
        lines.extend(["", f"Suggested correction: {finding.suggestion}"])
    lines.extend(["", f"<!-- pr-review-agent:{fingerprint} -->"])
    return "\n".join(lines)


def _extract_marker(body: str) -> str | None:
    prefix = "<!-- pr-review-agent:"
    suffix = " -->"
    start = body.find(prefix)
    if start == -1:
        return None
    end = body.find(suffix, start)
    if end == -1:
        return None
    return body[start + len(prefix) : end]
