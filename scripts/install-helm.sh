#!/usr/bin/env bash
set -euo pipefail

RELEASE_NAME="${RELEASE_NAME:-pr-review-agent}"
NAMESPACE="${NAMESPACE:-pr-review-agent}"
CHART_PATH="${CHART_PATH:-deploy/helm/pr-review-agent}"
IMAGE_REPOSITORY="${IMAGE_REPOSITORY:-kmc173/github-pull-request-review-agent}"
IMAGE_TAG="${IMAGE_TAG:-v0.1.0}"
SECRET_NAME="${SECRET_NAME:-pr-review-agent-secrets}"
INGRESS_ENABLED="${INGRESS_ENABLED:-false}"
INGRESS_CLASS_NAME="${INGRESS_CLASS_NAME:-nginx}"
INGRESS_HOST="${INGRESS_HOST:-}"

required_env() {
  local name="$1"
  if [ -z "${!name:-}" ]; then
    echo "Missing required environment variable: ${name}" >&2
    exit 1
  fi
}

require_command() {
  local command_name="$1"
  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "Missing required command: ${command_name}" >&2
    exit 1
  fi
}

require_command kubectl
require_command helm

required_env DATABASE_URL
required_env REDIS_URL
required_env GITHUB_WEBHOOK_SECRET
required_env GITHUB_APP_ID
required_env GITHUB_PRIVATE_KEY_FILE

if [ ! -f "$GITHUB_PRIVATE_KEY_FILE" ]; then
  echo "GITHUB_PRIVATE_KEY_FILE does not exist: ${GITHUB_PRIVATE_KEY_FILE}" >&2
  exit 1
fi

kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -

kubectl -n "$NAMESPACE" create secret generic "$SECRET_NAME" \
  --from-literal=DATABASE_URL="$DATABASE_URL" \
  --from-literal=REDIS_URL="$REDIS_URL" \
  --from-literal=GITHUB_WEBHOOK_SECRET="$GITHUB_WEBHOOK_SECRET" \
  --from-literal=GITHUB_APP_ID="$GITHUB_APP_ID" \
  --from-file=GITHUB_PRIVATE_KEY="$GITHUB_PRIVATE_KEY_FILE" \
  --from-literal=OPENAI_API_KEY="${OPENAI_API_KEY:-}" \
  --dry-run=client -o yaml | kubectl apply -f -

INGRESS_ARGS=()
if [ "$INGRESS_ENABLED" = "true" ]; then
  if [ -z "$INGRESS_HOST" ]; then
    echo "INGRESS_HOST is required when INGRESS_ENABLED=true" >&2
    exit 1
  fi
  INGRESS_ARGS=(
    --set ingress.enabled=true
    --set-string ingress.className="$INGRESS_CLASS_NAME"
    --set-string ingress.host="$INGRESS_HOST"
  )
fi

helm upgrade --install "$RELEASE_NAME" "$CHART_PATH" \
  --namespace "$NAMESPACE" \
  --set-string image.repository="$IMAGE_REPOSITORY" \
  --set-string image.tag="$IMAGE_TAG" \
  --set-string existingSecret.name="$SECRET_NAME" \
  "${INGRESS_ARGS[@]}"

kubectl -n "$NAMESPACE" rollout status deploy/pr-review-agent-api --timeout=180s
kubectl -n "$NAMESPACE" rollout status deploy/pr-review-agent-worker --timeout=180s

echo
echo "Installed ${RELEASE_NAME} in namespace ${NAMESPACE}"
echo "Image: ${IMAGE_REPOSITORY}:${IMAGE_TAG}"
if [ "$INGRESS_ENABLED" = "true" ]; then
  echo "Webhook URL: https://${INGRESS_HOST}/api/github/webhook"
else
  echo "Local health check:"
  echo "kubectl -n ${NAMESPACE} port-forward svc/pr-review-agent-api 8000:80"
  echo "curl http://localhost:8000/healthz"
fi
