import threading
import time
from datetime import datetime

class StateManager:
    """
    Sovereign Zero-Latency Architecture:
    Polls TradeLocker continuously in the background and stores
    account state and open positions in local RAM.
    Allows the Warden to make 0ms compliance decisions during order execution.
    """
    def __init__(self, tl_service, account_id):
        self.tl_service = tl_service
        self.account_id = account_id
        
        self.open_positions = []
        self.account_state = []
        self.instrument_cache = {}
        
        self.last_update = None
        self.is_running = False
        self.lock = threading.Lock()
        
    def _poll_loop(self):
        print("[StateManager] Booting Zero-Latency RAM Cache Daemon...")
        while self.is_running:
            try:
                # Only poll if we have a valid token
                if self.tl_service.token:
                    positions = self.tl_service.get_open_positions(self.account_id)
                    state = self.tl_service.get_account_state(self.account_id)
                    
                    # One-time instrument cache build if empty
                    if not self.instrument_cache:
                        insts = self.tl_service.get_instruments(self.account_id)
                        if insts:
                            for inst in insts:
                                self.instrument_cache[inst.get("symbol")] = (inst.get("id"), inst.get("routeId"))
                    
                    with self.lock:
                        if positions is not None:
                            self.open_positions = positions
                        if state is not None:
                            self.account_state = state
                        self.last_update = datetime.utcnow()
                
            except Exception as e:
                print(f"[StateManager] Warning - Polling Exception: {e}")
                
            # Sleep 3 seconds to avoid rate limits while maintaining ultra-recent state
            time.sleep(3.0)
            
    def start(self):
        if not self.is_running:
            self.is_running = True
            threading.Thread(target=self._poll_loop, daemon=True, name="StateManagerDaemon").start()
            
    def stop(self):
        self.is_running = False
        
    def get_open_positions(self):
        """Returns 0ms localized RAM cache of open positions"""
        with self.lock:
            return list(self.open_positions)
            
    def get_account_state(self):
        """Returns 0ms localized RAM cache of account equity state"""
        with self.lock:
            return list(self.account_state)
            
    def get_instruments(self):
        """Returns localized instrument mapping cache"""
        with self.lock:
            return dict(self.instrument_cache)
