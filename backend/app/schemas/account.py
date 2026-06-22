from pydantic import BaseModel, Field


class ApiKeyUpdateRequest(BaseModel):
    api_key: str = Field(min_length=1, max_length=1_000)


class AccountStatusResponse(BaseModel):
    username: str
    api_key_configured: bool
    api_key_active: bool
