from prometheus_client import Counter, Histogram

WEBHOOK_EVENTS = Counter(
    "github_webhook_events_total", "GitHub webhook events", ["event", "action"]
)
REVIEW_JOBS = Counter("review_jobs_total", "Review jobs", ["status"])
REVIEW_DURATION = Histogram("review_duration_seconds", "Review job duration")
PUBLISHED_FINDINGS = Counter("published_findings_total", "Published findings", ["severity"])
