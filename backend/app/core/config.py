from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://adapterflow:adapterflow_dev@localhost:5432/adapterflow"
    STORAGE_PATH: str = "./storage"
    BACKEND_CORS_ORIGINS: list[str] = [
        "https://flow.adapterco.com.br",
        "http://flow.adapterco.com.br",
        "http://localhost:3099",
        "http://localhost:3000"
    ]
    MAX_UPLOAD_SIZE_MB: int = 200
    PROJECT_NAME: str = "AdapterFlow"
    API_V1_PREFIX: str = "/api/v1"

    # Mercado Livre Integration
    MERCADOLIVRE_APP_ID: str | None = None
    MERCADOLIVRE_CLIENT_SECRET: str | None = None
    MERCADOLIVRE_REDIRECT_URI: str = "https://flow.adapterco.com.br/marketplaces/callback"

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()
