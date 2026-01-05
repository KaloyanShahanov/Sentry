#webhook = https://discord.com/api/webhooks/1457691651316121600/ZEfoCvufpGiAF8IC2cCeuIrmk_QH-ogzFwiCJiiwD2BVmufwtkpYNHkCXcFb8XhzWsve 
from dotenv import load_dotenv
load_dotenv()
import os
import requests
from logger_setup import setup_logger

logger = setup_logger("alerts")

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

def send_discord_alert(message: str) -> None:
    if not DISCORD_WEBHOOK_URL:
        logger.error("DISCORD_WEBHOOK_URL is not set.")
        raise RuntimeError("DISCORD_WEBHOOK_URL is not set.")

    try:
        resp = requests.post(DISCORD_WEBHOOK_URL, json={"content": message}, timeout=10)
        if resp.status_code == 204:
            logger.info("Discord alert sent successfully.")
            return
        logger.error(f"Discord webhook failed: {resp.status_code} {resp.text}")
        raise RuntimeError(f"Discord webhook failed: {resp.status_code} {resp.text}")
    except Exception:
        logger.exception("Discord webhook exception")
        raise
