from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Any, List, Optional
from sqlalchemy import text
from app.core.database_pool import db_pool


def _quantize_currency(amount: Any) -> Decimal:
    """Quantize a numeric/decimal value to 2 decimal places using standard half-up rounding."""
    if amount is None:
        return Decimal("0.00")
    return Decimal(str(amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


async def calculate_monthly_revenue(
    property_id: str,
    month: int,
    year: int,
    tenant_id: Optional[str] = None,
    db_session=None,
) -> Decimal:
    """
    Calculates revenue for a specific month using the property's local timezone
    and preserving sub-cent precision until final quantization.
    """
    start_date = datetime(year, month, 1)
    if month < 12:
        end_date = datetime(year, month + 1, 1)
    else:
        end_date = datetime(year + 1, 1, 1)

    query = text("""
        SELECT COALESCE(SUM(r.total_amount), 0) AS total
        FROM properties p
        LEFT JOIN reservations r
            ON r.property_id = p.id
            AND r.tenant_id = p.tenant_id
            AND (r.check_in_date AT TIME ZONE p.timezone) >= :start_date
            AND (r.check_in_date AT TIME ZONE p.timezone) < :end_date
        WHERE p.id = :property_id
          AND (:tenant_id IS NULL OR p.tenant_id = :tenant_id)
    """)

    if db_session is not None:
        result = await db_session.execute(
            query,
            {
                "property_id": property_id,
                "tenant_id": tenant_id,
                "start_date": start_date,
                "end_date": end_date,
            },
        )
        val = result.scalar()
        return _quantize_currency(val)

    await db_pool.initialize()
    async with db_pool.get_session() as session:
        result = await session.execute(
            query,
            {
                "property_id": property_id,
                "tenant_id": tenant_id,
                "start_date": start_date,
                "end_date": end_date,
            },
        )
        val = result.scalar()
        return _quantize_currency(val)


async def get_tenant_properties(tenant_id: str) -> List[Dict[str, Any]]:
    """
    Returns properties belonging strictly to the specified tenant.
    """
    await db_pool.initialize()
    if not db_pool.session_factory:
        raise RuntimeError("Database pool not available")

    async with db_pool.get_session() as session:
        query = text("""
            SELECT id, tenant_id, name, timezone
            FROM properties
            WHERE tenant_id = :tenant_id
            ORDER BY id
        """)
        result = await session.execute(query, {"tenant_id": tenant_id})
        return [
            {
                "id": row.id,
                "tenant_id": row.tenant_id,
                "name": row.name,
                "timezone": row.timezone,
            }
            for row in result.fetchall()
        ]


async def calculate_total_revenue(
    property_id: str,
    tenant_id: str,
    month: Optional[int] = 3,
    year: Optional[int] = 2024,
) -> Dict[str, Any]:
    """
    Aggregates revenue from database with strict tenant isolation,
    property timezone conversion for monthly boundaries, and Decimal quantization.
    """
    await db_pool.initialize()

    if not db_pool.session_factory:
        raise RuntimeError("Database pool not available")

    async with db_pool.get_session() as session:
        if month is not None and year is not None:
            start_date = datetime(year, month, 1)
            if month < 12:
                end_date = datetime(year, month + 1, 1)
            else:
                end_date = datetime(year + 1, 1, 1)

            query = text("""
                SELECT
                    p.id AS property_id,
                    p.name AS property_name,
                    p.timezone AS timezone,
                    COALESCE(SUM(r.total_amount), 0) AS total_revenue,
                    COUNT(r.id) AS reservation_count,
                    COALESCE(MAX(r.currency), 'USD') AS currency
                FROM properties p
                LEFT JOIN reservations r
                    ON r.property_id = p.id
                    AND r.tenant_id = p.tenant_id
                    AND (r.check_in_date AT TIME ZONE p.timezone) >= :start_date
                    AND (r.check_in_date AT TIME ZONE p.timezone) < :end_date
                WHERE p.id = :property_id
                  AND p.tenant_id = :tenant_id
                GROUP BY p.id, p.name, p.timezone
            """)
            params = {
                "property_id": property_id,
                "tenant_id": tenant_id,
                "start_date": start_date,
                "end_date": end_date,
            }
        else:
            query = text("""
                SELECT
                    p.id AS property_id,
                    p.name AS property_name,
                    p.timezone AS timezone,
                    COALESCE(SUM(r.total_amount), 0) AS total_revenue,
                    COUNT(r.id) AS reservation_count,
                    COALESCE(MAX(r.currency), 'USD') AS currency
                FROM properties p
                LEFT JOIN reservations r
                    ON r.property_id = p.id
                    AND r.tenant_id = p.tenant_id
                WHERE p.id = :property_id
                  AND p.tenant_id = :tenant_id
                GROUP BY p.id, p.name, p.timezone
            """)
            params = {
                "property_id": property_id,
                "tenant_id": tenant_id,
            }

        result = await session.execute(query, params)
        row = result.fetchone()

        if row:
            quantized_total = _quantize_currency(row.total_revenue)
            return {
                "property_id": row.property_id,
                "property_name": row.property_name,
                "timezone": row.timezone,
                "tenant_id": tenant_id,
                "total": str(quantized_total),
                "currency": row.currency or "USD",
                "count": int(row.reservation_count),
            }

        return {
            "property_id": property_id,
            "property_name": None,
            "timezone": "UTC",
            "tenant_id": tenant_id,
            "total": "0.00",
            "currency": "USD",
            "count": 0,
        }
