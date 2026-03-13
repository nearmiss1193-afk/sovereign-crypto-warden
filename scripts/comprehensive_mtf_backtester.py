import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings

warnings.filterwarnings('ignore')

PAIRS = ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X", "USDCAD=X", "USDCHF=X"]

# Timeframe matrices to test: (Entry_TF, Trend_TF, Risk_Reward, Stop_Pips)
CONFIGS = [
    ("1m", "5m", 1.5, 5),    # Hyper-Scalping
    ("2m", "15m", 1.5, 7),   # Micro-Scalping
    ("5m", "1h", 2.0, 10),   # Standard Scalping 
    ("15m", "4h", 2.0, 15),  # Intraday 
    ("1h", "1d", 2.5, 25),   # Swing
]

class SuperMTFBacktester:
    def __init__(self, data_entry: pd.DataFrame, data_trend: pd.DataFrame, config: tuple):
        self.df_entry = data_entry.copy()
        self.df_trend = data_trend.copy()
        
        # Total timezone annihilation: we let the solve loop handle it.
        pass
            
        self.entry_tf = config[0]
        self.trend_tf = config[1]
        self.rr_ratio = config[2]
        self.stop_pips = config[3]
        
    def prepare_data(self):
        # -- TREND TIMEFRAME INDICATORS --
        self.df_trend['ema_200'] = self.df_trend['Close'].ewm(span=200, adjust=False).mean()
        self.df_trend['ema_50'] = self.df_trend['Close'].ewm(span=50, adjust=False).mean()
        
        # Define Macro Trend (1 = UP, -1 = DOWN, 0 = RANGE)
        conditions_trend = [
            (self.df_trend['Close'] > self.df_trend['ema_50']) & (self.df_trend['ema_50'] > self.df_trend['ema_200']),
            (self.df_trend['Close'] < self.df_trend['ema_50']) & (self.df_trend['ema_50'] < self.df_trend['ema_200'])
        ]
        self.df_trend['macro_trend'] = np.select(conditions_trend, [1, -1], default=0)
        
        # -- ENTRY TIMEFRAME INDICATORS --
        self.df_entry['ema_20'] = self.df_entry['Close'].ewm(span=20, adjust=False).mean()
        self.df_entry['ema_50'] = self.df_entry['Close'].ewm(span=50, adjust=False).mean()
        
        # RSI 14
        delta = self.df_entry['Close'].diff()
        up = delta.clip(lower=0)
        down = -1 * delta.clip(upper=0)
        ma_up = up.rolling(14).mean()
        ma_down = down.rolling(14).mean()
        rs = ma_up / ma_down
        self.df_entry['rsi'] = 100 - (100 / (1 + rs))
        
        # MACD
        exp1 = self.df_entry['Close'].ewm(span=12, adjust=False).mean()
        exp2 = self.df_entry['Close'].ewm(span=26, adjust=False).mean()
        macd = exp1 - exp2
        signal = macd.ewm(span=9, adjust=False).mean()
        self.df_entry['macd_hist'] = macd - signal

    def solve(self, symbol) -> dict:
        self.prepare_data()
        
        # Absolute C-Level NumPy iteration bypass
        df_merged = self.df_entry.copy()
        trend_times = self.df_trend.index.values
        trend_vals = self.df_trend['macro_trend'].values
        
        macro_col = []
        t_idx = 0
        for current_time in df_merged.index.values:
            while t_idx < len(trend_times) - 1 and trend_times[t_idx + 1] <= current_time:
                t_idx += 1
            if len(trend_times) > 0 and trend_times[t_idx] <= current_time:
                macro_col.append(trend_vals[t_idx])
            else:
                macro_col.append(0)
                
        df_merged['macro_trend'] = macro_col
        # Drop rows where indicators are not yet calculated
        df_merged.dropna(inplace=True)
        
        is_jpy = "JPY" in symbol
        pip_multiplier = 100 if is_jpy else 10000
        
        trades = []
        in_trade = False
        trade_type = ""
        entry_price = 0
        sl_price = 0
        tp_price = 0
        
        for index, row in df_merged.iterrows():
            if in_trade:
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
                
            # Entry Logic:
            # 1. Macro Trend aligns
            # 2. Pullback occurred (RSI dip/peak)
            # 3. Momentum aligns (MACD Hist)
            
            # LONG SETUP
            if row['macro_trend'] == 1 and row['ema_20'] > row['ema_50']:
                if row['rsi'] < 45 and row['macd_hist'] > 0:
                    in_trade = True
                    trade_type = "BUY"
                    entry_price = row['Close']
                    sl_price = entry_price - (self.stop_pips / pip_multiplier)
                    tp_price = entry_price + ((self.stop_pips * self.rr_ratio) / pip_multiplier)
                    continue
                    
            # SHORT SETUP
            if row['macro_trend'] == -1 and row['ema_20'] < row['ema_50']:
                if row['rsi'] > 55 and row['macd_hist'] < 0:
                    in_trade = True
                    trade_type = "SELL"
                    entry_price = row['Close']
                    sl_price = entry_price + (self.stop_pips / pip_multiplier)
                    tp_price = entry_price - ((self.stop_pips * self.rr_ratio) / pip_multiplier)
                    continue

        wins = sum(1 for t in trades if t == 1)
        losses = sum(1 for t in trades if t == -1)
        total = wins + losses
        win_rate = (wins / total * 100) if total > 0 else 0
        
        return {
            "symbol": symbol,
            "entry_tf": self.entry_tf,
            "trend_tf": self.trend_tf,
            "total_trades": total,
            "wins": wins,
            "losses": losses,
            "win_rate": win_rate,
            "rr": self.rr_ratio,
            "profit_factor": (wins * self.rr_ratio) / losses if losses > 0 else float('inf')
        }

