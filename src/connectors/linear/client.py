"""Linear GraphQL API client.

Official API docs: https://developers.linear.app/docs/graphql/working-with-the-graphql-api
"""

import logging
from datetime import datetime
from typing import Any

import httpx

from src.connectors.linear.schemas import (
    LinearIssue,
    LinearIssuesResponse,
    LinearProject,
    LinearProjectsResponse,
)

logger = logging.getLogger(__name__)


class LinearGraphQLClient:
    """Client for Linear GraphQL API.

    Rate limits:
    - 1,500 requests per hour
    - 250,000 complexity per hour
    - Cursor-based pagination
    """

    ENDPOINT = "https://api.linear.app/graphql"

    def __init__(self, access_token: str):
        """Initialize Linear client.

        Args:
            access_token: Linear API key or OAuth access token
        """
        self.access_token = access_token

    async def get_issues(
        self,
        updated_after: datetime | None = None,
        cursor: str | None = None,
        limit: int = 50,
    ) -> tuple[list[LinearIssue], str | None]:
        """Fetch issues with pagination.

        Args:
            updated_after: Only fetch issues updated after this datetime
            cursor: Pagination cursor from previous call
            limit: Max issues per page (default 50, max 250)

        Returns:
            Tuple of (issues, next_cursor)
        """
        query = """
        query Issues($after: String, $first: Int, $filter: IssueFilter) {
            issues(first: $first, after: $after, filter: $filter) {
                pageInfo {
                    hasNextPage
                    endCursor
                }
                nodes {
                    id
                    identifier
                    title
                    description
                    state {
                        id
                        name
                        type
                    }
                    priority
                    labels {
                        nodes {
                            id
                            name
                            color
                        }
                    }
                    project {
                        id
                        name
                        description
                        state
                        url
                        createdAt
                        updatedAt
                    }
                    assignee {
                        id
                        name
                        email
                    }
                    creator {
                        id
                        name
                        email
                    }
                    url
                    createdAt
                    updatedAt
                    comments {
                        nodes {
                            id
                            body
                            user {
                                id
                                name
                            }
                            createdAt
                            updatedAt
                        }
                    }
                }
            }
        }
        """

        variables: dict[str, Any] = {
            "first": min(limit, 250),  # Linear max is 250
            "after": cursor,
        }

        # Build filter
        filter_dict: dict[str, Any] = {}
        if updated_after:
            filter_dict["updatedAt"] = {"gte": updated_after.isoformat()}

        if filter_dict:
            variables["filter"] = filter_dict

        result = await self._execute_query(query, variables)
        issues_data = result.get("data", {}).get("issues", {})

        # Parse response
        response = LinearIssuesResponse(**issues_data)

        # Convert nodes to LinearIssue objects
        issues = []
        for node in response.nodes:
            try:
                # Transform nested structures
                if "labels" in node and "nodes" in node["labels"]:
                    node["labels"] = node["labels"]["nodes"]
                if "comments" in node and "nodes" in node["comments"]:
                    node["comments"] = node["comments"]["nodes"]

                issue = LinearIssue(**node)
                issues.append(issue)
            except Exception as e:
                logger.warning(f"Failed to parse issue {node.get('id')}: {e}")
                continue

        next_cursor = response.page_info.end_cursor if response.page_info.has_next_page else None

        logger.info(f"[LINEAR] Fetched {len(issues)} issues (cursor: {cursor} -> {next_cursor})")
        return issues, next_cursor

    async def get_projects(
        self,
        cursor: str | None = None,
        limit: int = 50,
    ) -> tuple[list[LinearProject], str | None]:
        """Fetch projects with pagination.

        Args:
            cursor: Pagination cursor from previous call
            limit: Max projects per page (default 50, max 250)

        Returns:
            Tuple of (projects, next_cursor)
        """
        query = """
        query Projects($after: String, $first: Int) {
            projects(first: $first, after: $after) {
                pageInfo {
                    hasNextPage
                    endCursor
                }
                nodes {
                    id
                    name
                    description
                    state
                    url
                    createdAt
                    updatedAt
                }
            }
        }
        """

        variables = {
            "first": min(limit, 250),
            "after": cursor,
        }

        result = await self._execute_query(query, variables)
        projects_data = result.get("data", {}).get("projects", {})

        # Parse response
        response = LinearProjectsResponse(**projects_data)

        # Convert nodes to LinearProject objects
        projects = []
        for node in response.nodes:
            try:
                project = LinearProject(**node)
                projects.append(project)
            except Exception as e:
                logger.warning(f"Failed to parse project {node.get('id')}: {e}")
                continue

        next_cursor = response.page_info.end_cursor if response.page_info.has_next_page else None

        logger.info(f"[LINEAR] Fetched {len(projects)} projects (cursor: {cursor} -> {next_cursor})")
        return projects, next_cursor

    async def get_viewer(self) -> dict[str, Any]:
        """Get current authenticated user (for testing connection).

        Returns:
            User data dict

        Raises:
            httpx.HTTPStatusError: On API error
        """
        query = """
        query Viewer {
            viewer {
                id
                name
                email
            }
        }
        """

        result = await self._execute_query(query, {})
        return result.get("data", {}).get("viewer", {})

    async def _execute_query(
        self,
        query: str,
        variables: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute a GraphQL query.

        Args:
            query: GraphQL query string
            variables: Query variables

        Returns:
            Response data dict

        Raises:
            httpx.HTTPStatusError: On API error
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                self.ENDPOINT,
                headers={
                    "Authorization": self.access_token,
                    "Content-Type": "application/json",
                },
                json={
                    "query": query,
                    "variables": variables,
                },
            )

            response.raise_for_status()
            data = response.json()

            # Check for GraphQL errors
            if "errors" in data:
                error_msg = "; ".join(err.get("message", str(err)) for err in data["errors"])
                raise ValueError(f"GraphQL errors: {error_msg}")

            return data
