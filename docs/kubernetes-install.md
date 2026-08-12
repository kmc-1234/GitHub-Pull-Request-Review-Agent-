# Kubernetes and Helm Installation

These commands install the agent on a Kubernetes server using the Docker Hub image:

```text
kmc173/github-pull-request-review-agent
```

## Prerequisites

- Kubernetes cluster access with `kubectl`.
- Helm 3 installed.
- PostgreSQL available to the cluster.
- Redis available to the cluster.
- A GitHub App with:
  - Pull request read/write permissions.
  - Contents read permission.
  - Metadata read permission.
  - Webhook events for pull requests.

## 1. Clone the repository

```bash
git clone https://github.com/kmc-1234/GitHub-Pull-Request-Review-Agent-.git
cd GitHub-Pull-Request-Review-Agent-
```

## 2. Create namespace

```bash
kubectl create namespace pr-review-agent
```

## 3. Create application secret

Replace the values before running:

```bash
kubectl -n pr-review-agent create secret generic pr-review-agent-secrets \
  --from-literal=DATABASE_URL='postgresql+psycopg://USER:PASSWORD@POSTGRES_HOST:5432/review' \
  --from-literal=REDIS_URL='redis://REDIS_HOST:6379/0' \
  --from-literal=GITHUB_WEBHOOK_SECRET='CHANGE_ME' \
  --from-literal=GITHUB_APP_ID='123456' \
  --from-file=GITHUB_PRIVATE_KEY=./github-app-private-key.pem \
  --from-literal=OPENAI_API_KEY='sk-...'
```

## 4. Install with Helm

Without ingress:

```bash
helm upgrade --install pr-review-agent deploy/helm/pr-review-agent \
  --namespace pr-review-agent \
  --set-string image.repository=kmc173/github-pull-request-review-agent \
  --set-string image.tag=latest \
  --set-string existingSecret.name=pr-review-agent-secrets
```

With ingress and a specific image version:

```bash
helm upgrade --install pr-review-agent deploy/helm/pr-review-agent \
  --namespace pr-review-agent \
  --set-string image.repository=kmc173/github-pull-request-review-agent \
  --set-string image.tag=v0.1.0 \
  --set-string existingSecret.name=pr-review-agent-secrets \
  --set ingress.enabled=true \
  --set-string ingress.className=nginx \
  --set-string ingress.host=pr-review.example.com
```

## 5. Verify installation

```bash
kubectl -n pr-review-agent get pods
kubectl -n pr-review-agent rollout status deploy/pr-review-agent-api
kubectl -n pr-review-agent rollout status deploy/pr-review-agent-worker
kubectl -n pr-review-agent get svc
kubectl -n pr-review-agent logs deploy/pr-review-agent-api --tail=100
```

Health check:

```bash
kubectl -n pr-review-agent port-forward svc/pr-review-agent-api 8000:80
curl http://localhost:8000/healthz
```

Expected response:

```json
{"status":"ok"}
```

## 6. Configure GitHub webhook

In your GitHub App settings, set the webhook URL to:

```text
https://YOUR_DOMAIN/api/github/webhook
```

Use the same webhook secret you stored as `GITHUB_WEBHOOK_SECRET`.

Subscribe to:

- Pull request events.
- Pull request review comment events, if you want future duplicate/comment awareness workflows.

## Upgrade

After a new image is pushed:

```bash
helm upgrade pr-review-agent deploy/helm/pr-review-agent \
  --namespace pr-review-agent \
  --set-string image.repository=kmc173/github-pull-request-review-agent \
  --set-string image.tag=v0.2.0 \
  --set-string existingSecret.name=pr-review-agent-secrets
```

## Uninstall

```bash
helm uninstall pr-review-agent --namespace pr-review-agent
kubectl delete namespace pr-review-agent
```
