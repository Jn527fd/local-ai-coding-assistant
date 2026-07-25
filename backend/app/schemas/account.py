from pydantic import AliasChoices, BaseModel, Field


class ApiKeyUpdateRequest(BaseModel):
    api_key: str = Field(
        min_length=1,
        max_length=1_000,
        validation_alias=AliasChoices("api_key", "apiKey"),
    )


class AccountStatusResponse(BaseModel):
    username: str
    api_key_configured: bool
    api_key_active: bool
