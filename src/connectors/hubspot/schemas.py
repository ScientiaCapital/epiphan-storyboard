"""Pydantic models for HubSpot API responses."""

from pydantic import BaseModel, ConfigDict, Field


class HubSpotCallProperties(BaseModel):
    """Call properties from HubSpot API (populated by SalesMSG integration)."""

    model_config = ConfigDict(populate_by_name=True)

    hs_call_body: str | None = None  # Transcript/notes text from SalesMSG
    hs_call_title: str | None = None
    hs_call_duration: int | None = None  # Milliseconds
    hs_timestamp: str | None = None  # ISO 8601
    hs_call_status: str | None = None  # COMPLETED, BUSY, etc.
    hs_call_direction: str | None = None  # INBOUND, OUTBOUND


class HubSpotCall(BaseModel):
    """Full HubSpot call object from CRM v3 API."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    properties: HubSpotCallProperties
    created_at: str | None = Field(default=None, alias="createdAt")
    updated_at: str | None = Field(default=None, alias="updatedAt")


class HubSpotPaging(BaseModel):
    """Pagination cursor from HubSpot API.

    The next_link dict contains an "after" key with the cursor value.
    """

    model_config = ConfigDict(populate_by_name=True)

    next_link: dict | None = Field(default=None, alias="next")


class HubSpotCallsResponse(BaseModel):
    """Paginated response from HubSpot calls list endpoint."""

    model_config = ConfigDict(populate_by_name=True)

    results: list[HubSpotCall]
    paging: HubSpotPaging | None = None


class HubSpotAssociation(BaseModel):
    """HubSpot association (contact, company, etc.)."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    type: str
