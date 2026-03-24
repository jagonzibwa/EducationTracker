"""
tracker/services.py - Business Logic Services

Contains the SMS notification service that sends messages to parents via
Africa's Talking API (v1). Falls back to simulation mode when API credentials
are not configured, allowing the system to be tested without incurring SMS costs.
"""

import logging
from django.conf import settings
from .models import SMSNotification

logger = logging.getLogger(__name__)


def send_sms(student, reason="absent"):
    """
    Send an SMS notification to a student's parent.

    Uses Africa's Talking SMS API (v1) when credentials are configured in
    Django settings (AFRICASTALKING_USERNAME and AFRICASTALKING_API_KEY).
    Falls back to simulation mode when credentials are not set.

    Args:
        student (Student): The student who was marked absent/late
        reason (str): The reason for the notification, defaults to "absent"

    Returns:
        SMSNotification: The created notification database record
    """
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
