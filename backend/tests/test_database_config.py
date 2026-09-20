"""Synthetic credentials only; verify what asyncpg actually receives."""
import pytest
from sqlalchemy.dialects.postgresql.asyncpg import PGDialect_asyncpg
from app.core.config import Settings


@pytest.mark.parametrize("password", ["test@host", "test:/?#%+ @x", "test%40literal", "test$with${literal}"])
def test_compose_credentials_reach_driver_without_url_parsing(password):
    config = Settings(_env_file=None, DATABASE_HOST="db", DATABASE_PORT=5432,
                      POSTGRES_USER="synthetic-user", POSTGRES_PASSWORD=password, POSTGRES_DB="synthetic-db")
    url = config.database_connection_url()
    _, kwargs = PGDialect_asyncpg().create_connect_args(url)
    assert kwargs["host"] == "db"
    assert kwargs["port"] == 5432
    assert kwargs["user"] == "synthetic-user"
    assert kwargs["password"] == password
    assert kwargs["database"] == "synthetic-db"
    assert password not in str(url)


def test_explicit_database_url_still_supported():
    config = Settings(_env_file=None, DATABASE_HOST=None,
                      DATABASE_URL="postgresql+asyncpg://test:encoded%40password@localhost:5433/testdb")
    _, kwargs = PGDialect_asyncpg().create_connect_args(config.database_connection_url())
    assert kwargs["password"] == "encoded@password"
    assert kwargs["host"] == "localhost"
    assert kwargs["port"] == 5433


def test_incomplete_components_fail_without_revealing_password():
    config = Settings(_env_file=None, DATABASE_HOST="db", POSTGRES_USER=None,
                      POSTGRES_PASSWORD="synthetic-secret", POSTGRES_DB="test")
    with pytest.raises(ValueError, match="Configuração PostgreSQL incompleta") as caught:
        config.database_connection_url()
    assert "synthetic-secret" not in str(caught.value)
