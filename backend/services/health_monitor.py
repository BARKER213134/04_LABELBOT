import asyncio
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

ADMIN_TELEGRAM_ID = 7066790254
CHECK_INTERVAL_SECONDS = 3600  # 1 hour


async def _check_database():
    """Check MongoDB connection"""
    try:
        from database import Database
        db = Database.db
        if db is None:
            return False, "DB not initialized"
        result = await db.command("ping")
        if result.get("ok") == 1:
            users_count = await db.users.count_documents({})
            orders_count = await db.orders.count_documents({})
            return True, f"Users: {users_count}, Orders: {orders_count}"
        return False, "Ping failed"
    except Exception as e:
        return False, str(e)


async def _check_bot():
    """Check Telegram bot status"""
    try:
        from routes.telegram import _production_app, _sandbox_app, _get_current_environment_cached
        from database import Database
        env = await _get_current_environment_cached(Database.db)
        if env == "production":
            loaded = _production_app is not None
        else:
            loaded = _sandbox_app is not None
        if loaded:
            return True, f"Env: {env}, loaded"
        return False, f"Env: {env}, NOT loaded"
    except Exception as e:
        return False, str(e)


async def _check_webhook():
    """Check Telegram webhook status"""
    try:
        import os
        import httpx
        token = os.environ.get("TELEGRAM_BOT_TOKEN_PROD", "")
        if not token:
            return False, "No prod token"
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"https://api.telegram.org/bot{token}/getWebhookInfo")
            data = resp.json()
            if data.get("ok"):
                result = data["result"]
                pending = result.get("pending_update_count", 0)
                last_error = result.get("last_error_message", "")
                last_error_date = result.get("last_error_date", 0)

                # Only report error if it happened within the last 10 minutes
                now_ts = int(datetime.now(timezone.utc).timestamp())
                error_age = now_ts - last_error_date if last_error_date else 999999

                if last_error and error_age < 600:
                    mins_ago = error_age // 60
                    return False, f"Error {mins_ago}m ago: {last_error}"
                return True, f"OK, Pending: {pending}"
        return False, "API error"
    except Exception as e:
        return False, str(e)


async def _check_admin_api():
    """Check admin API endpoints"""
    try:
        import httpx
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get("http://127.0.0.1:8001/api/health")
            if resp.status_code == 200:
                return True, "API healthy"
            return False, f"HTTP {resp.status_code}"
    except Exception as e:
        return False, str(e)


async def _send_admin_report(results):
    """Send health report to admin via Telegram API directly"""
    import os
    import httpx

    now = datetime.now(timezone.utc).strftime("%d.%m.%Y %H:%M UTC")

    all_ok = all(ok for ok, _ in results.values())

    if all_ok:
        header = "✅ СИСТЕМА РАБОТАЕТ"
    else:
        header = "🔴 ОБНАРУЖЕНЫ ПРОБЛЕМЫ"

    lines = [
        "━━━━━━━━━━━━━━━━━━━━",
        f"🔍 {header}",
        "━━━━━━━━━━━━━━━━━━━━",
        f"⏰ {now}",
        "",
    ]

    checks = {
        "database": ("💾 База данных", results.get("database", (False, "not checked"))),
        "bot": ("🤖 Telegram бот", results.get("bot", (False, "not checked"))),
        "webhook": ("🔗 Webhook", results.get("webhook", (False, "not checked"))),
        "api": ("🌐 API сервер", results.get("api", (False, "not checked"))),
    }

    for key, (label, (ok, detail)) in checks.items():
        status = "✅" if ok else "❌"
        lines.append(f"{status} {label}")
        lines.append(f"    {detail}")
        lines.append("")

    text = "\n".join(lines)

    token = os.environ.get("TELEGRAM_BOT_TOKEN_PROD", "")
    if not token:
        logger.warning("[MONITOR] No TELEGRAM_BOT_TOKEN_PROD, cannot send report")
        return

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": ADMIN_TELEGRAM_ID, "text": text}
            )
    except Exception as e:
        logger.error(f"[MONITOR] Failed to send report: {e}")


async def run_health_check():
    """Run all health checks and send report"""
    logger.info("[MONITOR] Running health check...")

    results = {}
    results["database"] = await _check_database()
    results["bot"] = await _check_bot()
    results["webhook"] = await _check_webhook()
    results["api"] = await _check_admin_api()

    await _send_admin_report(results)
    return results


async def health_monitor_loop():
    """Background loop: check health every hour"""
    # Wait 5 minutes after startup before first check
    # (avoids spam if pod restarts frequently)
    await asyncio.sleep(300)

    while True:
        try:
            await run_health_check()
        except Exception as e:
            logger.error(f"[MONITOR] Health check error: {e}")

        await asyncio.sleep(CHECK_INTERVAL_SECONDS)
