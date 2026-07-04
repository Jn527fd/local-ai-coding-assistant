import logging

logger = logging.getLogger("app.audit")


class AuditLogger:
    """Emit redacted audit events for local security-sensitive actions."""

    def auth_event(
        self,
        event: str,
        *,
        username: str = "",
        client_host: str = "",
        success: bool,
        reason: str = "",
    ) -> None:
        logger.info(
            "audit event=%s username=%s client=%s success=%s reason=%s",
            event,
            _safe(username),
            _safe(client_host),
            success,
            _safe(reason),
        )

    def settings_event(
        self,
        event: str,
        *,
        username: str,
        client_host: str = "",
        success: bool,
    ) -> None:
        logger.info(
            "audit event=%s username=%s client=%s success=%s",
            event,
            _safe(username),
            _safe(client_host),
            success,
        )


def _safe(value: str) -> str:
    return value.replace("\n", "_").replace("\r", "_")[:120]
