class PipCalibrator:
    @staticmethod
    def get_pip_size(symbol: str) -> float:
        """
        Returns the decimal value of 1 pip for a given symbol.
        Standard Forex: 0.0001
        JPY Pairs: 0.01
        Gold/Silver: 0.1 / 0.01
        Crypto: 1.0 (1 pip = $1 move)
        """
        s = symbol.upper()
        if "BTC" in s or "ETH" in s:
            return 1.0
        if "JPY" in s:
            return 0.01
        if "XAU" in s:
            return 0.1
        if "XAG" in s:
            return 0.01
        return 0.0001

    @staticmethod
    def get_point_value(symbol: str) -> float:
        """
        Returns the $ value of a 1.0 price move per 1.0 standard lot.
        Forex Majors/Minors: $10.00 (Standard lot 100k)
        Indices (NAS100/US30): $100.00 (Standard lot 100 units on E8)
        Crypto (BTC/ETH): $1.00 (Standard lot 1 unit)
        """
        s = symbol.upper()
        if "NAS" in s or "USTEC" in s or "US30" in s or "USI" in s:
            return 5.0 # E8 TradeLocker uses Contract Size 5 ($5/point per lot)
        if "BTC" in s or "ETH" in s:
            return 1.0 # Standard 1 unit per lot
        return 10.0 # Default for Forex Majors ($10/pip per lot)

    @staticmethod
    def calculate_lots(risk_usd: float, sl_points: float, point_value: float) -> float:
        """
        risk_usd: amount to risk (e.g., $50)
        sl_points: stop loss distance in points/pips (e.g., 10 points or 15 pips)
        point_value: $ value per 1.0 move for 1.0 lot
        """
        if sl_points <= 0 or point_value <= 0:
            return 0.01
            
        raw_lots = risk_usd / (sl_points * point_value)
        return round(max(0.01, raw_lots), 2)
