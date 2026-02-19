"""
Runway API Client for Video Generation
=======================================

Client for Runway Gen-3 Alpha video generation.
Supports text-to-video and image-to-video.

NO OpenAI - Runway API only.
"""

import asyncio
import logging
from pathlib import Path
from typing import Any

import httpx

from src.tools.recording.config import RunwayConfig

logger = logging.getLogger(__name__)


class RunwayClient:
    """
    Client for Runway video generation API.

    Features:
    - Text-to-video generation (Gen-3 Alpha Turbo/Alpha)
    - Image-to-video generation
    - Async status polling
    - Video download
    - Exponential backoff retry

    Example:
        client = RunwayClient()

        # Text-to-video
        task = await client.generate_from_text(
            prompt="A futuristic city at sunset",
            duration=5,
        )

        # Poll until complete
        while True:
            status = await client.get_generation_status(task["id"])
            if status["status"] == "SUCCEEDED":
                break
            await asyncio.sleep(5)

        # Download video
        path = await client.download_video(task["id"], Path("/tmp/video.mp4"))
    """

    def __init__(self, config: RunwayConfig | None = None):
        """
        Initialize Runway client.

        Args:
            config: Optional configuration. If not provided, uses defaults
                   and reads from environment variables.
        """
        self.config = config or RunwayConfig()

    async def generate_from_text(
        self,
        prompt: str,
        duration: int | None = None,
        aspect_ratio: str | None = None,
        model: str | None = None,
    ) -> dict[str, Any]:
        """
        Generate video from text prompt.

        Args:
            prompt: Text description of desired video
            duration: Video duration in seconds (5 or 10)
            aspect_ratio: Aspect ratio ("16:9", "9:16", "1:1")
            model: Model to use ("gen3a_turbo" or "gen3a")

        Returns:
            Task dict with "id" and "status"

        Raises:
            ValueError: If API key missing or prompt empty
        """
        if not self.config.api_key:
            raise ValueError("Runway API key not configured")
        if not prompt or not prompt.strip():
            raise ValueError("prompt cannot be empty")

        payload = {
            "prompt": prompt.strip(),
            "model": model or self.config.default_model,
            "duration": duration or self.config.default_duration,
            "aspectRatio": aspect_ratio or self.config.default_aspect_ratio,
        }

        result = await self._call_api_with_retry(
            method="POST",
            endpoint="/text-to-video",
            payload=payload,
        )

        logger.info(f"[RUNWAY] Started text-to-video task: {result.get('id')}")
        return result

    async def generate_from_image(
        self,
        image_data: str,
        prompt: str,
        duration: int | None = None,
        model: str | None = None,
    ) -> dict[str, Any]:
        """
        Generate video from image + prompt.

        Args:
            image_data: Base64-encoded image data
            prompt: Text description of desired animation
            duration: Video duration in seconds (5 or 10)
            model: Model to use ("gen3a_turbo" or "gen3a")

        Returns:
            Task dict with "id" and "status"

        Raises:
            ValueError: If API key missing or image_data empty
        """
        if not self.config.api_key:
            raise ValueError("Runway API key not configured")
        if not image_data or not image_data.strip():
            raise ValueError("image_data cannot be empty")

        payload = {
            "image": image_data.strip(),
            "prompt": prompt.strip() if prompt else "",
            "model": model or self.config.default_model,
            "duration": duration or self.config.default_duration,
        }

        result = await self._call_api_with_retry(
            method="POST",
            endpoint="/image-to-video",
            payload=payload,
        )

        logger.info(f"[RUNWAY] Started image-to-video task: {result.get('id')}")
        return result

    async def get_generation_status(self, task_id: str) -> dict[str, Any]:
        """
        Get status of a generation task.

        Args:
            task_id: Task ID from generate_from_text or generate_from_image

        Returns:
            Task status dict with "id", "status", "progress", and optionally "output"

        Status values:
            - PENDING: Task queued
            - RUNNING: Generation in progress
            - SUCCEEDED: Complete, output available
            - FAILED: Generation failed
        """
        if not self.config.api_key:
            raise ValueError("Runway API key not configured")

        result = await self._call_api_with_retry(
            method="GET",
            endpoint=f"/tasks/{task_id}",
        )

        return result

    async def download_video(
        self,
        task_id: str,
        output_path: Path,
    ) -> str:
        """
        Download completed video to local path.

        Args:
            task_id: Task ID of completed generation
            output_path: Local path to save video

        Returns:
            Path to downloaded video file

        Raises:
            ValueError: If generation not complete
        """
        status = await self.get_generation_status(task_id)

        if status.get("status") != "SUCCEEDED":
            raise ValueError(
                f"Generation not complete. Status: {status.get('status')}, "
                f"Progress: {status.get('progress', 0)}%"
            )

        output_urls = status.get("output", [])
        if not output_urls:
            raise ValueError("No output URL in completed task")

        video_url = output_urls[0]

        # Download video
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.get(video_url)
            response.raise_for_status()

            output_path.write_bytes(response.content)

        logger.info(f"[RUNWAY] Downloaded video to: {output_path}")
        return str(output_path)

    async def wait_for_completion(
        self,
        task_id: str,
        poll_interval: int = 5,
        max_wait: int = 300,
    ) -> dict[str, Any]:
        """
        Wait for a generation task to complete.

        Args:
            task_id: Task ID to wait for
            poll_interval: Seconds between status checks
            max_wait: Maximum seconds to wait

        Returns:
            Final task status dict

        Raises:
            TimeoutError: If max_wait exceeded
            RuntimeError: If generation fails
        """
        elapsed = 0

        while elapsed < max_wait:
            status = await self.get_generation_status(task_id)
            task_status = status.get("status")

            if task_status == "SUCCEEDED":
                logger.info(f"[RUNWAY] Task {task_id} completed successfully")
                return status

            if task_status == "FAILED":
                error = status.get("error", "Unknown error")
                raise RuntimeError(f"Generation failed: {error}")

            logger.debug(
                f"[RUNWAY] Task {task_id} status: {task_status}, "
                f"progress: {status.get('progress', 0)}%"
            )

            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

        raise TimeoutError(f"Task {task_id} did not complete within {max_wait}s")

    async def _call_api_with_retry(
        self,
        method: str,
        endpoint: str,
        payload: dict | None = None,
        max_retries: int | None = None,
    ) -> dict:
        """
        Call Runway API with exponential backoff retry.

        Args:
            method: HTTP method (POST, GET)
            endpoint: API endpoint
            payload: Request body (for POST)
            max_retries: Override default max retries

        Returns:
            Response JSON as dict

        Raises:
            httpx.HTTPStatusError: If all retries fail
        """
        if max_retries is None:
            max_retries = self.config.max_retries

        url = f"{self.config.base_url}{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }

        last_error = None

        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                    if method.upper() == "POST":
                        response = await client.post(url, json=payload, headers=headers)
                    elif method.upper() == "GET":
                        response = await client.get(url, headers=headers)
                    else:
                        raise ValueError(f"Unsupported HTTP method: {method}")

                    response.raise_for_status()
                    return response.json()

            except httpx.HTTPStatusError as e:
                last_error = e
                if e.response.status_code == 429:
                    # Rate limited - exponential backoff
                    wait_time = (attempt + 1) * 5  # 5s, 10s, 15s
                    logger.warning(
                        f"[RUNWAY] Rate limited, waiting {wait_time}s "
                        f"(attempt {attempt + 1}/{max_retries})"
                    )
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    raise

            except Exception as e:
                last_error = e
                logger.error(f"[RUNWAY] API error: {e}")
                raise

        # All retries exhausted
        if last_error:
            raise last_error
        raise RuntimeError("All retries exhausted")
