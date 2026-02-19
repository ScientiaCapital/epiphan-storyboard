"""Pydantic models for Fireflies API responses."""

from datetime import datetime

from pydantic import BaseModel, Field


class FirefliesSentence(BaseModel):
    """A single sentence in a Fireflies transcript."""

    text: str
    speaker_name: str | None = Field(default=None, alias="speaker_name")
    speaker_id: str | None = Field(default=None, alias="speaker_id")
    start_time: float | None = Field(default=None, alias="start_time")  # seconds
    end_time: float | None = Field(default=None, alias="end_time")  # seconds

    class Config:
        populate_by_name = True


class FirefliesActionItem(BaseModel):
    """An action item from Fireflies."""

    text: str
    assignee: str | None = None


class FirefliesKeyword(BaseModel):
    """A keyword detected by Fireflies."""

    text: str
    score: float | None = None


class FirefliesUser(BaseModel):
    """User information."""

    user_id: str = Field(..., alias="user_id")
    name: str | None = None
    email: str | None = None

    class Config:
        populate_by_name = True


class FirefliesTranscript(BaseModel):
    """Full transcript from Fireflies."""

    id: str
    title: str | None = None
    date: datetime | None = None
    duration: int | None = None  # seconds
    meeting_url: str | None = Field(default=None, alias="meeting_url")
    video_url: str | None = Field(default=None, alias="video_url")

    # Participants
    participants: list[str] = Field(default_factory=list)
    organizer: FirefliesUser | None = None

    # Content
    sentences: list[FirefliesSentence] = Field(default_factory=list)
    action_items: list[FirefliesActionItem] = Field(default_factory=list)
    keywords: list[FirefliesKeyword] = Field(default_factory=list)

    # Summary
    summary: dict | None = None  # {overview, action_items, outline}

    class Config:
        populate_by_name = True

    def to_text(self) -> str:
        """Convert transcript to plain text format.

        Returns:
            Formatted transcript text with metadata
        """
        lines = []

        # Header
        lines.append(f"Meeting: {self.title or 'Untitled'}")
        if self.date:
            lines.append(f"Date: {self.date.strftime('%Y-%m-%d %H:%M')}")
        if self.duration:
            minutes = self.duration // 60
            lines.append(f"Duration: {minutes} minutes")
        if self.participants:
            lines.append(f"Participants: {', '.join(self.participants)}")

        lines.append("\n=== TRANSCRIPT ===\n")

        # Transcript
        current_speaker = None
        for sentence in self.sentences:
            speaker = sentence.speaker_name or "Unknown"
            if speaker != current_speaker:
                lines.append(f"\n[{speaker}]:")
                current_speaker = speaker
            lines.append(sentence.text)

        # Action items
        if self.action_items:
            lines.append("\n\n=== ACTION ITEMS ===\n")
            for item in self.action_items:
                assignee = f" ({item.assignee})" if item.assignee else ""
                lines.append(f"- {item.text}{assignee}")

        # Keywords
        if self.keywords:
            lines.append("\n\n=== KEYWORDS ===\n")
            keywords_text = ", ".join([k.text for k in self.keywords])
            lines.append(keywords_text)

        return "\n".join(lines)


class FirefliesTranscriptsResponse(BaseModel):
    """Response from Fireflies transcripts query."""

    transcripts: list[FirefliesTranscript] = Field(default_factory=list)
