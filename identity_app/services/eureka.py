"""
eureka
------
Handles Eureka registration and heartbeat for IDENTITY-SERVICE.
Mirrors the user-service eureka pattern exactly.
"""
import os
import socket
import logging
import time
import requests
from .config_loader import cached_config

logger = logging.getLogger(__name__)


# ---------------------------
# UTILITIES
# ---------------------------
def get_config(key, default=None):
    return cached_config.get(key, default)


def _get_host_ip():
    """Détecte l'IP locale, peut être remplacée par HOST_IP fixe."""
    host_ip = os.environ.get("HOST_IP")
    if host_ip:
        return host_ip

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        host_ip = s.getsockname()[0]
    except Exception:
        host_ip = "127.0.0.1"
    finally:
        s.close()
    return host_ip


# ---------------------------
# CLEANUP OLD INSTANCES
# ---------------------------
def cleanup_old_instances():
    """Supprime les anciennes instances IDENTITY-SERVICE d'Eureka."""
    EUREKA_SERVER = os.environ.get(
        "EUREKA_URL",
        get_config("eureka.server", "http://ec2-16-171-142-15.eu-north-1.compute.amazonaws.com:8761"),
    )
    APP_NAME = "IDENTITY-SERVICE"
    try:
        response = requests.get(f"{EUREKA_SERVER}/apps/{APP_NAME}", timeout=5)
        if response.status_code == 200:
            logger.info("Nettoyage des anciennes instances IDENTITY-SERVICE...")
    except Exception as exc:
        logger.warning("Impossible de nettoyer les anciennes instances: %s", exc)


# ---------------------------
# REGISTER TO EUREKA
# ---------------------------
def register():
    """Enregistre IDENTITY-SERVICE sur Eureka."""
    EUREKA_SERVER = os.environ.get(
        "EUREKA_URL",
        get_config("eureka.server", "http://ec2-16-171-142-15.eu-north-1.compute.amazonaws.com:8761"),
    )
    APP_NAME = "IDENTITY-SERVICE"
    PORT     = os.environ.get("APP_PORT", get_config("service.port", "8001"))
    HOST_IP  = _get_host_ip()
    INSTANCE_ID = f"{HOST_IP}:{APP_NAME}:{PORT}"

    url = f"{EUREKA_SERVER}/apps/{APP_NAME}"

    payload = {
        "instance": {
            "instanceId":      INSTANCE_ID,
            "hostName":        HOST_IP,
            "app":             APP_NAME,
            "ipAddr":          HOST_IP,
            "status":          "UP",
            "port":            {"$": int(PORT), "@enabled": "true"},
            "securePort":      {"$": 443, "@enabled": "false"},
            "vipAddress":      APP_NAME.lower(),
            "secureVipAddress": APP_NAME.lower(),
            "homePageUrl":     f"http://{HOST_IP}:{PORT}/",
            "statusPageUrl":   f"http://{HOST_IP}:{PORT}/identity/health/",
            "healthCheckUrl":  f"http://{HOST_IP}:{PORT}/identity/health/",
            "dataCenterInfo": {
                "@class": "com.netflix.appinfo.InstanceInfo$DefaultDataCenterInfo",
                "name":   "MyOwn",
            },
            "metadata": {
                "management.port": str(PORT),
                "instanceId":      INSTANCE_ID,
            },
            "leaseInfo": {
                "renewalIntervalInSecs": 30,
                "durationInSecs":        90,
            },
        }
    }

    try:
        cleanup_old_instances()
        r = requests.post(url, json=payload, timeout=5)
        if r.status_code in (200, 204):
            logger.info("IDENTITY-SERVICE enregistré sur Eureka: %s", INSTANCE_ID)
        else:
            logger.warning("Échec enregistrement Eureka %s: %s", r.status_code, r.text)
    except Exception as exc:
        logger.error("Enregistrement Eureka échoué: %s", exc)
        raise  # re-raise so apps.py retry logic works


# ---------------------------
# HEARTBEAT
# ---------------------------
def _should_reregister(status_code):
    return status_code in (404, 410)


def send_heartbeat():
    """Envoie un heartbeat à Eureka."""
    EUREKA_SERVER = os.environ.get(
        "EUREKA_URL",
        get_config("eureka.server", "http://ec2-16-171-142-15.eu-north-1.compute.amazonaws.com:8761"),
    )
    APP_NAME = "IDENTITY-SERVICE"
    PORT     = os.environ.get("APP_PORT", get_config("service.port", "8001"))
    HOST_IP  = _get_host_ip()
    INSTANCE_ID = f"{HOST_IP}:{APP_NAME}:{PORT}"

    url = f"{EUREKA_SERVER}/apps/{APP_NAME}/{INSTANCE_ID}"
    try:
        r = requests.put(url, timeout=5)
        logger.info("Heartbeat envoyé pour %s (status %s)", INSTANCE_ID, r.status_code)
        return r.status_code
    except Exception as exc:
        logger.error("Heartbeat échoué: %s", exc)
        return None


def start_heartbeat_loop():
    """Boucle infinie qui envoie un heartbeat toutes les 25 secondes."""
    logger.info("Démarrage du heartbeat pour IDENTITY-SERVICE...")
    while True:
        status_code = send_heartbeat()
        if status_code is None:
            logger.warning("Heartbeat error — will retry...")
        elif _should_reregister(status_code):
            logger.warning("Eureka reports instance missing — re-registering...")
            register()
        time.sleep(25)