if __name__ == "__main__":
    print("🚀 SOVEREIGN PRIME MULTI-TIMEFRAME QUANTITATIVE AUDIT 🚀")
    master_results = []
    
    # We fetch max exact historical bounds per timeframe
    now = datetime.utcnow()
    
    # Timeframe fetch mapping (string -> (yf_interval, timedelta_days))
    fetch_map = {
        "1m": ("1m", 6),       # 7 days max
        "2m": ("2m", 59),      # 60 days max
        "5m": ("5m", 59),      # 60 days max
        "15m": ("15m", 59),    # 60 days max
        "1h": ("1h", 720),     # 730 days max
        "4h": ("1h", 720),     # Synthesized from 1H
        "1d": ("1d", 3000)     # Long term
    }
    
    cache = {sym: {} for sym in PAIRS}
    
    for symbol in PAIRS:
        print(f"\nDownloading dataset for {symbol}...")
        for tf, (yf_int, limit) in fetch_map.items():
            start_d = now - timedelta(days=limit)
            try:
                if tf == "4h":
                    df = cache[symbol]["1h"].copy()
                    df = df.resample("4h").agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last'}).dropna()
                else:
                    df = yf.download(symbol, start=start_d, end=now, interval=yf_int, progress=False)
                cache[symbol][tf] = df
            except Exception as e:
                print(f"Failed to fetch {tf} for {symbol}: {e}")
                
    for config in CONFIGS:
        print(f"\nEvaluating Framework: {config[0]} Entry | {config[1]} Trend ($$$ 1:{config[2]} RR, {config[3]} Pip SL)")
        for symbol in PAIRS:
            entry_tf, trend_tf = config[0], config[1]
            df_en = cache[symbol].get(entry_tf)
            df_tr = cache[symbol].get(trend_tf)
            
            if df_en is None or df_tr is None or df_en.empty or df_tr.empty:
                continue
                
            tester = SuperMTFBacktester(df_en, df_tr, config)
            res = tester.solve(symbol)
            if res['total_trades'] > 0:
                master_results.append(res)
                print(f"  > {symbol} | Wins: {res['wins']} | Losses: {res['losses']} | WR: {res['win_rate']:.1f}% | PF: {res['profit_factor']:.2f}")

    # Calculate Top Strategies
    if master_results:
        df_res = pd.DataFrame(master_results)
        df_res = df_res.sort_values(by="profit_factor", ascending=False)
        print("\n🏆 == TOP 5 HIGHEST PROFIT FACTOR SETUPS == 🏆")
        top_5 = df_res.head(5)
        for _, row in top_5.iterrows():
            print(f"{row['symbol']} [{row['entry_tf']} / {row['trend_tf']}] -> WR: {row['win_rate']:.1f}% | PF: {row['profit_factor']:.2f} | Trades: {row['total_trades']}")
            
        # Write to report
        with open("comprehensive_strategy_audit.txt", "w") as f:
            f.write("# Sovereign Prime - Multi-Timeframe Algorithmic Audit\n")
            f.write("Evaluated: 1m, 2m, 5m, 15m, 1h, 4h, 1d\n\n")
            for _, row in df_res.iterrows():
                f.write(f"Pair: {row['symbol']}, TFs: {row['entry_tf']}/{row['trend_tf']}, WR: {row['win_rate']:.1f}%, PF: {row['profit_factor']:.2f}, Trades: {row['total_trades']}\n")
