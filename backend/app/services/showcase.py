"""Showcase digest — the public-safe view of a completed ritual.

Returns a single self-contained dict. Designed to be:

  - Plonked into a static website
  - Streamed into a fresh DB (e.g. for analytics later)
  - Read by humans (every field is named, no opaque IDs floating)

Contrast with the full export.zip bundle:
  - Bundle:    SQLite snapshot + every upload + raw audit log
  - Showcase:  digest, no emails, no IPs, no admin metadata
"""

from __future__ import annotations

import base64
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.config import settings
from app.models.event import Event
from app.models.page import Page
from app.models.participant import Participant
from app.models.participant_member import ParticipantMember
from app.models.phase import Phase
from app.models.project import Project
from app.models.repository import RepoCommit, Repository
from app.models.score import Score
from app.models.submission import Submission
from app.models.track import Track
from app.models.user import User


# Cap an individual portrait at ~30 KB so a malicious upload can't bloat the
# showcase. Dithered PNGs are typically 2–8 KB, so this is generous.
_PORTRAIT_MAX_BYTES = 30 * 1024


def _iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt else None


def _portrait_data_uri_for_participant(
    participant: Participant,
    db: Session,
) -> str | None:
    """Resolve participant → user → portrait_path → base64 data URI.

    Only humans currently have portraits. Agents have api keys; teams have
    multiple members — picking one as the team's "face" is a v2 decision.
    """
    if participant.type != "human":
        return None
    member = (
        db.query(ParticipantMember)
        .filter(ParticipantMember.participant_id == participant.id)
        .filter(ParticipantMember.user_id.isnot(None))
        .first()
    )
    if not member or not member.user_id:
        return None
    user = db.get(User, member.user_id)
    if not user or not user.portrait_path:
        return None
    path = Path(settings.upload_dir) / user.portrait_path
    if not path.exists():
        return None
    try:
        data = path.read_bytes()
    except OSError:
        return None
    if len(data) > _PORTRAIT_MAX_BYTES:
        return None
    return f"data:image/png;base64,{base64.b64encode(data).decode('ascii')}"


def _score_to_dict(s: Score) -> dict[str, Any]:
    breakdown: dict[str, float] = {}
    notes = None
    if s.breakdown_json:
        try:
            loaded = json.loads(s.breakdown_json)
            if isinstance(loaded, dict):
                breakdown = {
                    k: float(v)
                    for k, v in loaded.items()
                    if k != "_notes" and isinstance(v, (int, float))
                }
                notes = loaded.get("_notes")
        except Exception:
            pass
    return {
        "value": float(s.score_value) if s.score_value is not None else None,
        "breakdown": breakdown,
        "notes": notes,
        "scored_at": _iso(s.scored_at),
    }


