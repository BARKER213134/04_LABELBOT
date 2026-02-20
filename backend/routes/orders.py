from fastapi import APIRouter, Depends, HTTPException, status, Request
from motor.motor_asyncio import AsyncIOMotorDatabase
from models.order import CreateOrderRequest, Order, AddressInfo, PackageInfo, CarrierEnum, OrderStatus
from services.orders_service import normalize_carrier
from services.shipengine_service import ShipEngineService
from services.security import verify_admin, api_limiter, check_rate_limit, get_client_ip
from config import get_settings, Settings
from database import get_database
from datetime import datetime
import logging
from typing import Optional

router = APIRouter(prefix="/orders", tags=["orders"])
logger = logging.getLogger(__name__)

@router.post("/create")
async def create_order(
    request: CreateOrderRequest,
    settings: Settings = Depends(get_settings),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Create a shipping label order
    """
    try:
        # Get current environment setting from DB
        env_config = await db.api_config.find_one({"_id": "api_config"})
        current_env = env_config.get("environment", "sandbox") if env_config else "sandbox"
        
        # Get appropriate API key
        if current_env == "production":
            api_key = settings.shipengine_production_key
        else:
            api_key = settings.shipengine_sandbox_key
        
        # Create order object
        order = Order(
            shipFromAddress=AddressInfo(
                name=request.shipFromName,
                addressLine1=request.shipFromAddressLine1,
                addressLine2=request.shipFromAddressLine2,
                city=request.shipFromCity,
                state=request.shipFromState,
                postalCode=request.shipFromPostalCode,
                countryCode=request.shipFromCountryCode,
                phone=request.shipFromPhone,
                email=request.shipFromEmail,
            ),
            shipToAddress=AddressInfo(
                name=request.shipToName,
                addressLine1=request.shipToAddressLine1,
                addressLine2=request.shipToAddressLine2,
                city=request.shipToCity,
                state=request.shipToState,
                postalCode=request.shipToPostalCode,
                countryCode=request.shipToCountryCode,
                phone=request.shipToPhone,
                email=request.shipToEmail,
            ),
            package=PackageInfo(
                weight=request.packageWeight,
                length=request.packageLength,
                width=request.packageWidth,
                height=request.packageHeight,
            ),
            carrier=normalize_carrier(request.carrier),
            serviceCode=request.serviceCode,
            validateAddress=request.validateAddress,
            environment=current_env,
            telegram_user_id=request.telegram_user_id,
            telegram_username=request.telegram_username,
        )
        
        # Save pending order to database
        order_dict = order.model_dump()
        result = await db.orders.insert_one(order_dict)
        order.id = str(result.inserted_id)
        logger.info(f"Created pending order: {order.id}")
        
        # Initialize ShipEngine service
        shipengine = ShipEngineService(api_key=api_key)
        
        try:
            # Create label via ShipEngine API
            label_response = await shipengine.create_label(order)
            
            # Update order with label information
            update_data = {
                "labelId": label_response.get("label_id"),
                "trackingNumber": label_response.get("tracking_number"),
                "labelCost": label_response.get("shipment_cost", {}).get("amount"),
                "labelDownloadUrl": label_response.get("label_download", {}).get("pdf"),
                "status": OrderStatus.LABEL_CREATED.value,
                "shipDate": datetime.utcnow(),
                "updatedAt": datetime.utcnow()
            }
            
            await db.orders.update_one(
                {"_id": result.inserted_id},
                {"$set": update_data}
            )
            
            logger.info(f"Label created: {label_response.get('label_id')}")
            
            return {
                "success": True,
                "orderId": order.id,
                "labelId": label_response.get("label_id"),
                "trackingNumber": label_response.get("tracking_number"),
                "cost": label_response.get("shipment_cost", {}).get("amount"),
                "labelDownloadUrl": label_response.get("label_download", {}).get("pdf"),
                "status": "completed",
            }
            
        finally:
            await shipengine.close()
        
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create label"
        )

@router.get("/")
async def list_orders(
    skip: int = 0,
    limit: int = 20,
    carrier: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """List orders with optional filtering"""
    try:
        query = {}
        if carrier:
            query["carrier"] = carrier
        if status:
            query["status"] = status
        
        cursor = db.orders.find(query, {"_id": 0}).skip(skip).limit(limit).sort("createdAt", -1)
        orders = await cursor.to_list(length=limit)
        total = await db.orders.count_documents(query)
        
        return {
            "items": orders,
            "total": total,
            "skip": skip,
            "limit": limit,
        }
        
    except Exception as e:
        logger.error(f"Error listing orders: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list orders"
        )

@router.get("/{order_id}")
async def get_order(
    order_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get order by ID"""
    try:
        order = await db.orders.find_one({"id": order_id}, {"_id": 0})
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found"
            )
        return order
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving order: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve order"
        )


