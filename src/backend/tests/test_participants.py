"""
Tests for Participant Management (Task 05).

Tests cover:
- Solo participant creation
- Team creation and invite codes
- Joining teams via invite code
- Team member management
- Participant profile updates
- Admin moderation
"""

import uuid
from datetime import UTC, datetime

import pytest
from fastapi import status


def get_headers(token):
    """Get headers with auth token."""
    return {"Authorization": f"Bearer {token}"}


# ============================================================================= #
# Solo Participant Creation
# ============================================================================= #

class TestSoloParticipantCreation:
    """Test solo participant creation (5.2)."""
    
    @pytest.mark.asyncio
    async def test_create_solo_participant(self, client):
        """User can create a solo participant profile."""
        from app.database import SessionLocal
        from app.models.event import Event
        from app.models.user import User
        from app.services.auth import create_jwt
        
        # Ensure event exists
        with SessionLocal() as db:
            event = db.query(Event).first()
            if not event:
                event = Event(
                    id="test-event",
                    title="Test Event",
                    type="hackathon",
                    state="OPEN",
                    start_at=datetime(2026, 1, 1, tzinfo=UTC),
                    end_at=datetime(2026, 12, 31, tzinfo=UTC),
                )
                db.add(event)
                db.commit()
        
        # Create a user first
        with SessionLocal() as db:
            user = User(email=f"test_{uuid.uuid4()}@test.local", role="user")
            db.add(user)
            db.commit()
            db.refresh(user)
            token = create_jwt(user)
        
        resp = await client.post(
            "/api/participants",
            json={
                "display_name": "Alice",
                "affiliation": "University of Bern",
                "links": ["https://github.com/alice"],
                "type": "human",
            },
            headers=get_headers(token),
        )
        assert resp.status_code == status.HTTP_201_CREATED
        data = resp.json()
        assert data["display_name"] == "Alice"
        assert data["affiliation"] == "University of Bern"
        assert data["type"] == "human"
        assert data["status"] == "active"
    
    @pytest.mark.asyncio
    async def test_create_solo_participant_duplicate(self, client):
        """User cannot create multiple solo participants."""
        from app.database import SessionLocal
        from app.models.user import User
        from app.services.auth import create_jwt
        
        # Create a user
        with SessionLocal() as db:
            user = User(email=f"test_{uuid.uuid4()}@test.local", role="user")
            db.add(user)
            db.commit()
            db.refresh(user)
            token = create_jwt(user)
        
        # Create first participant
        resp = await client.post(
            "/api/participants",
            json={"display_name": "Alice", "type": "human"},
            headers=get_headers(token),
        )
        assert resp.status_code == status.HTTP_201_CREATED
        
        # Try to create second
        resp = await client.post(
            "/api/participants",
            json={"display_name": "Alice 2", "type": "human"},
            headers=get_headers(token),
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "already has" in resp.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_create_participant_requires_auth(self, client):
        """Creating participant requires authentication."""
        resp = await client.post(
            "/api/participants",
            json={"display_name": "Alice"},
        )
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED


# ============================================================================= #
# Team Creation
# ============================================================================= #

class TestTeamCreation:
    """Test team creation (5.3)."""
    
    @pytest.mark.asyncio
    async def test_create_team(self, client):
        """User can create a team and get invite code."""
        from app.database import SessionLocal
        from app.models.user import User
        from app.services.auth import create_jwt
        
        # Create a user
        with SessionLocal() as db:
            user = User(email=f"test_{uuid.uuid4()}@test.local", role="user")
            db.add(user)
            db.commit()
            db.refresh(user)
            token = create_jwt(user)
        
        resp = await client.post(
            "/api/teams",
            json={
                "display_name": "Team Forge",
                "affiliation": "Mixed",
                "links": [],
            },
            headers=get_headers(token),
        )
        assert resp.status_code == status.HTTP_201_CREATED
        data = resp.json()
        assert data["display_name"] == "Team Forge"
        assert data["type"] == "team"
        assert "invite_code" in data
        assert len(data["invite_code"]) == 8
        assert len(data["members"]) == 1
        assert data["members"][0]["role_in_team"] == "captain"
    
    @pytest.mark.asyncio
    async def test_team_invite_code_unique(self, client):
        """Team invite codes are unique."""
        from app.database import SessionLocal
        from app.models.user import User
        from app.services.auth import create_jwt
        
        # Create a user
        with SessionLocal() as db:
            user = User(email=f"test_{uuid.uuid4()}@test.local", role="user")
            db.add(user)
            db.commit()
            db.refresh(user)
            token = create_jwt(user)
        
        # Create multiple teams
        codes = set()
        for i in range(5):
            resp = await client.post(
                "/api/teams",
                json={"display_name": f"Team {i}"},
                headers=get_headers(token),
            )
            assert resp.status_code == status.HTTP_201_CREATED
            code = resp.json()["invite_code"]
            assert code not in codes
            codes.add(code)


# ============================================================================= #
# Join Team via Invite Code
# ============================================================================= #

class TestJoinTeam:
    """Test joining teams via invite code (5.4)."""
    
    @pytest.mark.asyncio
    async def test_join_team_with_invite(self, client):
        """User can join team using invite code."""
        from app.database import SessionLocal
        from app.models.user import User
        from app.services.auth import create_jwt
        
        # Create admin user and team
        with SessionLocal() as db:
            admin = User(email=f"admin_{uuid.uuid4()}@test.local", role="admin")
            db.add(admin)
            db.commit()
            db.refresh(admin)
            admin_token = create_jwt(admin)
        
        resp = await client.post(
            "/api/teams",
            json={"display_name": "Test Team"},
            headers=get_headers(admin_token),
        )
        invite_code = resp.json()["invite_code"]
        
        # Create test user and join
        with SessionLocal() as db:
            user = User(email=f"test_{uuid.uuid4()}@test.local", role="user")
            db.add(user)
            db.commit()
            db.refresh(user)
            token = create_jwt(user)
        
        resp = await client.post(
            f"/api/teams/join?invite_code={invite_code}",
            headers=get_headers(token),
        )
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert len(data["members"]) == 2
    
    @pytest.mark.asyncio
    async def test_join_invalid_invite_code(self, client):
        """Invalid invite code returns 404."""
        from app.database import SessionLocal
        from app.models.user import User
        from app.services.auth import create_jwt
        
        with SessionLocal() as db:
            user = User(email=f"test_{uuid.uuid4()}@test.local", role="user")
            db.add(user)
            db.commit()
            db.refresh(user)
            token = create_jwt(user)
        
        resp = await client.post(
            "/api/teams/join?invite_code=INVALID123",
            headers=get_headers(token),
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND
    
    @pytest.mark.asyncio
    async def test_join_already_member(self, client):
        """User cannot join same team twice."""
        from app.database import SessionLocal
        from app.models.user import User
        from app.services.auth import create_jwt
        
        with SessionLocal() as db:
            user = User(email=f"test_{uuid.uuid4()}@test.local", role="user")
            db.add(user)
            db.commit()
            db.refresh(user)
            token = create_jwt(user)
        
        # Create team
        resp = await client.post(
            "/api/teams",
            json={"display_name": "Test Team"},
            headers=get_headers(token),
        )
        invite_code = resp.json()["invite_code"]
        
        # Try to join own team
        resp = await client.post(
            f"/api/teams/join?invite_code={invite_code}",
            headers=get_headers(token),
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


# ============================================================================= #
# Team Member Management
# ============================================================================= #

class TestTeamMemberManagement:
    """Test team member management (5.5)."""
    
    @pytest.mark.asyncio
    async def test_list_team_members(self, client):
        """Team members can list team members."""
        from app.database import SessionLocal
        from app.models.user import User
        from app.services.auth import create_jwt
        
        with SessionLocal() as db:
            user = User(email=f"test_{uuid.uuid4()}@test.local", role="user")
            db.add(user)
            db.commit()
            db.refresh(user)
            token = create_jwt(user)
        
        # Create team
        resp = await client.post(
            "/api/teams",
            json={"display_name": "Test Team"},
            headers=get_headers(token),
        )
        team_id = resp.json()["id"]
        
        # List members
        resp = await client.get(
            f"/api/teams/{team_id}/members",
            headers=get_headers(token),
        )
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.json()["members"]) == 1
    
    @pytest.mark.asyncio
    async def test_remove_member_captain(self, client):
        """Captain can remove team members."""
        from app.database import SessionLocal
        from app.models.participant_member import ParticipantMember
        from app.models.user import User
        from app.services.auth import create_jwt
        
        # Create admin/captain
        with SessionLocal() as db:
            admin = User(email=f"admin_{uuid.uuid4()}@test.local", role="admin")
            db.add(admin)
            db.commit()
            db.refresh(admin)
            admin_token = create_jwt(admin)
        
        # Create team
        resp = await client.post(
            "/api/teams",
            json={"display_name": "Test Team"},
            headers=get_headers(admin_token),
        )
        team_id = resp.json()["id"]
        invite_code = resp.json()["invite_code"]
        
        # Add test user to team
        with SessionLocal() as db:
            user = User(email=f"test_{uuid.uuid4()}@test.local", role="user")
            db.add(user)
            db.commit()
            db.refresh(user)
            token = create_jwt(user)
        
        await client.post(
            f"/api/teams/join?invite_code={invite_code}",
            headers=get_headers(token),
        )
        
        # Captain removes member
        with SessionLocal() as db:
            member = db.query(ParticipantMember).filter(
                ParticipantMember.participant_id == team_id,
                ParticipantMember.user_id == user.id,
            ).first()
            
            resp = await client.delete(
                f"/api/teams/{team_id}/members/{member.id}",
                headers=get_headers(admin_token),
            )
            assert resp.status_code == status.HTTP_200_OK
    
    @pytest.mark.asyncio
    async def test_leave_team(self, client):
        """Member can leave team."""
        from app.database import SessionLocal
        from app.models.user import User
        from app.services.auth import create_jwt
        
        # Create admin/captain
        with SessionLocal() as db:
            admin = User(email=f"admin_{uuid.uuid4()}@test.local", role="admin")
            db.add(admin)
            db.commit()
            db.refresh(admin)
            admin_token = create_jwt(admin)
        
        # Create team
        resp = await client.post(
            "/api/teams",
            json={"display_name": "Test Team"},
            headers=get_headers(admin_token),
        )
        invite_code = resp.json()["invite_code"]
        team_id = resp.json()["id"]
        
        # Test user joins and leaves
        with SessionLocal() as db:
            user = User(email=f"test_{uuid.uuid4()}@test.local", role="user")
            db.add(user)
            db.commit()
            db.refresh(user)
            token = create_jwt(user)
        
        await client.post(
            f"/api/teams/join?invite_code={invite_code}",
            headers=get_headers(token),
        )
        
        resp = await client.post(
            f"/api/teams/{team_id}/leave",
            headers=get_headers(token),
        )
        assert resp.status_code == status.HTTP_200_OK
    
    @pytest.mark.asyncio
    async def test_cannot_leave_as_captain(self, client):
        """Captain cannot leave without transferring leadership."""
        from app.database import SessionLocal
        from app.models.user import User
        from app.services.auth import create_jwt
        
        with SessionLocal() as db:
            admin = User(email=f"admin_{uuid.uuid4()}@test.local", role="admin")
            db.add(admin)
            db.commit()
            db.refresh(admin)
            token = create_jwt(admin)
        
        # Create team
        resp = await client.post(
            "/api/teams",
            json={"display_name": "Test Team"},
            headers=get_headers(token),
        )
        team_id = resp.json()["id"]
        
        # Captain tries to leave
        resp = await client.post(
            f"/api/teams/{team_id}/leave",
            headers=get_headers(token),
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "captain" in resp.json()["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_regenerate_invite_code(self, client):
        """Captain can regenerate invite code."""
        from app.database import SessionLocal
        from app.models.user import User
        from app.services.auth import create_jwt
        
        with SessionLocal() as db:
            admin = User(email=f"admin_{uuid.uuid4()}@test.local", role="admin")
            db.add(admin)
            db.commit()
            db.refresh(admin)
            token = create_jwt(admin)
        
        # Create team
        resp = await client.post(
            "/api/teams",
            json={"display_name": "Test Team"},
            headers=get_headers(token),
        )
        team_id = resp.json()["id"]
        old_code = resp.json()["invite_code"]
        
        # Regenerate
        resp = await client.post(
            f"/api/teams/{team_id}/regenerate-invite",
            headers=get_headers(token),
        )
        assert resp.status_code == status.HTTP_200_OK
        new_code = resp.json()["invite_code"]
        assert new_code != old_code
        assert len(new_code) == 8


# ============================================================================= #
# Participant Profile
# ============================================================================= #

class TestParticipantProfile:
    """Test participant profile management (5.6)."""
    
    @pytest.mark.asyncio
    async def test_get_own_participant(self, client):
        """User can get their own participant info."""
        from app.database import SessionLocal
        from app.models.user import User
        from app.services.auth import create_jwt
        
        with SessionLocal() as db:
            user = User(email=f"test_{uuid.uuid4()}@test.local", role="user")
            db.add(user)
            db.commit()
            db.refresh(user)
            token = create_jwt(user)
        
        # Create participant
        await client.post(
            "/api/participants",
            json={"display_name": "Alice"},
            headers=get_headers(token),
        )
        
        # Get own participant
        resp = await client.get(
            "/api/participants/me",
            headers=get_headers(token),
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["display_name"] == "Alice"
    
    @pytest.mark.asyncio
    async def test_update_own_participant(self, client):
        """User can update their own participant profile."""
        from app.database import SessionLocal
        from app.models.user import User
        from app.services.auth import create_jwt
        
        with SessionLocal() as db:
            user = User(email=f"test_{uuid.uuid4()}@test.local", role="user")
            db.add(user)
            db.commit()
            db.refresh(user)
            token = create_jwt(user)
        
        # Create participant
        await client.post(
            "/api/participants",
            json={"display_name": "Alice", "affiliation": "Original"},
            headers=get_headers(token),
        )
        
        # Update
        resp = await client.patch(
            "/api/participants/me",
            json={"display_name": "Alice B.", "affiliation": "Updated"},
            headers=get_headers(token),
        )
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["display_name"] == "Alice B."
        assert data["affiliation"] == "Updated"
    
    @pytest.mark.asyncio
    async def test_get_participant_public(self, client):
        """Anyone can view public participant info."""
        from app.database import SessionLocal
        from app.models.user import User
        from app.services.auth import create_jwt
        
        with SessionLocal() as db:
            user = User(email=f"test_{uuid.uuid4()}@test.local", role="user")
            db.add(user)
            db.commit()
            db.refresh(user)
            token = create_jwt(user)
        
        # Create participant
        resp = await client.post(
            "/api/participants",
            json={"display_name": "Alice", "affiliation": "Uni"},
            headers=get_headers(token),
        )
        participant_id = resp.json()["id"]
        
        # Get public info (no auth needed)
        resp = await client.get(f"/api/participants/{participant_id}")
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["display_name"] == "Alice"


# ============================================================================= #
# Participant Listing
# ============================================================================= #

class TestParticipantListing:
    """Test participant listing (5.7)."""
    
    @pytest.mark.asyncio
    async def test_list_participants(self, client):
        """Public can list active participants."""
        from app.database import SessionLocal
        from app.models.user import User
        from app.services.auth import create_jwt
        
        with SessionLocal() as db:
            user = User(email=f"test_{uuid.uuid4()}@test.local", role="user")
            db.add(user)
            db.commit()
            db.refresh(user)
            token = create_jwt(user)
        
        # Create some participants
        await client.post(
            "/api/participants",
            json={"display_name": "Alice"},
            headers=get_headers(token),
        )
        
        resp = await client.get("/api/participants")
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert "participants" in data
        assert "total" in data
    
    @pytest.mark.asyncio
    async def test_list_participants_filter_type(self, client):
        """Can filter participants by type."""
        from app.database import SessionLocal
        from app.models.user import User
        from app.services.auth import create_jwt
        
        with SessionLocal() as db:
            user = User(email=f"test_{uuid.uuid4()}@test.local", role="user")
            db.add(user)
            db.commit()
            db.refresh(user)
            token = create_jwt(user)
        
        # Create solo participant
        await client.post(
            "/api/participants",
            json={"display_name": "Alice", "type": "human"},
            headers=get_headers(token),
        )
        
        # Create team
        await client.post(
            "/api/teams",
            json={"display_name": "Team"},
            headers=get_headers(token),
        )
        
        # Filter by human
        resp = await client.get("/api/participants?type=human")
        assert resp.status_code == status.HTTP_200_OK
        humans = [p for p in resp.json()["participants"] if p["type"] == "human"]
        assert len(humans) >= 1


# ============================================================================= #
# Admin Moderation
# ============================================================================= #

class TestAdminModeration:
    """Test admin moderation (5.8)."""
    
    @pytest.mark.asyncio
    async def test_admin_list_all_participants(self, client):
        """Admin can list all participants with full details."""
        from app.database import SessionLocal
        from app.models.user import User
        from app.services.auth import create_jwt
        
        with SessionLocal() as db:
            admin = User(email=f"admin_{uuid.uuid4()}@test.local", role="admin")
            db.add(admin)
            db.commit()
            db.refresh(admin)
            token = create_jwt(admin)
        
        resp = await client.get(
            "/api/admin/participants",
            headers=get_headers(token),
        )
        assert resp.status_code == status.HTTP_200_OK
        assert "participants" in resp.json()
    
    @pytest.mark.asyncio
    async def test_admin_update_participant_status(self, client):
        """Admin can update participant status."""
        from app.database import SessionLocal
        from app.models.user import User
        from app.services.auth import create_jwt
        
        # Create admin
        with SessionLocal() as db:
            admin = User(email=f"admin_{uuid.uuid4()}@test.local", role="admin")
            db.add(admin)
            db.commit()
            db.refresh(admin)
            admin_token = create_jwt(admin)
        
        # Create user and participant
        with SessionLocal() as db:
            user = User(email=f"test_{uuid.uuid4()}@test.local", role="user")
            db.add(user)
            db.commit()
            db.refresh(user)
            token = create_jwt(user)
        
        resp = await client.post(
            "/api/participants",
            json={"display_name": "Alice"},
            headers=get_headers(token),
        )
        participant_id = resp.json()["id"]
        
        # Admin disables participant
        resp = await client.patch(
            f"/api/admin/participants/{participant_id}/status",
            json={"status": "disabled"},
            headers=get_headers(admin_token),
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["status"] == "disabled"
    
    @pytest.mark.asyncio
    async def test_admin_create_participant(self, client):
        """Admin can create participant on behalf of user."""
        from app.database import SessionLocal
        from app.models.user import User
        from app.services.auth import create_jwt
        
        with SessionLocal() as db:
            admin = User(email=f"admin_{uuid.uuid4()}@test.local", role="admin")
            db.add(admin)
            db.commit()
            db.refresh(admin)
            admin_token = create_jwt(admin)
            
            user = User(email=f"test_{uuid.uuid4()}@test.local", role="user")
            db.add(user)
            db.commit()
            db.refresh(user)
        
        resp = await client.post(
            "/api/admin/participants",
            json={
                "display_name": "Admin Created",
                "type": "human",
            },
            params={"user_id": user.id},
            headers=get_headers(admin_token),
        )
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.json()["display_name"] == "Admin Created"
    
    @pytest.mark.asyncio
    async def test_non_admin_cannot_moderate(self, client):
        """Non-admin cannot access admin endpoints."""
        from app.database import SessionLocal
        from app.models.user import User
        from app.services.auth import create_jwt
        
        with SessionLocal() as db:
            user = User(email=f"test_{uuid.uuid4()}@test.local", role="user")
            db.add(user)
            db.commit()
            db.refresh(user)
            token = create_jwt(user)
        
        resp = await client.get(
            "/api/admin/participants",
            headers=get_headers(token),
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.anyio
async def test_public_team_roster_carries_members_without_secrets(client):
    """GET /api/teams lists members by display name — no emails, no invite codes."""
    from app.database import SessionLocal
    from app.services.seeder import seed_fixtures

    with SessionLocal() as db:
        seed_fixtures(db)

    resp = await client.get("/api/teams")
    assert resp.status_code == 200
    teams = resp.json()
    owls = next((t for t in teams if t["display_name"] == "the_owls"), None)
    assert owls is not None
    roles = {m["display_name"]: m["role_in_team"] for m in owls["members"]}
    assert roles.get("June K.") == "captain"
    assert roles.get("Ada Cole") == "member"
    blob = resp.text
    assert "invite_code" not in blob
    assert "@demo.rite" not in blob
