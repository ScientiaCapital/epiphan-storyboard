"""Tests for Google Docs API client."""

import pytest
import respx
from httpx import Response

from src.connectors.google_docs.client import GoogleDocsAPIClient
from src.connectors.google_docs.schemas import GoogleDocument, GoogleDriveFile


@pytest.fixture
def mock_drive_files_response():
    """Mock response from Drive API files.list."""
    return {
        "kind": "drive#fileList",
        "nextPageToken": "next_token_123",
        "incompleteSearch": False,
        "files": [
            {
                "id": "doc_1",
                "name": "Product Roadmap 2025",
                "mimeType": "application/vnd.google-apps.document",
                "modifiedTime": "2025-01-15T10:30:00Z",
                "createdTime": "2025-01-01T09:00:00Z",
                "webViewLink": "https://docs.google.com/document/d/doc_1/edit",
                "owners": [{"displayName": "John Doe", "emailAddress": "john@example.com"}],
                "lastModifyingUser": {
                    "displayName": "Jane Smith",
                    "emailAddress": "jane@example.com",
                },
            },
            {
                "id": "doc_2",
                "name": "Feature Spec: AI Assistant",
                "mimeType": "application/vnd.google-apps.document",
                "modifiedTime": "2025-01-14T14:20:00Z",
                "createdTime": "2025-01-10T11:00:00Z",
                "webViewLink": "https://docs.google.com/document/d/doc_2/edit",
            },
        ],
    }


@pytest.fixture
def mock_document_response():
    """Mock response from Docs API documents.get."""
    return {
        "documentId": "doc_1",
        "title": "Product Roadmap 2025",
        "revisionId": "rev_123",
        "body": {
            "content": [
                {
                    "startIndex": 1,
                    "endIndex": 50,
                    "paragraph": {
                        "elements": [
                            {
                                "startIndex": 1,
                                "endIndex": 20,
                                "textRun": {"content": "Product Roadmap 2025\n"},
                            }
                        ],
                        "paragraphStyle": {"namedStyleType": "HEADING_1"},
                    },
                },
                {
                    "startIndex": 50,
                    "endIndex": 150,
                    "paragraph": {
                        "elements": [
                            {
                                "startIndex": 50,
                                "endIndex": 150,
                                "textRun": {
                                    "content": "Q1 Goals: Launch AI assistant feature with 90% accuracy.\n"
                                },
                            }
                        ],
                    },
                },
                {
                    "startIndex": 150,
                    "endIndex": 250,
                    "table": {
                        "rows": 2,
                        "columns": 2,
                        "tableRows": [
                            {
                                "tableCells": [
                                    {
                                        "content": [
                                            {
                                                "paragraph": {
                                                    "elements": [
                                                        {
                                                            "textRun": {
                                                                "content": "Feature"
                                                            }
                                                        }
                                                    ]
                                                }
                                            }
                                        ]
                                    },
                                    {
                                        "content": [
                                            {
                                                "paragraph": {
                                                    "elements": [
                                                        {
                                                            "textRun": {
                                                                "content": "Status"
                                                            }
                                                        }
                                                    ]
                                                }
                                            }
                                        ]
                                    },
                                ]
                            },
                            {
                                "tableCells": [
                                    {
                                        "content": [
                                            {
                                                "paragraph": {
                                                    "elements": [
                                                        {
                                                            "textRun": {
                                                                "content": "AI Assistant"
                                                            }
                                                        }
                                                    ]
                                                }
                                            }
                                        ]
                                    },
                                    {
                                        "content": [
                                            {
                                                "paragraph": {
                                                    "elements": [
                                                        {
                                                            "textRun": {
                                                                "content": "In Progress"
                                                            }
                                                        }
                                                    ]
                                                }
                                            }
                                        ]
                                    },
                                ]
                            },
                        ],
                    },
                },
            ]
        },
    }


@pytest.mark.asyncio
@respx.mock
async def test_list_documents(mock_drive_files_response):
    """Test listing Google Docs from Drive API."""
    # Mock Drive API
    route = respx.get("https://www.googleapis.com/drive/v3/files").mock(
        return_value=Response(200, json=mock_drive_files_response)
    )

    client = GoogleDocsAPIClient(access_token="test_token")

    files, next_token = await client.list_documents(page_size=100)

    # Verify request
    assert route.called
    request = route.calls.last.request
    assert request.headers["Authorization"] == "Bearer test_token"
    assert "pageSize=100" in str(request.url)
    # URL-encoded version of mimeType='application/vnd.google-apps.document'
    assert "mimeType" in str(request.url)
    assert "google-apps.document" in str(request.url)

    # Verify response
    assert len(files) == 2
    assert next_token == "next_token_123"

    # Verify first file
    assert isinstance(files[0], GoogleDriveFile)
    assert files[0].id == "doc_1"
    assert files[0].name == "Product Roadmap 2025"
    assert files[0].mime_type == "application/vnd.google-apps.document"
    assert files[0].web_view_link == "https://docs.google.com/document/d/doc_1/edit"


