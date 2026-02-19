"""
Input Validation & Content Moderation Module

Validates and sanitizes input before processing.
Includes PII detection, content moderation, and token estimation.
"""

import os
import re
import logging
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

logging.basicConfig(level=logging.INFO)


class ValidationLevel(Enum):
    """Validation strictness levels"""
    STRICT = "strict"      # Block on any issue
    MODERATE = "moderate"  # Block on serious, warn on minor
    PERMISSIVE = "permissive"  # Warn only


class ContentCategory(Enum):
    """Content moderation categories"""
    SAFE = "safe"
    PII = "pii"
    PROFANITY = "profanity"
    INJECTION = "injection"
    MALICIOUS = "malicious"


@dataclass
class ValidationResult:
    """Result of input validation"""
    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    sanitized_input: Optional[Any] = None
    estimated_tokens: int = 0
    categories_detected: List[str] = field(default_factory=list)
    pii_redacted: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "valid": self.valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "estimated_tokens": self.estimated_tokens,
            "categories_detected": self.categories_detected,
            "pii_redacted": self.pii_redacted,
        }


@dataclass
class ValidationStats:
    """Validation statistics"""
    total_validated: int = 0
    total_blocked: int = 0
    total_warnings: int = 0
    pii_redacted: int = 0
    by_category: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_validated": self.total_validated,
            "total_blocked": self.total_blocked,
            "total_warnings": self.total_warnings,
            "pii_redacted": self.pii_redacted,
            "by_category": self.by_category,
        }


