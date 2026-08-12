import logging
import time
from typing import Any

from sqlalchemy.exc import IntegrityError

from app.analyzers.runner import StaticAnalyzerRunner
from app.core.config import get_settings
from app.core.metrics import REVIEW_DURATION, REVIEW_JOBS
from app.db.models import FindingRecord, ReviewRule, ReviewRun
from app.db.session import SessionLocal
from app.github.client import GitHubClient
from app.github.publisher import ReviewPublisher
from app.review.engine import ReviewEngine
from app.review.validator import FindingValidator, finding_fingerprint
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="review_pull_request", autoretry_for=(TimeoutError,), retry_backoff=True)
def review_pull_request(job_payload: dict[str, Any]) -> dict[str, Any]:
    started = time.monotonic()
    settings = get_settings()
    REVIEW_JOBS.labels(status="started").inc()

    with SessionLocal() as db:
        run = _create_or_get_run(db, job_payload)
        run.status = "running"
        db.commit()

        try:
            github = GitHubClient.for_installation(job_payload["installation_id"], settings)
            pr = github.get_pull_request(
                job_payload["repository_full_name"], job_payload["pull_request_number"]
            )
            files = github.list_pull_request_files(
                job_payload["repository_full_name"], job_payload["pull_request_number"]
            )
            rules = _load_rules(db, job_payload["repository_full_name"])

            static_findings = StaticAnalyzerRunner().run(files)
            review_result = ReviewEngine(settings).review(pr, files, rules, static_findings)
            validator = FindingValidator(files, settings.min_confidence, settings.max_comments)
            findings = validator.validate([*static_findings, *review_result.findings])

            publisher = ReviewPublisher(github)
            published = publisher.publish(
                job_payload["repository_full_name"],
                job_payload["pull_request_number"],
                pr["head"]["sha"],
                findings,
                review_result.summary,
                review_result.decision.value,
            )

            run.status = "completed"
            run.summary = review_result.summary
            run.decision = review_result.decision.value
            for finding in findings:
                db.add(
                    FindingRecord(
                        review_run_id=run.id,
                        fingerprint=finding_fingerprint(finding),
                        file_path=finding.file_path,
                        line=finding.line,
                        title=finding.title,
                        description=finding.description,
                        severity=finding.severity.value,
                        category=finding.category,
                        suggestion=finding.suggestion,
                        confidence=finding.confidence,
                        source=finding.source,
                    )
                )
            db.commit()
            REVIEW_JOBS.labels(status="completed").inc()
            return {"review_run_id": run.id, "findings": len(findings), "published": published}
        except Exception:
            logger.exception("review job failed")
            run.status = "failed"
            db.commit()
            REVIEW_JOBS.labels(status="failed").inc()
            raise
        finally:
            REVIEW_DURATION.observe(time.monotonic() - started)


def _create_or_get_run(db, payload: dict[str, Any]) -> ReviewRun:
    run = ReviewRun(
        repository_full_name=payload["repository_full_name"],
        pull_request_number=payload["pull_request_number"],
        installation_id=payload["installation_id"],
        head_sha=payload.get("head_sha", ""),
        raw_payload=payload.get("payload"),
    )
    db.add(run)
    try:
        db.commit()
        db.refresh(run)
        return run
    except IntegrityError:
        db.rollback()
        return (
            db.query(ReviewRun)
            .filter_by(
                repository_full_name=payload["repository_full_name"],
                pull_request_number=payload["pull_request_number"],
                head_sha=payload.get("head_sha", ""),
            )
            .one()
        )


def _load_rules(db, repository_full_name: str) -> dict[str, Any]:
    record = db.query(ReviewRule).filter_by(repository_full_name=repository_full_name).one_or_none()
    return record.rules if record else {}
