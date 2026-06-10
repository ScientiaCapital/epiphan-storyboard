"""Pydantic models for Clari Copilot API responses."""

from pydantic import BaseModel, ConfigDict, Field


class ClariParticipant(BaseModel):
    """Participant in a Clari call."""

    model_config = ConfigDict(populate_by_name=True)

    name: str | None = None
    email: str | None = None
    role: str | None = None  # e.g. "host", "attendee"


class ClariTranscriptEntry(BaseModel):
    """A single utterance in a Clari transcript."""

    model_config = ConfigDict(populate_by_name=True)

    speaker_id: str = Field(..., alias="speakerId")
    speaker_name: str | None = Field(default=None, alias="speakerName")
    start: float  # seconds
    end: float  # seconds
    text: str


class ClariCall(BaseModel):
    """Clari call metadata."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    title: str | None = None
    date: str | None = None  # ISO 8601
    duration: int | None = None  # seconds
    participants: list[ClariParticipant] = Field(default_factory=list)


class ClariCallDetails(BaseModel):
    """Full call with transcript."""

    model_config = ConfigDict(populate_by_name=True)

    call: ClariCall
    transcript: list[ClariTranscriptEntry] = Field(default_factory=list)

    def transcript_to_text(self) -> str:
        """Convert transcript to plain text format.

        Returns:
            Formatted transcript as "Speaker Name: text\\n..." lines.
            Uses speaker_name, falls back to speaker_id, then a generic
            "Speaker" label — never emits a bare "None:" prefix. Utterances
            with no text are skipped so blank turns don't pollute the prompt.
        """
        lines = []
        for entry in self.transcript:
            text = (entry.text or "").strip()
            if not text:
                continue
            speaker = (entry.speaker_name or "").strip() or (
                entry.speaker_id or ""
            ).strip() or "Speaker"
            lines.append(f"{speaker}: {text}")
        return "\n".join(lines)


class ClariCallsResponse(BaseModel):
    """Paginated response from Clari calls list endpoint."""

    model_config = ConfigDict(populate_by_name=True)

    calls: list[ClariCall] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    has_more: bool = False
