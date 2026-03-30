"""tracker/services.py - SMS notification service using Africa's Talking API."""

import logging
from django.conf import settings
from .models import SMSNotification

logger = logging.getLogger(__name__)


def send_sms(student, reason="absent"):
    """Send an absence/late SMS to the student's parent and log the result."""
    message = (
        f"Dear {student.parent_name}, your child {student.first_name} "
        f"{student.last_name} was marked {reason} today. "
        f"Please contact the school for more information. "
        f"- Education Tracker System"
    )

    at_username = getattr(settings, 'AFRICASTALKING_USERNAME', None)
    at_api_key = getattr(settings, 'AFRICASTALKING_API_KEY', None)

    if at_username and at_api_key:
        # Production mode: send real SMS via Africa's Talking API v1
        try:
            import africastalking
            africastalking.initialize(at_username, at_api_key)
            sms = africastalking.SMS
            response = sms.send(message, [student.parent_phone])
            logger.info(f"SMS sent to {student.parent_phone}: {response}")
            status = 'sent'
        except Exception as e:
            logger.error(f"SMS failed for {student.parent_phone}: {e}")
            status = 'failed'
    else:
        # Simulation mode: log to database only (no API credentials configured)
        status = 'simulated'

    notification = SMSNotification.objects.create(
        student=student,
        parent_phone=student.parent_phone,
        message=message,
        status=status,
    )

    return notification
