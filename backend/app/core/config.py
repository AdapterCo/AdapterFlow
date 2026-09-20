from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://localhost/adapterflow"
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

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
