"""Google Docs REST API client.

Official API docs:
- Docs API v1: https://developers.google.com/docs/api/reference/rest
- Drive API v3: https://developers.google.com/drive/api/reference/rest/v3
"""

import logging
from typing import Any

import httpx

from src.connectors.google_docs.schemas import (
    GoogleDocument,
    GoogleDriveFile,
    GoogleDriveFilesResponse,
)

logger = logging.getLogger(__name__)


class GoogleDocsAPIClient:
    """Client for Google Docs and Drive REST APIs.

    Rate limits:
    - 300 queries per minute per user (Drive API)
    - 600 reads per minute per user (Docs API)
    - Cursor-based pagination via pageToken

    API Versions:
    - Docs API v1
    - Drive API v3
    """

    DOCS_URL = "https://docs.googleapis.com/v1"
    DRIVE_URL = "https://www.googleapis.com/drive/v3"

    def __init__(self, access_token: str):
        """Initialize Google Docs client.

        Args:
            access_token: OAuth2 access token with required scopes
        """
        self.access_token = access_token

    async def list_documents(
        self,
        page_token: str | None = None,
        page_size: int = 100,
        modified_after: str | None = None,
    ) -> tuple[list[GoogleDriveFile], str | None]:
        """List Google Docs in Drive using Drive API.

        Args:
            page_token: Pagination token from previous call
            page_size: Results per page (max 1000)
            modified_after: RFC 3339 timestamp (e.g., "2024-01-01T00:00:00Z")

        Returns:
            Tuple of (files, next_page_token)
        """
        params: dict[str, Any] = {
            "pageSize": min(page_size, 1000),
            "fields": "nextPageToken,files(id,name,mimeType,modifiedTime,createdTime,webViewLink,owners,lastModifyingUser)",
            "q": "mimeType='application/vnd.google-apps.document' and trashed=false",
        }

        # Add modified time filter if provided
        if modified_after:
            params["q"] += f" and modifiedTime > '{modified_after}'"

        if page_token:
            params["pageToken"] = page_token

        result = await self._get_drive("/files", params=params)

        # Parse response
        response = GoogleDriveFilesResponse(**result)

        # Convert to GoogleDriveFile objects
        files: list[GoogleDriveFile] = []
        for file_dict in response.files:
            try:
                files.append(GoogleDriveFile(**file_dict))
            except Exception as e:
                logger.warning(f"Failed to parse file {file_dict.get('id')}: {e}")
                continue

        next_token = response.next_page_token

        logger.info(
            f"[GOOGLE_DOCS] Listed {len(files)} documents "
            f"(page_token: {page_token} -> {next_token})"
        )
        return files, next_token

    async def get_document(self, document_id: str) -> GoogleDocument:
        """Get full document content from Docs API.

        Args:
            document_id: Google Docs document ID

        Returns:
            GoogleDocument object
        """
        result = await self._get_docs(f"/documents/{document_id}")
        return GoogleDocument(**result)

    def extract_text_from_body(self, body: dict) -> str:
        """Extract plain text from document body structure.

        Google Docs body has nested structure:
        body.content[] contains paragraphs, tables, etc.
        Each paragraph has elements[] with textRun.content

        Args:
            body: Document body dict

        Returns:
            Plain text content
        """
        parts = []

        content_elements = body.get("content", [])

        for element in content_elements:
            # Extract from paragraph
            if "paragraph" in element:
                paragraph = element["paragraph"]
                para_elements = paragraph.get("elements", [])

                para_text_parts = []
                for para_elem in para_elements:
                    if "textRun" in para_elem:
                        text_run = para_elem["textRun"]
                        content = text_run.get("content", "")
                        para_text_parts.append(content)

                para_text = "".join(para_text_parts).strip()
                if para_text:
                    parts.append(para_text)

            # Extract from table
            elif "table" in element:
                table = element["table"]
                table_rows = table.get("tableRows", [])

                for row in table_rows:
                    cells = row.get("tableCells", [])
                    row_text_parts = []

                    for cell in cells:
                        cell_content = cell.get("content", [])
                        cell_text = self.extract_text_from_body(
                            {"content": cell_content}
                        )
                        if cell_text:
                            row_text_parts.append(cell_text)

                    if row_text_parts:
                        parts.append(" | ".join(row_text_parts))

        return "\n".join(parts)

    async def _get_docs(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute GET request to Docs API.

        Args:
            endpoint: API endpoint (e.g., "/documents/{id}")
            params: Query parameters

        Returns:
            Response data dict

        Raises:
            httpx.HTTPStatusError: On API error
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.DOCS_URL}{endpoint}",
                headers=self._get_headers(),
                params=params or {},
            )

            response.raise_for_status()
            return response.json()

    async def _get_drive(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute GET request to Drive API.

        Args:
            endpoint: API endpoint (e.g., "/files")
            params: Query parameters

        Returns:
            Response data dict

        Raises:
            httpx.HTTPStatusError: On API error
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.DRIVE_URL}{endpoint}",
                headers=self._get_headers(),
                params=params or {},
            )

            response.raise_for_status()
            return response.json()

    def _get_headers(self) -> dict[str, str]:
        """Get request headers with auth.

        Returns:
            Headers dict
        """
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
