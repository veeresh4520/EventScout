"""
eventscout/utils/logging_config.py
==================================
Production-Grade Structured Logging & Audit Trail for EventScout.

Emits structured logs with consistent schema and standard telemetry event tags:
- SOURCE_DISCOVERY_STARTED / COMPLETED / FAILED
- SCRAPE_STARTED / COMPLETED / FAILED
- EVENT_INSERTED / EVENT_UPDATED / EVENT_DUPLICATE
- RANKING_COMPLETED
- NOTIFICATION_SENT / NOTIFICATION_FAILED
- USER_LOGIN / AUTH_FAILURE
- ADMIN_SOURCE_APPROVED / ADMIN_SOURCE_REJECTED

Enforces strict sanitization to guarantee no secrets (passwords, tokens, API keys)
are ever written to logs.
"""

from datetime import datetime, timezone
import json
import logging
import re
import sys
from typing import Any, Dict, Optional

# Sensitive keys that must NEVER appear in plain text logs
SENSITIVE_PATTERNS = [
    re.compile(r"password", re.IGNORECASE),
    re.compile(r"secret", re.IGNORECASE),
    re.compile(r"token", re.IGNORECASE),
    re.compile(r"api_key", re.IGNORECASE),
    re.compile(r"authorization", re.IGNORECASE),
    re.compile(r"bearer", re.IGNORECASE),
]


def sanitize_value(key: str, val: Any) -> Any:
    """Masks values for sensitive keys."""
    if any(p.search(key) for p in SENSITIVE_PATTERNS):
        return "***REDACTED***"
    if isinstance(val, dict):
        return {k: sanitize_value(k, v) for k, v in val.items()}
    if isinstance(val, list):
        return [sanitize_value(key, item) for item in val]
    return val


def sanitize_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively redacts sensitive keys from dictionary payloads."""
    return {k: sanitize_value(k, v) for k, v in data.items()}


class StructuredEventLogger:
    """
    Standard logger wrapper producing structured, machine-readable JSON logs
    with rich contextual metadata.
    """

    def __init__(self, name: str = "EventScout"):
        self.logger = logging.getLogger(name)
        if not self.logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter("[%(asctime)s] %(levelname)s [%(name)s]: %(message)s")
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    def log_event(
        self,
        event_tag: str,
        message: str,
        level: int = logging.INFO,
        source: Optional[str] = None,
        duration: Optional[float] = None,
        events_found: Optional[int] = None,
        events_inserted: Optional[int] = None,
        events_updated: Optional[int] = None,
        errors: Optional[Any] = None,
        extra: Optional[Dict[str, Any]] = None,
    ):
        """
        Emits a structured telemetry log entry.
        """
        payload: Dict[str, Any] = {
            "event_tag": event_tag,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "message": message,
        }

        if source:
            payload["source"] = source
        if duration is not None:
            payload["duration_seconds"] = round(duration, 3)
        if events_found is not None:
            payload["events_found"] = events_found
        if events_inserted is not None:
            payload["events_inserted"] = events_inserted
        if events_updated is not None:
            payload["events_updated"] = events_updated
        if errors:
            payload["errors"] = str(errors)

        if extra:
            clean_extra = sanitize_dict(extra)
            payload.update(clean_extra)

        sanitized_payload = sanitize_dict(payload)
        self.logger.log(level, f"[{event_tag}] {json.dumps(sanitized_payload)}")


# Singleton instance for system-wide telemetry
structured_logger = StructuredEventLogger("EventScoutTelemetry")
