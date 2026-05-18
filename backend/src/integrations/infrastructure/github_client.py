"""GitHub REST + GraphQL client (httpx)."""
from __future__ import annotations

from typing import Any

import httpx
import structlog

logger = structlog.get_logger(__name__)

GITHUB_API = "https://api.github.com"
GITHUB_GRAPHQL = "https://api.github.com/graphql"


class GithubClient:
    def __init__(self, access_token: str) -> None:
        self._token = access_token
        self._headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "cvs-saas-integration/0.2",
        }

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.get(GITHUB_API + path, headers=self._headers, params=params)
            r.raise_for_status()
            return r.json()

    async def _graphql(self, query: str, variables: dict[str, Any] | None = None) -> Any:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(
                GITHUB_GRAPHQL,
                headers={**self._headers, "Content-Type": "application/json"},
                json={"query": query, "variables": variables or {}},
            )
            r.raise_for_status()
            data = r.json()
            if "errors" in data:
                raise RuntimeError(f"GraphQL error: {data['errors']}")
            return data["data"]

    async def get_authenticated_user(self) -> dict[str, Any]:
        return await self._get("/user")

    async def get_emails(self) -> list[dict[str, Any]]:
        return await self._get("/user/emails")

    async def list_orgs(self) -> list[dict[str, Any]]:
        return await self._get("/user/orgs")

    async def list_repos(self, *, per_page: int = 100) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        page = 1
        while True:
            chunk = await self._get(
                "/user/repos",
                {"per_page": per_page, "page": page, "sort": "pushed", "affiliation": "owner,collaborator"},
            )
            if not chunk:
                break
            out.extend(chunk)
            if len(chunk) < per_page:
                break
            page += 1
            if page > 5:  # cap at 500 repos
                break
        return out

    async def get_repo_languages(self, owner: str, repo: str) -> dict[str, int]:
        return await self._get(f"/repos/{owner}/{repo}/languages")

    async def get_repo_readme(self, owner: str, repo: str) -> str | None:
        try:
            r = await self._get(f"/repos/{owner}/{repo}/readme")
        except httpx.HTTPStatusError:
            return None
        import base64

        if r.get("encoding") == "base64" and r.get("content"):
            try:
                return base64.b64decode(r["content"]).decode("utf-8", errors="ignore")
            except Exception:  # noqa: BLE001
                return None
        return None

    async def pinned_and_contributions(self, login: str) -> dict[str, Any]:
        query = """
        query($login: String!) {
          user(login: $login) {
            pinnedItems(first: 6, types: [REPOSITORY]) {
              nodes {
                ... on Repository {
                  name
                  description
                  stargazerCount
                  primaryLanguage { name }
                  url
                  pushedAt
                }
              }
            }
            contributionsCollection {
              totalContributions
              totalCommitContributions
              totalPullRequestContributions
              totalIssueContributions
              totalPullRequestReviewContributions
            }
          }
        }
        """
        return await self._graphql(query, {"login": login})


async def exchange_code_for_token(
    *,
    client_id: str,
    client_secret: str,
    code: str,
    redirect_uri: str,
) -> dict[str, Any]:
    """Exchange OAuth authorization code for access token."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(
            "https://github.com/login/oauth/access_token",
            headers={"Accept": "application/json"},
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
                "redirect_uri": redirect_uri,
            },
        )
        r.raise_for_status()
        return r.json()
