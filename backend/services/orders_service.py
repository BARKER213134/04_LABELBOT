import logging
from typing import Dict, Any
from motor.motor_asyncio import AsyncIOMotorDatabase
from models.order import Order, AddressInfo, PackageInfo, CarrierEnum, OrderStatus, CreateOrderRequest
from services.shipengine_service import ShipEngineService
from config import get_settings
from datetime import datetime

logger = logging.getLogger(__name__)

class OrdersService:
    """Service for handling order operations"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.settings = get_settings()
    
    async def create_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a shipping label order
        
        Args:
            order_data: Dictionary with order information
            
        Returns:
            Dictionary with created order information
        """
        try:
            # Get current environment setting from DB
            env_config = await self.db.api_config.find_one({"_id": "api_config"})
            current_env = env_config.get("environment", "sandbox") if env_config else "sandbox"
            
            # Get appropriate API key
            if current_env == "production":
                api_key = self.settings.shipengine_production_key
            else:
                api_key = self.settings.shipengine_sandbox_key
            
            logger.info(f"Creating order in {current_env} environment")
            
            # Create order object
            order = Order(
                shipFromAddress=AddressInfo(
                    name=order_data.get('shipFromName'),
                    addressLine1=order_data.get('shipFromAddressLine1'),
                    addressLine2=order_data.get('shipFromAddressLine2'),
                    city=order_data.get('shipFromCity'),
                    state=order_data.get('shipFromState'),
                    postalCode=order_data.get('shipFromPostalCode'),
                    countryCode=order_data.get('shipFromCountryCode', 'US'),
                    phone=order_data.get('shipFromPhone'),
                    email=order_data.get('shipFromEmail'),
                ),
                shipToAddress=AddressInfo(
                    name=order_data.get('shipToName'),
                    addressLine1=order_data.get('shipToAddressLine1'),
                    addressLine2=order_data.get('shipToAddressLine2'),
                    city=order_data.get('shipToCity'),
                    state=order_data.get('shipToState'),
                    postalCode=order_data.get('shipToPostalCode'),
                    countryCode=order_data.get('shipToCountryCode', 'US'),
                    phone=order_data.get('shipToPhone'),
                    email=order_data.get('shipToEmail'),
                ),
                package=PackageInfo(
                    weight=float(order_data.get('packageWeight')),
                    length=float(order_data.get('packageLength')),
                    width=float(order_data.get('packageWidth')),
                    height=float(order_data.get('packageHeight')),
                ),
                carrier=CarrierEnum(order_data.get('carrier')),
                carrier_id=order_data.get('carrier_id'),
                serviceCode=order_data.get('serviceCode'),
                validateAddress=order_data.get('validateAddress', 'validate_and_clean'),
                environment=current_env,
                telegram_user_id=order_data.get('telegram_user_id'),
                telegram_username=order_data.get('telegram_username'),
            )
            
            # Save pending order to database
            order_dict = order.model_dump()
            result = await self.db.orders.insert_one(order_dict)
            order.id = str(result.inserted_id)
            logger.info(f"Created pending order: {order.id}")
            
            # Initialize ShipEngine service
            shipengine = ShipEngineService(api_key=api_key)
            
            try:
                # Always use regular label creation to ensure company_name is empty
                # rate_id method uses cached shipment data which may have default company
                logger.info(f"Creating label with service_code: {order.serviceCode}")
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
                
                await self.db.orders.update_one(
                    {"_id": result.inserted_id},
                    {"$set": update_data}
                )
                
                # Update telegram user stats
                if order_data.get('telegram_user_id'):
                    await self.db.telegram_users.update_one(
                        {"telegram_id": order_data.get('telegram_user_id')},
                        {"$inc": {"total_orders": 1}},
                        upsert=False
                    )
                
                logger.info(f"Label created: {label_response.get('label_id')}")
                
                return {
                    "success": True,
                    "orderId": order.id,
                    "labelId": label_response.get("label_id"),
                    "trackingNumber": label_response.get("tracking_number"),
                    "cost": label_response.get("shipment_cost", {}).get("amount"),
                    "labelDownloadUrl": label_response.get("label_download", {}).get("pdf"),
                    "carrier": order_data.get('carrier'),
                }
                
            finally:
                await shipengine.close()
            
        except Exception as e:
            logger.error(f"Error creating order: {e}", exc_info=True)
            raise
