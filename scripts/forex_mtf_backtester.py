import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Pairs to analyze
PAIRS = ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X", "USDCAD=X"]

class ForexMTFBacktester:
    def __init__(self, data_15m: pd.DataFrame, data_1h: pd.DataFrame):
        self.df_15m = data_15m.copy()
        self.df_1h = data_1h.copy()
        self.df_15m.index = self.df_15m.index.tz_convert('UTC')
        self.df_1h.index = self.df_1h.index.tz_convert('UTC')

    def calculate_indicators_1h(self):
        # 1H 200 EMA for Macro Trend
        self.df_1h['ema_200'] = self.df_1h['Close'].ewm(span=200, adjust=False).mean()
        
    def calculate_indicators_15m(self):
        # 15M 50 EMA and 20 EMA for Micro Trend/Pullbacks
        self.df_15m['ema_20'] = self.df_15m['Close'].ewm(span=20, adjust=False).mean()
        self.df_15m['ema_50'] = self.df_15m['Close'].ewm(span=50, adjust=False).mean()
        
        # Stochastic Oscillator (14, 3, 3) for exhaustion detection
        low_min = self.df_15m['Low'].rolling(window=14).min()
        high_max = self.df_15m['High'].rolling(window=14).max()
        self.df_15m['%K'] = (self.df_15m['Close'] - low_min) * 100 / (high_max - low_min)
        self.df_15m['%D'] = self.df_15m['%K'].rolling(window=3).mean()
        
        # MACD (12, 26, 9) for Momentum entry confirmation
        exp1 = self.df_15m['Close'].ewm(span=12, adjust=False).mean()
        exp2 = self.df_15m['Close'].ewm(span=26, adjust=False).mean()
        self.df_15m['macd'] = exp1 - exp2
        self.df_15m['signal'] = self.df_15m['macd'].ewm(span=9, adjust=False).mean()
        self.df_15m['histogram'] = self.df_15m['macd'] - self.df_15m['signal']

    def run_backtest(self, symbol) -> dict:
        self.calculate_indicators_1h()
        self.calculate_indicators_15m()
        
        # Merge 1H Trend onto 15M dataframe
        self.df_1h['macro_trend'] = np.where(self.df_1h['Close'] > self.df_1h['ema_200'], 1, -1)
        
        # Resample the 1H trend down to the 15m index using forward fill
        df_merged = pd.merge_asof(
            self.df_15m.sort_index(), 
            self.df_1h[['macro_trend']].sort_index(),
            left_index=True, 
            right_index=True, 
            direction='backward'
        )

        df_merged.dropna(inplace=True)
        
        trades = []
        in_trade = False
        entry_price = 0
        sl_price = 0
        tp_price = 0
        trade_type = ""
        
        # Strict Risk parameters
        is_jpy = "JPY" in symbol
        pip_multiplier = 100 if is_jpy else 10000
        
        # 1:1.5 to 1:2 R:R
        target_pips = 15
        stop_pips = 10 
        
        for index, row in df_merged.iterrows():
            if in_trade:
                # Check outcome
                if trade_type == "BUY":
                    if row['High'] >= tp_price:
                        trades.append(1)
                        in_trade = False
                    elif row['Low'] <= sl_price:
                        trades.append(-1)
                        in_trade = False
                elif trade_type == "SELL":
                    if row['Low'] <= tp_price:
                        trades.append(1)
                        in_trade = False
                    elif row['High'] >= sl_price:
                        trades.append(-1)
                        in_trade = False
                continue
                
            # Long Setup Conditions:
            # 1. Macro Trend is UP (1H Price > 1H 200 EMA)
            # 2. Micro Trend is UP (15m 20 EMA > 15m 50 EMA)
            # 3. Pullback to Value (Price dipped below 20 EMA but closed above 50 EMA)
            # 4. Exhaustion (Stochastic %D recently dipped below 25 and is crossing up)
            # 5. Momentum Shift (MACD Histogram is > 0 and expanding)
            
            if row['macro_trend'] == 1 and row['ema_20'] > row['ema_50']:
                if row['Close'] > row['ema_50'] and row['Close'] < row['ema_20']:
                    if row['%D'] < 30 and row['histogram'] > 0:
                        in_trade = True
                        trade_type = "BUY"
                        entry_price = row['Close']
                        sl_price = entry_price - (stop_pips / pip_multiplier)
                        tp_price = entry_price + (target_pips / pip_multiplier)
                        continue
                        
            # Short Setup Conditions
            if row['macro_trend'] == -1 and row['ema_20'] < row['ema_50']:
                if row['Close'] < row['ema_50'] and row['Close'] > row['ema_20']:
                    if row['%D'] > 70 and row['histogram'] < 0:
                        in_trade = True
                        trade_type = "SELL"
                        entry_price = row['Close']
                        sl_price = entry_price + (stop_pips / pip_multiplier)
                        tp_price = entry_price - (target_pips / pip_multiplier)
                        continue
                        
        wins = sum(1 for t in trades if t == 1)
        losses = sum(1 for t in trades if t == -1)
        total = wins + losses
        win_rate = (wins / total * 100) if total > 0 else 0
        
        return {
            "symbol": symbol,
            "total_trades": total,
            "wins": wins,
            "losses": losses,
            "win_rate": win_rate
        }

if __name__ == "__main__":
    end_date = datetime.now()
    start_date = end_date - timedelta(days=59) # max 60 days for 15m yfinance
    
    results = []
    
    print("Initiating Multi-Timeframe High-Probability Audit...")
    
    for symbol in PAIRS:
        print(f"Fetching {symbol} 15m and 1h data...")
        try:
            df_15m = yf.download(symbol, start=start_date, end=end_date, interval="15m", progress=False)
            df_1h = yf.download(symbol, start=start_date, end=end_date, interval="1h", progress=False)
            
            if df_15m.empty or df_1h.empty:
                continue
                
            tester = ForexMTFBacktester(df_15m, df_1h)
            res = tester.run_backtest(symbol)
            results.append(res)
            print(f"[{symbol}] TRADES: {res['total_trades']} | WIN RATE: {res['win_rate']:.2f}%")
        except Exception as e:
            print(f"Failed {symbol}: {e}")
            
    with open("mtf_forex_results.txt", "w") as f:
        f.write("=== PHASE 33 MULTI-TIMEFRAME BACKTEST RESULTS ===\n")
        for r in results:
            f.write(f"- {r['symbol']}: {r['total_trades']} Trades | {r['win_rate']:.2f}% Win Rate\n")
