import pandas as pd

class L2Service:
    """
    Sovereign L2 Service: Handles Order Book (DOM) analysis.
    Quantifies 'Market Whales' vs 'Retail Noise' via Bid/Ask Imbalance.
    """

    @staticmethod
    def analyze_order_book(depth: dict) -> dict:
        """
        Analyzes a Market Depth snapshot.
        Returns metrics for imbalance and liquidity density.
        """
        if not depth or not depth.get("bids") or not depth.get("asks"):
            return {"imbalance": 1.0, "spread": 0.0, "bias": "Neutral"}

        # 1. Volume Imbalance
        bid_vol = sum(float(b[1]) for b in depth["bids"])
        ask_vol = sum(float(a[1]) for a in depth["asks"])
        
        imbalance = 1.0
        if ask_vol > 0:
            imbalance = bid_vol / ask_vol
        else:
            imbalance = 2.0 # capped high bias

        # 2. Spread Detection
        best_bid = float(depth["bids"][0][0]) if depth["bids"] else 0
        best_ask = float(depth["asks"][0][0]) if depth["asks"] else 0
        spread = best_ask - best_bid

        # 3. Bias Determination
        bias = "Neutral"
        if imbalance > 1.5: bias = "Strong Bullish"
        elif imbalance > 1.1: bias = "Bullish"
        elif imbalance < 0.6: bias = "Strong Bearish"
        elif imbalance < 0.9: bias = "Bearish"

        return {
            "imbalance": round(imbalance, 2),
            "spread": round(spread, 5),
            "total_bid_vol": round(bid_vol, 2),
            "total_ask_vol": round(ask_vol, 2),
            "bias": bias
        }

    @staticmethod
    def get_confidence_multiplier(imbalance: float, side: str) -> float:
        """
        Adjusts strategy confidence based on L2 imbalance.
        """
        if side.upper() == "BUY":
            if imbalance > 1.5: return 1.2 # Boost confidence
            if imbalance < 0.8: return 0.5 # Reduce confidence (Strong Sellers)
        elif side.upper() == "SELL":
            if imbalance < 0.6: return 1.2 # Boost confidence
            if imbalance > 1.2: return 0.5 # Reduce confidence (Strong Buyers)
        
        return 1.0
