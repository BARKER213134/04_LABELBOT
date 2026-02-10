"""
OxaPay Crypto Payment Service
Handles cryptocurrency payment processing for balance top-ups
"""
import aiohttp
import logging
import uuid
import hmac
import hashlib
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from config import get_settings

logger = logging.getLogger(__name__)

OXAPAY_API_URL = "https://api.oxapay.com/merchants/request"
OXAPAY_INVOICE_INFO_URL = "https://api.oxapay.com/merchants/inquiry"

# Supported cryptocurrencies
SUPPORTED_CRYPTO = ["BTC", "ETH", "USDT", "LTC"]


class OxaPayService:
    """Service for OxaPay crypto payment operations"""
    
    def __init__(self, db):
        self.db = db
        settings = get_settings()
        self.merchant_api_key = settings.oxapay_merchant_api_key
        self.webhook_url = f"{settings.webhook_url.replace('/telegram/webhook', '/oxapay/webhook')}"
    
    async def create_invoice(
        self,
        user_id: str,
        telegram_id: str,
        amount: float,
        currency: str = "USD"
    ) -> Dict[str, Any]:
        """
        Create a new payment invoice via OxaPay API
        
        Args:
            user_id: Internal user ID
            telegram_id: Telegram user ID
            amount: Amount in fiat currency
            currency: Fiat currency code (USD)
        
        Returns:
            Dict with invoice details including payment URL
        """
        if amount < 10:
            raise ValueError("Minimum amount is $10")
        
        order_id = str(uuid.uuid4())
        
        # Prepare invoice request payload
        payload = {
            "merchant": self.merchant_api_key,
            "amount": amount,
            "currency": currency,
            "lifeTime": 60,  # 60 minutes
            "feePaidByPayer": 1,  # Payer covers fees
            "underPaidCover": 10,  # 10% tolerance
            "callbackUrl": self.webhook_url,
            "returnUrl": "https://t.me/whitelabel_shipping_bot",
            "orderId": order_id,
            "description": f"Balance top-up ${amount}",
        }
        
        logger.info(f"Creating OxaPay invoice: {payload}")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    OXAPAY_API_URL,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    result = await response.json()
                    logger.info(f"OxaPay response: {result}")
                    
                    if result.get("result") != 100:
                        error_msg = result.get("message", "Unknown error")
                        raise Exception(f"OxaPay error: {error_msg}")
                    
                    track_id = result.get("trackId")
                    payment_url = result.get("payLink")
                    
                    # Store invoice in database
                    invoice_doc = {
                        "user_id": user_id,
                        "telegram_id": telegram_id,
                        "order_id": order_id,
                        "track_id": track_id,
                        "amount": amount,
                        "currency": currency,
                        "status": "pending",
                        "payment_url": payment_url,
                        "created_at": datetime.now(timezone.utc),
                        "expires_at": None,
                        "paid_amount": None,
                        "paid_currency": None,
                        "tx_hash": None,
                        "confirmed": False
                    }
                    
                    await self.db.crypto_invoices.insert_one(invoice_doc)
                    
                    return {
                        "success": True,
                        "track_id": track_id,
                        "payment_url": payment_url,
                        "amount": amount,
                        "currency": currency,
                        "order_id": order_id
                    }
                    
        except aiohttp.ClientError as e:
            logger.error(f"OxaPay API request failed: {e}")
            raise Exception(f"Payment service unavailable: {str(e)}")
    
    async def get_invoice_status(self, track_id: str) -> Optional[Dict[str, Any]]:
        """
        Get invoice status from database
        """
        invoice = await self.db.crypto_invoices.find_one(
            {"track_id": track_id},
            {"_id": 0}
        )
        return invoice
    
    async def check_invoice_status_api(self, track_id: str) -> Dict[str, Any]:
        """
        Check invoice status directly from OxaPay API
        """
        payload = {
            "merchant": self.merchant_api_key,
            "trackId": track_id
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    OXAPAY_INVOICE_INFO_URL,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    result = await response.json()
                    return result
        except Exception as e:
            logger.error(f"Failed to check invoice status: {e}")
            return {"error": str(e)}
    
    def verify_webhook_signature(self, payload_bytes: bytes, hmac_header: str) -> bool:
        """
        Verify HMAC signature of incoming webhook
        """
        calculated_hmac = hmac.new(
            self.merchant_api_key.encode(),
            payload_bytes,
            hashlib.sha512
        ).hexdigest()
        
        return hmac.compare_digest(calculated_hmac.lower(), hmac_header.lower())
    
    async def process_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process webhook notification from OxaPay
        
        Returns:
            Dict with processing result
        """
        track_id = payload.get("trackId")
        status = payload.get("status")
        
        logger.info(f"Processing webhook: track_id={track_id}, status={status}")
        
        if not track_id:
            return {"success": False, "error": "Missing trackId"}
        
        # Get invoice from database
        invoice = await self.db.crypto_invoices.find_one({"track_id": track_id})
        if not invoice:
            logger.warning(f"Invoice not found for track_id: {track_id}")
            return {"success": False, "error": "Invoice not found"}
        
        # Status mappings from OxaPay
        # Waiting = waiting for payment
        # Confirming = payment received, waiting for confirmations
        # Paid = payment confirmed
        # Failed = payment failed
        # Expired = invoice expired
        
        if status in ["Paid", "paid"]:
            # Payment confirmed
            paid_amount = payload.get("amount", 0)
            paid_currency = payload.get("currency", "USD")
            tx_id = payload.get("txID", "")
            
            # Update invoice status
            await self.db.crypto_invoices.update_one(
                {"track_id": track_id},
                {
                    "$set": {
                        "status": "paid",
                        "paid_amount": float(paid_amount),
                        "paid_currency": paid_currency,
                        "tx_hash": tx_id,
                        "confirmed": True,
                        "confirmed_at": datetime.now(timezone.utc)
                    }
                }
            )
            
            # Credit user balance
            telegram_id = invoice.get("telegram_id")
            credit_amount = float(invoice.get("amount", 0))  # Use original USD amount
            
            if telegram_id and credit_amount > 0:
                # Update user balance
                result = await self.db.users.update_one(
                    {"telegram_id": telegram_id},
                    {
                        "$inc": {"balance": credit_amount},
                        "$push": {
                            "balance_history": {
                                "amount": credit_amount,
                                "type": "crypto_topup",
                                "reason": f"Crypto payment: {paid_currency}",
                                "tx_hash": tx_id,
                                "timestamp": datetime.now(timezone.utc)
                            }
                        }
                    }
                )
                
                if result.modified_count > 0:
                    logger.info(f"User {telegram_id} balance credited with ${credit_amount}")
                    return {
                        "success": True, 
                        "telegram_id": telegram_id,
                        "credited_amount": credit_amount,
                        "action": "balance_credited"
                    }
            
            return {"success": True, "action": "payment_confirmed"}
        
        elif status in ["Confirming", "confirming"]:
            # Payment received, waiting for confirmations
            await self.db.crypto_invoices.update_one(
                {"track_id": track_id},
                {"$set": {"status": "confirming"}}
            )
            return {"success": True, "action": "payment_confirming"}
        
        elif status in ["Expired", "expired"]:
            await self.db.crypto_invoices.update_one(
                {"track_id": track_id},
                {"$set": {"status": "expired"}}
            )
            return {"success": True, "action": "invoice_expired"}
        
        elif status in ["Failed", "failed"]:
            await self.db.crypto_invoices.update_one(
                {"track_id": track_id},
                {"$set": {"status": "failed"}}
            )
            return {"success": True, "action": "payment_failed"}
        
        else:
            logger.info(f"Unhandled status: {status}")
            return {"success": True, "action": "status_updated"}
    
    async def get_user_invoices(self, telegram_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get user's payment history
        """
        cursor = self.db.crypto_invoices.find(
            {"telegram_id": telegram_id},
            {"_id": 0}
        ).sort("created_at", -1).limit(limit)
        
        invoices = await cursor.to_list(length=limit)
        return invoices
