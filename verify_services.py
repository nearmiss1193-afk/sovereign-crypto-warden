from src.services.strategy_service import StrategyService
from src.utils.pip_calibrator import PipCalibrator
import pandas as pd
from datetime import datetime

def test_services():
    print("--- Testing Sovereign Forex v2.5 Services ---")
    
    # 1. Test Pip Calibrator
    print("\n[PipCalibrator] Testing JPY vs Major...")
    eurusd_pip = PipCalibrator.get_pip_size("EURUSD")
    eurjpy_pip = PipCalibrator.get_pip_size("EURJPY")
    print(f"  EURUSD Pip: {eurusd_pip}")
    print(f"  EURJPY Pip: {eurjpy_pip}")
    
    risk = 100.0
    sl = 20.0 # 20 pips
    lots = PipCalibrator.calculate_lots(risk, sl, 10.0)
    print(f"  Risk: ${risk} | SL: {sl}pips | Lots: {lots}")
    
    # 2. Test Strategy Service
    print("\n[StrategyService] Testing Window Detection...")
    strat = StrategyService()
    # Mock date for London window (around 3 AM EST / 8 AM UTC)
    mock_london = datetime(2026, 3, 11, 8, 0, 0) 
    window = strat.is_in_silver_bullet_window(mock_london)
    print(f"  Mock Time: {mock_london} (UTC) | Window: {window}")
    
    # 3. Test MSS + FVG Detection
    print("\n[StrategyService] Testing Detection Logic...")
    # Bullish MSS + FVG: Highs: 1.0, 1.1, 1.2, 1.3 | Lows: 0.9, 0.95, 1.1, 1.25 | Closes: 0.95, 1.05, 1.25, 1.35
    data = {
        "High": [1.0, 1.1, 1.2, 1.3, 1.4],
        "Low": [0.9, 0.9, 1.05, 1.15, 1.25],
        "Open": [0.95, 1.0, 1.1, 1.2, 1.3],
        "Close": [0.98, 1.05, 1.2, 1.3, 1.35],
        "Datetime": [datetime.now()] * 5
    }
    df = pd.DataFrame(data)
    setup = strat.detect_setup(df)
    print(f"  Setup Detected: {setup}")

if __name__ == "__main__":
    test_services()
