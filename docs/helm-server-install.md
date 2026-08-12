# Install on a Kubernetes Server with Helm

This is the shortest production install path for your image:

```text
kmc173/github-pull-request-review-agent:v0.1.0
```

## 1. Log in to your server

SSH to the server that has `kubectl` access to your Kubernetes cluster:

```bash
ssh USER@SERVER_IP
```

Check tools:

```bash
kubectl version --client
helm version
kubectl get nodes
```

## 2. Clone the repo

```bash
git clone https://github.com/kmc-1234/GitHub-Pull-Request-Review-Agent-.git
cd GitHub-Pull-Request-Review-Agent-
```

## 3. Prepare required values

You need PostgreSQL and Redis reachable from Kubernetes.

Create or copy your GitHub App private key file to the server, for example:

```bash
ls ./github-app-private-key.pem
```

Export install values:

```bash
export IMAGE_TAG=v0.1.0
export NAMESPACE=pr-review-agent

export DATABASE_URL='postgresql+psycopg://USER:PASSWORD@POSTGRES_HOST:5432/review'
export REDIS_URL='redis://REDIS_HOST:6379/0'

export GITHUB_WEBHOOK_SECRET='CHANGE_ME_TO_YOUR_WEBHOOK_SECRET'
export GITHUB_APP_ID='123456'
export GITHUB_PRIVATE_KEY_FILE='./github-app-private-key.pem'

export OPENAI_API_KEY='sk-...'
```

For ingress:

```bash
export INGRESS_ENABLED=true
export INGRESS_CLASS_NAME=nginx
export INGRESS_HOST=pr-review.example.com
```

If you do not have ingress yet:

```bash
export INGRESS_ENABLED=false
```

## 4. Run Helm install

```bash
bash scripts/install-helm.sh
```

The script will:

- Create namespace `pr-review-agent`.
- Create/update Kubernetes secret `pr-review-agent-secrets`.
- Install or upgrade the Helm release.
- Deploy API and worker pods.
- Wait for rollout.

## 5. Verify

```bash
kubectl -n pr-review-agent get pods
kubectl -n pr-review-agent get svc
kubectl -n pr-review-agent logs deploy/pr-review-agent-api --tail=100
kubectl -n pr-review-agent logs deploy/pr-review-agent-worker --tail=100
```

Without ingress, test locally:

```bash
kubectl -n pr-review-agent port-forward svc/pr-review-agent-api 8000:80
curl http://localhost:8000/healthz
```

Expected:

```json
{"status":"ok"}
```

## 6. Configure GitHub App webhook

If ingress is enabled, set the GitHub App webhook URL to:

```text
https://pr-review.example.com/api/github/webhook
```

Use the same value as:

```text
GITHUB_WEBHOOK_SECRET
```

Subscribe to pull request events.

## Upgrade later

After GitHub Actions pushes a new Docker image tag, for example `v0.2.0`:

```bash
export IMAGE_TAG=v0.2.0
bash scripts/install-helm.sh
```

## Remove

```bash
helm uninstall pr-review-agent --namespace pr-review-agent
kubectl delete namespace pr-review-agent
```
