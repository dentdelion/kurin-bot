"""
Centralized logging configuration for the Kurin Bot
Provides JSON structured logging with consistent formatting
"""

import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        log_entry: Dict[str, Any] = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'module': record.module,
            'message': record.getMessage(),
            'logger': record.name
        }
        
        # Add extra fields if they exist
        extra_fields = ['user_id', 'action', 'book_id', 'process', 'scheduler_task']
        for field in extra_fields:
            if hasattr(record, field):
                log_entry[field] = getattr(record, field)
        
        # Add any additional extra fields
        if hasattr(record, '__dict__'):
            for key, value in record.__dict__.items():
                if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                              'filename', 'module', 'lineno', 'funcName', 'created', 
                              'msecs', 'relativeCreated', 'thread', 'threadName', 
                              'processName', 'process', 'getMessage', 'exc_info', 
                              'exc_text', 'stack_info'] + extra_fields:
                    log_entry[key] = value
        
        return json.dumps(log_entry, ensure_ascii=False)


def setup_logging(level: str = 'INFO') -> None:
    """Setup JSON logging for the application"""
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(message)s'  # JSON formatter will handle the format
    )
    
    # Set up JSON formatter
    json_formatter = JSONFormatter()
    handler = logging.StreamHandler()
    handler.setFormatter(json_formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(getattr(logging, level.upper()))


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the specified name"""
    return logging.getLogger(name)


def log_with_context(logger: logging.Logger, level: str, message: str, 
                    **context: Any) -> None:
    """Log a message with structured context"""
    log_method = getattr(logger, level.lower())
    log_method(message, extra=context)


# Log levels for easy reference
LOG_LEVELS = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARNING': logging.WARNING,
    'ERROR': logging.ERROR,
    'CRITICAL': logging.CRITICAL
} 