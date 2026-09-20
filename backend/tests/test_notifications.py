"""Synthetic provider messages; no production credentials or external calls."""
from unittest.mock import AsyncMock

import httpx
import pytest
from sqlalchemy.exc import OperationalError

from app.main import app
from app.core.config import settings
from app.core.database import get_db
from app.core.security import require_admin
from app.schemas.marketplace_notification import MercadoLivreNotification
from app.services.marketplace_notification import notification_key

PATH = "/api/v1/marketplaces/mercadolivre/notifications"
PAYLOAD = {"resource": "/items/MLB123456", "user_id": 123, "application_id": 456,
           "topic": "items", "attempts": 1, "received": "2026-09-20T10:00:00Z"}


@pytest.fixture
def receipt_session(monkeypatch):
    monkeypatch.setattr(settings, "MERCADOLIVRE_APP_ID", "456")
    monkeypatch.setattr(settings, "ADMIN_USERNAME", "test-operator")
    from pydantic import SecretStr
    monkeypatch.setattr(settings, "ADMIN_PASSWORD", SecretStr("synthetic-only"))
    app.dependency_overrides.pop(require_admin, None)
    session = AsyncMock()
    async def dependency():
        yield session
    app.dependency_overrides[get_db] = dependency
    return session


@pytest.mark.asyncio
async def test_public_receipt_persists_before_ack_and_admin_stays_private(receipt_session):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(PATH, json=PAYLOAD)
        assert response.status_code == 200
        assert response.json() == {"status": "received"}
        assert [call[0] for call in receipt_session.mock_calls] == ["execute", "commit"]
        assert (await client.get("/api/v1/marketplaces/accounts")).status_code == 401
        assert (await client.get(PATH)).status_code == 405


@pytest.mark.asyncio
@pytest.mark.parametrize("body, expected", [
    ({**PAYLOAD, "application_id": 789}, 403),
    ({**PAYLOAD, "resource": "https://untrusted.invalid"}, 422),
    ({**PAYLOAD, "resource": "//untrusted.invalid"}, 422),
    ({"topic": "items"}, 422),
    ({**PAYLOAD, "unused": "x" * 17000}, 413),
])
async def test_invalid_receipts_are_not_acknowledged(receipt_session, body, expected):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        assert (await client.post(PATH, json=body)).status_code == expected
    receipt_session.execute.assert_not_awaited()
    receipt_session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_unconfigured_app_and_non_json_rejected(receipt_session, monkeypatch):
    monkeypatch.setattr(settings, "MERCADOLIVRE_APP_ID", None)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        assert (await client.post(PATH, json=PAYLOAD)).status_code == 503
        assert (await client.post(PATH, content="invalid")).status_code == 415
        assert (await client.post(PATH, content="{", headers={"content-type": "application/json"})).status_code == 422
    receipt_session.execute.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("failure_at", ["execute", "commit"])
async def test_database_failure_never_returns_success(receipt_session, failure_at):
    getattr(receipt_session, failure_at).side_effect = OperationalError("", {}, Exception("offline"))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        assert (await client.post(PATH, json=PAYLOAD)).status_code == 503
    receipt_session.rollback.assert_awaited_once()


def test_retries_deduplicated_but_distinct_events_preserved():
    first = MercadoLivreNotification.model_validate(PAYLOAD)
    retry = MercadoLivreNotification.model_validate({**PAYLOAD, "attempts": 2, "sent": "2026-09-20T10:01:00Z"})
    assert notification_key(first) == notification_key(retry)
    next_event = MercadoLivreNotification.model_validate({**PAYLOAD, "received": "2026-09-20T11:00:00Z"})
    assert notification_key(first) != notification_key(next_event)
    without_id_or_time = first.model_copy(update={"received": None})
    assert notification_key(without_id_or_time) != notification_key(without_id_or_time)