class InputValidator:
    """
    Validates and sanitizes input requests.

    Configure via environment variables:
    - VALIDATION_ENABLED: Enable input validation (default: true)
    - VALIDATION_LEVEL: Strictness level (default: moderate)
    - VALIDATION_MAX_TOKENS: Maximum estimated tokens (default: 100000)
    - VALIDATION_MAX_MESSAGES: Maximum messages in chat (default: 100)
    - VALIDATION_MAX_MESSAGE_LENGTH: Max chars per message (default: 100000)
    - VALIDATION_PII_REDACTION: Enable PII redaction (default: false)
    - VALIDATION_BLOCK_INJECTIONS: Block prompt injections (default: true)
    """

    def __init__(self):
        self.enabled = os.getenv("VALIDATION_ENABLED", "true").lower() == "true"
        self.level = ValidationLevel(os.getenv("VALIDATION_LEVEL", "moderate"))
        self.max_tokens = int(os.getenv("VALIDATION_MAX_TOKENS", "100000"))
        self.max_messages = int(os.getenv("VALIDATION_MAX_MESSAGES", "100"))
        self.max_message_length = int(os.getenv("VALIDATION_MAX_MESSAGE_LENGTH", "100000"))
        self.pii_redaction = os.getenv("VALIDATION_PII_REDACTION", "false").lower() == "true"
        self.block_injections = os.getenv("VALIDATION_BLOCK_INJECTIONS", "true").lower() == "true"

        # PII patterns
        self._pii_patterns = {
            "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            "phone": r'\b(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b',
            "ssn": r'\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b',
            "credit_card": r'\b(?:\d{4}[-\s]?){3}\d{4}\b',
            "ip_address": r'\b(?:\d{1,3}\.){3}\d{1,3}\b',
        }

        # Injection patterns
        self._injection_patterns = [
            r'ignore\s+(?:all\s+)?(?:previous|prior|above)\s+instructions',
            r'disregard\s+(?:all\s+)?(?:previous|prior|above)',
            r'forget\s+(?:everything|all)',
            r'you\s+are\s+now\s+(?:a\s+)?(?:different|new)',
            r'act\s+as\s+(?:if|though)\s+you',
            r'pretend\s+(?:you\s+are|to\s+be)',
            r'system\s*:\s*',
            r'\[system\]',
        ]

        # Statistics
        self._stats = ValidationStats()

        if self.enabled:
            logging.info(f"[VALIDATION] Input validation enabled (level={self.level.value})")

    def validate(
        self,
        messages: Any,
        max_tokens: Optional[int] = None,
        route: Optional[str] = None
    ) -> ValidationResult:
        """
        Validate input messages.

        Args:
            messages: Input messages (string or list of message dicts)
            max_tokens: Override max tokens for this request
            route: API route for context

        Returns:
            ValidationResult with status and details
        """
        if not self.enabled:
            return ValidationResult(valid=True, sanitized_input=messages)

        self._stats.total_validated += 1
        errors = []
        warnings = []
        categories = []
        sanitized = messages
        pii_redacted = False

        # Normalize to list of messages
        if isinstance(messages, str):
            message_list = [{"role": "user", "content": messages}]
        elif isinstance(messages, list):
            message_list = messages
        else:
            errors.append(f"Invalid message format: {type(messages)}")
            return self._create_result(False, errors, warnings, messages, 0, categories)

        # Check message count
        if len(message_list) > self.max_messages:
            errors.append(f"Too many messages: {len(message_list)} (max: {self.max_messages})")

        total_chars = 0
        estimated_tokens = 0

        for i, msg in enumerate(message_list):
            if not isinstance(msg, dict):
                errors.append(f"Message {i} is not a dict")
                continue

            content = msg.get("content", "")
            if isinstance(content, list):
                # Handle multimodal content
                text_content = " ".join(
                    part.get("text", "") for part in content
                    if isinstance(part, dict) and part.get("type") == "text"
                )
                content = text_content

            if not isinstance(content, str):
                content = str(content)

            # Check message length
            if len(content) > self.max_message_length:
                errors.append(f"Message {i} too long: {len(content)} chars (max: {self.max_message_length})")

            total_chars += len(content)

            # Check for PII
            pii_found = self._detect_pii(content)
            if pii_found:
                categories.append(ContentCategory.PII.value)
                self._stats.by_category["pii"] = self._stats.by_category.get("pii", 0) + 1

                if self.pii_redaction:
                    sanitized_content = self._redact_pii(content)
                    if isinstance(messages, str):
                        sanitized = sanitized_content
                    else:
                        sanitized = [
                            {**m, "content": self._redact_pii(m.get("content", ""))}
                            if isinstance(m.get("content"), str) else m
                            for m in message_list
                        ]
                    pii_redacted = True
                    warnings.append(f"PII detected and redacted: {', '.join(pii_found)}")
                else:
                    if self.level == ValidationLevel.STRICT:
                        errors.append(f"PII detected: {', '.join(pii_found)}")
                    else:
                        warnings.append(f"PII detected: {', '.join(pii_found)}")

            # Check for injection attempts
            if self.block_injections:
                injections = self._detect_injections(content)
                if injections:
                    categories.append(ContentCategory.INJECTION.value)
                    self._stats.by_category["injection"] = self._stats.by_category.get("injection", 0) + 1

                    if self.level in [ValidationLevel.STRICT, ValidationLevel.MODERATE]:
                        errors.append(f"Potential prompt injection detected in message {i}")
                    else:
                        warnings.append(f"Potential prompt injection detected in message {i}")

        # Estimate tokens (rough: ~4 chars per token)
        estimated_tokens = total_chars // 4
        effective_max = max_tokens or self.max_tokens

        if estimated_tokens > effective_max:
            errors.append(f"Estimated tokens ({estimated_tokens}) exceeds limit ({effective_max})")

        # Update stats
        if errors:
            self._stats.total_blocked += 1
        if warnings:
            self._stats.total_warnings += 1
        if pii_redacted:
            self._stats.pii_redacted += 1

        return self._create_result(
            len(errors) == 0,
            errors,
            warnings,
            sanitized if pii_redacted else messages,
            estimated_tokens,
            categories,
            pii_redacted
        )

    def _create_result(
        self,
        valid: bool,
        errors: List[str],
        warnings: List[str],
        sanitized: Any,
        tokens: int,
        categories: List[str],
        pii_redacted: bool = False
    ) -> ValidationResult:
        return ValidationResult(
            valid=valid,
            errors=errors,
            warnings=warnings,
            sanitized_input=sanitized,
            estimated_tokens=tokens,
            categories_detected=list(set(categories)),
            pii_redacted=pii_redacted
        )

    def _detect_pii(self, text: str) -> List[str]:
        """Detect PII patterns in text"""
        found = []
        for pii_type, pattern in self._pii_patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                found.append(pii_type)
        return found

    def _redact_pii(self, text: str) -> str:
        """Redact PII from text"""
        redacted = text
        for pii_type, pattern in self._pii_patterns.items():
            redacted = re.sub(pattern, f"[REDACTED_{pii_type.upper()}]", redacted, flags=re.IGNORECASE)
        return redacted

    def _detect_injections(self, text: str) -> List[str]:
        """Detect potential prompt injections"""
        found = []
        text_lower = text.lower()
        for pattern in self._injection_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                found.append(pattern)
        return found

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text"""
        # Simple estimation: ~4 chars per token
        return len(text) // 4

    def get_stats(self) -> ValidationStats:
        """Get validation statistics"""
        return self._stats


# Global validator
_validator: Optional[InputValidator] = None


def get_input_validator() -> InputValidator:
    """Get or create the global input validator"""
    global _validator
    if _validator is None:
        _validator = InputValidator()
    return _validator


def handle_validation_stats_request() -> Dict[str, Any]:
    """Handle /validation/stats request"""
    validator = get_input_validator()
    stats = validator.get_stats()
    return {
        "enabled": validator.enabled,
        "level": validator.level.value,
        "max_tokens": validator.max_tokens,
        "pii_redaction": validator.pii_redaction,
        **stats.to_dict(),
    }
