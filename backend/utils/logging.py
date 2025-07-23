import json
import logging
import logging.config
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from constants import LogMessages


class StructuredFormatter(logging.Formatter):
    def __init__(self, include_extra: bool = True):
        super().__init__()
        self.include_extra = include_extra

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        if hasattr(record, "process") and record.process:
            log_data["process_id"] = record.process
        if hasattr(record, "thread") and record.thread:
            log_data["thread_id"] = record.thread

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        if self.include_extra and hasattr(record, "__dict__"):
            standard_fields = {
                "name",
                "msg",
                "args",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "exc_info",
                "exc_text",
                "stack_info",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
                "getMessage",
                "message",
            }

            extra_data = {
                k: v
                for k, v in record.__dict__.items()
                if k not in standard_fields and not k.startswith("_")
            }

            if extra_data:
                log_data["extra"] = extra_data

        return json.dumps(log_data, default=str, ensure_ascii=False)


class ColoredConsoleFormatter(logging.Formatter):
    COLORS = {
        "DEBUG": "\033[36m",
        "INFO": "\033[32m",
        "WARNING": "\033[33m",
        "ERROR": "\033[31m",
        "CRITICAL": "\033[35m",
        "RESET": "\033[0m",
    }

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, "")
        reset = self.COLORS["RESET"]

        timestamp = datetime.fromtimestamp(record.created).strftime("%H:%M:%S")
        formatted = f"{color}[{timestamp}] {record.levelname:8} {record.name:20} | {record.getMessage()}{reset}"

        if hasattr(record, "__dict__"):
            extra_fields = [
                "event",
                "operation",
                "document_id",
                "conversation_id",
                "user_id",
            ]
            extra_info = []

            for field in extra_fields:
                if hasattr(record, field):
                    value = getattr(record, field)
                    extra_info.append(f"{field}={value}")

            if extra_info:
                formatted += f" ({', '.join(extra_info)})"

        if record.exc_info:
            formatted += f"\n{self.formatException(record.exc_info)}"

        return formatted


class ApplicationLogger:
    def __init__(self):
        self._configured = False
        self._loggers = {}

    def setup_logging(
        self,
        debug: bool = False,
        log_file: Optional[str] = None,
        structured_logs: bool = False,
        log_level: str = "INFO",
    ):
        if self._configured:
            return

        numeric_level = getattr(logging, log_level.upper(), logging.INFO)
        if debug:
            numeric_level = logging.DEBUG

        root_logger = logging.getLogger()
        root_logger.setLevel(numeric_level)

        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(numeric_level)

        if structured_logs:
            console_handler.setFormatter(StructuredFormatter())
        else:
            console_handler.setFormatter(ColoredConsoleFormatter())

        root_logger.addHandler(console_handler)

        if log_file:
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)

            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(numeric_level)
            file_handler.setFormatter(StructuredFormatter())
            root_logger.addHandler(file_handler)

        self._configure_loggers(debug)
        self._configured = True

        logger = self.get_logger(__name__)
        logger.info(
            "Logging configuration completed",
            extra={
                "debug": debug,
                "log_level": log_level,
                "structured_logs": structured_logs,
                "log_file": log_file,
            },
        )

    def _configure_loggers(self, debug: bool):
        """Configure specific loggers."""
        # Reduce noise from external libraries
        external_loggers = [
            "httpx",
            "urllib3",
            "requests",
            "openai",
            "qdrant_client",
            "chromadb",
            "langchain",
        ]

        for logger_name in external_loggers:
            logger = logging.getLogger(logger_name)
            logger.setLevel(logging.WARNING if not debug else logging.INFO)

        # Configure uvicorn logger
        uvicorn_logger = logging.getLogger("uvicorn")
        uvicorn_logger.setLevel(logging.INFO)

        # Configure our application loggers
        app_loggers = ["routes", "utils", "dto", "services", "db"]

        for logger_name in app_loggers:
            logger = logging.getLogger(logger_name)
            logger.setLevel(logging.DEBUG if debug else logging.INFO)

    def get_logger(self, name: str) -> logging.Logger:
        """
        Get a logger instance with consistent configuration.

        Args:
            name: Logger name (usually __name__)

        Returns:
            Configured logger instance
        """
        if name not in self._loggers:
            self._loggers[name] = logging.getLogger(name)

        return self._loggers[name]


# Global logger instance
app_logger = ApplicationLogger()


def get_logger(name: str) -> logging.Logger:
    return app_logger.get_logger(name)


def setup_logging(
    debug: bool = False,
    log_file: Optional[str] = None,
    structured_logs: bool = False,
    log_level: str = "INFO",
):
    app_logger.setup_logging(debug, log_file, structured_logs, log_level)


class LoggerMixin:
    @property
    def logger(self) -> logging.Logger:
        return get_logger(f"{self.__class__.__module__}.{self.__class__.__name__}")

    def log_operation(self, operation: str, **kwargs):
        self.logger.info(
            f"Operation: {operation}",
            extra={
                "event": LogMessages.ERROR_OCCURRED,
                "operation": operation,
                "class": self.__class__.__name__,
                **kwargs,
            },
        )

    def log_error(self, operation: str, error: Exception, **kwargs):
        self.logger.error(
            f"Operation failed: {operation}",
            extra={
                "event": LogMessages.ERROR_OCCURRED,
                "operation": operation,
                "class": self.__class__.__name__,
                "error_type": type(error).__name__,
                "error_message": str(error),
                **kwargs,
            },
            exc_info=True,
        )

    def log_performance(self, operation: str, duration: float, **kwargs):
        self.logger.info(
            f"Performance: {operation}",
            extra={
                "event": "performance_metric",
                "operation": operation,
                "duration_seconds": duration,
                "class": self.__class__.__name__,
                **kwargs,
            },
        )


def log_api_request(logger: logging.Logger, method: str, path: str, **kwargs):
    logger.info(
        f"API Request: {method} {path}",
        extra={"event": "api_request", "method": method, "path": path, **kwargs},
    )


def log_api_response(
    logger: logging.Logger,
    method: str,
    path: str,
    status_code: int,
    duration: float,
    **kwargs,
):
    logger.info(
        f"API Response: {method} {path} -> {status_code}",
        extra={
            "event": "api_response",
            "method": method,
            "path": path,
            "status_code": status_code,
            "duration_seconds": duration,
            **kwargs,
        },
    )


def log_database_operation(
    logger: logging.Logger, operation: str, table: str, **kwargs
):
    logger.debug(
        f"DB Operation: {operation} on {table}",
        extra={
            "event": "database_operation",
            "operation": operation,
            "table": table,
            **kwargs,
        },
    )


def log_external_api_call(
    logger: logging.Logger, service: str, operation: str, duration: float, **kwargs
):
    logger.info(
        f"External API: {service}.{operation}",
        extra={
            "event": "external_api_call",
            "service": service,
            "operation": operation,
            "duration_seconds": duration,
            **kwargs,
        },
    )
