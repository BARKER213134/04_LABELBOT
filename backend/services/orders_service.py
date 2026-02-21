import logging
from typing import Dict, Any
from motor.motor_asyncio import AsyncIOMotorDatabase
from models.order import Order, AddressInfo, PackageInfo, CarrierEnum, OrderStatus, CreateOrderRequest
from services.shipengine_service import ShipEngineService
from config import get_settings
from datetime import datetime

logger = logging.getLogger(__name__)


def normalize_carrier(carrier_code: str) -> CarrierEnum:
    """Normalize carrier code to CarrierEnum, handling various formats"""
    if not carrier_code:
        return CarrierEnum.USPS
    
    carrier_lower = carrier_code.lower()
    
    # Map various carrier codes to our enum
    if 'fedex' in carrier_lower:
        if 'walleted' in carrier_lower:
            return CarrierEnum.FEDEX_WALLETED
        return CarrierEnum.FEDEX
    elif 'ups' in carrier_lower:
        if 'walleted' in carrier_lower:
            return CarrierEnum.UPS_WALLETED
        return CarrierEnum.UPS
    elif 'usps' in carrier_lower:
        return CarrierEnum.USPS
    elif 'stamps' in carrier_lower:
        return CarrierEnum.STAMPS_COM
    elif 'dhl' in carrier_lower:
        return CarrierEnum.DHL
    
    # Try direct enum match
    try:
        return CarrierEnum(carrier_code)
    except ValueError:
        logger.warning(f"Unknown carrier code: {carrier_code}, defaulting to USPS")
        return CarrierEnum.USPS


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
                    weight=float(order_data.get('packageWeight') or 0),
                    length=float(order_data.get('packageLength') or 0),
                    width=float(order_data.get('packageWidth') or 0),
                    height=float(order_data.get('packageHeight') or 0),
                ),
                carrier=normalize_carrier(order_data.get('carrier')),
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
                
                # Get actual label cost from ShipEngine
                label_cost = label_response.get("shipment_cost", {}).get("amount", 0)
                
                # Пользователь платит total_cost (оценка + $10 наценка)
                # Реальная прибыль = total_cost - реальная стоимость ShipEngine
                total_cost_paid = order_data.get('total_cost', 0)
                if total_cost_paid > 0:
                    # Новая логика: пользователь платит оценочную цену
                    user_paid = total_cost_paid
                    profit = total_cost_paid - label_cost if label_cost else 10
                else:
                    # Fallback на старую логику
                    from services.shipengine_service import RATE_MARKUP
                    user_paid = label_cost + RATE_MARKUP
                    profit = RATE_MARKUP
                
                update_data = {
                    "labelId": label_response.get("label_id"),
                    "trackingNumber": label_response.get("tracking_number"),
                    "labelCost": label_cost,  # Original ShipEngine price
                    "userPaid": user_paid,    # What user actually paid
                    "profit": profit,          # Real profit
                    "labelDownloadUrl": label_response.get("label_download", {}).get("pdf"),
                    "status": OrderStatus.LABEL_CREATED.value,
                    "shipDate": datetime.utcnow(),
                    "updatedAt": datetime.utcnow(),
                    "actualCost": label_cost    # Real ShipEngine cost
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
                    "userPaid": user_paid,  # Actual cost + $10 markup - for balance deduction
                    "labelDownloadUrl": label_response.get("label_download", {}).get("pdf"),
                    "carrier": order_data.get('carrier'),
                }
                
            finally:
                await shipengine.close()
            
        except Exception as e:
            logger.error(f"Error creating order: {e}", exc_info=True)
            raise
