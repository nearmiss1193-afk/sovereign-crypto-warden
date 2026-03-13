from typing import Dict, List, Tuple

class SovereignWarden:
    def __init__(self, daily_loss_limit_pct: float = 4.0):
        self.daily_loss_limit_pct = daily_loss_limit_pct
        
        # E8 Rules: "Holding multiple opposite positions... on the same or highly correlated assets"
        self.CORRELATION_GROUPS = [
            {"BTCUSD", "ETHUSD"},                  # Crypto Group
            {"NAS100", "US30", "SPX500"},          # US Indices Group
            {"EURUSD", "GBPUSD", "AUDUSD", "NZDUSD"}, # USD Majors Group
            {"USDJPY", "EURJPY", "GBPJPY"}         # JPY Pairs Group
        ]

    def _get_group_for_symbol(self, symbol: str) -> set:
        for group in self.CORRELATION_GROUPS:
            if symbol in group:
                return group
        return {symbol} # Default to itself if not in a designated group

    def _map_tradable_ids_to_symbols(self, position_data: List[list], instrument_cache: Dict[str, tuple]) -> List[Dict]:
        """Convert TradeLocker raw position array to distinct symbol/side maps."""
        # position array: [0:Id, 1:PosId, 2:TradableId, 3:Route, 4:Side, 5:Qty, ...]
        reverse_cache = {str(val[0]): sym for sym, val in instrument_cache.items()}
        
        mapped = []
        for pos in position_data:
            if len(pos) < 5: continue
            tradable_id = str(pos[2])
            side = str(pos[4]).upper() # "BUY" or "SELL"
            symbol = reverse_cache.get(tradable_id, "UNKNOWN")
            mapped.append({"symbol": symbol, "side": side, "tradable_id": tradable_id})
            
        return mapped

    def check_hedge_violation(self, target_symbol: str, target_direction: str, open_positions: List[list], instrument_cache: Dict[str, tuple]) -> Tuple[bool, str]:
        """
        Returns (is_safe, reason).
        If is_safe is False, the order MUST be blocked to prevent an E8 violation.
        """
        if not open_positions:
            return True, "No open positions"
            
        mapped_positions = self._map_tradable_ids_to_symbols(open_positions, instrument_cache)
        
        target_group = self._get_group_for_symbol(target_symbol)
        
        for pos in mapped_positions:
            open_sym = pos["symbol"]
            open_side = pos["side"]
            
            # Check 1: Exact Same Symbol Hedging
            if open_sym == target_symbol and open_side != target_direction:
                return False, f"HEDGE BLOCK: Cannot {target_direction} {target_symbol} while holding {open_side} {open_sym}"
                
            # Check 2: Correlated Symbol Hedging
            if open_sym in target_group and open_side != target_direction:
                return False, f"CORRELATION BLOCK: Cannot {target_direction} {target_symbol} while holding {open_side} {open_sym}"
                
        return True, "Hedge Check Passed"

    def check_drawdown_violation(self, account_state: List[float], eod_balance: float) -> Tuple[bool, str]:
        """
        Returns (is_safe, reason).
        Uses TradeLocker's accountDetailsData array.
        Index 0: Account Balance
        Index 2: Live Equity
        """
        if not account_state or len(account_state) < 3:
            return True, "No state data available, passing by default"
            
        balance = account_state[0]
        equity = account_state[2]
        
        # In case the bot restarted and lost EOD balance, we use the literal balance if it's lower.
        # But EOD balance is safer for prop firms since drawdown trails from peak.
        reference_high = max(balance, eod_balance)
        
        max_allowed_loss = reference_high * (self.daily_loss_limit_pct / 100.0)
        current_loss = reference_high - equity
        
        if current_loss >= max_allowed_loss:
            return False, f"DRAWDOWN BLOCK: Equity {equity} is down {current_loss} (Limit is {max_allowed_loss})"
            
        # Warning Zone: If within 10% of blowing the limit
        if current_loss >= (max_allowed_loss * 0.9):
            print(f"[WARDEN WARNING] Approaching Daily Loss Limit! Down ${round(current_loss,2)} / ${round(max_allowed_loss,2)}")
            
        return True, "Drawdown Check Passed"
