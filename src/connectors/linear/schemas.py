"""Pydantic models for Linear API responses."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class LinearState(BaseModel):
    """Linear issue state."""

    id: str
    name: str
    type: str  # "triage", "backlog", "unstarted", "started", "completed", "canceled"


class LinearLabel(BaseModel):
    """Linear issue label."""

    id: str
    name: str
    color: str | None = None


class LinearProject(BaseModel):
    """Linear project."""

    id: str
    name: str
    description: str | None = None
    state: str  # "planned", "started", "paused", "completed", "canceled"
    url: str | None = None
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")

    class Config:
        populate_by_name = True


class LinearUser(BaseModel):
    """Linear user."""

    id: str
    name: str
    email: str | None = None


class LinearComment(BaseModel):
    """Linear issue comment."""

    id: str
    body: str
    user: LinearUser | None = None
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")

    class Config:
        populate_by_name = True


class LinearIssue(BaseModel):
    """Linear issue."""

    id: str
    identifier: str  # e.g., "ENG-123"
    title: str
    description: str | None = None
    state: LinearState | None = None
    priority: int = 0  # 0 (no priority) to 4 (urgent)
    labels: list[LinearLabel] = Field(default_factory=list)
    project: LinearProject | None = None
    assignee: LinearUser | None = None
    creator: LinearUser | None = None
    comments: list[LinearComment] = Field(default_factory=list)
    url: str | None = None
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")

    class Config:
        populate_by_name = True

    def to_text(self) -> str:
        """Convert issue to plain text for extraction."""
        parts = [
            f"Issue: {self.identifier}",
            f"Title: {self.title}",
        ]

        if self.description:
            parts.append(f"Description: {self.description}")

        if self.state:
            parts.append(f"State: {self.state.name} ({self.state.type})")

        if self.priority > 0:
            priority_labels = ["", "Low", "Medium", "High", "Urgent"]
            parts.append(f"Priority: {priority_labels[self.priority]}")

        if self.labels:
            parts.append(f"Labels: {', '.join(label.name for label in self.labels)}")

        if self.project:
            parts.append(f"Project: {self.project.name}")

        if self.creator:
            parts.append(f"Created by: {self.creator.name}")

        if self.assignee:
            parts.append(f"Assigned to: {self.assignee.name}")

        if self.comments:
            parts.append("\nComments:")
            for comment in self.comments:
                user_name = comment.user.name if comment.user else "Unknown"
                parts.append(f"- {user_name}: {comment.body}")

        return "\n".join(parts)


class LinearPageInfo(BaseModel):
    """GraphQL pagination info."""

    has_next_page: bool = Field(alias="hasNextPage")
    end_cursor: str | None = Field(alias="endCursor")

    class Config:
        populate_by_name = True


class LinearIssuesResponse(BaseModel):
    """Response from issues query."""

    page_info: LinearPageInfo = Field(alias="pageInfo")
    nodes: list[dict[str, Any]]

    class Config:
        populate_by_name = True


class LinearProjectsResponse(BaseModel):
    """Response from projects query."""

    page_info: LinearPageInfo = Field(alias="pageInfo")
    nodes: list[dict[str, Any]]

    class Config:
        populate_by_name = True
