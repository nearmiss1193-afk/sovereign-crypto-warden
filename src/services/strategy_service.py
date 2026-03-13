import pandas as pd
from datetime import datetime
from typing import Optional

class StrategyService:
    def __init__(self, high_confidence_threshold=72):
        self.threshold = high_confidence_threshold
        # Windows in EST/EDT
        self.sessions = {
            "London_SB": {"start": 3, "end": 4},
            "NY Open":   {"start": 8, "end": 11},
            "NY_AM_SB":  {"start": 10, "end": 11},
            "NY_PM_SB":  {"start": 14, "end": 15}
        }
        self.executed_today = {} # {"date_symbol_session": True}

    def is_in_silver_bullet_window(self, now_utc=None) -> str:
        if now_utc is None:
            now_utc = datetime.utcnow()
        
        # Approximate ET (using -4 for EDT, common for ICT setups)
        # Note: In production, consider pytz or similar for DST protection.
        hour_et = (now_utc.hour - 4) % 24
        
        for name, window in self.sessions.items():
            if window["start"] <= hour_et < window["end"]:
                return name
        return None

    def detect_setup(self, df: pd.DataFrame, symbol: str = "EURUSD", l2_data: dict = None) -> dict:
        """
        Sovereign Multi-Strategy Detector:
        ICT Silver Bullet + Live Traders 3-Bar Play + L2 Imbalance.
        """
        now = datetime.utcnow()
        day_of_week = now.weekday()

        is_index = any(x in symbol.upper() for x in ["NAS", "USTEC", "US30", "USI"])
        is_jpy = "JPY" in symbol.upper()
        is_crypto = any(x in symbol.upper() for x in ["BTC", "ETH"])

        if is_index and day_of_week == 3: return None
        if len(df) < 10: return None # Need more history for ending volume

        pip_ref = 1.0 if (is_index or is_crypto) else (0.01 if is_jpy else 0.0001)

        # --- A+ SETUP 1: ICT Silver Bullet (MSS + FVG) ---
        mss_bull = df.iloc[-1]['Close'] > df.iloc[-4:-1]['High'].max()
        fvg_bull = df.iloc[-3]['High'] < df.iloc[-1]['Low']
        
        if mss_bull and fvg_bull:
            res = {
                "type": "BUY", "entry": (df.iloc[-1]['Low'] + df.iloc[-3]['High']) / 2,
                "sl_pips": abs(df.iloc[-1]['Low'] - df.iloc[-3]['High']) / pip_ref,
                "reason": "ICT Silver Bullet (Bullish)"
            }
            return self._apply_l2_filter(res, l2_data)

        # --- A+ SETUP 2: Live Traders 3-Bar Play ---
        tbp = self._detect_3_bar_play(df)
        if tbp:
            res = {
                "type": tbp["type"], "entry": df.iloc[-1]['Close'],
                "sl_pips": abs(df.iloc[-1]['Close'] - df.iloc[-2]['Low']) / pip_ref,
                "reason": f"Manual Setup: {tbp['reason']}"
            }
            return self._apply_l2_filter(res, l2_data)

        return None

    def _detect_3_bar_play(self, df: pd.DataFrame) -> Optional[dict]:
        """Detects expansion -> rest -> expansion pattern."""
        b1, b2, b3 = df.iloc[-3], df.iloc[-2], df.iloc[-1]
        b1_range = b1['High'] - b1['Low']
        if b1_range == 0: return None
        
        # Bullish: Igniting bar -> Small inside bar in top 1/3 -> Breakout
        if b1['Close'] > b1['Open'] and b2['High'] <= b1['High'] and b2['Low'] >= b1['Low'] + (b1_range * 0.6):
            if b3['Close'] > b1['High'] and b3['Volume'] > b2['Volume']:
                return {"type": "BUY", "reason": "3-Bar Play Continuation"}
        
        # Bearish: Ending bar -> Small inside bar in bottom 1/3 -> Breakdown
        if b1['Close'] < b1['Open'] and b2['Low'] >= b1['Low'] and b2['High'] <= b1['Low'] + (b1_range * 0.4):
            if b3['Close'] < b1['Low'] and b3['Volume'] > b2['Volume']:
                return {"type": "SELL", "reason": "3-Bar Play Continuation"}
        return None

    def _apply_l2_filter(self, setup: dict, l2_data: dict) -> dict:
        """Applies Level 2 Order Book Imbalance check as a final guard."""
        if not l2_data: return setup
        
        imbalance = l2_data.get("imbalance", 1.0)
        side = setup["type"]
        
        # Guard: Don't Long if sellers are pinning price (imbalance < 0.8)
        if side == "BUY" and imbalance < 0.8:
            return None # Blocked by L2 Order flow
        # Guard: Don't Short if buyers are pinning price (imbalance > 1.2)
        if side == "SELL" and imbalance > 1.2:
            return None 
            
        setup["l2_confirmed"] = True
        setup["imbalance"] = imbalance
        return setup

    def check_session_cap(self, symbol, session, date_str):
        key = f"{date_str}_{symbol}_{session}"
        if self.executed_today.get(key):
            return False
        return True

    def mark_session_executed(self, symbol, session, date_str):
        key = f"{date_str}_{symbol}_{session}"
        self.executed_today[key] = True
