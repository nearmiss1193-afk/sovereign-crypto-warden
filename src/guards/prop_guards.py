import json
import os
from datetime import datetime, timedelta

class PropGuards:
    def __init__(self, prop_firm_mode="E8", news_blackout_mins=5, daily_profit_cap_pct=40.0):
        self.mode = prop_firm_mode
        self.news_blackout_mins = news_blackout_mins
        self.daily_profit_cap_pct = daily_profit_cap_pct
        self.recurring_news = [
            (4, 13, 30, "NFP / US Jobs"),
            (4, 13, 30, "US Unemployment Rate"),
            (1, 13, 30, "US CPI"),
            (2, 14,  0, "FOMC Rate Decision"),
            (2, 18, 30, "FOMC Press Conference"),
            (3, 13, 30, "US GDP"),
            (3, 13, 30, "US Jobless Claims"),
            (3, 15,  0, "ISM Manufacturing"),
            (0, 13, 30, "US Retail Sales"),
            (3, 12, 15, "ECB Rate Decision"),
            (3, 12, 45, "ECB Press Conference"),
            (3, 12,  0, "BoE Rate Decision"),
            (4, 23, 50, "BoJ Rate Decision"),
        ]
        self.extra_news = []
        self._load_extra_news()
        self.daily_tracker = {} # Persist this in a DB in production

    def _load_extra_news(self):
        try:
            raw = os.environ.get("NEWS_EVENTS_EXTRA", "")
            if raw:
                self.extra_news = json.loads(raw)
        except:
            pass

    def is_news_blackout(self, now_utc=None) -> dict:
        if now_utc is None:
            now_utc = datetime.utcnow()

        delta = timedelta(minutes=self.news_blackout_mins)

        return {"blocked": False, "reason": "News trading enabled (Alert only)"}

    def check_profit_cap(self, account_key, current_total_profit, current_day_profit) -> dict:
        """
        Logic from wsgi.py: today's profit cannot exceed X% of total profit.
        Only applies if total_profit > 10.0
        """
        if current_total_profit <= 10.0:
            return {"blocked": False, "reason": "Cap not active"}

        cap_amount = current_total_profit * (self.daily_profit_cap_pct / 100.0)
        
        if current_day_profit >= cap_amount:
            return {
                "blocked": True,
                "reason": f"DAILY PROFIT CAP: ${current_day_profit:.2f} >= ${cap_amount:.2f} ({self.daily_profit_cap_pct}%)"
            }
            
        return {"blocked": False, "reason": "Profit cap OK"}
