import httpx
import logging
from typing import Dict, Any, List
from models.order import Order

logger = logging.getLogger(__name__)

# Markup to add to each rate (our profit)
RATE_MARKUP = 10.0

class ShipEngineService:
    """Service for handling ShipEngine API interactions"""
    
    def __init__(self, api_key: str, base_url: str = "https://api.shipengine.com"):
        self.api_key = api_key
        self.base_url = base_url
        self.client = httpx.AsyncClient(
            base_url=base_url,
            headers={
                "API-Key": api_key,
                "Content-Type": "application/json"
            },
            timeout=30.0
        )
    
    async def get_rates(self, shipment_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Get shipping rates from ShipEngine API
        Automatically adds markup to each rate
        """
        try:
            payload = {
                "rate_options": {
                    "carrier_ids": [],  # Will use all connected carriers
                },
                "shipment": {
                    "validate_address": "no_validation",
                    "ship_from": shipment_data["ship_from"],
                    "ship_to": shipment_data["ship_to"],
                    "packages": shipment_data["packages"]
                }
            }
            
            response = await self.client.post(
                "/v1/rates",
                json=payload
            )
            response.raise_for_status()
            
            rates_data = response.json()
            rates = rates_data.get("rate_response", {}).get("rates", [])
            
            # Add markup to each rate
            for rate in rates:
                original_amount = rate.get("shipping_amount", {}).get("amount", 0)
                rate["original_amount"] = original_amount
                rate["markup"] = RATE_MARKUP
                rate["total_amount"] = original_amount + RATE_MARKUP
            
            logger.info(f"Got {len(rates)} rates from ShipEngine")
            return rates
            
        except httpx.HTTPStatusError as e:
            error_detail = e.response.json() if e.response.text else str(e)
            logger.error(f"ShipEngine rates API error: {error_detail}")
            raise ValueError(f"Failed to get rates: {error_detail}")
        except httpx.RequestError as e:
            logger.error(f"Request error calling ShipEngine: {e}")
            raise ValueError(f"Network error: {str(e)}")
    
    async def create_label(self, order: Order) -> Dict[str, Any]:
        """
        Create a shipping label via ShipEngine API
        """
        try:
            payload = self._prepare_label_payload(order)
            
            response = await self.client.post(
                "/v1/labels",
                json=payload
            )
            response.raise_for_status()
            
            label_data = response.json()
            
            logger.info(
                f"Label created successfully: {label_data.get('label_id')} "
                f"for tracking {label_data.get('tracking_number')}"
            )
            
            return label_data
            
        except httpx.HTTPStatusError as e:
            error_detail = e.response.json() if e.response.text else str(e)
            logger.error(f"ShipEngine API error: {error_detail}")
            raise ValueError(f"Failed to create label: {error_detail}")
        except httpx.RequestError as e:
            logger.error(f"Request error calling ShipEngine: {e}")
            raise ValueError(f"Network error: {str(e)}")
    
    def _prepare_label_payload(self, order: Order) -> Dict[str, Any]:
        """Prepare request payload for ShipEngine label creation"""
        return {
            "shipment": {
                "validate_address": order.validateAddress,
                "service_code": order.serviceCode,
                "ship_from": {
                    "name": order.shipFromAddress.name,
                    "address_line1": order.shipFromAddress.addressLine1,
                    "address_line2": order.shipFromAddress.addressLine2,
                    "city_locality": order.shipFromAddress.city,
                    "state_province": order.shipFromAddress.state,
                    "postal_code": order.shipFromAddress.postalCode,
                    "country_code": order.shipFromAddress.countryCode,
                    "phone": order.shipFromAddress.phone,
                    "email": order.shipFromAddress.email,
                },
                "ship_to": {
                    "name": order.shipToAddress.name,
                    "address_line1": order.shipToAddress.addressLine1,
                    "address_line2": order.shipToAddress.addressLine2,
                    "city_locality": order.shipToAddress.city,
                    "state_province": order.shipToAddress.state,
                    "postal_code": order.shipToAddress.postalCode,
                    "country_code": order.shipToAddress.countryCode,
                    "phone": order.shipToAddress.phone,
                    "email": order.shipToAddress.email,
                },
                "packages": [
                    {
                        "weight": {
                            "value": order.package.weight,
                            "unit": "ounce"
                        },
                        "dimensions": {
                            "length": order.package.length,
                            "width": order.package.width,
                            "height": order.package.height,
                            "unit": "inch"
                        }
                    }
                ]
            }
        }
    
    async def close(self):
        """Close the HTTP client connection"""
        await self.client.aclose()