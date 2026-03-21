from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from database import get_database
from datetime import datetime, timedelta
import logging

router = APIRouter(prefix="/statistics", tags=["statistics"])
logger = logging.getLogger(__name__)

@router.get("/")
async def get_statistics(
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get statistics for orders"""
    try:
        # Total orders
        total_orders = await db.orders.count_documents({})
        
        # Orders by status
        pipeline_status = [
            {"$group": {"_id": "$status", "count": {"$sum": 1}}}
        ]
        status_counts = await db.orders.aggregate(pipeline_status).to_list(100)
        
        # Orders by carrier
        pipeline_carrier = [
            {"$group": {"_id": "$carrier", "count": {"$sum": 1}}}
        ]
        carrier_counts = await db.orders.aggregate(pipeline_carrier).to_list(100)
        
        # Total cost
        pipeline_cost = [
            {"$group": {"_id": None, "total": {"$sum": "$labelCost"}}}
        ]
        cost_result = await db.orders.aggregate(pipeline_cost).to_list(1)
        total_cost = cost_result[0]["total"] if cost_result else 0
        
        # Recent orders (last 7 days)
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        recent_orders = await db.orders.count_documents({
            "createdAt": {"$gte": seven_days_ago}
        })
        
        return {
            "total_orders": total_orders,
            "status_breakdown": {item["_id"]: item["count"] for item in status_counts},
            "carrier_breakdown": {item["_id"]: item["count"] for item in carrier_counts},
            "total_cost": round(total_cost, 2) if total_cost else 0,
            "recent_orders_7d": recent_orders
        }
        
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get statistics"
        )