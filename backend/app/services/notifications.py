"""
Notifications service.
В MVP — просто логирует; в проде подключится SMTP / Twilio / push.
"""
import logging
from typing import Any

logger = logging.getLogger(__name__)


class NotificationService:
    """Унифицированный интерфейс уведомлений."""
    
    @staticmethod
    async def send_booking_confirmed(
        email: str,
        booking_number: str,
        checkin_code: str,
        rest_point_name: str,
    ) -> None:
        logger.info(
            "📧 [email=%s] Booking %s confirmed at '%s'. Code: %s",
            email, booking_number, rest_point_name, checkin_code,
        )
    
    @staticmethod
    async def send_check_in_reminder(email: str, booking_number: str, date: str) -> None:
        logger.info("📧 [email=%s] Reminder for %s on %s", email, booking_number, date)
    
    @staticmethod
    async def send_owner_new_booking(
        email: str,
        booking_number: str,
        guest_name: str,
        rest_point_name: str,
    ) -> None:
        logger.info(
            "🔔 [owner=%s] New booking %s from %s at '%s'",
            email, booking_number, guest_name, rest_point_name,
        )
    
    @staticmethod
    async def send_loyalty_level_up(email: str, new_level: str) -> None:
        logger.info("🎉 [email=%s] Level up! New tier: %s", email, new_level)
    
    @staticmethod
    async def send_generic(email: str, subject: str, body: str) -> None:
        logger.info("📧 [email=%s] %s\n%s", email, subject, body)