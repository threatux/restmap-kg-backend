"""
Импорты всех моделей (для Alembic и SQLAlchemy)
"""
from app.models.user import User, UserRole
from app.models.rest_point import RestPoint, RestPointStatus, RestPointType
from app.models.booking import Booking, BookingStatus, PaymentMethod
from app.models.transaction import Transaction, TransactionType, TransactionStatus
from app.models.checkin import Checkin
from app.models.review import Review
from app.models.rest_points_wallet import (
    RestPointsWallet,
    RestPointsTransaction,
    LoyaltyLevel,
    RestPointsTransactionType,
)

__all__ = [
    "User", "UserRole",
    "RestPoint", "RestPointStatus", "RestPointType",
    "Booking", "BookingStatus", "PaymentMethod",
    "Transaction", "TransactionType", "TransactionStatus",
    "Checkin",
    "Review",
    "RestPointsWallet", "RestPointsTransaction", "LoyaltyLevel", "RestPointsTransactionType",
]