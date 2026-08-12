from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Float, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ReviewRun(Base):
    __tablename__ = "review_runs"
    __table_args__ = (
        UniqueConstraint(
            "repository_full_name", "pull_request_number", "head_sha", name="uq_review_run"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    repository_full_name: Mapped[str] = mapped_column(String(255), index=True)
    pull_request_number: Mapped[int] = mapped_column(Integer, index=True)
    installation_id: Mapped[int] = mapped_column(Integer)
    head_sha: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(32), default="queued")
    summary: Mapped[str | None] = mapped_column(Text)
    decision: Mapped[str | None] = mapped_column(String(32))
    raw_payload: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class FindingRecord(Base):
    __tablename__ = "finding_records"
    __table_args__ = (
        UniqueConstraint("review_run_id", "fingerprint", name="uq_finding_fingerprint"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    review_run_id: Mapped[int] = mapped_column(Integer, index=True)
    fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    file_path: Mapped[str] = mapped_column(String(512))
    line: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(32))
    category: Mapped[str] = mapped_column(String(64))
    suggestion: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(64))
    published_comment_id: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ReviewRule(Base):
    __tablename__ = "review_rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    repository_full_name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    rules: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
