from typing import Any

import httpx

from app.core.config import Settings
from app.github.auth import build_app_jwt


class GitHubClient:
    def __init__(self, token: str, api_url: str = "https://api.github.com") -> None:
        self.api_url = api_url.rstrip("/")
        self.client = httpx.Client(
            base_url=self.api_url,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {token}",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=30,
        )

    @classmethod
    def for_installation(cls, installation_id: int, settings: Settings) -> "GitHubClient":
        app_token = build_app_jwt(settings)
        response = httpx.post(
            f"{settings.github_api_url.rstrip('/')}/app/installations/{installation_id}/access_tokens",
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {app_token}",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=30,
        )
        response.raise_for_status()
        return cls(response.json()["token"], settings.github_api_url)

    def get_pull_request(self, repo: str, number: int) -> dict[str, Any]:
        response = self.client.get(f"/repos/{repo}/pulls/{number}")
        response.raise_for_status()
        return response.json()

    def list_pull_request_files(self, repo: str, number: int) -> list[dict[str, Any]]:
        files: list[dict[str, Any]] = []
        page = 1
        while True:
            response = self.client.get(
                f"/repos/{repo}/pulls/{number}/files",
                params={"page": page, "per_page": 100},
            )
            response.raise_for_status()
            batch = response.json()
            files.extend(batch)
            if len(batch) < 100:
                return files
            page += 1

    def create_review(
        self,
        repo: str,
        number: int,
        commit_id: str,
        body: str,
        event: str,
        comments: list[dict[str, Any]],
    ) -> dict[str, Any]:
        response = self.client.post(
            f"/repos/{repo}/pulls/{number}/reviews",
            json={"commit_id": commit_id, "body": body, "event": event, "comments": comments},
        )
        response.raise_for_status()
        return response.json()

    def list_review_comments(self, repo: str, number: int) -> list[dict[str, Any]]:
        comments: list[dict[str, Any]] = []
        page = 1
        while True:
            response = self.client.get(
                f"/repos/{repo}/pulls/{number}/comments", params={"page": page, "per_page": 100}
            )
            response.raise_for_status()
            batch = response.json()
            comments.extend(batch)
            if len(batch) < 100:
                return comments
            page += 1
