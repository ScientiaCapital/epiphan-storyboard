"""
Configuration Validation Module

Validates all configuration on startup to fail fast with clear errors.
Reduces support tickets and debugging time.
"""

import os
import sys
import logging
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum

logging.basicConfig(level=logging.INFO)


class ValidationLevel(Enum):
    ERROR = "error"      # Startup must fail
    WARNING = "warning"  # Log warning but continue
    INFO = "info"        # Informational


@dataclass
class ValidationResult:
    """Result of a validation check"""
    name: str
    level: ValidationLevel
    passed: bool
    message: str
    suggestion: Optional[str] = None

    def __str__(self) -> str:
        status = "PASS" if self.passed else self.level.value.upper()
        msg = f"[{status}] {self.name}: {self.message}"
        if not self.passed and self.suggestion:
            msg += f"\n         Suggestion: {self.suggestion}"
        return msg


class ConfigValidator:
    """
    Validates configuration on startup.

    Configure via environment variables:
    - VALIDATION_STRICT: Exit on warnings too (default: false)
    - VALIDATION_SKIP: Skip validation entirely (default: false)
    """

    def __init__(self):
        self.strict = os.getenv("VALIDATION_STRICT", "false").lower() == "true"
        self.skip = os.getenv("VALIDATION_SKIP", "false").lower() == "true"
        self._results: List[ValidationResult] = []

    def validate_all(self) -> Tuple[bool, List[ValidationResult]]:
        """
        Run all validation checks.

        Returns:
            (success, results) - success is False if any errors found
        """
        if self.skip:
            logging.info("[VALIDATION] Skipping validation (VALIDATION_SKIP=true)")
            return True, []

        self._results = []

        # Core configuration
        self._validate_model_config()
        self._validate_gpu_config()
        self._validate_memory_config()

        # Enterprise features
        self._validate_auth_config()
        self._validate_metering_config()
        self._validate_cache_config()

        # Network/URLs
        self._validate_url_configs()

        # Log results
        self._log_results()

        # Check for failures
        has_errors = any(
            not r.passed and r.level == ValidationLevel.ERROR
            for r in self._results
        )
        has_warnings = any(
            not r.passed and r.level == ValidationLevel.WARNING
            for r in self._results
        )

        if has_errors:
            return False, self._results

        if has_warnings and self.strict:
            logging.error("[VALIDATION] Failing due to warnings (VALIDATION_STRICT=true)")
            return False, self._results

        return True, self._results

    def _add_result(self, result: ValidationResult):
        """Add a validation result"""
        self._results.append(result)

    def _validate_model_config(self):
        """Validate model configuration"""
        model = os.getenv("MODEL_NAME") or os.getenv("MODEL_REPO")

        if not model:
            self._add_result(ValidationResult(
                name="MODEL_NAME",
                level=ValidationLevel.ERROR,
                passed=False,
                message="No model specified",
                suggestion="Set MODEL_NAME or MODEL_REPO environment variable"
            ))
        else:
            self._add_result(ValidationResult(
                name="MODEL_NAME",
                level=ValidationLevel.INFO,
                passed=True,
                message=f"Model: {model}"
            ))

        # Check max model length
        max_len = os.getenv("MAX_MODEL_LEN")
        if max_len:
            try:
                max_len_int = int(max_len)
                if max_len_int < 128:
                    self._add_result(ValidationResult(
                        name="MAX_MODEL_LEN",
                        level=ValidationLevel.WARNING,
                        passed=False,
                        message=f"MAX_MODEL_LEN={max_len_int} is very small",
                        suggestion="Consider setting MAX_MODEL_LEN >= 512 for most use cases"
                    ))
                elif max_len_int > 131072:
                    self._add_result(ValidationResult(
                        name="MAX_MODEL_LEN",
                        level=ValidationLevel.WARNING,
                        passed=False,
                        message=f"MAX_MODEL_LEN={max_len_int} is very large",
                        suggestion="Ensure you have sufficient GPU memory for this context length"
                    ))
                else:
                    self._add_result(ValidationResult(
                        name="MAX_MODEL_LEN",
                        level=ValidationLevel.INFO,
                        passed=True,
                        message=f"Context length: {max_len_int}"
                    ))
            except ValueError:
                self._add_result(ValidationResult(
                    name="MAX_MODEL_LEN",
                    level=ValidationLevel.ERROR,
                    passed=False,
                    message=f"Invalid MAX_MODEL_LEN: {max_len}",
                    suggestion="MAX_MODEL_LEN must be an integer"
                ))

    def _validate_gpu_config(self):
        """Validate GPU configuration"""
        try:
            import torch
            if torch.cuda.is_available():
                gpu_count = torch.cuda.device_count()
                gpu_name = torch.cuda.get_device_name(0)

                self._add_result(ValidationResult(
                    name="GPU",
                    level=ValidationLevel.INFO,
                    passed=True,
                    message=f"Found {gpu_count} GPU(s): {gpu_name}"
                ))

                # Check tensor parallel size
                tp_size = int(os.getenv("TENSOR_PARALLEL_SIZE", "1"))
                if tp_size > gpu_count:
                    self._add_result(ValidationResult(
                        name="TENSOR_PARALLEL_SIZE",
                        level=ValidationLevel.ERROR,
                        passed=False,
                        message=f"TENSOR_PARALLEL_SIZE={tp_size} > available GPUs ({gpu_count})",
                        suggestion=f"Set TENSOR_PARALLEL_SIZE <= {gpu_count}"
                    ))
                elif tp_size > 1:
                    self._add_result(ValidationResult(
                        name="TENSOR_PARALLEL_SIZE",
                        level=ValidationLevel.INFO,
                        passed=True,
                        message=f"Tensor parallelism: {tp_size} GPUs"
                    ))
            else:
                self._add_result(ValidationResult(
                    name="GPU",
                    level=ValidationLevel.ERROR,
                    passed=False,
                    message="No CUDA GPUs available",
                    suggestion="Ensure NVIDIA drivers and CUDA are properly installed"
                ))
        except ImportError:
            self._add_result(ValidationResult(
                name="GPU",
                level=ValidationLevel.WARNING,
                passed=False,
                message="PyTorch not available for GPU check",
                suggestion="Install PyTorch to enable GPU validation"
            ))

    def _validate_memory_config(self):
        """Validate memory configuration"""
        gpu_util = os.getenv("GPU_MEMORY_UTILIZATION", "0.95")
        try:
            util = float(gpu_util)
            if util <= 0 or util > 1:
                self._add_result(ValidationResult(
                    name="GPU_MEMORY_UTILIZATION",
                    level=ValidationLevel.ERROR,
                    passed=False,
                    message=f"Invalid GPU_MEMORY_UTILIZATION: {util}",
                    suggestion="Set GPU_MEMORY_UTILIZATION between 0 and 1 (e.g., 0.9)"
                ))
            elif util > 0.95:
                self._add_result(ValidationResult(
                    name="GPU_MEMORY_UTILIZATION",
                    level=ValidationLevel.WARNING,
                    passed=False,
                    message=f"GPU_MEMORY_UTILIZATION={util} is very high",
                    suggestion="Consider lowering to 0.9 to prevent OOM errors"
                ))
            else:
                self._add_result(ValidationResult(
                    name="GPU_MEMORY_UTILIZATION",
                    level=ValidationLevel.INFO,
                    passed=True,
                    message=f"GPU memory utilization: {util*100:.0f}%"
                ))
        except ValueError:
            self._add_result(ValidationResult(
                name="GPU_MEMORY_UTILIZATION",
                level=ValidationLevel.ERROR,
                passed=False,
                message=f"Invalid GPU_MEMORY_UTILIZATION: {gpu_util}",
                suggestion="GPU_MEMORY_UTILIZATION must be a number between 0 and 1"
            ))

    def _validate_auth_config(self):
        """Validate authentication configuration"""
        auth_enabled = os.getenv("AUTH_ENABLED", "false").lower() == "true"

        if auth_enabled:
            has_keys = bool(os.getenv("AUTH_KEYS") or os.getenv("AUTH_KEYS_FILE"))
            if not has_keys:
                self._add_result(ValidationResult(
                    name="AUTH_KEYS",
                    level=ValidationLevel.WARNING,
                    passed=False,
                    message="AUTH_ENABLED=true but no API keys configured",
                    suggestion="Set AUTH_KEYS or AUTH_KEYS_FILE, or a development key will be used"
                ))
            else:
                self._add_result(ValidationResult(
                    name="AUTH_KEYS",
                    level=ValidationLevel.INFO,
                    passed=True,
                    message="Authentication enabled with keys configured"
                ))

    def _validate_metering_config(self):
        """Validate metering/billing configuration"""
        metering_enabled = os.getenv("METERING_ENABLED", "true").lower() == "true"
        webhook_url = os.getenv("METERING_WEBHOOK_URL")

        if metering_enabled and not webhook_url:
            self._add_result(ValidationResult(
                name="METERING_WEBHOOK_URL",
                level=ValidationLevel.WARNING,
                passed=False,
                message="Metering enabled but no webhook URL configured",
                suggestion="Set METERING_WEBHOOK_URL to enable billing data collection"
            ))
        elif metering_enabled and webhook_url:
            self._add_result(ValidationResult(
                name="METERING_WEBHOOK_URL",
                level=ValidationLevel.INFO,
                passed=True,
                message=f"Metering webhook: {webhook_url[:50]}..."
            ))

    def _validate_cache_config(self):
        """Validate cache configuration"""
        cache_enabled = os.getenv("CACHE_ENABLED", "false").lower() == "true"

        if cache_enabled:
            ttl = int(os.getenv("CACHE_TTL_SECONDS", "3600"))
            max_size = int(os.getenv("CACHE_MAX_SIZE", "1000"))

            if ttl < 60:
                self._add_result(ValidationResult(
                    name="CACHE_TTL_SECONDS",
                    level=ValidationLevel.WARNING,
                    passed=False,
                    message=f"CACHE_TTL_SECONDS={ttl} is very short",
                    suggestion="Consider setting TTL >= 300 for better cache efficiency"
                ))

            self._add_result(ValidationResult(
                name="CACHE_CONFIG",
                level=ValidationLevel.INFO,
                passed=True,
                message=f"Cache enabled (TTL={ttl}s, max_size={max_size})"
            ))

    def _validate_url_configs(self):
        """Validate URL configurations"""
        url_vars = [
            ("METERING_WEBHOOK_URL", "metering webhook"),
            ("AUTH_WEBHOOK_URL", "auth webhook"),
        ]

        for var_name, description in url_vars:
            url = os.getenv(var_name)
            if url:
                if not url.startswith(("http://", "https://")):
                    self._add_result(ValidationResult(
                        name=var_name,
                        level=ValidationLevel.ERROR,
                        passed=False,
                        message=f"Invalid URL for {description}: {url}",
                        suggestion="URL must start with http:// or https://"
                    ))
                elif url.startswith("http://") and "localhost" not in url and "127.0.0.1" not in url:
                    self._add_result(ValidationResult(
                        name=var_name,
                        level=ValidationLevel.WARNING,
                        passed=False,
                        message=f"Using insecure HTTP for {description}",
                        suggestion="Consider using HTTPS for production"
                    ))

    def _log_results(self):
        """Log all validation results"""
        logging.info("=" * 60)
        logging.info("CONFIGURATION VALIDATION RESULTS")
        logging.info("=" * 60)

        for result in self._results:
            if not result.passed:
                if result.level == ValidationLevel.ERROR:
                    logging.error(str(result))
                elif result.level == ValidationLevel.WARNING:
                    logging.warning(str(result))
            else:
                logging.info(str(result))

        logging.info("=" * 60)

        # Summary
        errors = sum(1 for r in self._results if not r.passed and r.level == ValidationLevel.ERROR)
        warnings = sum(1 for r in self._results if not r.passed and r.level == ValidationLevel.WARNING)
        passed = sum(1 for r in self._results if r.passed)

        if errors > 0:
            logging.error(f"VALIDATION FAILED: {errors} error(s), {warnings} warning(s), {passed} passed")
        elif warnings > 0:
            logging.warning(f"VALIDATION PASSED WITH WARNINGS: {warnings} warning(s), {passed} passed")
        else:
            logging.info(f"VALIDATION PASSED: {passed} check(s) passed")


def validate_config() -> bool:
    """
    Validate all configuration on startup.

    Returns:
        True if validation passed, False otherwise
    """
    validator = ConfigValidator()
    success, results = validator.validate_all()

    if not success:
        logging.error("Configuration validation failed. Please fix the errors above.")
        return False

    return True


def require_valid_config():
    """
    Validate configuration and exit if invalid.

    Call this at startup to fail fast on misconfiguration.
    """
    if not validate_config():
        logging.error("Exiting due to configuration errors")
        sys.exit(1)
