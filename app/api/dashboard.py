from collections import Counter
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.db.models import FindingRecord, ReviewRule, ReviewRun
from app.db.session import get_db

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])
DbSession = Annotated[Session, Depends(get_db)]


class RuleUpdate(BaseModel):
    repository_full_name: str = Field(min_length=1)
    rules: dict[str, Any] = Field(default_factory=dict)


@router.get("/overview")
def overview(db: DbSession) -> dict[str, Any]:
    total_runs = db.query(func.count(ReviewRun.id)).scalar() or 0
    total_findings = db.query(func.count(FindingRecord.id)).scalar() or 0
    open_projects = (
        db.query(func.count(func.distinct(ReviewRun.repository_full_name))).scalar() or 0
    )
    latest_run = db.query(ReviewRun).order_by(desc(ReviewRun.created_at)).first()

    severity_rows = (
        db.query(FindingRecord.severity, func.count(FindingRecord.id))
        .group_by(FindingRecord.severity)
        .all()
    )
    status_rows = (
        db.query(ReviewRun.status, func.count(ReviewRun.id)).group_by(ReviewRun.status).all()
    )
    category_rows = (
        db.query(FindingRecord.category, func.count(FindingRecord.id))
        .group_by(FindingRecord.category)
        .order_by(desc(func.count(FindingRecord.id)))
        .limit(8)
        .all()
    )

    return {
        "totals": {
            "projects": open_projects,
            "review_runs": total_runs,
            "findings": total_findings,
            "last_review_at": _dt(latest_run.created_at) if latest_run else None,
        },
        "severity": {name or "unknown": count for name, count in severity_rows},
        "status": {name or "unknown": count for name, count in status_rows},
        "categories": [
            {"name": name or "unknown", "count": count} for name, count in category_rows
        ],
        "quality_gate": _quality_gate(total_findings, Counter(dict(severity_rows))),
    }


@router.get("/projects")
def projects(db: DbSession) -> list[dict[str, Any]]:
    rows = (
        db.query(
            ReviewRun.repository_full_name,
            func.count(ReviewRun.id).label("review_runs"),
            func.max(ReviewRun.created_at).label("last_review_at"),
        )
        .group_by(ReviewRun.repository_full_name)
        .order_by(desc("last_review_at"))
        .all()
    )
    output = []
    for repository, review_runs, last_review_at in rows:
        latest = (
            db.query(ReviewRun)
            .filter(ReviewRun.repository_full_name == repository)
            .order_by(desc(ReviewRun.created_at))
            .first()
        )
        findings = (
            db.query(FindingRecord.severity, func.count(FindingRecord.id))
            .join(ReviewRun, ReviewRun.id == FindingRecord.review_run_id)
            .filter(ReviewRun.repository_full_name == repository)
            .group_by(FindingRecord.severity)
            .all()
        )
        output.append(
            {
                "repository_full_name": repository,
                "review_runs": review_runs,
                "last_review_at": _dt(last_review_at),
                "latest_status": latest.status if latest else None,
                "latest_decision": latest.decision if latest else None,
                "findings": {severity or "unknown": count for severity, count in findings},
            }
        )
    return output


@router.get("/runs")
def runs(db: DbSession, limit: int = 50) -> list[dict[str, Any]]:
    records = db.query(ReviewRun).order_by(desc(ReviewRun.created_at)).limit(min(limit, 200)).all()
    return [
        {
            "id": item.id,
            "repository_full_name": item.repository_full_name,
            "pull_request_number": item.pull_request_number,
            "head_sha": item.head_sha,
            "status": item.status,
            "decision": item.decision,
            "summary": item.summary,
            "created_at": _dt(item.created_at),
            "updated_at": _dt(item.updated_at),
        }
        for item in records
    ]


@router.get("/findings")
def findings(db: DbSession, limit: int = 100) -> list[dict[str, Any]]:
    records = (
        db.query(FindingRecord, ReviewRun)
        .join(ReviewRun, ReviewRun.id == FindingRecord.review_run_id)
        .order_by(desc(FindingRecord.created_at))
        .limit(min(limit, 300))
        .all()
    )
    return [
        {
            "id": finding.id,
            "repository_full_name": run.repository_full_name,
            "pull_request_number": run.pull_request_number,
            "file_path": finding.file_path,
            "line": finding.line,
            "title": finding.title,
            "description": finding.description,
            "severity": finding.severity,
            "category": finding.category,
            "suggestion": finding.suggestion,
            "confidence": finding.confidence,
            "source": finding.source,
            "created_at": _dt(finding.created_at),
        }
        for finding, run in records
    ]


@router.get("/rules")
def rules(db: DbSession) -> list[dict[str, Any]]:
    records = db.query(ReviewRule).order_by(ReviewRule.repository_full_name).all()
    return [
        {
            "repository_full_name": item.repository_full_name,
            "rules": item.rules,
            "updated_at": _dt(item.updated_at),
        }
        for item in records
    ]


@router.put("/rules")
def upsert_rules(payload: RuleUpdate, db: DbSession) -> dict[str, Any]:
    record = (
        db.query(ReviewRule)
        .filter(ReviewRule.repository_full_name == payload.repository_full_name)
        .one_or_none()
    )
    if record is None:
        record = ReviewRule(
            repository_full_name=payload.repository_full_name,
            rules=payload.rules,
        )
        db.add(record)
    else:
        record.rules = payload.rules
    db.commit()
    return {"saved": True, "repository_full_name": payload.repository_full_name}


@router.delete("/rules/{repository_full_name:path}")
def delete_rules(repository_full_name: str, db: DbSession) -> dict[str, Any]:
    record = (
        db.query(ReviewRule)
        .filter(ReviewRule.repository_full_name == repository_full_name)
        .one_or_none()
    )
    if record is None:
        raise HTTPException(status_code=404, detail="rules not found")
    db.delete(record)
    db.commit()
    return {"deleted": True}


def _quality_gate(total_findings: int, severity: Counter[str]) -> str:
    if severity.get("critical", 0) or severity.get("high", 0):
        return "failed"
    if total_findings:
        return "warning"
    return "passed"


def _dt(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.isoformat()
