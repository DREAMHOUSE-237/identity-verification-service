"""
identity_app/apps.py
--------------------
Mirrors the user-service AppConfig pattern:
  - Imports signals (if any)
  - Skips startup threads during tests / management commands
  - Starts config loader, Eureka registration + heartbeat in daemon threads
  - Optionally starts RabbitMQ consumers (controlled by START_RABBITMQ_CONSUMER env var)
"""
import os
import sys
import threading
import logging
import time
from django.apps import AppConfig
from django.conf import settings

logger = logging.getLogger(__name__)


class IdentityAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name               = 'identity_app'
    verbose_name       = 'Identity & Verification'

    def ready(self):
        # 1. Always import signals (no-op if file doesn't exist yet)
        try:
            from . import signals  # noqa: F401
        except ImportError:
            pass
        except Exception:
            logger.exception("Failed to import signals")

        # 2. Never run background threads during tests
        if getattr(settings, "TESTING", False):
            return

        # 3. Never run during management commands that don't need it
        mgmt_commands_to_skip = {
            "makemigrations", "migrate", "collectstatic", "test", "shell",
        }
        if any(cmd in sys.argv for cmd in mgmt_commands_to_skip):
            return

        # 4. Only run in the main server process (gunicorn worker or runserver)
        # GUNICORN_MAIN_PID n'est pas injecté automatiquement — on utilise
        # la variable WORKER_ID injectée par docker-compose (="0" pour le worker principal)
        worker_id    = os.environ.get("WORKER_ID", "0")
        is_runserver = os.environ.get("RUN_MAIN") == "true"

        if worker_id != "0" and not is_runserver:
            return

        # 5. Optionally start RabbitMQ consumers
        start_rabbit = os.environ.get(
            "START_RABBITMQ_CONSUMER", "false"
        ).lower() in ("1", "true", "yes", "on")

        if start_rabbit:
            self._start_thread(self._run_identity_request_consumer, name="consumer-identity-requests")

        # 6. Always start config loader and Eureka
        self._start_thread(self._maybe_load_config,     name="config-loader")
        self._start_thread(self._maybe_register_eureka, name="eureka-register")

    # ------------------------------------------------------------------ #

    def _start_thread(self, target, name=None):
        t = threading.Thread(target=target, name=name or target.__name__, daemon=True)
        t.start()

    # ------------------------------------------------------------------ #
    # RabbitMQ consumer (placeholder — add management commands as needed)
    # ------------------------------------------------------------------ #

    def _run_identity_request_consumer(self):
        """
        Placeholder for any future RabbitMQ consumer management command.
        Add the command name below and create the corresponding management command.
        E.g.: call_command("consume_identity_requests")
        """
        time.sleep(3)  # anti-deadlock: let Django finish loading all modules first
        from django.core.management import call_command
        try:
            logger.info("[consumer] Starting identity request consumer thread...")
            call_command("consume_identity_requests")
        except Exception as exc:
            logger.exception("Identity request consumer thread crashed: %s", exc)

    # ------------------------------------------------------------------ #
    # Config loader
    # ------------------------------------------------------------------ #

    def _maybe_load_config(self):
        time.sleep(1)  # anti-deadlock
        try:
            from .services import config_loader
            logger.info("Triggering config_loader.load_config()")
            config_loader.load_config()
        except Exception:
            logger.exception("Exception while calling config_loader.load_config()")

    # ------------------------------------------------------------------ #
    # Eureka registration + heartbeat
    # ------------------------------------------------------------------ #

    def _maybe_register_eureka(self):
        time.sleep(2)  # anti-deadlock (critical — Eureka must not race with Django init)
        try:
            from .services import eureka
        except Exception:
            logger.exception("Could not import eureka service; skipping registration.")
            return

        max_attempts = int(os.environ.get("EUREKA_REG_MAX_ATTEMPTS", "6"))
        base_wait    = float(os.environ.get("EUREKA_REG_BASE_WAIT", "2.0"))

        for attempt in range(1, max_attempts + 1):
            try:
                eureka.register()
                logger.info("Eureka registration successful.")
                self._start_thread(eureka.start_heartbeat_loop, name="eureka-heartbeat")
                return
            except Exception as exc:
                wait = base_wait * (2 ** (attempt - 1))
                logger.warning(
                    "Eureka registration attempt %d failed: %s — retrying in %.1f seconds",
                    attempt, exc, wait,
                )
                time.sleep(wait)

        logger.error("Eureka registration failed after %d attempts.", max_attempts)
