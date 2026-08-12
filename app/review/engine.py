import json
import logging
from typing import Any

from openai import OpenAI
from pydantic import ValidationError

from app.core.config import Settings
from app.review.schemas import ReviewDecision, ReviewFinding, ReviewResult

logger = logging.getLogger(__name__)


class ReviewEngine:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def review(
        self,
        pr: dict[str, Any],
        files: list[dict[str, Any]],
        rules: dict[str, Any],
        static_findings: list[ReviewFinding],
    ) -> ReviewResult:
        if not self.settings.openai_api_key:
            return self._fallback_result(pr, static_findings)

        client = OpenAI(api_key=self.settings.openai_api_key)
        prompt = _build_prompt(pr, files, rules, static_findings)
        response = client.responses.create(
            model=self.settings.openai_model,
            input=[
                {
                    "role": "system",
                    "content": (
                        "You are a senior code reviewer. Return only JSON matching the "
                        "requested schema. "
                        "Review only changed lines present in the provided patches."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            text={"format": {"type": "json_object"}},
        )
        text = response.output_text
        try:
            return ReviewResult.model_validate_json(text)
        except ValidationError:
            logger.exception("LLM returned invalid review JSON")
            return self._fallback_result(pr, static_findings)

    def _fallback_result(
        self, pr: dict[str, Any], static_findings: list[ReviewFinding]
    ) -> ReviewResult:
        title = pr.get("title") or "pull request"
        decision = (
            ReviewDecision.request_changes
            if any(f.severity.value in {"critical", "high"} for f in static_findings)
            else ReviewDecision.comment
        )
        return ReviewResult(
            findings=[],
            summary=(
                f"Automated review completed for '{title}'. LLM review is disabled; "
                "static-analysis findings were processed."
            ),
            decision=decision,
        )


def _build_prompt(
    pr: dict[str, Any],
    files: list[dict[str, Any]],
    rules: dict[str, Any],
    static_findings: list[ReviewFinding],
) -> str:
    payload = {
        "pull_request": {
            "title": pr.get("title"),
            "body": pr.get("body"),
            "base": (pr.get("base") or {}).get("ref"),
            "head": (pr.get("head") or {}).get("ref"),
        },
        "repository_rules": rules,
        "static_findings": [finding.model_dump(mode="json") for finding in static_findings],
        "files": [
            {
                "filename": item.get("filename"),
                "status": item.get("status"),
                "additions": item.get("additions"),
                "deletions": item.get("deletions"),
                "patch": item.get("patch"),
            }
            for item in files
            if item.get("patch") and not _is_generated_or_binary(item)
        ],
        "required_schema": {
            "findings": [
                {
                    "file_path": "string",
                    "line": "integer changed line only",
                    "title": "string",
                    "description": "string",
                    "severity": "critical|high|medium|low",
                    "category": "security|bug|quality|tests|maintainability",
                    "suggestion": "string|null",
                    "confidence": "number 0..1",
                }
            ],
            "summary": "complete PR summary",
            "decision": "APPROVE|COMMENT|REQUEST_CHANGES",
        },
    }
    return json.dumps(payload, indent=2)


def _is_generated_or_binary(item: dict[str, Any]) -> bool:
    filename = item.get("filename", "")
    generated_extensions = (".lock", ".min.js", ".png", ".jpg", ".jpeg", ".gif", ".pdf")
    return item.get("patch") is None or filename.endswith(generated_extensions)
