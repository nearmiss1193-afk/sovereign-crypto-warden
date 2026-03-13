import yfinance as yf
import pandas as pd
import numpy as np

def download_data(symbol, days=180):
    df = yf.download(symbol, period=f"{days}d", interval="1h", progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.droplevel(1)
    df.dropna(inplace=True)
    return df

def simulate_max_drawdown(data, rr_ratio, sl_pct, signal_col, risk_per_trade=1.0):
    trades = 0
    pnl = 0.0
    peak = 0.0
    max_dd = 0.0
    
    in_pos = False
    entry_price = 0.0
    pos_type = 0 
    
    # We will track exactly how the account equity fluctuates
    equity_curve = [0.0]
    
    for i in range(1, len(data)):
        current_close = data['Close'].iloc[i]
        current_high = data['High'].iloc[i]
        current_low = data['Low'].iloc[i]
        
        if in_pos:
            if pos_type == 1:
                sl = entry_price * (1 - sl_pct)
                tp = entry_price * (1 + (sl_pct * rr_ratio))
                if current_low <= sl:
                    trades += 1; pnl -= risk_per_trade; in_pos = False
                    equity_curve.append(pnl)
                elif current_high >= tp:
                    trades += 1; pnl += (risk_per_trade * rr_ratio); in_pos = False
                    equity_curve.append(pnl)
            elif pos_type == -1:
                sl = entry_price * (1 + sl_pct)
                tp = entry_price * (1 - (sl_pct * rr_ratio))
                if current_high >= sl:
                    trades += 1; pnl -= risk_per_trade; in_pos = False
                    equity_curve.append(pnl)
                elif current_low <= tp:
                    trades += 1; pnl += (risk_per_trade * rr_ratio); in_pos = False
                    equity_curve.append(pnl)
                    
        if not in_pos and data[signal_col].iloc[i-1] != 0:
            in_pos = True
            pos_type = data[signal_col].iloc[i-1]
            entry_price = data['Open'].iloc[i]
            
        # Drawdown calculation
        if pnl > peak:
            peak = pnl
        current_dd = peak - pnl
        if current_dd > max_dd:
            max_dd = current_dd
            
    avg_trades_per_day = trades / 180.0
    return trades, avg_trades_per_day, pnl, max_dd

def run_crypto_rsi(df, period=9, rr=3.0):
    data = df.copy()
    delta = data['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    data['RSI'] = 100 - (100 / (1 + rs))
    data['Signal'] = 0
    data.loc[data['RSI'] < 25, 'Signal'] = 1
    data.loc[data['RSI'] > 75, 'Signal'] = -1
    return simulate_max_drawdown(data, rr, 0.0015, 'Signal')

def run_index_bb(df, period=50, rr=3.0):
    data = df.copy()
    data['SMA'] = data['Close'].rolling(window=period).mean()
    data['STD'] = data['Close'].rolling(window=period).std()
    data['Upper'] = data['SMA'] + (data['STD'] * 2.0)
    data['Lower'] = data['SMA'] - (data['STD'] * 2.0)
    data['Signal'] = 0
    data.loc[data['Close'] > data['Upper'], 'Signal'] = 1
    data.loc[data['Close'] < data['Lower'], 'Signal'] = -1
    return simulate_max_drawdown(data, rr, 0.002, 'Signal')

if __name__ == "__main__":
    print("--- BTC-USD: RSI(9) Mean Reversion ---")
    df_btc = download_data("BTC-USD")
    t_btc, tpd_btc, pnl_btc, dd_btc = run_crypto_rsi(df_btc)
    print(f"Trades: {t_btc} | Trades/Day: {tpd_btc:.2f} | Net PnL: +{pnl_btc:.2f}% | Max DD: -{dd_btc:.2f}%")
    
    print("\n--- ETH-USD: RSI(9) Mean Reversion ---")
    df_eth = download_data("ETH-USD")
    t_eth, tpd_eth, pnl_eth, dd_eth = run_crypto_rsi(df_eth)
    print(f"Trades: {t_eth} | Trades/Day: {tpd_eth:.2f} | Net PnL: +{pnl_eth:.2f}% | Max DD: -{dd_eth:.2f}%")
    
    print("\n--- NQ=F (Nasdaq): BB(50) Breakout ---")
    df_nq = download_data("NQ=F")
    t_nq, tpd_nq, pnl_nq, dd_nq = run_index_bb(df_nq)
    print(f"Trades: {t_nq} | Trades/Day: {tpd_nq:.2f} | Net PnL: +{pnl_nq:.2f}% | Max DD: -{dd_nq:.2f}%")
