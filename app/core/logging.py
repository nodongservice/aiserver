import logging
import os
import re
import sys

EMAIL_PATTERN = re.compile(r"([A-Za-z0-9._%+-]{1,64})@([A-Za-z0-9.-]+\.[A-Za-z]{2,})")
PHONE_PATTERN = re.compile(r"(01[016789])-?(\d{3,4})-?(\d{4})")
TOKEN_PATTERN = re.compile(r"(?i)(bearer\s+)([A-Za-z0-9._~+/=-]+)")


def sanitize_log_text(text: str) -> str:
    if not text:
        return text

    sanitized = EMAIL_PATTERN.sub(lambda match: f"{match.group(1)[:1]}***@{match.group(2)}", text)
    sanitized = PHONE_PATTERN.sub(r"\1-****-\3", sanitized)
    sanitized = TOKEN_PATTERN.sub(r"\1[REDACTED]", sanitized)
    return sanitized


class RedactingFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        formatted = super().format(record)
        return sanitize_log_text(formatted)


def setup_logging() -> None:
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(RedactingFormatter("[%(levelname)s] %(asctime)s %(name)s: %(message)s"))

    logging.basicConfig(
        level=log_level,
        handlers=[handler],
        force=True,
    )

    logging.getLogger("uvicorn").setLevel(log_level)
    logging.getLogger("uvicorn.error").setLevel(log_level)
    logging.getLogger("uvicorn.access").setLevel(log_level)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
