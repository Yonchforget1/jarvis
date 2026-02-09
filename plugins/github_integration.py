"""Plugin: GitHub integration

Tools for interacting with GitHub repositories: list repos, issues,
pull requests, and create issues/PRs.

Requires: GITHUB_TOKEN env var with appropriate scopes.
"""

import json
import os

import httpx

from jarvis.tool_registry import ToolDef

GITHUB_API = "https://api.github.com"
TIMEOUT = 15


def _headers() -> dict:
    token = os.getenv("GITHUB_TOKEN", "")
    if not token:
        return {}
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _get(endpoint: str) -> dict | list | str:
    headers = _headers()
    if not headers:
        return "Error: GITHUB_TOKEN not set in environment."
    try:
        resp = httpx.get(f"{GITHUB_API}{endpoint}", headers=headers, timeout=TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return f"GitHub API error: {e}"


def _post(endpoint: str, data: dict) -> dict | str:
    headers = _headers()
    if not headers:
        return "Error: GITHUB_TOKEN not set in environment."
    try:
        resp = httpx.post(f"{GITHUB_API}{endpoint}", headers=headers, json=data, timeout=TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return f"GitHub API error: {e}"


def github_list_repos(owner: str = "", per_page: int = 10) -> str:
    """List repositories for a user/org or the authenticated user."""
    endpoint = f"/users/{owner}/repos?per_page={per_page}&sort=updated" if owner else f"/user/repos?per_page={per_page}&sort=updated"
    result = _get(endpoint)
    if isinstance(result, str):
        return result
    lines = []
    for repo in result:
        stars = repo.get("stargazers_count", 0)
        desc = repo.get("description", "") or ""
        lines.append(f"  {repo['full_name']} ({stars} stars) - {desc[:80]}")
    return f"Repositories ({len(result)}):\n" + "\n".join(lines)


def github_list_issues(repo: str, state: str = "open", per_page: int = 10) -> str:
    """List issues for a repository."""
    result = _get(f"/repos/{repo}/issues?state={state}&per_page={per_page}")
    if isinstance(result, str):
        return result
    lines = []
    for issue in result:
        if issue.get("pull_request"):
            continue  # Skip PRs
        labels = ", ".join(l["name"] for l in issue.get("labels", []))
        lines.append(f"  #{issue['number']} {issue['title']} [{labels}]")
    return f"Issues for {repo} ({state}):\n" + "\n".join(lines) if lines else f"No {state} issues for {repo}."


def github_create_issue(repo: str, title: str, body: str = "", labels: str = "") -> str:
    """Create an issue in a repository."""
    data = {"title": title, "body": body}
    if labels:
        data["labels"] = [l.strip() for l in labels.split(",")]
    result = _post(f"/repos/{repo}/issues", data)
    if isinstance(result, str):
        return result
    return f"Issue created: #{result['number']} - {result['html_url']}"


def github_list_prs(repo: str, state: str = "open", per_page: int = 10) -> str:
    """List pull requests for a repository."""
    result = _get(f"/repos/{repo}/pulls?state={state}&per_page={per_page}")
    if isinstance(result, str):
        return result
    lines = []
    for pr in result:
        lines.append(f"  #{pr['number']} {pr['title']} ({pr['user']['login']}) - {pr['state']}")
    return f"Pull requests for {repo} ({state}):\n" + "\n".join(lines) if lines else f"No {state} PRs for {repo}."


def register(registry) -> None:
    registry.register(ToolDef(
        name="github_list_repos",
        description="List GitHub repositories for a user/org or the authenticated user.",
        parameters={
            "properties": {
                "owner": {"type": "string", "description": "GitHub username or org. Empty for authenticated user.", "default": ""},
                "per_page": {"type": "integer", "description": "Number of repos to return.", "default": 10},
            },
            "required": [],
        },
        func=github_list_repos,
        category="integration",
    ))
    registry.register(ToolDef(
        name="github_list_issues",
        description="List issues for a GitHub repository.",
        parameters={
            "properties": {
                "repo": {"type": "string", "description": "Repository in owner/repo format."},
                "state": {"type": "string", "description": "Issue state: open, closed, all.", "default": "open"},
                "per_page": {"type": "integer", "description": "Number of issues to return.", "default": 10},
            },
            "required": ["repo"],
        },
        func=github_list_issues,
        category="integration",
    ))
    registry.register(ToolDef(
        name="github_create_issue",
        description="Create a new issue in a GitHub repository.",
        parameters={
            "properties": {
                "repo": {"type": "string", "description": "Repository in owner/repo format."},
                "title": {"type": "string", "description": "Issue title."},
                "body": {"type": "string", "description": "Issue body (markdown).", "default": ""},
                "labels": {"type": "string", "description": "Comma-separated label names.", "default": ""},
            },
            "required": ["repo", "title"],
        },
        func=github_create_issue,
        category="integration",
    ))
    registry.register(ToolDef(
        name="github_list_prs",
        description="List pull requests for a GitHub repository.",
        parameters={
            "properties": {
                "repo": {"type": "string", "description": "Repository in owner/repo format."},
                "state": {"type": "string", "description": "PR state: open, closed, all.", "default": "open"},
                "per_page": {"type": "integer", "description": "Number of PRs to return.", "default": 10},
            },
            "required": ["repo"],
        },
        func=github_list_prs,
        category="integration",
    ))
