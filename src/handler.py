import os
import runpod
from utils import JobInput, create_error_response
from engine import vLLMEngine, OpenAIvLLMEngine
from metering import get_meter, RequestTimer
from tracing import get_logger, setup_structured_logging, ErrorCodes
from health import get_health_checker, handle_health_request
from auth import get_authenticator
from metrics import get_metrics_collector, handle_metrics_request
from cache import get_cache, handle_cache_stats_request
from priority import get_priority_queue, handle_queue_stats_request, PriorityLevel
from dlq import handle_dlq_stats_request, handle_dlq_list_request, handle_dlq_retry_request
from validation import validate_config
from shutdown import get_shutdown_manager, handle_shutdown_status_request
from timeout import get_timeout_manager
from audit import get_audit_logger, handle_audit_stats_request, handle_audit_events_request, handle_audit_verify_request, AuditEventType, AuditSeverity
from circuit_breaker import get_circuit_manager, get_retry_handler, handle_circuit_stats_request, handle_circuit_reset_request, handle_retry_stats_request, CircuitOpenError
from quotas import get_quota_manager, handle_quota_stats_request, handle_quota_usage_request
from router import get_router, handle_router_stats_request, handle_router_backends_request, handle_router_experiments_request, handle_router_weight_request
from input_validation import get_input_validator, handle_validation_stats_request
from deduplication import get_dedup_manager, handle_dedup_stats_request, handle_dedup_clear_request
from webhooks import get_webhook_manager, handle_webhooks_stats_request, handle_webhooks_list_request, handle_webhooks_subscribe_request, handle_webhooks_unsubscribe_request, EventType
from providers import get_provider_manager, handle_providers_list_request, handle_provider_health_request
from cost_optimizer import get_cost_optimizer, handle_optimizer_stats_request, handle_optimizer_recommend_request, handle_optimizer_report_request
from model_catalog import get_model_catalog, handle_models_list_request, handle_models_retrieve_request, handle_models_compare_request, handle_models_recommend_request

# Initialize structured logging
setup_structured_logging()
logger = get_logger()

# Validate configuration before initializing engines
logger.info("Validating configuration...")
if not validate_config():
    logger.error("Configuration validation failed - some features may not work correctly")

# Initialize engines
vllm_engine = vLLMEngine()
OpenAIvLLMEngine = OpenAIvLLMEngine(vllm_engine)

# Initialize enterprise features
health_checker = get_health_checker()
health_checker.set_engine(vllm_engine)

metrics_collector = get_metrics_collector()
metrics_collector.set_model_info(vllm_engine.engine_args.model)

authenticator = get_authenticator()
cache = get_cache()
priority_queue = get_priority_queue()
shutdown_manager = get_shutdown_manager()
timeout_manager = get_timeout_manager()
audit_logger = get_audit_logger()
circuit_manager = get_circuit_manager()
retry_handler = get_retry_handler()
quota_manager = get_quota_manager()
router = get_router()
input_validator = get_input_validator()
dedup_manager = get_dedup_manager()
webhook_manager = get_webhook_manager()
provider_manager = get_provider_manager()
cost_optimizer = get_cost_optimizer()
model_catalog = get_model_catalog()

# Add local model to catalog
model_catalog.add_local_model(
    vllm_engine.engine_args.model,
    context_window=getattr(vllm_engine.engine_args, 'max_model_len', 4096)
)

logger.info("Worker initialized",
    model=vllm_engine.engine_args.model,
    auth_enabled=authenticator.enabled,
    cache_enabled=cache.enabled,
    metrics_enabled=metrics_collector.enabled,
    priority_queue_enabled=priority_queue.enabled
)

