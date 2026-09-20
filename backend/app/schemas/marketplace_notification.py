from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


class MercadoLivreNotification(BaseModel):
    model_config = ConfigDict(extra="ignore")

    notification_id: str | None = Field(default=None, alias="_id", max_length=200)
    resource: str = Field(min_length=2, max_length=2048, pattern=r"^/[^/\s]")
    user_id: int = Field(gt=0)
    application_id: int = Field(gt=0)
    topic: str = Field(min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9_-]+$")
    attempts: int | None = Field(default=None, ge=1)
    sent: AwareDatetime | None = None
    received: AwareDatetime | None = None


class NotificationReceipt(BaseModel):
    status: str = "received"
