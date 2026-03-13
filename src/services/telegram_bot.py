import os
import requests

class TelegramBot:
    """
    Sovereign Overwatch System:
    Instantly relays execution events, blocks, and emergencies to the user via Telegram.
    Requires TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in environment variables.
    """
    def __init__(self):
        self.enabled = False
        self.bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
        self.chat_id = os.environ.get("TELEGRAM_CHAT_ID")
        
        if self.bot_token and self.chat_id:
            self.enabled = True
            self.base_url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            print("[TelegramBot] Sovereign Overwatch System initialized and enabled.")
        else:
            print("[TelegramBot] Overwatch System DISABLED: Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID")

    def send_message(self, message: str):
        """Asynchronously fires a notification to Telegram."""
        if not self.enabled:
            return
            
        try:
            payload = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "HTML"
            }
            # Fire and forget (timeout 3s so it never lags the main thread)
            requests.post(self.base_url, json=payload, timeout=3.0)
        except Exception as e:
            print(f"[TelegramBot] Failed to send message: {e}")

    def notify_trade_fired(self, project: str, symbol: str, direction: str, price: float, risk_usd: float):
        msg = f"🟢 <b>TRADE FIRED</b>\n" \
              f"<b>Project:</b> {project}\n" \
              f"<b>Action:</b> {direction} {symbol}\n" \
              f"<b>Entry:</b> {price}\n" \
              f"<b>Risk:</b> ${risk_usd:.2f}"
        self.send_message(msg)
        
    def notify_warden_block(self, project: str, symbol: str, direction: str, reason: str):
        msg = f"🛡️ <b>WARDEN BLOCK</b>\n" \
              f"<b>Project:</b> {project}\n" \
              f"<b>Action:</b> {direction} {symbol}\n" \
              f"<b>Reason:</b> {reason}"
        self.send_message(msg)

    def notify_emergency(self, project: str, reason: str):
        msg = f"⚠️ <b>EMERGENCY STOP</b>\n" \
              f"<b>Project:</b> {project}\n" \
              f"<b>Reason:</b> {reason}\n" \
              f"<b>Action:</b> ALL TRADING HALTED."
        self.send_message(msg)
