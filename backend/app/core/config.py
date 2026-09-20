from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr, field_validator
from sqlalchemy.engine import URL, make_url

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://localhost/adapterflow"
    DATABASE_HOST: str | None = None
    DATABASE_PORT: int = 5432
    POSTGRES_USER: str | None = None
    POSTGRES_PASSWORD: SecretStr | None = None
    POSTGRES_DB: str | None = None

    def database_connection_url(self) -> URL:
        # Compose passes components separately: never parse a raw password as URL syntax.
        if self.DATABASE_HOST is not None:
            if not self.DATABASE_HOST or not self.POSTGRES_USER or not self.POSTGRES_PASSWORD or not self.POSTGRES_DB:
                raise ValueError("Configuração PostgreSQL incompleta: confira host, usuário, senha e banco.")
            return URL.create(
                "postgresql+asyncpg", username=self.POSTGRES_USER,
                password=self.POSTGRES_PASSWORD.get_secret_value(),
                host=self.DATABASE_HOST, port=self.DATABASE_PORT, database=self.POSTGRES_DB,
            )
        return make_url(self.DATABASE_URL)

    ADMIN_USERNAME: str | None = None
    ADMIN_PASSWORD: SecretStr | None = None
    TOKEN_ENCRYPTION_KEY: SecretStr | None = None
    MAX_PDF_PAGES: int = 500
    OCR_ENABLED: bool = False
    OCR_LANGUAGE: str = "por+eng"
    STORAGE_PATH: str = "./storage"
    BACKEND_CORS_ORIGINS: list[str] = [
        "http://localhost:3099",
        "http://localhost:3000"
    ]
    MAX_UPLOAD_SIZE_MB: int = 200
    PROJECT_NAME: str = "AdapterFlow"
    API_V1_PREFIX: str = "/api/v1"

    # Mercado Livre Integration
    MERCADOLIVRE_APP_ID: str | None = None
    MERCADOLIVRE_CLIENT_SECRET: str | None = None
    MERCADOLIVRE_REDIRECT_URI: str | None = None

    @field_validator("MERCADOLIVRE_APP_ID", "MERCADOLIVRE_CLIENT_SECRET", "MERCADOLIVRE_REDIRECT_URI", mode="before")
    @classmethod
    def _strip_credential(cls, value):
        # Spaces, CRLF or wrapping quotes pasted into .env make the provider answer invalid_client.
        return value.strip().strip("\"'").strip() or None if isinstance(value, str) else value

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
