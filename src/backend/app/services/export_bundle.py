"""
Structured JSON export — the artefact the ritual leaves behind.

A self-contained, versioned ZIP of structured JSON files, suitable for long-term
storage or publishing. Distinct from `export.py` (a full SQLite backup): this
bundle is curated, redacted, and deterministic — sorted by id so the same input
yields the same bytes (only the timestamp differs).

Privacy is governed by `RedactionConfig`. In `public` mode emails are reduced to
a stable, irreversible hash (`sha256(email + event_id)[:16]`) and audit actors
are likewise anonymised. Secrets never enter the bundle — we read only the
curated models below, never config, API-key hashes, sessions, login codes, or
the task queue.
"""

from __future__ import annotations

import hashlib
import io
import json
import zipfile
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.config import settings
from app.models.agent import Agent
from app.models.audit_log import AuditLog
from app.models.event import Event
from app.models.file import File
from app.models.participant import Participant
from app.models.participant_member import ParticipantMember
from app.models.score import Score
from app.models.submission import Submission
from app.models.user import User
from app.scoring import DefaultScorer
from app.services.event import load_config

SCHEMA_VERSION = "1.0.0"


@dataclass
class RedactionConfig:
    """How much of the private layer the export reveals."""

    mode: str = "public"        # public | private | full
    include_audit: bool = True
    include_assets: bool = False

    @property
    def hash_emails(self) -> bool:
        return self.mode == "public"


def email_hash(email: str, event_id: str) -> str:
    """Stable within an event, irreversible. `sha256(email + event_id)[:16]`."""
    return hashlib.sha256(f"{email}{event_id}".encode("utf-8")).hexdigest()[:16]


def _iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() if dt else None


def _participant_email(db: Session, participant_id: str) -> Optional[str]:
    """The email of a participant's first human member, if any."""
    member = (
        db.query(ParticipantMember)
        .filter(
            ParticipantMember.participant_id == participant_id,
            ParticipantMember.user_id.isnot(None),
        )
        .order_by(ParticipantMember.id)
        .first()
    )
    if member is None or member.user_id is None:
        return None
    user = db.get(User, member.user_id)
    return user.email if user else None


# --------------------------------------------------------------------------- #
# Per-entity exporters (each returns a list sorted by id for determinism)
# --------------------------------------------------------------------------- #
def export_participants(db: Session, redaction: RedactionConfig) -> list[dict]:
    rows = (
        db.query(Participant)
        .filter(Participant.event_id == settings.event_id)
        .order_by(Participant.id)
        .all()
    )
    out: list[dict] = []
    for p in rows:
        email = _participant_email(db, p.id)
        record = {
            "id": p.id,
            "type": p.type,
            "display_name": p.display_name,
            "affiliation": p.affiliation,
            "status": p.status,
            "created_at": _iso(p.created_at),
        }
        if email:
            if redaction.hash_emails:
                record["email_hash"] = email_hash(email, settings.event_id)
            else:
                record["email"] = email
        out.append(record)
    return out


def export_teams(db: Session) -> list[dict]:
    teams = (
        db.query(Participant)
        .filter(
            Participant.event_id == settings.event_id,
            Participant.type == "team",
        )
        .order_by(Participant.id)
        .all()
    )
    out: list[dict] = []
    for team in teams:
        members = (
            db.query(ParticipantMember)
            .filter(ParticipantMember.participant_id == team.id)
            .order_by(ParticipantMember.id)
            .all()
        )
        out.append(
            {
                "id": team.id,
                "display_name": team.display_name,
                "members": [
                    {
                        "user_id": m.user_id,
                        "agent_id": m.agent_id,
                        "role_in_team": m.role_in_team,
                    }
                    for m in members
                ],
            }
        )
    return out


