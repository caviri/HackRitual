"""Repository discovery + commit fetching.

GitHub-only for v1 (other hosts follow the same pattern). All requests go
to the public REST API. An optional `GITHUB_TOKEN` env var bumps the rate
limit from 60/hr to 5000/hr — no per-user OAuth needed because we only
read public repos.

The fetcher is *defensive* — any network or parsing failure is recorded
on the Repository's `polling_error` field, never raised up to the caller.
The UI shows the recorded error inline so the user can see what went wrong.
"""

from __future__ import annotations

import os
import re
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlparse

import httpx
from sqlalchemy.orm import Session

from app.models.repository import RepoCommit, Repository


GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("HACKRITUAL_GITHUB_TOKEN")
DEFAULT_TTL = timedelta(minutes=5)
MAX_COMMITS_PER_BRANCH = 8
MAX_BRANCHES_SCANNED = 4  # default branch + 3 most-recently-active


_GITHUB_PATTERN = re.compile(
    r"^(?:https?://)?(?:www\.)?github\.com/([^/\s]+)/([^/\s?#]+?)(?:\.git)?/?(?:[?#].*)?$"
)


def parse_url(url: str) -> tuple[str, str, str] | None:
    """Return (host, owner, repo) for a known host URL, or None if unrecognised."""
    cleaned = url.strip()
    m = _GITHUB_PATTERN.match(cleaned)
    if m:
        return "github", m.group(1), m.group(2)
    # Future: gitlab, bitbucket, codeberg
    return None


def normalize_url(host: str, owner: str, repo: str) -> str:
    if host == "github":
        return f"https://github.com/{owner}/{repo}"
    return f"https://{host}.com/{owner}/{repo}"


def _gh_headers() -> dict[str, str]:
    h = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "HackRitual/0.1.0",
    }
    if GITHUB_TOKEN:
        h["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return h


def _parse_dt(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        # GitHub returns "2026-05-14T08:23:11Z" — naive UTC after stripping tz
        return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc).replace(tzinfo=None)
    except Exception:
        return None


async def _gh_get(client: httpx.AsyncClient, path: str, **params: Any) -> Any:
    # Follow redirects so renamed repos (301) still resolve.
    resp = await client.get(
        f"https://api.github.com{path}",
        headers=_gh_headers(),
        params={k: v for k, v in params.items() if v is not None},
        timeout=15,
        follow_redirects=True,
    )
    if resp.status_code == 404:
        raise RuntimeError(f"github: not found · {path}")
    if resp.status_code == 403 and "rate limit" in resp.text.lower():
        raise RuntimeError("github: rate limit exceeded — set GITHUB_TOKEN to lift")
    if resp.status_code >= 400:
        raise RuntimeError(f"github {resp.status_code}: {resp.text[:200]}")
    return resp.json()


async def fetch_github(repo: Repository, db: Session) -> None:
    """Refresh a Repository's cached metadata + commits.

    Idempotent. On failure, sets `polling_error` and bumps `last_polled_at`
    so we don't hammer the host. Never raises.
    """
    try:
        async with httpx.AsyncClient() as client:
            meta = await _gh_get(client, f"/repos/{repo.owner}/{repo.repo}")
            repo.default_branch = meta.get("default_branch")
            repo.description = meta.get("description")
            repo.stars = meta.get("stargazers_count")
            repo.last_pushed_at = _parse_dt(meta.get("pushed_at"))

            # Determine which branches to scan
            branches = await _gh_get(
                client,
                f"/repos/{repo.owner}/{repo.repo}/branches",
                per_page=20,
            )
            branch_names: list[str] = [b["name"] for b in branches if isinstance(b, dict)]
            # Always include the default first, then pick up to 3 others (alphabetical
            # — branches listing isn't ordered by activity, so we keep it deterministic).
            default = repo.default_branch
            scan_order: list[str] = []
            if default and default in branch_names:
                scan_order.append(default)
            for b in branch_names:
                if b == default:
                    continue
                if len(scan_order) >= MAX_BRANCHES_SCANNED:
                    break
                scan_order.append(b)
            if not scan_order and branch_names:
                scan_order = branch_names[:1]

            # Replace cached commits with the freshly-fetched set.
            db.query(RepoCommit).filter(RepoCommit.repository_id == repo.id).delete()
            seen_sha: set[str] = set()
            for branch_name in scan_order:
                try:
                    commits = await _gh_get(
                        client,
                        f"/repos/{repo.owner}/{repo.repo}/commits",
                        sha=branch_name,
                        per_page=MAX_COMMITS_PER_BRANCH,
                    )
                except RuntimeError:
                    continue
                if not isinstance(commits, list):
                    continue
                for c in commits:
                    sha = c.get("sha")
                    if not sha or sha in seen_sha:
                        continue
                    seen_sha.add(sha)
                    commit_obj = c.get("commit") or {}
                    author_obj = commit_obj.get("author") or {}
                    gh_author = c.get("author") or {}
                    db.add(
                        RepoCommit(
                            repository_id=repo.id,
                            sha=sha,
                            branch=branch_name,
                            message=(commit_obj.get("message") or "").strip(),
                            author_name=(author_obj.get("name") or "(unknown)"),
                            author_login=gh_author.get("login"),
                            author_avatar_url=gh_author.get("avatar_url"),
                            author_profile_url=gh_author.get("html_url"),
                            committed_at=_parse_dt(author_obj.get("date")) or datetime.utcnow(),
                            fetched_at=datetime.utcnow(),
                        )
                    )
        repo.polling_error = None
    except RuntimeError as e:
        repo.polling_error = str(e)
    except httpx.HTTPError as e:
        repo.polling_error = f"network: {e}"
    except Exception as e:  # pragma: no cover — defensive
        repo.polling_error = f"unexpected: {e!r}"
    finally:
        repo.last_polled_at = datetime.utcnow()
        db.add(repo)
        db.commit()


async def refresh_if_stale(repo: Repository, db: Session, ttl: timedelta = DEFAULT_TTL) -> None:
    """Refresh if `last_polled_at` is older than TTL (or never polled)."""
    if repo.last_polled_at and datetime.utcnow() - repo.last_polled_at < ttl:
        return
    if repo.host == "github":
        await fetch_github(repo, db)
