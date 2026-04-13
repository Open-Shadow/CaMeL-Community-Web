"""Service for atomic quota operations on the shared users table."""
from decimal import Decimal

from django.db import connection, transaction


QUOTA_PER_DOLLAR = 500_000


class QuotaError(ValueError):
    pass


class QuotaService:
    @staticmethod
    def usd_to_quota(usd: Decimal) -> int:
        return int(usd * QUOTA_PER_DOLLAR)

    @staticmethod
    def quota_to_usd(quota: int) -> Decimal:
        return Decimal(quota) / Decimal(QUOTA_PER_DOLLAR)

    @staticmethod
    @transaction.atomic
    def deduct_quota(user_id: int, quota_units: int) -> int:
        """Atomically deduct quota. Returns new balance. Raises QuotaError if insufficient."""
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT quota FROM users WHERE id = %s AND deleted_at IS NULL FOR UPDATE",
                [user_id],
            )
            row = cursor.fetchone()
            if row is None:
                raise QuotaError("用户不存在")
            if row[0] < quota_units:
                raise QuotaError("余额不足")
            cursor.execute(
                "UPDATE users SET quota = quota - %s WHERE id = %s RETURNING quota",
                [quota_units, user_id],
            )
            return cursor.fetchone()[0]

    @staticmethod
    @transaction.atomic
    def add_quota(user_id: int, quota_units: int) -> int:
        """Atomically add quota. Returns new balance."""
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE users SET quota = quota + %s WHERE id = %s AND deleted_at IS NULL RETURNING quota",
                [quota_units, user_id],
            )
            row = cursor.fetchone()
            if row is None:
                raise QuotaError("用户不存在")
            return row[0]

    @classmethod
    def deduct_usd(cls, user_id: int, amount_usd: Decimal) -> int:
        return cls.deduct_quota(user_id, cls.usd_to_quota(amount_usd))

    @classmethod
    def add_usd(cls, user_id: int, amount_usd: Decimal) -> int:
        return cls.add_quota(user_id, cls.usd_to_quota(amount_usd))
