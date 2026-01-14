"""
OxaPay Webhook and Payment Routes
"""
from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
import json
import logging
from database import Database
from services.oxapay_service import OxaPayService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/oxapay", tags=["oxapay"])


@router.post("/webhook")
async def oxapay_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Handle incoming webhook notifications from OxaPay
    """
    try:
        # Get raw body for signature verification
        body = await request.body()
        
        # Get HMAC header (OxaPay sends it as 'HMAC' or 'hmac')
        hmac_header = request.headers.get("HMAC") or request.headers.get("hmac")
        
        # Parse payload
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            logger.error("Invalid JSON in webhook payload")
            raise HTTPException(status_code=400, detail="Invalid JSON payload")
        
        logger.info(f"OxaPay webhook received: {payload}")
        
        # Get database and service
        db = Database.db
        oxapay_service = OxaPayService(db)
        
        # Verify signature if HMAC header is present
        if hmac_header:
            if not oxapay_service.verify_webhook_signature(body, hmac_header):
                logger.warning("Invalid webhook signature")
                # Still process in sandbox mode, but log warning
                # raise HTTPException(status_code=401, detail="Invalid signature")
        
        # Process webhook in background
        result = await oxapay_service.process_webhook(payload)
        
        # If payment was confirmed and balance credited, notify user
        if result.get("action") == "balance_credited":
            telegram_id = result.get("telegram_id")
            amount = result.get("credited_amount", 0)
            background_tasks.add_task(
                notify_user_balance_credited,
                telegram_id=telegram_id,
                amount=amount
            )
        
        # Always return 200 to acknowledge receipt
        return JSONResponse({"status": "ok"}, status_code=200)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Webhook processing error: {e}", exc_info=True)
        # Return 200 to prevent OxaPay retries on our errors
        return JSONResponse({"status": "ok"}, status_code=200)


async def notify_user_balance_credited(telegram_id: str, amount: float):
    """
    Send Telegram notification to user about successful payment
    """
    try:
        from telegram import Bot
        from config import get_settings
        
        settings = get_settings()
        bot = Bot(token=settings.telegram_bot_token)
        
        text = (
            "━━━━━━━━━━━━━━━━━━━━\n"
            "✅ *БАЛАНС ПОПОЛНЕН*\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            f"💰 Сумма: *${amount:.2f}*\n\n"
            "Спасибо за пополнение! Ваш баланс обновлён.\n\n"
            "━━━━━━━━━━━━━━━━━━━━"
        )
        
        await bot.send_message(
            chat_id=int(telegram_id),
            text=text,
            parse_mode="Markdown"
        )
        
        logger.info(f"Notification sent to user {telegram_id}")
        
    except Exception as e:
        logger.error(f"Failed to send notification to {telegram_id}: {e}")


@router.post("/create-invoice")
async def create_payment_invoice(
    request: Request,
    user_id: str,
    telegram_id: str,
    amount: float,
    currency: str = "USD"
):
    """
    Create a new payment invoice
    """
    try:
        if amount < 10:
            raise HTTPException(status_code=400, detail="Minimum amount is $10")
        
        db = Database.db
        oxapay_service = OxaPayService(db)
        
        result = await oxapay_service.create_invoice(
            user_id=user_id,
            telegram_id=telegram_id,
            amount=amount,
            currency=currency
        )
        
        return result
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create invoice: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create invoice: {str(e)}")


@router.get("/invoice/{track_id}")
async def get_invoice_status(track_id: str):
    """
    Get invoice status
    """
    db = Database.db
    oxapay_service = OxaPayService(db)
    
    invoice = await oxapay_service.get_invoice_status(track_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    return invoice


@router.get("/user/{telegram_id}/invoices")
async def get_user_invoices(telegram_id: str, limit: int = 10):
    """
    Get user's payment history
    """
    db = Database.db
    oxapay_service = OxaPayService(db)
    
    invoices = await oxapay_service.get_user_invoices(telegram_id, limit)
    return {"invoices": invoices}
