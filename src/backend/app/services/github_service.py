"""
GitHub export — push the archive to a repo via the Git Data API (Step 17).

The Git Data API (blobs → tree → commit → ref) gives an atomic multi-file commit,
unlike the Contents API. Async via `httpx`. The client is injectable so the
orchestration can be tested against a mock transport without touching GitHub.
"""

from __future__ import annotations

import base64
from typing import Optional

import httpx

GITHUB_API = "https://api.github.com"


def pages_url(repo: str) -> str:
    """The GitHub Pages URL for ``org/name`` → ``https://org.github.io/name/``."""
    if "/" not in repo:
        return ""
    owner, name = repo.split("/", 1)
    return f"https://{owner}.github.io/{name}/"


def validate_no_secrets(files: dict[str, bytes], secrets: list[str]) -> list[str]:
    """Scan file contents for any configured secret. Returns violation messages."""
    live = [s for s in secrets if s]
    violations: list[str] = []
    for name, content in files.items():
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            continue
        for secret in live:
            if secret in text:
                violations.append(f"secret leaked in {name}")
                break
    return violations


def _headers(token: str) -> dict:
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


async def check_access(
    repo: str, token: str, client: Optional[httpx.AsyncClient] = None
) -> bool:
    """True if the token can write to the repo."""
    own = client is None
    client = client or httpx.AsyncClient(
        base_url=GITHUB_API, headers=_headers(token), timeout=30
    )
    try:
        r = await client.get(f"/repos/{repo}")
        if r.status_code != 200:
            return False
        perms = r.json().get("permissions", {})
        return bool(perms.get("push"))
    finally:
        if own:
            await client.aclose()


async def push_export(
    files: dict[str, bytes],
    repo: str,
    token: str,
    branch: str = "gh-pages",
    commit_message: str = "Export HackRitual archive",
    client: Optional[httpx.AsyncClient] = None,
) -> dict:
    """
    Commit ``files`` to ``repo``@``branch`` as a single tree.

    Creates the branch from the default branch if it doesn't exist yet. Returns
    ``{commit_sha, commit_url, pages_url}``. Raises ``httpx.HTTPStatusError`` on
    any API failure.
    """
    own = client is None
    client = client or httpx.AsyncClient(
        base_url=GITHUB_API, headers=_headers(token), timeout=30
    )
    try:
        # 1. Base commit SHA — from the target branch, or the default branch.
        create_ref = False
        ref = await client.get(f"/repos/{repo}/git/ref/heads/{branch}")
        if ref.status_code == 200:
            base_sha = ref.json()["object"]["sha"]
        elif ref.status_code == 404:
            info = await client.get(f"/repos/{repo}")
            info.raise_for_status()
            default = info.json()["default_branch"]
            dref = await client.get(f"/repos/{repo}/git/ref/heads/{default}")
            dref.raise_for_status()
            base_sha = dref.json()["object"]["sha"]
            create_ref = True
        else:
            ref.raise_for_status()
            base_sha = ref.json()["object"]["sha"]

        base_commit = await client.get(f"/repos/{repo}/git/commits/{base_sha}")
        base_commit.raise_for_status()
        base_tree = base_commit.json()["tree"]["sha"]

        # 2. Blob per file (sorted for deterministic trees).
        tree_entries = []
        for path in sorted(files):
            blob = await client.post(
                f"/repos/{repo}/git/blobs",
                json={
                    "content": base64.b64encode(files[path]).decode("ascii"),
                    "encoding": "base64",
                },
            )
            blob.raise_for_status()
            tree_entries.append(
                {"path": path, "mode": "100644", "type": "blob", "sha": blob.json()["sha"]}
            )

        # 3. Tree.
        tree = await client.post(
            f"/repos/{repo}/git/trees",
            json={"base_tree": base_tree, "tree": tree_entries},
        )
        tree.raise_for_status()
        tree_sha = tree.json()["sha"]

        # 4. Commit.
        commit = await client.post(
            f"/repos/{repo}/git/commits",
            json={"message": commit_message, "tree": tree_sha, "parents": [base_sha]},
        )
        commit.raise_for_status()
        commit_sha = commit.json()["sha"]

        # 5. Move (or create) the branch ref.
        if create_ref:
            upd = await client.post(
                f"/repos/{repo}/git/refs",
                json={"ref": f"refs/heads/{branch}", "sha": commit_sha},
            )
        else:
            upd = await client.patch(
                f"/repos/{repo}/git/refs/heads/{branch}",
                json={"sha": commit_sha, "force": True},
            )
        upd.raise_for_status()

        return {
            "commit_sha": commit_sha,
            "commit_url": f"https://github.com/{repo}/commit/{commit_sha}",
            "pages_url": pages_url(repo),
        }
    finally:
        if own:
            await client.aclose()
