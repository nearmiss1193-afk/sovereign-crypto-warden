import os
import resend

class SovereignMailer:
    """
    Sovereign Overwatch System (Phase 34.2):
    Fires ultra-fast HTML execution receipts directly to the user's phone via email.
    Leverages Resend API for assured 100% deliverability.
    """
    def __init__(self):
        self.enabled = False
        self.api_key = os.environ.get("RESEND_API_KEY")
        self.target_email = os.environ.get("OWNER_EMAIL", "dan@aiserviceco.com") # User's personal inbox
        
        if self.api_key:
            self.enabled = True
            resend.api_key = self.api_key
            print("[EmailOverwatch] Sovereign Resend Mailer initialized and active.")
        else:
            print("[EmailOverwatch] System DISABLED: Missing RESEND_API_KEY")

    def _fire_async_email(self, subject: str, html_body: str):
        """Dispatches an email non-blocking."""
        if not self.enabled:
            return
            
        try:
            # We use owner@aiserviceco.com as the verified sending identity
            resend.Emails.send({
                "from": "Sovereign Prime <owner@aiserviceco.com>",
                "to": [self.target_email],
                "subject": subject,
                "html": html_body
            })
        except Exception as e:
            print(f"[EmailOverwatch] Delivery Failure: {e}")

    def notify_trade_fired(self, project: str, symbol: str, direction: str, price: float, risk_usd: float):
        subject = f"🟢 Sovereign Execution: {direction} {symbol}"
        html = f"""
        <div style="font-family: Arial, sans-serif; padding: 20px; border-left: 5px solid #00E676; background-color: #0f172a; color: white;">
            <h2>Trade Executed successfully.</h2>
            <p><b>Project Engine:</b> {project}</p>
            <p><b>Asset:</b> {direction} {symbol}</p>
            <p><b>Entry Price:</b> {price}</p>
            <p><b>Risk Capital:</b> ${risk_usd:.2f}</p>
        </div>
        """
        # Execute asynchronously in background immediately
        import threading
        threading.Thread(target=self._fire_async_email, args=(subject, html), daemon=True).start()
        
    def notify_warden_block(self, project: str, symbol: str, direction: str, reason: str):
        subject = f"🛡️ Sovereign Blocked: {direction} {symbol}"
        html = f"""
        <div style="font-family: Arial, sans-serif; padding: 20px; border-left: 5px solid #F59E0B; background-color: #0f172a; color: white;">
            <h2>Warden Overrode Execution.</h2>
            <p><b>Project Engine:</b> {project}</p>
            <p><b>Attempted Action:</b> {direction} {symbol}</p>
            <p><b>Reason:</b> {reason}</p>
        </div>
        """
        import threading
        threading.Thread(target=self._fire_async_email, args=(subject, html), daemon=True).start()

    def notify_emergency(self, project: str, reason: str):
        subject = f"⚠️ SOVEREIGN EMERGENCY STOP ⚠️"
        html = f"""
        <div style="font-family: Arial, sans-serif; padding: 20px; border-left: 5px solid #EF4444; background-color: #450a0a; color: white;">
            <h2>CRITICAL HALT INITIATED</h2>
            <p><b>Project Engine:</b> {project}</p>
            <p><b>Trigger Reason:</b> {reason}</p>
            <p><b>Status:</b> All Autonomous Trading Halted Immediately.</p>
        </div>
        """
        import threading
        threading.Thread(target=self._fire_async_email, args=(subject, html), daemon=True).start()
