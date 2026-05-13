"""
config_loader
-------------
Fetches configuration from Spring Cloud Config Server and caches it locally.
Mirrors the user-service config_loader pattern.
"""
import os
import logging
import threading
import time
import requests

logger = logging.getLogger(__name__)

CONFIG_SERVER_URL = os.environ.get("CONFIG_SERVER_URL", "http://192.168.172.22:8080")
APP_NAME          = os.environ.get("APP_NAME", "IDENTITY-SERVICE")
PROFILE           = os.environ.get("PROFILE", "default")

cached_config: dict = {}
_lock = threading.Lock()

MAX_RETRIES    = 5
RETRY_DELAYS   = [3, 5, 10, 20, 30]   # secondes entre chaque tentative


def load_config():
    """Fetch external config from Spring Cloud Config Server (runs in background thread)."""
    def _fetch():
        global cached_config
        url = f"{CONFIG_SERVER_URL}/{APP_NAME}/{PROFILE}"
        logger.info("Fetching config from: %s", url)

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                data   = response.json()
                merged = {}
                for src in data.get("propertySources", []):
                    merged.update(src.get("source", {}))
                with _lock:
                    cached_config = merged
                logger.info("Config fetched successfully (%d keys) on attempt %d.", len(merged), attempt)
                return
            except Exception as exc:
                delay = RETRY_DELAYS[attempt - 1] if attempt <= len(RETRY_DELAYS) else RETRY_DELAYS[-1]
                if attempt < MAX_RETRIES:
                    logger.warning(
                        "Config fetch attempt %d/%d failed: %s — retrying in %ds...",
                        attempt, MAX_RETRIES, exc, delay
                    )
                    time.sleep(delay)
                else:
                    logger.error(
                        "Config fetch failed after %d attempts: %s — service will use env vars only.",
                        MAX_RETRIES, exc
                    )

    threading.Thread(target=_fetch, daemon=True).start()


def get_config(key, default=None):
    """Retrieve a config value safely from cached_config."""
    with _lock:
        return cached_config.get(key, default)