def export_agents(db: Session) -> list[dict]:
    # api_key_hash is deliberately excluded — never export credentials.
    rows = db.query(Agent).order_by(Agent.id).all()
    return [
        {
            "id": a.id,
            "name": a.name,
            "owner_user_id": a.owner_user_id,
            "status": a.status,
            "created_at": _iso(a.created_at),
        }
        for a in rows
    ]


def export_submissions(db: Session) -> list[dict]:
    rows = (
        db.query(Submission)
        .filter(Submission.event_id == settings.event_id)
        .order_by(Submission.id)
        .all()
    )
    out: list[dict] = []
    for s in rows:
        files = (
            db.query(File)
            .filter(File.submission_id == s.id)
            .order_by(File.id)
            .all()
        )
        payload = None
        if s.payload_json:
            try:
                payload = json.loads(s.payload_json)
            except (ValueError, TypeError):
                payload = None
        out.append(
            {
                "id": s.id,
                "participant_id": s.participant_id,
                "project_id": s.project_id,
                "version": s.version,
                "title": s.title,
                "description": s.description,
                "result": s.result,
                "payload": payload,
                "status": s.status,
                "files": [
                    {
                        "filename": f.path.rsplit("/", 1)[-1],
                        "path": f.path,
                        "mime_type": f.mime_type,
                        "size_bytes": f.size_bytes,
                        "sha256": f.sha256,
                    }
                    for f in files
                ],
                "created_at": _iso(s.created_at),
            }
        )
    return out


def export_scores(db: Session) -> list[dict]:
    rows = (
        db.query(Score)
        .join(Submission, Submission.id == Score.submission_id)
        .filter(Submission.event_id == settings.event_id)
        .order_by(Score.id)
        .all()
    )
    out: list[dict] = []
    for s in rows:
        breakdown = None
        if s.breakdown_json:
            try:
                breakdown = json.loads(s.breakdown_json)
            except (ValueError, TypeError):
                breakdown = None
        submission = db.get(Submission, s.submission_id)
        out.append(
            {
                "id": s.id,
                "submission_id": s.submission_id,
                "participant_id": submission.participant_id if submission else None,
                "score_value": s.score_value,
                "breakdown": breakdown,
                "status": s.status,
                "scorer_version": s.scorer_version,
                "scored_at": _iso(s.scored_at),
            }
        )
    return out


def export_audit_log(db: Session, redaction: RedactionConfig) -> list[dict]:
    rows = db.query(AuditLog).order_by(AuditLog.id).all()
    out: list[dict] = []
    for r in rows:
        actor = r.actor_user_id
        if actor and redaction.hash_emails:
            actor = email_hash(actor, settings.event_id)
        metadata = None
        if r.metadata_json:
            try:
                metadata = json.loads(r.metadata_json)
            except (ValueError, TypeError):
                metadata = None
        out.append(
            {
                "id": r.id,
                "actor": actor,
                "action": r.action,
                "target_type": r.target_type,
                "target_id": r.target_id,
                "metadata": metadata,
                "created_at": _iso(r.created_at),
            }
        )
    return out


def export_statistics(db: Session) -> dict:
    participants = (
        db.query(Participant)
        .filter(Participant.event_id == settings.event_id)
        .all()
    )
    by_type: dict[str, int] = {}
    for p in participants:
        by_type[p.type] = by_type.get(p.type, 0) + 1

    submissions = (
        db.query(Submission)
        .filter(Submission.event_id == settings.event_id)
        .all()
    )
    by_status: dict[str, int] = {}
    for s in submissions:
        by_status[s.status] = by_status.get(s.status, 0) + 1

    scored = (
        db.query(Score)
        .join(Submission, Submission.id == Score.submission_id)
        .filter(Submission.event_id == settings.event_id, Score.status == "scored")
        .all()
    )
    values = [s.score_value for s in scored]
    return {
        "participants_total": len(participants),
        "participants_by_type": by_type,
        "submissions_total": len(submissions),
        "submissions_by_status": by_status,
        "scores_total": len(scored),
        "average_score": round(sum(values) / len(values), 2) if values else None,
        "highest_score": max(values) if values else None,
    }


