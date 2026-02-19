"""Pydantic models for Gong API responses."""

from datetime import datetime

from pydantic import BaseModel, Field


class GongParty(BaseModel):
    """Participant in a Gong call."""

    id: str | None = None
    name: str | None = None
    email: str | None = None
    role: str | None = None  # "COMPANY_MEMBER" or "EXTERNAL_PARTY"


class GongCall(BaseModel):
    """Gong call metadata."""

    id: str = Field(..., alias="metaData")  # Will extract from nested structure
    title: str | None = None
    started: datetime | None = None
    duration: int | None = None  # seconds
    url: str | None = None
    parties: list[GongParty] = Field(default_factory=list)

    class Config:
        populate_by_name = True

    @classmethod
    def from_api_response(cls, data: dict) -> "GongCall":
        """Parse call from Gong API response format.

        Gong API returns:
        {
          "metaData": {"id": "123", "title": "...", "scheduled": "...", "started": "...", "duration": 3600, "url": "..."},
          "parties": [{"id": "p1", "emailAddress": "...", "name": "...", "affiliation": "COMPANY_MEMBER"}]
        }
        """
        metadata = data.get("metaData", {})
        parties_data = data.get("parties", [])

        # Parse parties
        parties = []
        for p in parties_data:
            parties.append(GongParty(
                id=p.get("id"),
                name=p.get("name"),
                email=p.get("emailAddress"),
                role=p.get("affiliation"),
            ))

        return cls(
            metaData=metadata.get("id", ""),
            title=metadata.get("title"),
            started=metadata.get("started"),
            duration=metadata.get("duration"),
            url=metadata.get("url"),
            parties=parties,
        )


class GongTranscriptSentence(BaseModel):
    """A single sentence in a Gong transcript."""

    start: int  # milliseconds
    end: int  # milliseconds
    text: str
    speaker_id: str = Field(..., alias="speakerId")

    class Config:
        populate_by_name = True


class GongTranscriptTopic(BaseModel):
    """A topic section in Gong transcript."""

    topic_name: str = Field(..., alias="topicName")
    sentences: list[GongTranscriptSentence] = Field(default_factory=list)

    class Config:
        populate_by_name = True


class GongTranscript(BaseModel):
    """Full transcript for a Gong call."""

    call_id: str = Field(..., alias="callId")
    topics: list[GongTranscriptTopic] = Field(default_factory=list)

    class Config:
        populate_by_name = True

    def to_text(self, speaker_map: dict[str, str] | None = None) -> str:
        """Convert transcript to plain text format.

        Args:
            speaker_map: Optional mapping of speaker IDs to names

        Returns:
            Formatted transcript text
        """
        lines = []
        for topic in self.topics:
            lines.append(f"\n=== {topic.topic_name} ===\n")
            for sentence in topic.sentences:
                speaker_name = (
                    speaker_map.get(sentence.speaker_id, sentence.speaker_id)
                    if speaker_map
                    else sentence.speaker_id
                )
                lines.append(f"[{speaker_name}]: {sentence.text}")
        return "\n".join(lines)


class GongCallsResponse(BaseModel):
    """Response from Gong calls list endpoint."""

    calls: list[dict] = Field(default_factory=list)  # Raw call data
    cursor: str | None = Field(default=None, alias="records")  # Nested cursor
    total_records: int = Field(default=0, alias="totalRecords")

    class Config:
        populate_by_name = True

    @classmethod
    def from_api_response(cls, data: dict) -> "GongCallsResponse":
        """Parse from Gong API response.

        Gong returns:
        {
          "calls": [...],
          "records": {
            "totalRecords": 100,
            "currentPageSize": 50,
            "currentPageNumber": 1,
            "cursor": "next-cursor-token"
          }
        }
        """
        calls = data.get("calls", [])
        records = data.get("records", {})

        return cls(
            calls=calls,
            records=records.get("cursor"),
            totalRecords=records.get("totalRecords", 0),
        )
