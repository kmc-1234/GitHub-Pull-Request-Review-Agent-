from enum import StrEnum

from pydantic import BaseModel, Field


class Severity(StrEnum):
    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"


class ReviewDecision(StrEnum):
    approve = "APPROVE"
    comment = "COMMENT"
    request_changes = "REQUEST_CHANGES"


class ReviewFinding(BaseModel):
    file_path: str
    line: int
    title: str
    description: str
    severity: Severity
    category: str
    suggestion: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    source: str = "llm"


class ReviewResult(BaseModel):
    findings: list[ReviewFinding] = Field(default_factory=list)
    summary: str
    decision: ReviewDecision = ReviewDecision.comment
