import pytest
from unittest.mock import patch
from app.main import app
from app.core.security import require_admin

@pytest.fixture(autouse=True)
def isolated_api_tests():
    original = dict(app.dependency_overrides)
    app.dependency_overrides[require_admin] = lambda: "test-operator"
    # ASGI requests stay local; any accidentally unmocked external request fails.
    with patch("httpx.AsyncHTTPTransport.handle_async_request", side_effect=AssertionError("External HTTP disabled in tests")):
        yield
    app.dependency_overrides.clear()
    app.dependency_overrides.update(original)
