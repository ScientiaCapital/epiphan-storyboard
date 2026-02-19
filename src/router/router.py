"""AgentRouter - Core routing logic for task classification and chain execution.

This module provides the AgentRouter class which orchestrates:
1. Task classification via TaskClassifier
2. Chain selection via ChainRegistry
3. Chain execution with state management
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from time import perf_counter
from typing import TYPE_CHECKING, Any

from src.router.schemas import (
    ClassificationRequest,
    ClassificationResult,
    RouterJob,
    RouterJobStatus,
    RouterRequest,
)

if TYPE_CHECKING:
    from src.router.chains import ChainRegistry
    from src.router.classifier import TaskClassifier
    from src.router.state import RouterJobManager

logger = logging.getLogger(__name__)


class AgentRouter:
    """Routes tasks to appropriate chains based on classification.

    Orchestrates the full routing flow:
    1. Receive request
    2. Classify task (or use forced chain)
    3. Select appropriate chain
    4. Execute chain
    5. Return results

    Attributes:
        _classifier: TaskClassifier for determining task type
        _chain_registry: Registry of available chains
        _job_manager: Optional job state manager
    """

    def __init__(
        self,
        classifier: TaskClassifier,
        chain_registry: ChainRegistry,
        job_manager: RouterJobManager | None = None,
    ):
        """Initialize AgentRouter.

        Args:
            classifier: TaskClassifier instance
            chain_registry: ChainRegistry instance
            job_manager: Optional RouterJobManager for state persistence
        """
        self._classifier = classifier
        self._chain_registry = chain_registry
        self._job_manager = job_manager

    async def route_and_execute(
        self,
        request: RouterRequest,
        org_id: str,
    ) -> RouterJob:
        """Route a task to the appropriate chain and execute.

        Args:
            request: RouterRequest with query and optional params
            org_id: Organization ID

        Returns:
            RouterJob with classification and execution results
        """
        start_time = perf_counter()

        # Create job
        job = RouterJob(
            org_id=org_id,
            query=request.query,
            context=request.context or {},
            max_steps=request.max_steps,
            status=RouterJobStatus.PENDING,
        )

        try:
            # Step 1: Classify (if not forced)
            if request.force_chain:
                classification = ClassificationResult(
                    task_type=request.force_chain,
                    confidence=1.0,
                    reasoning="Forced chain selection",
                    extracted_params=request.context or {},
                    recommended_model=None,
                )
            else:
                job.status = RouterJobStatus.CLASSIFYING

                classification = await self._classifier.classify(
                    ClassificationRequest(
                        query=request.query,
                        context=str(request.context) if request.context else None,
                    )
                )

            job.classification = classification

            # Step 2: Route to chain
            job.status = RouterJobStatus.ROUTING

            chain = self._chain_registry.get(classification.task_type)
            if not chain:
                job.status = RouterJobStatus.FAILED
                job.error_message = f"No chain found for task type: {classification.task_type}"
                job.execution_time_ms = int((perf_counter() - start_time) * 1000)
                job.completed_at = datetime.now(UTC)
                return job

            # Step 3: Execute chain
            job.status = RouterJobStatus.EXECUTING

            # Merge params
            params = {**(request.context or {}), **classification.extracted_params}

            result = await chain.execute(params=params, classification=classification)
            job.chain_result = result
            job.status = RouterJobStatus.COMPLETED

            # Record timing
            job.execution_time_ms = int((perf_counter() - start_time) * 1000)
            job.completed_at = datetime.now(UTC)

            logger.info(
                f"[AGENT_ROUTER] Routed {request.query[:50]}... "
                f"to {classification.task_type.value} chain "
                f"(confidence={classification.confidence:.2f})"
            )

            return job

        except Exception as e:
            logger.error(f"[AGENT_ROUTER] Routing failed: {e}")
            job.status = RouterJobStatus.FAILED
            job.error_message = str(e)
            job.execution_time_ms = int((perf_counter() - start_time) * 1000)
            job.completed_at = datetime.now(UTC)
            return job

    def get_available_chains(self) -> list[dict[str, Any]]:
        """Get list of available chains.

        Returns:
            List of chain info dicts
        """
        return self._chain_registry.list_chains()
