"""Transform Linear data to KnowledgeEntry objects."""

import logging

from src.connectors.linear.schemas import LinearIssue, LinearProject
from src.knowledge.base import (
    KnowledgeEntry,
    KnowledgeSource,
    SourceType,
)
from src.knowledge.extraction import KnowledgeExtractor

logger = logging.getLogger(__name__)


class LinearTransformer:
    """Transform Linear issues and projects into knowledge entries."""

    def __init__(self):
        self.extractor = KnowledgeExtractor()

    async def transform_issue(
        self,
        issue: LinearIssue,
        org_id: str,
    ) -> tuple[KnowledgeSource, list[KnowledgeEntry]]:
        """Transform a Linear issue into knowledge entries.

        Bug reports → pain_point
        Feature requests → feature, use_case
        Tasks → use_case (context about how product is used)

        Args:
            issue: Linear issue
            org_id: Organization ID for source

        Returns:
            Tuple of (source, entries)
        """
        # Create knowledge source
        source = KnowledgeSource(
            source_type=SourceType.MANUAL_ENTRY,  # Use existing enum value
            external_id=issue.id,
            external_url=issue.url,
            source_title=f"Linear {issue.identifier}: {issue.title}",
            source_date=issue.created_at,
            participant_names=[
                issue.creator.name if issue.creator else "Unknown",
            ],
            raw_content=issue.to_text(),
        )

        # Determine extraction context based on issue state and labels
        context_parts = [f"Linear issue {issue.identifier}"]

        if issue.state and issue.state.type:
            context_parts.append(f"State: {issue.state.type}")

        if issue.labels:
            label_names = [label.name.lower() for label in issue.labels]
            context_parts.append(f"Labels: {', '.join(label_names)}")

            # Hint knowledge types based on labels
            if any(label in ["bug", "issue", "problem"] for label in label_names):
                context_parts.append("Extract as pain points")
            elif any(
                label in ["feature", "enhancement", "request"] for label in label_names
            ):
                context_parts.append("Extract as features and use cases")

        if issue.project:
            context_parts.append(f"Project: {issue.project.name}")

        additional_context = " | ".join(context_parts)

        # Extract knowledge using LLM
        extraction_result = await self.extractor.extract(
            source=source,
            additional_context=additional_context,
        )

        return source, extraction_result.entries

    async def transform_project(
        self,
        project: LinearProject,
        org_id: str,
    ) -> tuple[KnowledgeSource, list[KnowledgeEntry]]:
        """Transform a Linear project into knowledge entries.

        Projects often describe features, use cases, or product areas.

        Args:
            project: Linear project
            org_id: Organization ID for source

        Returns:
            Tuple of (source, entries)
        """
        # Create knowledge source
        source = KnowledgeSource(
            source_type=SourceType.MANUAL_ENTRY,
            external_id=project.id,
            external_url=project.url,
            source_title=f"Linear Project: {project.name}",
            source_date=project.created_at,
            raw_content=self._project_to_text(project),
        )

        additional_context = (
            f"Linear project in {project.state} state | "
            "Extract features, use cases, and product areas"
        )

        # Extract knowledge using LLM
        extraction_result = await self.extractor.extract(
            source=source,
            additional_context=additional_context,
        )

        return source, extraction_result.entries

    def _project_to_text(self, project: LinearProject) -> str:
        """Convert project to plain text."""
        parts = [
            f"Project: {project.name}",
            f"State: {project.state}",
        ]

        if project.description:
            parts.append(f"Description: {project.description}")

        return "\n".join(parts)
