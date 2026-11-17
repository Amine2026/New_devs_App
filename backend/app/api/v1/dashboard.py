from fastapi import APIRouter, Depends, HTTPException, Query
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Any, List
from app.services.cache import get_revenue_summary
from app.services.reservations import get_tenant_properties
from app.core.auth import authenticate_request as get_current_user

router = APIRouter()


@router.get("/dashboard/properties")
async def list_dashboard_properties(
    current_user: Any = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    tenant_id = getattr(current_user, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=403, detail="Tenant context required")
    return await get_tenant_properties(tenant_id)


@router.get("/dashboard/summary")
async def get_dashboard_summary(
    property_id: str,
    month: int = Query(default=3, ge=1, le=12),
    year: int = Query(default=2024, ge=2000, le=2100),
    current_user: Any = Depends(get_current_user),
) -> Dict[str, Any]:
    tenant_id = getattr(current_user, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=403, detail="Tenant context required")

    revenue_data = await get_revenue_summary(
        property_id=property_id,
        tenant_id=tenant_id,
        month=month,
        year=year,
    )

    quantized_total = Decimal(str(revenue_data["total"])).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    return {
        "property_id": revenue_data["property_id"],
        "property_name": revenue_data.get("property_name"),
        "timezone": revenue_data.get("timezone", "UTC"),
        "tenant_id": tenant_id,
        "total_revenue": float(quantized_total),
        "currency": revenue_data["currency"],
        "reservations_count": revenue_data["count"],
    }
