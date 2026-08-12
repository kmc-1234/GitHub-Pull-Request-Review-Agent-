# GitHub Pull Request Review Agent

Production-oriented Python service that reviews GitHub pull requests using static analyzers and optional LLM review.

## What it does

- Receives GitHub pull request webhooks through FastAPI.
- Verifies `X-Hub-Signature-256`.
- Enqueues review jobs with Celery and Redis.
- Fetches PR files and patches with GitHub App installation tokens.
- Reviews only added or modified diff lines.
- Runs Ruff, Bandit, and Semgrep when available.
- Optionally calls the OpenAI API for contextual review.
- Validates, deduplicates, caps, and stores findings.
- Publishes inline review comments and a summary review.

## Local setup

1. Copy `.env.example` to `.env` and fill GitHub App settings.
2. Start dependencies and services:

```bash
docker compose up --build
```

3. Expose `http://localhost:8000/api/github/webhook` to GitHub.

## Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

Static tools are optional at runtime. If `ruff`, `bandit`, or `semgrep` are missing, the worker logs the skip and continues.

## GitHub Actions and Kubernetes

- GitHub Actions setup: [docs/github-actions.md](docs/github-actions.md)
- Kubernetes/Helm installation: [docs/kubernetes-install.md](docs/kubernetes-install.md)
- Server install script guide: [docs/helm-server-install.md](docs/helm-server-install.md)
- Default Docker Hub image: `kmc173/github-pull-request-review-agent`

## Repository rules

Per-repository rules can be stored in `review_rules` or configured by extending `RepositoryConfigStore`. Rules are passed to the LLM reviewer and can also set limits like minimum confidence and maximum comments.