@router.get("/admin/statistics")
async def get_order_statistics(
    request: Request,
    db: AsyncIOMotorDatabase = Depends(get_database),
    admin: str = Depends(verify_admin)
):
    """Get order statistics (protected)"""
    check_rate_limit(get_client_ip(request), api_limiter)
    
    try:
        # Get all completed orders with label info
        pipeline = [
            {"$match": {"status": "label_created"}},
            {"$group": {
                "_id": None,
                "totalOrders": {"$sum": 1},
                "totalLabelCost": {"$sum": {"$ifNull": ["$labelCost", 0]}},
                "totalUserPaid": {"$sum": {"$ifNull": ["$userPaid", 0]}},
                "totalProfit": {"$sum": {"$ifNull": ["$profit", 0]}},
            }}
        ]
        
        result = await db.orders.aggregate(pipeline).to_list(1)
        stats = result[0] if result else {
            "totalOrders": 0,
            "totalLabelCost": 0,
            "totalUserPaid": 0,
            "totalProfit": 0,
        }
        
        # Remove MongoDB _id
        stats.pop("_id", None)
        
        # Get orders with low profit (< $10)
        low_profit_count = await db.orders.count_documents({
            "status": "label_created",
            "$or": [
                {"profit": {"$lt": 10}},
                {"profit": {"$exists": False}}
            ]
        })
        
        stats["lowProfitOrders"] = low_profit_count
        
        return stats
        
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get statistics"
        )


@router.get("/admin/list")
async def list_orders_admin(
    request: Request,
    skip: int = 0,
    limit: int = 50,
    db: AsyncIOMotorDatabase = Depends(get_database),
    admin: str = Depends(verify_admin)
):
    """List orders with profit info (protected)"""
    check_rate_limit(get_client_ip(request), api_limiter)
    
    try:
        cursor = db.orders.find(
            {"status": "label_created"},
            {
                "_id": 0,
                "id": 1,
                "carrier": 1,
                "serviceCode": 1,
                "labelCost": 1,
                "userPaid": 1,
                "profit": 1,
                "trackingNumber": 1,
                "telegram_username": 1,
                "createdAt": 1,
                "shipFromCity": {"$ifNull": ["$shipFromAddress.city", ""]},
                "shipToCity": {"$ifNull": ["$shipToAddress.city", ""]},
            }
        ).skip(skip).limit(limit).sort("createdAt", -1)
        
        orders = await cursor.to_list(length=limit)
        
        # Calculate profit for orders that don't have it
        for order in orders:
            if order.get("profit") is None:
                label_cost = order.get("labelCost") or 0
                user_paid = order.get("userPaid") or 0
                order["profit"] = user_paid - label_cost
            
            # Mark low profit orders
            order["isLowProfit"] = order.get("profit", 0) < 10
        
        total = await db.orders.count_documents({"status": "label_created"})
        
        return {
            "items": orders,
            "total": total,
            "skip": skip,
            "limit": limit,
        }
        
    except Exception as e:
        logger.error(f"Error listing orders: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list orders"
        )
