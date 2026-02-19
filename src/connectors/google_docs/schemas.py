"""Pydantic models for Google Docs and Drive API responses."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class GoogleDriveFile(BaseModel):
    """Google Drive file metadata from Drive API v3."""

    id: str
    name: str
    mime_type: str = Field(alias="mimeType")
    modified_time: datetime = Field(alias="modifiedTime")
    created_time: datetime | None = Field(default=None, alias="createdTime")
    web_view_link: str | None = Field(default=None, alias="webViewLink")
    owners: list[dict] | None = None
    last_modifying_user: dict | None = Field(default=None, alias="lastModifyingUser")

    class Config:
        populate_by_name = True


class GoogleDocumentContent(BaseModel):
    """Structural content element in Google Doc."""

    start_index: int = Field(alias="startIndex")
    end_index: int = Field(alias="endIndex")
    paragraph: dict | None = None
    table: dict | None = None
    section_break: dict | None = Field(default=None, alias="sectionBreak")
    table_of_contents: dict | None = Field(default=None, alias="tableOfContents")

    class Config:
        populate_by_name = True


class GoogleDocumentBody(BaseModel):
    """Document body structure."""

    content: list[dict] = Field(default_factory=list)


class GoogleDocument(BaseModel):
    """Google Docs document from Docs API v1."""

    document_id: str = Field(alias="documentId")
    title: str
    body: GoogleDocumentBody
    revision_id: str | None = Field(default=None, alias="revisionId")
    inline_objects: dict[str, Any] | None = Field(default=None, alias="inlineObjects")
    lists: dict[str, Any] | None = None
    named_styles: dict | None = Field(default=None, alias="namedStyles")
    suggested_changes: dict | None = Field(default=None, alias="suggestedChanges")

    class Config:
        populate_by_name = True


class GoogleDriveFilesResponse(BaseModel):
    """Response from Drive API files.list endpoint."""

    kind: str = "drive#fileList"
    next_page_token: str | None = Field(default=None, alias="nextPageToken")
    incomplete_search: bool = Field(default=False, alias="incompleteSearch")
    files: list[dict] = Field(default_factory=list)

    class Config:
        populate_by_name = True
