import httpx
import logging
import asyncio
from typing import Dict, Any, List
from models.order import Order

logger = logging.getLogger(__name__)

# Markup to add to each rate (our profit)
RATE_MARKUP = 10.0

# Low balance threshold for notifications
LOW_BALANCE_THRESHOLD = 50.0

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
            timeout=60.0  # Increased timeout
        )
        self._carrier_ids = None
        self._max_retries = 3
        self._retry_delay = 2  # seconds
    
    async def _request_with_retry(self, method: str, url: str, **kwargs) -> httpx.Response:
        """Make HTTP request with retry logic"""
        last_error = None
        for attempt in range(self._max_retries):
            try:
                if method == "GET":
                    response = await self.client.get(url, **kwargs)
                elif method == "POST":
                    response = await self.client.post(url, **kwargs)
                else:
                    raise ValueError(f"Unsupported method: {method}")
                response.raise_for_status()
                return response
            except (httpx.TimeoutException, httpx.ConnectError, httpx.ReadTimeout) as e:
                last_error = e
                logger.warning(f"[SHIPENGINE] Request attempt {attempt + 1}/{self._max_retries} failed: {e}")
                if attempt < self._max_retries - 1:
                    await asyncio.sleep(self._retry_delay)
            except httpx.HTTPStatusError as e:
                # Don't retry on HTTP errors (4xx, 5xx)
                raise
        raise last_error or Exception("Max retries exceeded")
    
    async def get_account_balance(self) -> Dict[str, Any]:
        """Get ShipEngine account balance"""
        try:
            response = await self._request_with_retry("GET", "/v1/account/settings")
            data = response.json()
            
            # Extract balance info
            balance = data.get("account_balance", {})
            return {
                "balance": balance.get("balance", 0),
                "currency": balance.get("currency", "USD"),
                "low_balance": balance.get("balance", 0) < LOW_BALANCE_THRESHOLD
            }
        except Exception as e:
            logger.error(f"Error fetching account balance: {e}")
            return {"balance": 0, "currency": "USD", "low_balance": False, "error": str(e)}
    
    async def _get_carrier_ids(self) -> List[str]:
        """Get list of connected carrier IDs with fallback to cached values"""
        if self._carrier_ids is not None:
            return self._carrier_ids
        
        # Fallback carrier IDs - update these if carriers change in ShipEngine account
        # These are typical carrier IDs for ShipEngine accounts
        FALLBACK_CARRIER_IDS = [
            "se-4002321",   # usps
            "se-4002326",   # ups
            "se-4002328",   # fedex_walleted
        ]
        
        try:
            response = await self._request_with_retry("GET", "/v1/carriers")
            carriers_data = response.json()
            
            self._carrier_ids = [
                carrier["carrier_id"] 
                for carrier in carriers_data.get("carriers", [])
                if carrier.get("carrier_code") != "globalpost"
            ]
            logger.info(f"Found {len(self._carrier_ids)} carriers: {self._carrier_ids}")
            return self._carrier_ids
        except Exception as e:
            logger.warning(f"Error fetching carriers, using fallback: {e}")
            # Use fallback carrier IDs if API fails
            self._carrier_ids = FALLBACK_CARRIER_IDS
            return self._carrier_ids
    
    async def get_rates(self, shipment_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Get shipping rates from ShipEngine API
        Automatically adds markup to each rate
        """
        try:
            # Get carrier IDs first
            carrier_ids = await self._get_carrier_ids()
            if not carrier_ids:
                raise ValueError("No carriers available")
            
            # Set company_name to dash to override carrier defaults (SITKAGEAR fix)
            ship_from = shipment_data["ship_from"].copy()
            ship_to = shipment_data["ship_to"].copy()
            ship_from["company_name"] = "-"
            ship_to["company_name"] = "-"
            
            payload = {
                "rate_options": {
                    "carrier_ids": carrier_ids,
                },
                "shipment": {
                    "validate_address": "no_validation",
                    "ship_from": ship_from,
                    "ship_to": ship_to,
                    "packages": shipment_data["packages"]
                }
            }
            
            response = await self._request_with_retry("POST", "/v1/rates", json=payload)
            
            rates_data = response.json()
            rates = rates_data.get("rate_response", {}).get("rates", [])
            
            # Log carriers in response
            carriers_in_rates = set()
            for rate in rates:
                carriers_in_rates.add(rate.get("carrier_code", "unknown"))
            logger.info(f"Carriers in rates response: {carriers_in_rates}")
            
            # Check for rate errors (log only, non-critical)
            rate_errors = rates_data.get("rate_response", {}).get("errors", [])
            if rate_errors:
                # Filter out known non-critical carrier errors (GlobalPost etc.)
                critical_errors = [e for e in rate_errors if e.get("carrier_code") not in ("globalpost",)]
                if critical_errors:
                    logger.warning(f"Rate errors from carriers: {critical_errors}")
            
            # Add markup to each rate - include ALL cost components
            for rate in rates:
                # Get all cost components
                shipping_amount = rate.get("shipping_amount", {}).get("amount", 0)
                other_amount = rate.get("other_amount", {}).get("amount", 0)  # Fuel surcharge
                insurance_amount = rate.get("insurance_amount", {}).get("amount", 0)
                confirmation_amount = rate.get("confirmation_amount", {}).get("amount", 0)
                
                # Include ALL cost components to match what ShipEngine actually charges
                full_cost = shipping_amount + other_amount + insurance_amount + confirmation_amount
                
                # Store original amounts for transparency
                rate["shipping_only"] = shipping_amount
                rate["other_fees"] = other_amount
                rate["insurance_fee"] = insurance_amount
                rate["confirmation_fee"] = confirmation_amount
                rate["original_amount"] = full_cost  # Full cost before markup
                rate["markup"] = RATE_MARKUP
                rate["total_amount"] = full_cost + RATE_MARKUP  # What user pays
                
                carrier = rate.get("carrier_code", "")
                service = rate.get("service_code", "")
                logger.info(f"Rate {carrier}/{service}: ship=${shipping_amount:.2f} + fuel=${other_amount:.2f} + ins=${insurance_amount:.2f} + confirm=${confirmation_amount:.2f} + markup=${RATE_MARKUP} = ${rate['total_amount']:.2f}")
            
            logger.info(f"Got {len(rates)} rates")
            return rates
            
        except httpx.HTTPStatusError as e:
            error_detail = e.response.json() if e.response.text else str(e)
            logger.error(f"Rates API error: {error_detail}")
            raise ValueError(f"Failed to get rates")
        except httpx.RequestError as e:
            logger.error(f"Request error: {e}")
            raise ValueError(f"Network error")
    
    async def create_label_from_rate(self, rate_id: str) -> Dict[str, Any]:
        """
        Create a shipping label directly from a rate_id
        This is more reliable than creating from scratch
        """
        try:
            payload = {
                "rate_id": rate_id,
                "validate_address": "no_validation",
                "label_format": "pdf",
                "label_layout": "4x6"
            }
            
            logger.info(f"Creating label from rate_id: {rate_id}")
            
            response = await self._request_with_retry(
                "POST", 
                "/v1/labels/rates/" + rate_id,
                json=payload
            )
            
            label_data = response.json()
            
            logger.info(
                f"Label created successfully from rate: {label_data.get('label_id')} "
                f"for tracking {label_data.get('tracking_number')}"
            )
            
            return label_data
            
        except httpx.HTTPStatusError as e:
            error_detail = e.response.json() if e.response.text else str(e)
            logger.error(f"API error creating label from rate: {error_detail}")
            # Parse user-friendly error message
            user_error = self._parse_error_message(error_detail)
            raise ValueError(f"Failed to create label: {user_error}")
        except httpx.RequestError as e:
            logger.error(f"Request error: {e}")
            raise ValueError(f"Network error")

    async def create_label(self, order: Order) -> Dict[str, Any]:
        """
        Create a shipping label via API
        """
        try:
            payload = self._prepare_label_payload(order)
            
            response = await self._request_with_retry("POST", "/v1/labels", json=payload)
            
            label_data = response.json()
            
            logger.info(
                f"Label created successfully: {label_data.get('label_id')} "
                f"for tracking {label_data.get('tracking_number')}"
            )
            
            return label_data
            
        except httpx.HTTPStatusError as e:
            error_detail = e.response.json() if e.response.text else str(e)
            logger.error(f"API error: {error_detail}")
            user_error = self._parse_error_message(error_detail)
            raise ValueError(f"Failed to create label: {user_error}")
        except httpx.RequestError as e:
            logger.error(f"Request error: {e}")
            raise ValueError(f"Network error")
    
    def _parse_error_message(self, error_detail) -> str:
        """Parse error detail and return user-friendly message"""
        raw_message = ""
        
        if isinstance(error_detail, dict):
            errors = error_detail.get("errors", [])
            if errors:
                # Get first error message
                first_error = errors[0] if isinstance(errors, list) else errors
                if isinstance(first_error, dict):
                    raw_message = first_error.get("message", "Unknown error")
        
        if not raw_message:
            raw_message = str(error_detail)[:100]
        
        # Convert technical messages to user-friendly
        raw_lower = raw_message.lower()
        
        # Carrier system errors
        if "unavailable" in raw_lower or "try again later" in raw_lower:
            return "Carrier temporarily unavailable. Please try again in a few minutes."
        
        # XML/System errors  
        if "xml" in raw_lower or "system" in raw_lower:
            return "Carrier service temporarily unavailable."
        
        # Address errors
        if "address" in raw_lower:
            return "Address validation failed. Please check the address."
        
        # Weight/dimensions errors
        if "weight" in raw_lower or "dimension" in raw_lower:
            return "Invalid package weight or dimensions."
        
        # Rate errors
        if "rate" in raw_lower:
            return "Rate no longer available. Please select a new rate."
        
        # Generic carrier error
        if "carrier" in raw_lower:
            return "Carrier error. Please try again or select a different carrier."
        
        # Return original if no match (truncated)
        return raw_message[:80] if len(raw_message) > 80 else raw_message
    
    def _prepare_label_payload(self, order: Order) -> Dict[str, Any]:
        """Prepare request payload for ShipEngine label creation"""
        # Ensure phone numbers are in correct format (required for FedEx/UPS)
        ship_from_phone = order.shipFromAddress.phone or "555-555-5555"
        ship_to_phone = order.shipToAddress.phone or "555-555-5555"
        
        # Clean phone format - remove non-digits except + and -
        def clean_phone(phone):
            if not phone:
                return "555-555-5555"
            # Keep only digits, +, -, spaces, parentheses
            cleaned = ''.join(c for c in phone if c.isdigit() or c in '+-() ')
            return cleaned if cleaned else "555-555-5555"
        
        ship_from_phone = clean_phone(ship_from_phone)
        ship_to_phone = clean_phone(ship_to_phone)
        
        payload = {
            "shipment": {
                "validate_address": "no_validation",  # Already validated in bot flow
                "service_code": order.serviceCode,
                "ship_from": {
                    "name": order.shipFromAddress.name,
                    "company_name": "-",  # Dash to override carrier defaults (SITKAGEAR fix)
                    "address_line1": order.shipFromAddress.addressLine1,
                    "address_line2": order.shipFromAddress.addressLine2 or "",
                    "city_locality": order.shipFromAddress.city,
                    "state_province": order.shipFromAddress.state.upper()[:2],  # Ensure 2-letter state code
                    "postal_code": order.shipFromAddress.postalCode,
                    "country_code": order.shipFromAddress.countryCode.upper()[:2],  # Ensure 2-letter country
                    "phone": ship_from_phone,
                },
                "ship_to": {
                    "name": order.shipToAddress.name,
                    "company_name": "-",  # Dash to override carrier defaults (SITKAGEAR fix)
                    "address_line1": order.shipToAddress.addressLine1,
                    "address_line2": order.shipToAddress.addressLine2 or "",
                    "city_locality": order.shipToAddress.city,
                    "state_province": order.shipToAddress.state.upper()[:2],  # Ensure 2-letter state code
                    "postal_code": order.shipToAddress.postalCode,
                    "country_code": order.shipToAddress.countryCode.upper()[:2],  # Ensure 2-letter country
                    "phone": ship_to_phone,
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
        
        # Add carrier_id if available
        if order.carrier_id:
            payload["shipment"]["carrier_id"] = order.carrier_id
        
        return payload
    
    async def close(self):
        """Close the HTTP client connection"""
        await self.client.aclose()