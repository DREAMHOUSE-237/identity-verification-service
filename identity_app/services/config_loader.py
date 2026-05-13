"""
config_loader
-------------
Fetches configuration from Spring Cloud Config Server and caches it locally.
Mirrors the user-service config_loader pattern.
"""
import os
import logging
import threading
import requests

logger = logging.getLogger(__name__)

CONFIG_SERVER_URL = os.environ.get("CONFIG_SERVER_URL", "http://192.168.172.22:8080")
APP_NAME          = os.environ.get("APP_NAME", "IDENTITY-SERVICE")
PROFILE           = os.environ.get("PROFILE", "dev")

cached_config: dict = {}
_lock = threading.Lock()


def load_config():
    """Fetch external config from Spring Cloud Config Server (runs in background thread)."""
    def _fetch():
        global cached_config
        url = f"{CONFIG_SERVER_URL}/{APP_NAME}/{PROFILE}"
        logger.info("Fetching config from: %s", url)
        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            data   = response.json()
            merged = {}
            for src in data.get("propertySources", []):
                merged.update(src.get("source", {}))
            with _lock:
                cached_config = merged
            logger.info("Config fetched successfully (%d keys).", len(merged))
        except Exception as exc:
            logger.error("Failed to fetch config: %s", exc)

    threading.Thread(target=_fetch, daemon=True).start()


def get_config(key, default=None):
    """Retrieve a config value safely from cached_config."""
    with _lock:
        return cached_config.get(key, default)
