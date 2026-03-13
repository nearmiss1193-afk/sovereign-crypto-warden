import pandas as pd
import numpy as np

class ReversionWarden:
    def __init__(self, rsi_period=9, overbought=70, oversold=30):
        self.rsi_period = rsi_period
        self.overbought = overbought
        self.oversold = oversold

    def calculate_rsi(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty or len(df) <= self.rsi_period:
            return df
            
        # Parse close prices (TradeLocker format: [time, open, high, low, close, volume])
        if 'c' not in df.columns and len(df.columns) >= 5:
            # Native array structure if converted straight to DF
            df['c'] = df.iloc[:, 4]
            
        close_delta = df['c'].astype(float).diff()

        up = close_delta.clip(lower=0)
        down = -1 * close_delta.clip(upper=0)

        # Smooth Moving Average (Wilder's RSI)
        ma_up = up.rolling(window=self.rsi_period, min_periods=self.rsi_period).mean()
        ma_down = down.rolling(window=self.rsi_period, min_periods=self.rsi_period).mean()

        # Handle division by zero
        rs = ma_up / ma_down
        df['RSI'] = 100 - (100 / (1 + rs))
        
        return df

    def detect_setup(self, df: pd.DataFrame, symbol: str) -> dict:
        """
        Detects RSI Mean Reversion anomalies on the 1-Hour candle.
        RSI <= 30 -> BUY
        RSI >= 70 -> SELL
        Requires the candle to be fully closed.
        """
        df = self.calculate_rsi(df)
        if df.empty or 'RSI' not in df.columns or len(df) < 2:
            return None
            
        # Get the deeply confirmed closed candle (Current candle is forming, so we use -2)
        closed_candle = df.iloc[-2]
        rsi_value = closed_candle['RSI']
        
        # Failsafe NaN check
        if pd.isna(rsi_value):
            return None
            
        close_price = float(closed_candle['c'])
        
        setup = None
        if rsi_value <= self.oversold:
            setup = {
                "type": "BUY",
                "confidence_reason": f"RSI({self.rsi_period}) mathematically oversold at {round(rsi_value, 2)}",
                "entry": close_price,
                "sl_pips": 200 # Placeholder baseline, wsgi scaler calculates dynamic
            }
        elif rsi_value >= self.overbought:
            setup = {
                "type": "SELL",
                "confidence_reason": f"RSI({self.rsi_period}) mathematically overbought at {round(rsi_value, 2)}",
                "entry": close_price,
                "sl_pips": 200
            }
            
        return setup
