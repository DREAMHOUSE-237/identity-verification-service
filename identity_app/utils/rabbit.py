import pika
import json
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


def publish_message(queue: str, message: dict):
    params     = pika.URLParameters(settings.RABBITMQ_URL)
    connection = pika.BlockingConnection(params)
    channel    = connection.channel()
    channel.queue_declare(queue=queue, durable=True)
    channel.basic_publish(
        exchange='',
        routing_key=queue,
        body=json.dumps(message),
        properties=pika.BasicProperties(delivery_mode=2),
    )
    connection.close()
    logger.info("[→ %s] %s", queue, message)


def publish_identity_result(record):
    """
    Notify user service that identity verification is done.
    Sends: email, status, requested_role, and the 3 CNI fields.
    Queue: user_identified
    """
    message = {
        "event":            "user.identified",
        "email":            record.email,
        "requested_role":   record.requested_role,
        "status":           record.status,           # "verified" or "rejected"
        "rejection_reason": record.rejection_reason,
        # CNI data (populated after OCR or manual admin entry)
        "nom":              record.nom_extrait,
        "prenom":           record.prenom_extrait,
        "numero_cni":       record.numero_cni,
    }
    publish_message("user_identified", message)
    logger.info("[identity] Published result for %s: %s", record.email, record.status)