@pytest.mark.asyncio
@respx.mock
async def test_list_documents_with_modified_after(mock_drive_files_response):
    """Test listing documents with modified_after filter."""
    route = respx.get("https://www.googleapis.com/drive/v3/files").mock(
        return_value=Response(200, json=mock_drive_files_response)
    )

    client = GoogleDocsAPIClient(access_token="test_token")

    await client.list_documents(
        page_size=50,
        modified_after="2025-01-01T00:00:00Z",
    )

    # Verify request includes modifiedTime filter
    request = route.calls.last.request
    assert "pageSize=50" in str(request.url)
    # URL-encoded version of modifiedTime > '2025-01-01T00:00:00Z'
    assert "modifiedTime" in str(request.url)
    assert "2025-01-01" in str(request.url)


@pytest.mark.asyncio
@respx.mock
async def test_list_documents_pagination(mock_drive_files_response):
    """Test pagination with page_token."""
    route = respx.get("https://www.googleapis.com/drive/v3/files").mock(
        return_value=Response(200, json=mock_drive_files_response)
    )

    client = GoogleDocsAPIClient(access_token="test_token")

    await client.list_documents(page_token="prev_token_456")

    # Verify page token in request
    request = route.calls.last.request
    assert "pageToken=prev_token_456" in str(request.url)


@pytest.mark.asyncio
@respx.mock
async def test_get_document(mock_document_response):
    """Test fetching full document content."""
    route = respx.get("https://docs.googleapis.com/v1/documents/doc_1").mock(
        return_value=Response(200, json=mock_document_response)
    )

    client = GoogleDocsAPIClient(access_token="test_token")

    document = await client.get_document("doc_1")

    # Verify request
    assert route.called
    request = route.calls.last.request
    assert request.headers["Authorization"] == "Bearer test_token"

    # Verify response
    assert isinstance(document, GoogleDocument)
    assert document.document_id == "doc_1"
    assert document.title == "Product Roadmap 2025"
    assert document.revision_id == "rev_123"
    assert len(document.body.content) == 3


def test_extract_text_from_body(mock_document_response):
    """Test extracting plain text from document body."""
    client = GoogleDocsAPIClient(access_token="test_token")

    body = mock_document_response["body"]
    text = client.extract_text_from_body(body)

    # Verify extracted text
    assert "Product Roadmap 2025" in text
    assert "Q1 Goals: Launch AI assistant feature with 90% accuracy." in text
    assert "Feature | Status" in text
    assert "AI Assistant | In Progress" in text


def test_extract_text_from_empty_body():
    """Test extracting text from empty body."""
    client = GoogleDocsAPIClient(access_token="test_token")

    body = {"content": []}
    text = client.extract_text_from_body(body)

    assert text == ""


def test_extract_text_from_nested_table():
    """Test extracting text from table structure."""
    client = GoogleDocsAPIClient(access_token="test_token")

    body = {
        "content": [
            {
                "table": {
                    "tableRows": [
                        {
                            "tableCells": [
                                {
                                    "content": [
                                        {
                                            "paragraph": {
                                                "elements": [
                                                    {
                                                        "textRun": {
                                                            "content": "Cell 1"
                                                        }
                                                    }
                                                ]
                                            }
                                        }
                                    ]
                                },
                                {
                                    "content": [
                                        {
                                            "paragraph": {
                                                "elements": [
                                                    {
                                                        "textRun": {
                                                            "content": "Cell 2"
                                                        }
                                                    }
                                                ]
                                            }
                                        }
                                    ]
                                },
                            ]
                        }
                    ]
                }
            }
        ]
    }

    text = client.extract_text_from_body(body)

    assert "Cell 1 | Cell 2" in text


@pytest.mark.asyncio
@respx.mock
async def test_api_error_handling():
    """Test handling of API errors."""
    # Mock 401 Unauthorized
    respx.get("https://www.googleapis.com/drive/v3/files").mock(
        return_value=Response(401, json={"error": {"message": "Invalid credentials"}})
    )

    client = GoogleDocsAPIClient(access_token="invalid_token")

    with pytest.raises(Exception):
        await client.list_documents()


@pytest.mark.asyncio
@respx.mock
async def test_list_documents_no_next_page(mock_drive_files_response):
    """Test list_documents when there's no next page."""
    # Remove nextPageToken
    response = mock_drive_files_response.copy()
    response["nextPageToken"] = None

    respx.get("https://www.googleapis.com/drive/v3/files").mock(
        return_value=Response(200, json=response)
    )

    client = GoogleDocsAPIClient(access_token="test_token")

    files, next_token = await client.list_documents()

    assert len(files) == 2
    assert next_token is None