def _scoring_block(db: Session) -> dict:
    """Describe the active scorer for the manifest (WASM module or Python default)."""
    config = load_config(db.get(Event, settings.event_id) or Event())
    scorer = config.get("scorer") if isinstance(config, dict) else None
    if scorer and scorer.get("type") == "wasm":
        return {
            "mode": "server_authoritative",
            "scorer_type": "wasm",
            "scorer_version": scorer.get("version"),
            "notes": "",
        }
    return {
        "mode": "server_authoritative",
        "scorer_type": "python",
        "scorer_version": DefaultScorer().version,
        "notes": "",
    }


def generate_manifest(
    db: Session, event: Event, redaction: RedactionConfig, counts: dict
) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "exported_at": datetime.utcnow().isoformat() + "Z",
        "exporter_version": settings.app_version,
        "event": {
            "id": event.id,
            "title": event.title,
            "type": event.type,
            "state": event.state,
            "start": _iso(event.start_at),
            "end": _iso(event.end_at),
        },
        "scoring": _scoring_block(db),
        "privacy": {
            "emails_exported": not redaction.hash_emails,
            "participant_ids_stable": True,
            "redaction_mode": redaction.mode,
        },
        "counts": counts,
    }


# --------------------------------------------------------------------------- #
# Bundle assembly
# --------------------------------------------------------------------------- #
def _collect(db: Session, redaction: RedactionConfig) -> dict[str, object]:
    """Build every JSON section (no zipping) — shared by preview and build."""
    participants = export_participants(db, redaction)
    teams = export_teams(db)
    agents = export_agents(db)
    submissions = export_submissions(db)
    scores = export_scores(db)
    sections: dict[str, object] = {
        "participants": participants,
        "teams": teams,
        "agents": agents,
        "submissions": submissions,
        "scores": scores,
        "statistics": export_statistics(db),
    }
    if redaction.include_audit:
        sections["audit_log"] = export_audit_log(db, redaction)
    return sections


def _counts(sections: dict[str, object]) -> dict:
    return {
        "participants": len(sections["participants"]),  # type: ignore[arg-type]
        "teams": len(sections["teams"]),                # type: ignore[arg-type]
        "agents": len(sections["agents"]),              # type: ignore[arg-type]
        "submissions": len(sections["submissions"]),    # type: ignore[arg-type]
        "scores": len(sections["scores"]),              # type: ignore[arg-type]
    }


def bundle_files(db: Session, redaction: RedactionConfig) -> dict[str, bytes]:
    """The export as a {filename: bytes} map — deterministic (sorted) JSON.

    Shared by the ZIP builder and the GitHub push so both ship identical content.
    """
    event = db.get(Event, settings.event_id) or db.query(Event).first()
    if event is None:
        raise ValueError("event not seeded")

    sections = _collect(db, redaction)
    manifest = generate_manifest(db, event, redaction, _counts(sections))

    files: dict[str, bytes] = {
        "manifest.json": json.dumps(manifest, indent=2, sort_keys=True).encode("utf-8")
    }
    for name, payload in sections.items():
        files[f"{name}.json"] = json.dumps(
            payload, indent=2, sort_keys=True, ensure_ascii=False
        ).encode("utf-8")
    return files


def build_bundle(db: Session, redaction: RedactionConfig) -> bytes:
    """Generate the export ZIP and return its bytes."""
    files = bundle_files(db, redaction)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return buf.getvalue()


def preview(db: Session, redaction: RedactionConfig | None = None) -> dict:
    """Counts and an estimated (pre-compression) size, without building the zip."""
    redaction = redaction or RedactionConfig()
    sections = _collect(db, redaction)
    raw = sum(
        len(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
        for payload in sections.values()
    )
    return {
        "counts": _counts(sections),
        "estimated_size_mb": round(raw / (1024 * 1024), 4),
    }