async def handler(job):
    job_input = JobInput(job["input"])

    # Handle special routes first (no auth/metering for these)
    if job_input.openai_route == "/health":
        yield handle_health_request("/health")
        return
    elif job_input.openai_route == "/ready":
        yield handle_health_request("/ready")
        return
    elif job_input.openai_route == "/model":
        yield handle_health_request("/model")
        return
    elif job_input.openai_route == "/metrics":
        yield {"metrics": handle_metrics_request()}
        return
    elif job_input.openai_route == "/cache/stats":
        yield handle_cache_stats_request()
        return
    elif job_input.openai_route == "/queue/stats":
        yield handle_queue_stats_request()
        return
    elif job_input.openai_route == "/dlq/stats":
        yield handle_dlq_stats_request()
        return
    elif job_input.openai_route == "/dlq/list":
        limit = 100
        if job_input.openai_input:
            limit = job_input.openai_input.get("limit", 100)
        yield handle_dlq_list_request(limit)
        return
    elif job_input.openai_route == "/dlq/retry":
        message_id = None
        if job_input.openai_input:
            message_id = job_input.openai_input.get("message_id")
        result = await handle_dlq_retry_request(message_id)
        yield result
        return
    elif job_input.openai_route == "/shutdown/status":
        yield handle_shutdown_status_request()
        return
    elif job_input.openai_route == "/audit/stats":
        yield handle_audit_stats_request()
        return
    elif job_input.openai_route == "/audit/events":
        params = job_input.openai_input or {}
        yield handle_audit_events_request(
            limit=params.get("limit", 100),
            event_type=params.get("event_type"),
            severity=params.get("severity"),
            user_id=params.get("user_id"),
            request_id=params.get("request_id"),
        )
        return
    elif job_input.openai_route == "/audit/verify":
        yield handle_audit_verify_request()
        return
    elif job_input.openai_route == "/circuit/stats":
        yield handle_circuit_stats_request()
        return
    elif job_input.openai_route == "/circuit/reset":
        name = None
        if job_input.openai_input:
            name = job_input.openai_input.get("name")
        result = await handle_circuit_reset_request(name)
        yield result
        return
    elif job_input.openai_route == "/retry/stats":
        yield handle_retry_stats_request()
        return
    elif job_input.openai_route == "/quota/stats":
        yield handle_quota_stats_request()
        return
    elif job_input.openai_route == "/quota/usage":
        params = job_input.openai_input or {}
        result = await handle_quota_usage_request(
            user_id=params.get("user_id", ""),
            organization_id=params.get("organization_id"),
        )
        yield result
        return
    elif job_input.openai_route == "/router/stats":
        yield handle_router_stats_request()
        return
    elif job_input.openai_route == "/router/backends":
        yield handle_router_backends_request()
        return
    elif job_input.openai_route == "/router/experiments":
        yield handle_router_experiments_request()
        return
    elif job_input.openai_route == "/router/weight":
        params = job_input.openai_input or {}
        result = await handle_router_weight_request(
            backend=params.get("backend", ""),
            weight=params.get("weight", 100),
        )
        yield result
        return
    elif job_input.openai_route == "/validation/stats":
        yield handle_validation_stats_request()
        return
    elif job_input.openai_route == "/dedup/stats":
        yield handle_dedup_stats_request()
        return
    elif job_input.openai_route == "/dedup/clear":
        result = await handle_dedup_clear_request()
        yield result
        return
    elif job_input.openai_route == "/webhooks/stats":
        yield handle_webhooks_stats_request()
        return
    elif job_input.openai_route == "/webhooks/list":
        yield handle_webhooks_list_request()
        return
    elif job_input.openai_route == "/webhooks/subscribe":
        params = job_input.openai_input or {}
        result = await handle_webhooks_subscribe_request(
            url=params.get("url", ""),
            events=params.get("events", []),
            secret=params.get("secret"),
            user_ids=params.get("user_ids"),
            tiers=params.get("tiers"),
            models=params.get("models"),
        )
        yield result
        return
    elif job_input.openai_route == "/webhooks/unsubscribe":
        params = job_input.openai_input or {}
        result = await handle_webhooks_unsubscribe_request(
            subscription_id=params.get("subscription_id", ""),
        )
        yield result
        return
    elif job_input.openai_route == "/providers/list":
        yield handle_providers_list_request()
        return
    elif job_input.openai_route == "/providers/health":
        result = await handle_provider_health_request()
        yield result
        return
    elif job_input.openai_route == "/optimizer/stats":
        yield handle_optimizer_stats_request()
        return
    elif job_input.openai_route == "/optimizer/recommend":
        params = job_input.openai_input or {}
        yield handle_optimizer_recommend_request(
            messages=params.get("messages", []),
            strategy=params.get("strategy"),
            max_tokens=params.get("max_tokens"),
            required_features=params.get("required_features"),
            excluded_providers=params.get("excluded_providers"),
            min_quality=params.get("min_quality"),
        )
        return
    elif job_input.openai_route == "/optimizer/report":
        yield handle_optimizer_report_request()
        return
    elif job_input.openai_route == "/v1/models":
        params = job_input.openai_input or {}
        yield handle_models_list_request(
            provider=params.get("provider"),
            quality_tier=params.get("quality_tier"),
        )
        return
    elif job_input.openai_route and job_input.openai_route.startswith("/v1/models/"):
        model_id = job_input.openai_route.split("/v1/models/")[1]
        yield handle_models_retrieve_request(model_id)
        return
    elif job_input.openai_route == "/models/compare":
        params = job_input.openai_input or {}
        yield handle_models_compare_request(params.get("model_ids", []))
        return
    elif job_input.openai_route == "/models/recommend":
        params = job_input.openai_input or {}
        yield handle_models_recommend_request(params.get("task_type", "general"))
        return

    # Authentication check
    api_key = None
    if job_input.openai_input:
        # Check for API key in headers or input
        api_key = job_input.openai_input.get("api_key") or job_input.openai_input.get("authorization")

    auth_result = authenticator.authenticate(api_key)
    if not auth_result.authenticated:
        # Log auth failure
        await audit_logger.log_auth_failure(
            reason=auth_result.error_message or "Authentication failed",
            api_key_id=auth_result.key_info.key_id if auth_result.key_info else None,
            request_id=job_input.request_id,
        )
        yield create_error_response(
            auth_result.error_message or "Authentication failed",
            err_type=auth_result.error_code or "AuthenticationError"
        ).model_dump()
        return

    # Check if shutting down
    if not await shutdown_manager.register_request(job_input.request_id):
        yield create_error_response(
            "Service is shutting down, not accepting new requests",
            err_type="ServiceUnavailable"
        ).model_dump()
        return

    # Log auth success
    if auth_result.key_info:
        await audit_logger.log_auth_success(
            user_id=auth_result.key_info.user_id,
            api_key_id=auth_result.key_info.key_id,
            organization_id=auth_result.key_info.organization_id,
            request_id=job_input.request_id,
        )

    # Check quota before processing
    user_id = auth_result.key_info.user_id if auth_result.key_info else "anonymous"
    org_id = auth_result.key_info.organization_id if auth_result.key_info else None
    user_tier = auth_result.key_info.tier if auth_result.key_info else "free"

    quota_result = await quota_manager.check_quota(
        user_id=user_id,
        organization_id=org_id,
        tier=user_tier,
    )

    if not quota_result.allowed:
        yield create_error_response(
            quota_result.reason or "Quota exceeded",
            err_type="QuotaExceeded"
        ).model_dump()
        await shutdown_manager.complete_request(job_input.request_id)
        return

    if quota_result.warning:
        logger.warning("Quota warning", request_id=job_input.request_id, warning=quota_result.warning)

    engine = OpenAIvLLMEngine if job_input.openai_route else vllm_engine

    # Initialize metering and tracing
    meter = get_meter()
    timer = RequestTimer().start()

    # Set correlation ID for request tracing
    logger.set_correlation_id(job_input.request_id)

    # Record metrics start
    metrics_collector.record_request_start()

    # Determine model name early for logging
    model_name = ""
    messages = None
    sampling_params = {}

    if job_input.openai_route and job_input.openai_input:
        model_name = job_input.openai_input.get("model", "")
        messages = job_input.openai_input.get("messages") or job_input.openai_input.get("prompt")
        sampling_params = {
            "temperature": job_input.openai_input.get("temperature", 1.0),
            "top_p": job_input.openai_input.get("top_p", 1.0),
            "max_tokens": job_input.openai_input.get("max_tokens"),
            "seed": job_input.openai_input.get("seed"),
        }
    else:
        messages = job_input.llm_input

    if not model_name:
        model_name = os.getenv("OPENAI_SERVED_MODEL_NAME_OVERRIDE", "") or vllm_engine.engine_args.model

    # Validate input
    validation_result = input_validator.validate(
        messages=messages,
        max_tokens=sampling_params.get("max_tokens"),
        route=job_input.openai_route,
    )

    if not validation_result.valid:
        yield create_error_response(
            "; ".join(validation_result.errors),
            err_type="ValidationError"
        ).model_dump()
        await shutdown_manager.complete_request(job_input.request_id)
        return

    # Use sanitized input if PII was redacted
    if validation_result.pii_redacted:
        messages = validation_result.sanitized_input

    # Check for duplicate request
    idempotency_key = None
    if job_input.openai_input:
        idempotency_key = job_input.openai_input.get("idempotency_key")

    is_duplicate, cached_response, wait_key = await dedup_manager.check_duplicate(
        request_id=job_input.request_id,
        idempotency_key=idempotency_key,
        messages=messages,
        sampling_params=sampling_params,
        user_id=user_id,
    )

    if is_duplicate:
        if cached_response:
            logger.info("Duplicate request - returning cached response", request_id=job_input.request_id)
            yield cached_response
            await shutdown_manager.complete_request(job_input.request_id)
            return
        elif wait_key:
            # Wait for in-progress request
            cached_response = await dedup_manager.wait_for_duplicate(wait_key)
            if cached_response:
                yield cached_response
                await shutdown_manager.complete_request(job_input.request_id)
                return

    # Determine priority based on user tier
    priority = PriorityLevel.from_tier(user_tier)

    # Log request start
    logger.request_start(
        request_id=job_input.request_id,
        route=job_input.openai_route or "native",
        model=model_name,
        stream=job_input.stream,
        user_id=auth_result.key_info.user_id if auth_result.key_info else None,
        tier=user_tier,
        priority=priority.value
    )

    # Audit log request start
    await audit_logger.log_request_start(
        request_id=job_input.request_id,
        user_id=auth_result.key_info.user_id if auth_result.key_info else None,
        api_key_id=auth_result.key_info.key_id if auth_result.key_info else None,
        model=model_name,
        route=job_input.openai_route or "native",
    )

    # Check cache first
    cached_response, cache_hit = cache.get(
        model=model_name,
        messages=messages,
        sampling_params=sampling_params,
        stream=job_input.stream
    )

    if cache_hit:
        logger.info("Cache hit", request_id=job_input.request_id)
        timer.stop()

        # Return cached response
        yield cached_response

        # Record metrics for cache hit
        metrics_collector.record_request_complete(
            latency_ms=timer.latency_ms,
            time_to_first_token_ms=0,
            input_tokens=0,
            output_tokens=0,
            success=True
        )
        return

    # Track usage metrics
    total_input_tokens = 0
    total_output_tokens = 0
    is_first_batch = True
    success = True
    error_message = None
    error_code = None
    all_batches = []  # Collect for caching

    try:
        results_generator = engine.generate(job_input)
        async for batch in results_generator:
            # Mark first token time
            if is_first_batch:
                timer.mark_first_token()
                is_first_batch = False

            # Extract token counts from batch
            if isinstance(batch, dict):
                if "error" in batch:
                    success = False
                    error_message = batch.get("error", {}).get("message", "Unknown error")
                    error_code = ErrorCodes.categorize_error(error_message)
                elif "usage" in batch:
                    usage = batch["usage"]
                    total_input_tokens = usage.get("input", 0)
                    total_output_tokens = usage.get("output", 0)

            # Collect batches for caching (non-streaming only)
            if not job_input.stream:
                all_batches.append(batch)

            yield batch

    except Exception as e:
        success = False
        error_message = str(e)
        error_code = ErrorCodes.categorize_error(error_message)
        logger.request_error(
            request_id=job_input.request_id,
            error_code=error_code,
            error_message=error_message
        )
        # Audit log error
        await audit_logger.log_request_error(
            request_id=job_input.request_id,
            error_code=error_code,
            error_message=error_message,
            user_id=auth_result.key_info.user_id if auth_result.key_info else None,
            api_key_id=auth_result.key_info.key_id if auth_result.key_info else None,
            model=model_name,
        )
        raise
    finally:
        # Record usage after request completes
        timer.stop()

        # Determine model type
        model_type = "completion"
        if job_input.openai_route:
            model_type = "chat" if "chat" in job_input.openai_route else "completion"

        # Log request completion
        logger.request_complete(
            request_id=job_input.request_id,
            latency_ms=timer.latency_ms,
            input_tokens=total_input_tokens,
            output_tokens=total_output_tokens,
            success=success,
            time_to_first_token_ms=timer.time_to_first_token_ms,
            model=model_name,
            error_code=error_code,
            user_id=auth_result.key_info.user_id if auth_result.key_info else None
        )

        # Record metrics
        metrics_collector.record_request_complete(
            latency_ms=timer.latency_ms,
            time_to_first_token_ms=timer.time_to_first_token_ms,
            input_tokens=total_input_tokens,
            output_tokens=total_output_tokens,
            success=success,
            error_code=error_code
        )

        # Create and record usage for billing
        record = meter.create_record(
            request_id=job_input.request_id,
            model=model_name,
            model_type=model_type,
            input_tokens=total_input_tokens,
            output_tokens=total_output_tokens,
            latency_ms=timer.latency_ms,
            time_to_first_token_ms=timer.time_to_first_token_ms,
            stream=job_input.stream,
            success=success,
            error_code=error_code,
            error_message=error_message,
            user_id=auth_result.key_info.user_id if auth_result.key_info else None,
            organization_id=auth_result.key_info.organization_id if auth_result.key_info else None,
            api_key_id=auth_result.key_info.key_id if auth_result.key_info else None,
        )

        await meter.record_usage(record)

        # Record auth usage for rate limiting
        if auth_result.key_info:
            authenticator.record_usage(
                auth_result.key_info.key_id,
                total_input_tokens + total_output_tokens
            )

        # Record quota usage
        await quota_manager.record_usage(
            user_id=user_id,
            organization_id=org_id,
            tokens=total_input_tokens + total_output_tokens,
        )

        # Store response for deduplication
        if success and all_batches:
            final_response = all_batches[-1] if len(all_batches) == 1 else all_batches
            await dedup_manager.store_response(
                request_id=job_input.request_id,
                response=final_response,
                idempotency_key=idempotency_key,
                messages=messages,
                sampling_params=sampling_params,
                user_id=user_id,
            )
        elif not success:
            await dedup_manager.cancel_in_progress(job_input.request_id, idempotency_key)

        # Emit webhook event
        event_type = EventType.REQUEST_COMPLETE if success else EventType.REQUEST_ERROR
        await webhook_manager.emit(
            event_type=event_type,
            data={
                "latency_ms": timer.latency_ms,
                "input_tokens": total_input_tokens,
                "output_tokens": total_output_tokens,
                "error_code": error_code,
                "error_message": error_message,
            },
            user_id=user_id,
            tier=user_tier,
            model=model_name,
            request_id=job_input.request_id,
        )

        # Cache successful responses
        if success and all_batches and not job_input.stream:
            # Cache the last batch (which contains the full response)
            cache.put(
                model=model_name,
                messages=messages,
                sampling_params=sampling_params,
                response=all_batches[-1] if len(all_batches) == 1 else all_batches,
                input_tokens=total_input_tokens,
                output_tokens=total_output_tokens,
                stream=job_input.stream
            )

        # Record request for health metrics
        health_checker.record_request(success=success)

        # Audit log request completion
        await audit_logger.log_request_complete(
            request_id=job_input.request_id,
            user_id=auth_result.key_info.user_id if auth_result.key_info else None,
            api_key_id=auth_result.key_info.key_id if auth_result.key_info else None,
            model=model_name,
            input_tokens=total_input_tokens,
            output_tokens=total_output_tokens,
            latency_ms=timer.latency_ms,
            success=success,
        )

        # Complete request for shutdown draining
        await shutdown_manager.complete_request(job_input.request_id)

        # Clear correlation ID
        logger.clear_correlation_id()

runpod.serverless.start(
    {
        "handler": handler,
        "concurrency_modifier": lambda x: vllm_engine.max_concurrency,
        "return_aggregate_stream": True,
    }
)
