import sys
from loguru import logger

logger.remove()

logger.add(
    sys.stdout,
    format="<green>{time:HH:mm:ss}</green> | <level>{level:<7}</level> | <level>{message}</level>",
    level="WARNING",
    colorize=True,
)

logger.add(
    "logs/agent_{time:YYYY-MM-DD}.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level:<7} | {message}",
    level="DEBUG",
    rotation="00:00",
    retention="7 days",
    encoding="utf-8",
)

log = logger
