"""Google Docs connector module.

Syncs documents and content from Google Docs.
"""

from src.connectors.google_docs.client import GoogleDocsAPIClient
from src.connectors.google_docs.connector import GoogleDocsConnector
from src.connectors.google_docs.schemas import GoogleDocument, GoogleDriveFile
from src.connectors.google_docs.transformer import GoogleDocsTransformer

__all__ = [
    "GoogleDocsConnector",
    "GoogleDocsAPIClient",
    "GoogleDocsTransformer",
    "GoogleDocument",
    "GoogleDriveFile",
]
