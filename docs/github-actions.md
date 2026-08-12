# GitHub Actions Setup

This repository includes three workflows:

| Workflow | File | Purpose |
| --- | --- | --- |
| CI | `.github/workflows/ci.yml` | Runs Ruff, Pytest, `helm lint`, and `helm template` on PRs and pushes. |
| Docker publish | `.github/workflows/docker-publish.yml` | Builds and pushes `kmc173/github-pull-request-review-agent` to Docker Hub. |
| Kubernetes deploy | `.github/workflows/deploy-kubernetes.yml` | Manual Helm deployment to your Kubernetes server. |
| Versioned release | `.github/workflows/release-deploy.yml` | Manual one-button flow: validate version, test, build, push Docker image, then deploy that exact image tag with Helm. |

## Required GitHub repository secrets

Add these in GitHub:

`Settings` -> `Secrets and variables` -> `Actions` -> `New repository secret`

### Docker Hub

- `DOCKERHUB_USERNAME`: Docker Hub username, for example `kmc173`.
- `DOCKERHUB_TOKEN`: Docker Hub access token, not the account password.

### Kubernetes deployment

- `KUBE_CONFIG_BASE64`: base64-encoded kubeconfig for the target server.
- `DATABASE_URL`: PostgreSQL connection string.
- `REDIS_URL`: Redis connection string.
- `GITHUB_WEBHOOK_SECRET`: webhook secret configured in the GitHub App.
- `GITHUB_APP_ID`: GitHub App ID.
- `GITHUB_PRIVATE_KEY`: GitHub App private key PEM content.
- `OPENAI_API_KEY`: OpenAI API key. Leave empty only if you want static-analysis-only review.

Create `KUBE_CONFIG_BASE64` locally:

```bash
base64 -w 0 ~/.kube/config
```

On macOS, use:

```bash
base64 < ~/.kube/config | tr -d '\n'
```

## Publishing the Docker image

Use explicit version tags for real deployments. Recommended format:

```text
vMAJOR.MINOR.PATCH
```

Examples:

```text
v0.1.0
v0.2.0
v1.0.0
```

The Docker workflow publishes these tags:

- `latest` on the default branch.
- Branch name tags.
- Git tag names like `v0.1.0`.
- Commit SHA tags like `sha-abc1234`.
- Manual `image_tag` input, for example `v0.1.0`.

Manual publish:

1. Open GitHub repository `Actions`.
2. Select `Build and Publish Docker Image`.
3. Click `Run workflow`.
4. Enter `image_tag`, for example `v0.1.0`.

This workflow runs tests and Helm validation before pushing the image.

## Recommended full release flow

Use this when you want GitHub Actions to test, push the image to Docker Hub, and deploy to Kubernetes in one run.

1. Commit and push your code to `main`.
2. Open GitHub repository `Actions`.
3. Select `Versioned Build Test Push Deploy`.
4. Click `Run workflow`.
5. Enter:
   - `version`: `v0.1.0`
   - `namespace`: `pr-review-agent`
   - `deploy`: `true`
   - `ingress_host`: your domain, for example `pr-review.example.com`

The workflow order is:

```text
validate version -> ruff/test/helm checks -> docker build -> docker push -> helm deploy -> rollout verify
```

For version `v0.1.0`, the pushed image will be:

```text
kmc173/github-pull-request-review-agent:v0.1.0
```

The workflow also pushes a commit-specific tag:

```text
kmc173/github-pull-request-review-agent:sha-COMMIT_SHA
```

## Deploying from GitHub Actions

1. Open `Actions`.
2. Select `Deploy to Kubernetes`.
3. Click `Run workflow`.
4. Enter:
   - `namespace`: for example `pr-review-agent`.
   - `image_tag`: for example `v0.1.0` or `sha-abc1234`.
   - `ingress_host`: your public domain, for example `pr-review.example.com`.

The webhook URL will be:

```text
https://YOUR_INGRESS_HOST/api/github/webhook
```

## Exact first-time setup checklist

1. Push this project to:

```bash
git remote add origin https://github.com/kmc-1234/GitHub-Pull-Request-Review-Agent-.git
git branch -M main
git add .
git commit -m "Add PR review agent CI/CD and Helm deployment"
git push -u origin main
```

2. Add Docker Hub secrets:

```text
DOCKERHUB_USERNAME=kmc173
DOCKERHUB_TOKEN=your Docker Hub access token
```

3. Add Kubernetes and app secrets:

```text
KUBE_CONFIG_BASE64=base64 encoded kubeconfig
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/review
REDIS_URL=redis://HOST:6379/0
GITHUB_WEBHOOK_SECRET=your webhook secret
GITHUB_APP_ID=your GitHub App ID
GITHUB_PRIVATE_KEY=full private key PEM
OPENAI_API_KEY=your OpenAI API key
```

4. Run `Versioned Build Test Push Deploy` with:

```text
version=v0.1.0
namespace=pr-review-agent
deploy=true
ingress_host=pr-review.example.com
```

5. After rollout succeeds, configure the GitHub App webhook:

```text
https://pr-review.example.com/api/github/webhook
```

Use the same secret as `GITHUB_WEBHOOK_SECRET`.
