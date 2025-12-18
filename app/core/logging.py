import logging
import sys
from typing import Any

from core.config import get_settings

settings = get_settings()

def setup_logging() -> None:
    """
    Configure logging for the application.
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    
    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s in %(module)s: %(message)s"
    )
    handler.setFormatter(formatter)
    
    root_logger.addHandler(handler)
    
    # Silence noisy libraries if needed
    logging.getLogger("httpx").setLevel(logging.WARNING)

    logging.info(f"Logging initialized for {settings.PROJECT_NAME}")