def build_showcase(db: Session) -> dict[str, Any]:
    """Build the public-safe digest. Safe to call in any event state — the
    result reflects whatever's currently in the database; in DRAFT it's mostly
    empty, in FINAL/ARCHIVED it's complete."""
    event = db.get(Event, settings.event_id) or db.query(Event).first()

    # ── tracks ──
    track_rows = db.query(Track).order_by(Track.created_at).all()
    track_by_id = {t.id: t for t in track_rows}
    tracks = [
        {
            "id": t.id,
            "name": t.name,
            "description": t.description,
        }
        for t in track_rows
    ]

    # ── phases ──
    phase_rows = (
        db.query(Phase)
        .order_by(Phase.starts_at.asc().nullslast(), Phase.created_at)
        .all()
    )
    phases = [
        {
            "name": p.name,
            "description": p.description,
            "starts_at": _iso(p.starts_at),
            "ends_at": _iso(p.ends_at),
        }
        for p in phase_rows
    ]

    # ── content pages (only visible ones) ──
    page_rows = (
        db.query(Page)
        .filter(Page.visible.is_(True))
        .order_by(Page.order, Page.created_at)
        .all()
    )
    pages = [
        {"title": p.title, "content": p.content, "order": p.order} for p in page_rows
    ]

    # ── participants (no waitlisted, no inactive; display_name only) ──
    participant_rows = (
        db.query(Participant)
        .filter(
            Participant.is_waiting.is_(False),
            Participant.status == "active",
        )
        .order_by(Participant.created_at)
        .all()
    )
    part_by_id = {p.id: p for p in participant_rows}
    participants = [
        {
            "id": p.id,
            "display_name": p.display_name,
            "type": p.type,
            "affiliation": p.affiliation,
            # base64 data URI of the dithered PNG, or None if no portrait
            # uploaded. ~2–8 KB per portrait in practice.
            "portrait": _portrait_data_uri_for_participant(p, db),
        }
        for p in participant_rows
    ]

    # ── projects (approved + final/archived states; rejected excluded) ──
    project_rows = (
        db.query(Project)
        .filter(Project.status != "rejected")
        .order_by(Project.created_at)
        .all()
    )

    # Latest scored submission per project → score for the headline
    project_score: dict[str, dict[str, Any] | None] = {}
    for proj in project_rows:
        latest_final = (
            db.query(Submission)
            .filter(Submission.project_id == proj.id, Submission.status == "final")
            .order_by(Submission.version.desc())
            .first()
        )
        if latest_final is None:
            project_score[proj.id] = None
            continue
        sc = (
            db.query(Score)
            .filter(Score.submission_id == latest_final.id)
            .order_by(Score.scored_at.desc().nullslast())
            .first()
        )
        project_score[proj.id] = _score_to_dict(sc) if sc else None

    # Repos + recent commits per project
    repo_rows = db.query(Repository).all()
    repos_by_project: dict[str, list[dict[str, Any]]] = {}
    for r in repo_rows:
        commits = (
            db.query(RepoCommit)
            .filter(RepoCommit.repository_id == r.id)
            .order_by(RepoCommit.committed_at.desc())
            .limit(20)
            .all()
        )
        repos_by_project.setdefault(r.project_id, []).append(
            {
                "url": r.url,
                "host": r.host,
                "owner": r.owner,
                "repo": r.repo,
                "default_branch": r.default_branch,
                "description": r.description,
                "stars": r.stars,
                "last_pushed_at": _iso(r.last_pushed_at),
                "commits": [
                    {
                        "sha": c.sha[:12],
                        "branch": c.branch,
                        "message": (c.message or "").split("\n", 1)[0][:160],
                        "author_name": c.author_name,
                        "author_login": c.author_login,
                        "author_profile_url": c.author_profile_url,
                        "committed_at": _iso(c.committed_at),
                    }
                    for c in commits
                ],
            }
        )

    # Submissions per project (final only, in the showcase view)
    subs_by_project: dict[str, list[dict[str, Any]]] = {}
    for s in (
        db.query(Submission)
        .filter(Submission.status == "final")
        .order_by(Submission.version)
        .all()
    ):
        subs_by_project.setdefault(s.project_id, []).append(
            {
                "version": s.version,
                "title": s.title,
                "result": s.result,
                "modified_at": _iso(s.modified_at),
                "team": part_by_id[s.participant_id].display_name
                if s.participant_id in part_by_id
                else None,
            }
        )

    projects = []
    for proj in project_rows:
        proposer = part_by_id.get(proj.proposed_by_participant_id)
        track = track_by_id.get(proj.track_id) if proj.track_id else None
        projects.append(
            {
                "id": proj.id,
                "title": proj.title,
                "description": proj.description,
                "status": proj.status,
                "track": track.name if track else None,
                "proposer": proposer.display_name if proposer else None,
                "proposer_type": proposer.type if proposer else None,
                "score": project_score.get(proj.id),
                "submissions": subs_by_project.get(proj.id, []),
                "repos": repos_by_project.get(proj.id, []),
            }
        )

    # ── ranked winners — top 3 by headline score ──
    scored = [p for p in projects if p["score"] and p["score"].get("value") is not None]
    scored.sort(key=lambda p: p["score"]["value"], reverse=True)
    winners = scored[:3]

    return {
        "schema": "hackritual.showcase.v1",
        "exported_at": datetime.utcnow().isoformat() + "Z",
        "event": {
            "id": event.id if event else settings.event_id,
            "title": event.title if event else settings.event_title,
            "type": event.type if event else "hackathon",
            "state": event.state if event else "UNKNOWN",
            "start_at": _iso(event.start_at) if event else None,
            "end_at": _iso(event.end_at) if event else None,
        },
        "stats": {
            "participants": len(participants),
            "humans": sum(1 for p in participants if p["type"] == "human"),
            "agents": sum(1 for p in participants if p["type"] == "agent"),
            "teams": sum(1 for p in participants if p["type"] == "team"),
            "projects": len(projects),
            "approved": sum(1 for p in projects if p["status"] == "approved"),
            "final_submissions": sum(
                len(p["submissions"]) for p in projects
            ),
            "linked_repos": sum(len(rs) for rs in repos_by_project.values()),
            "portraits": sum(1 for p in participants if p.get("portrait")),
        },
        "tracks": tracks,
        "phases": phases,
        "pages": pages,
        "winners": winners,
        "projects": projects,
        "participants": participants,
    }
