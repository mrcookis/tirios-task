from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.db.models.user import User
from app.services.auth import create_access_token, create_refresh_token, verify_password
from main import app

# Pre-hashed password for "password123" to avoid bcrypt during test setup
HASHED_PASSWORD = "$2b$12$5J9H9Ld5L5L5L5L5L5L5L.bGNtbVLIGQKxKQ5KQ5KQ5KQ5"


@pytest.fixture
async def client_with_mocked_db():
    """Test client with mocked database."""
    # Pre-define the users
    test_user = User(
        id=1,
        name="Test User",
        email="test@example.com",
        hashed_password=HASHED_PASSWORD,
        is_active=True,
        token=None,
        created_at=datetime.now(timezone.utc),
    )
    inactive_user = User(
        id=2,
        name="Inactive User",
        email="inactive@example.com",
        hashed_password=HASHED_PASSWORD,
        is_active=False,
        token=None,
        created_at=datetime.now(timezone.utc),
    )

    users_by_email = {
        "test@example.com": test_user,
        "inactive@example.com": inactive_user,
    }
    users_by_id = {
        1: test_user,
        2: inactive_user,
    }

    class MockResult:
        def __init__(self):
            self.user = None

        def scalar_one_or_none(self):
            return self.user

    async def mock_execute(query_obj):
        """Mock database execute that looks at query object to determine user."""
        result = MockResult()

        # For select queries, we'll use a simple heuristic:
        # Check the query object's whereclause to see what's being filtered
        if hasattr(query_obj, "whereclause"):
            clause_str = str(query_obj.whereclause).lower() if query_obj.whereclause else ""

            # Check for email comparisons
            if "test@example.com" in clause_str or ("email" in clause_str and "test" in clause_str):
                result.user = users_by_email["test@example.com"]
            elif "inactive@example.com" in clause_str or ("email" in clause_str and "inactive" in clause_str):
                result.user = users_by_email["inactive@example.com"]
            # Check for ID comparisons
            elif "= 1" in clause_str or "1" in clause_str and "id" in clause_str:
                result.user = users_by_id[1]
            elif "= 2" in clause_str or "2" in clause_str and "id" in clause_str:
                result.user = users_by_id[2]

        return result

    mock_db = AsyncMock(spec=AsyncSession)
    mock_db.execute = mock_execute
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    def get_db_override():
        return mock_db

    app.dependency_overrides[get_db] = get_db_override
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_login_success(client_with_mocked_db):
    with patch("app.api.routes.auth.verify_password", return_value=True):
        response = await client_with_mocked_db.post(
            "/auth/login",
            json={"email": "test@example.com", "password": "password123"},
        )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client_with_mocked_db):
    response = await client_with_mocked_db.post(
        "/auth/login",
        json={"email": "test@example.com", "password": "wrongpassword"},
    )

    assert response.status_code == 401
    assert "Invalid email or password" in response.json()["detail"]


@pytest.mark.asyncio
async def test_login_user_not_found(client_with_mocked_db):
    response = await client_with_mocked_db.post(
        "/auth/login",
        json={"email": "nonexistent@example.com", "password": "password123"},
    )

    assert response.status_code == 401
    assert "Invalid email or password" in response.json()["detail"]


@pytest.mark.asyncio
async def test_login_inactive_user(client_with_mocked_db):
    with patch("app.api.routes.auth.verify_password", return_value=True):
        response = await client_with_mocked_db.post(
            "/auth/login",
            json={"email": "inactive@example.com", "password": "password123"},
        )

    assert response.status_code == 403
    assert "User account is inactive" in response.json()["detail"]


@pytest.mark.asyncio
async def test_logout_success(client_with_mocked_db):
    original_created_at = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    test_user = User(
        id=1,
        name="Test User",
        email="test@example.com",
        hashed_password=HASHED_PASSWORD,
        is_active=True,
        token=None,
        created_at=original_created_at,
    )
    access_token = create_access_token(data={"sub": str(test_user.id)})
    test_user.token = access_token

    async def mock_get_current_user():
        return test_user

    app.dependency_overrides[get_current_user] = mock_get_current_user

    response = await client_with_mocked_db.post(
        "/auth/logout",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200
    assert "Successfully logged out" in response.json()["message"]

    # Verify token was cleared
    assert test_user.token is None

    # Verify created_at was updated (should be more recent than original)
    assert test_user.created_at != original_created_at
    assert test_user.created_at > original_created_at

    del app.dependency_overrides[get_current_user]


@pytest.mark.asyncio
async def test_logout_invalid_token(client_with_mocked_db):
    response = await client_with_mocked_db.post(
        "/auth/logout",
        headers={"Authorization": "Bearer invalid.token.here"},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_success(client_with_mocked_db):
    refresh_token = create_refresh_token(data={"sub": "1"})

    response = await client_with_mocked_db.post(
        "/auth/refresh",
        headers={"Authorization": f"Bearer {refresh_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_refresh_invalid_token(client_with_mocked_db):
    response = await client_with_mocked_db.post(
        "/auth/refresh",
        headers={"Authorization": "Bearer invalid.token.here"},
    )

    assert response.status_code == 401
    assert "Invalid refresh token" in response.json()["detail"]


@pytest.mark.asyncio
async def test_refresh_access_token_instead_of_refresh(client_with_mocked_db):
    access_token = create_access_token(data={"sub": "1"})

    response = await client_with_mocked_db.post(
        "/auth/refresh",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 401
    assert "Invalid refresh token" in response.json()["detail"]


@pytest.mark.asyncio
async def test_health_check_still_works(client_with_mocked_db):
    response = await client_with_mocked_db.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
