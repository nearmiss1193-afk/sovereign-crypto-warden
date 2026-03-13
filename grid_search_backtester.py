import yfinance as yf
import pandas as pd
import numpy as np

def download_data(symbol="EURUSD=X", days=180, interval="1h"):
    print(f"Downloading {days} days of {interval} data for {symbol}...")
    df = yf.download(symbol, period=f"{days}d", interval=interval, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.droplevel(1)
    df.dropna(inplace=True)
    return df

def simulate_trades(data, rr_ratio, sl_pct, strategy_name, params):
    trades = 0
    wins = 0
    losses = 0
    pnl = 0.0
    
    in_pos = False
    entry_price = 0.0
    pos_type = 0 # 1 long, -1 short
    
    for i in range(1, len(data)):
        current_close = data['Close'].iloc[i]
        current_high = data['High'].iloc[i]
        current_low = data['Low'].iloc[i]
        
        if in_pos:
            if pos_type == 1:
                sl = entry_price * (1 - sl_pct)
                tp = entry_price * (1 + (sl_pct * rr_ratio))
                if current_low <= sl:
                    trades += 1; losses += 1; pnl -= 1.0; in_pos = False
                elif current_high >= tp:
                    trades += 1; wins += 1; pnl += rr_ratio; in_pos = False
            elif pos_type == -1:
                sl = entry_price * (1 + sl_pct)
                tp = entry_price * (1 - (sl_pct * rr_ratio))
                if current_high >= sl:
                    trades += 1; losses += 1; pnl -= 1.0; in_pos = False
                elif current_low <= tp:
                    trades += 1; wins += 1; pnl += rr_ratio; in_pos = False
                    
        # New Signals
        if not in_pos and data['Signal'].iloc[i-1] != 0:
            in_pos = True
            pos_type = data['Signal'].iloc[i-1]
            entry_price = data['Open'].iloc[i]
            
    win_rate = (wins / trades * 100) if trades > 0 else 0
    return {
        "Strategy": strategy_name,
        "Params": params,
        "Trades": trades,
        "WinRate%": round(win_rate, 2),
        "Net PnL (R)": round(pnl, 2),
        "RR": rr_ratio
    }

def run_rsi_sweep(df):
    results = []
    for rrp in [1.0, 1.5, 2.0, 3.0]:
        for period in [9, 14, 21]:
            data = df.copy()
            delta = data['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            data['RSI'] = 100 - (100 / (1 + rs))
            
            data['Signal'] = 0
            data.loc[data['RSI'] < 25, 'Signal'] = 1
            data.loc[data['RSI'] > 75, 'Signal'] = -1
            
            res = simulate_trades(data, rrp, 0.0015, "RSI Mean Reversion", f"RSI({period})")
            results.append(res)
    return results

def run_bb_sweep(df):
    results = []
    for rrp in [1.0, 2.0, 3.0]:
        for period in [20, 50]:
            data = df.copy()
            data['SMA'] = data['Close'].rolling(window=period).mean()
            data['STD'] = data['Close'].rolling(window=period).std()
            data['Upper'] = data['SMA'] + (data['STD'] * 2.0)
            data['Lower'] = data['SMA'] - (data['STD'] * 2.0)
            
            data['Signal'] = 0
            # Breakout logic
            data.loc[data['Close'] > data['Upper'], 'Signal'] = 1
            data.loc[data['Close'] < data['Lower'], 'Signal'] = -1
            
            res = simulate_trades(data, rrp, 0.002, "BB Breakout", f"BB({period})")
            results.append(res)
    return results

if __name__ == "__main__":
    symbols = [
        "EURUSD=X", "USDCHF=X", "GBPJPY=X",  # Forex
        "NQ=F", "YM=F",                      # Indices (Nasdaq, Dow)
        "BTC-USD", "ETH-USD"                 # Crypto
    ]
    
    print("\n[Running 6-Month Multi-Asset Grid Search: RSI(21) Reversion vs BB(20) Breakout]")
    all_results = []
    
    for sym in symbols:
        try:
            df = download_data(sym, days=180, interval="1h")
            if df.empty:
                continue
            
            # Run RSI Sweep on this symbol
            rsi_res = run_rsi_sweep(df)
            for r in rsi_res: r["Symbol"] = sym
            
            # Run BB Sweep on this symbol
            bb_res = run_bb_sweep(df)
            for r in bb_res: r["Symbol"] = sym
            
            all_results.extend(rsi_res)
            all_results.extend(bb_res)
        except Exception as e:
            print(f"Skipping {sym} due to data error.")
    
    df_res = pd.DataFrame(all_results)
    if not df_res.empty:
        df_res = df_res[df_res['Trades'] > 20] # Filter out noise
        df_res = df_res.sort_values(by="Net PnL (R)", ascending=False)
        
        print("\nTHE MULTI-ASSET LEADERBOARD (Top 15 Cross-Asset Configurations):")
        print("-" * 90)
        # Reorder columns for readability
        df_sorted = df_res[['Symbol', 'Strategy', 'Params', 'RR', 'Trades', 'WinRate%', 'Net PnL (R)']].head(15)
        print(df_sorted.to_string(index=False))
        print("-" * 90)
        
        # Aggregate by Symbol to see which assets mathematically 'accept' bots best
        print("\nPROFITABILITY BY ASSET (Total Net R Generated by all systems):")
        agg = df_res.groupby('Symbol')['Net PnL (R)'].sum().sort_values(ascending=False)
        print(agg.to_string())
    else:
        print("No valid trades triggered across the portfolio.")
