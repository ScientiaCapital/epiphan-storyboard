"""Pydantic models for Notion API responses."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class NotionParent(BaseModel):
    """Notion page parent."""

    type: str  # "database_id", "page_id", "workspace", "block_id"
    database_id: str | None = None
    page_id: str | None = None
    block_id: str | None = None


class NotionUser(BaseModel):
    """Notion user."""

    object: str = "user"
    id: str
    name: str | None = None
    avatar_url: str | None = None
    type: str | None = None
    person: dict | None = None
    bot: dict | None = None


class NotionRichText(BaseModel):
    """Notion rich text object."""

    type: str  # "text", "mention", "equation"
    text: dict | None = None
    mention: dict | None = None
    equation: dict | None = None
    annotations: dict | None = None
    plain_text: str
    href: str | None = None


class NotionPage(BaseModel):
    """Notion page."""

    object: str = "page"
    id: str
    created_time: datetime
    last_edited_time: datetime
    created_by: NotionUser | None = None
    last_edited_by: NotionUser | None = None
    cover: dict | None = None
    icon: dict | None = None
    parent: NotionParent
    archived: bool = False
    properties: dict[str, Any] = Field(default_factory=dict)
    url: str

    def get_title(self) -> str:
        """Extract page title from properties.

        Notion stores titles in different property keys (title, Name, etc.).

        Returns:
            Page title or "Untitled"
        """
        for prop_name, prop_value in self.properties.items():
            if isinstance(prop_value, dict) and prop_value.get("type") == "title":
                title_array = prop_value.get("title", [])
                if title_array:
                    return "".join(item.get("plain_text", "") for item in title_array)
        return "Untitled"


class NotionDatabase(BaseModel):
    """Notion database."""

    object: str = "database"
    id: str
    created_time: datetime
    last_edited_time: datetime
    created_by: NotionUser | None = None
    last_edited_by: NotionUser | None = None
    title: list[NotionRichText] = Field(default_factory=list)
    description: list[NotionRichText] = Field(default_factory=list)
    icon: dict | None = None
    cover: dict | None = None
    properties: dict[str, Any] = Field(default_factory=dict)
    parent: NotionParent
    url: str
    archived: bool = False

    def get_title(self) -> str:
        """Extract database title.

        Returns:
            Database title or "Untitled Database"
        """
        if self.title:
            return "".join(item.plain_text for item in self.title)
        return "Untitled Database"

    def get_description(self) -> str | None:
        """Extract database description.

        Returns:
            Description text or None
        """
        if self.description:
            return "".join(item.plain_text for item in self.description)
        return None


class NotionBlock(BaseModel):
    """Notion block (content element)."""

    object: str = "block"
    id: str
    parent: NotionParent | None = None
    created_time: datetime
    last_edited_time: datetime
    created_by: NotionUser | None = None
    last_edited_by: NotionUser | None = None
    has_children: bool = False
    archived: bool = False
    type: str  # "paragraph", "heading_1", "heading_2", "heading_3", "bulleted_list_item", "numbered_list_item", "to_do", "toggle", "code", etc.

    # Block-type specific content (dynamically populated)
    paragraph: dict | None = None
    heading_1: dict | None = None
    heading_2: dict | None = None
    heading_3: dict | None = None
    bulleted_list_item: dict | None = None
    numbered_list_item: dict | None = None
    to_do: dict | None = None
    toggle: dict | None = None
    code: dict | None = None
    quote: dict | None = None
    callout: dict | None = None
    divider: dict | None = None
    table_of_contents: dict | None = None
    equation: dict | None = None
    image: dict | None = None
    video: dict | None = None
    file: dict | None = None
    pdf: dict | None = None
    bookmark: dict | None = None
    embed: dict | None = None

    def get_text_content(self) -> str:
        """Extract text content from block.

        Returns:
            Plain text content or empty string
        """
        # Get the block-type specific content
        block_content = getattr(self, self.type, None)
        if not block_content or not isinstance(block_content, dict):
            return ""

        # Extract rich_text array
        rich_text = block_content.get("rich_text", [])
        if not rich_text:
            return ""

        # Concatenate plain_text from all rich text elements
        return "".join(item.get("plain_text", "") for item in rich_text)


class NotionSearchResponse(BaseModel):
    """Response from search endpoint."""

    object: str = "list"
    results: list[dict[str, Any]]
    next_cursor: str | None = None
    has_more: bool = False


class NotionBlocksResponse(BaseModel):
    """Response from blocks endpoint."""

    object: str = "list"
    results: list[dict[str, Any]]
    next_cursor: str | None = None
    has_more: bool = False


class NotionDatabaseQueryResponse(BaseModel):
    """Response from database query endpoint."""

    object: str = "list"
    results: list[dict[str, Any]]
    next_cursor: str | None = None
    has_more: bool = False
