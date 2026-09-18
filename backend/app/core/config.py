from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://adapterflow:adapterflow_dev@localhost:5432/adapterflow"
    STORAGE_PATH: str = "./storage"
    BACKEND_CORS_ORIGINS: list[str] = ["http://localhost:3099", "http://localhost:3000"]
    MAX_UPLOAD_SIZE_MB: int = 50
    PROJECT_NAME: str = "AdapterFlow"
    API_V1_PREFIX: str = "/api/v1"

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()
