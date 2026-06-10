# Import all models here so that:
# 1. Alembic autogenerate can discover them via Base.metadata
# 2. Any module doing `from app.models import *` gets the full set

from app.models.agent import Agent
from app.models.audit_log import AuditLog
from app.models.event import Event
from app.models.file import File
from app.models.metrics_daily import MetricsDaily
from app.models.page import Page
from app.models.participant import Participant
from app.models.participant_member import ParticipantMember
from app.models.phase import Phase
from app.models.project import Project
from app.models.repository import RepoCommit, Repository
from app.models.score import Score
from app.models.session import Session
from app.models.submission import Submission
from app.models.task import Task
from app.models.track import Track
from app.models.user import User

__all__ = [
    "Agent",
    "AuditLog",
    "Event",
    "File",
    "MetricsDaily",
    "Page",
    "Participant",
    "ParticipantMember",
    "Phase",
    "Project",
    "RepoCommit",
    "Repository",
    "Score",
    "Session",
    "Submission",
    "Task",
    "Track",
    "User",
]
