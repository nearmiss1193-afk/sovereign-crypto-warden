import os
import json
import requests
import urllib3
import threading
from datetime import datetime, timedelta
from typing import Optional
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Using Standard SSL for v2.6.0 (Let requests/certifi handle it)
# Cloudflare (E8) prefers modern ciphers without custom adapter interference

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class TradeLockerService:
    def __init__(self, base_url, email, password, server):
        self.base_url = base_url.rstrip("/")
        self.email = email
        self.password = password
        self.server = server
        self.token = None
        self.token_expiry = None
        self.last_error = None
        self._lock = threading.Lock()
        self._is_refreshing = False
        self._real_acc_nums = {}  # Cache accountId -> true accNum
        
        # Setup Session with Retries
        self.session = requests.Session()
        retries = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
        self.session.mount("https://", HTTPAdapter(max_retries=retries))
        
        # Static Headers (v2.6.3 Identity -> v2.9.2 Browser Spoof)
        self.session.headers.update({
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        })
        
        # DNS Resolution Cache/Debug (Handled manually to avoid blocking)
        self.last_dns_check = None
        self.resolved_ip = None
        self.dns_mode = "System"

    def resolve_doh(self, hostname: str) -> Optional[str]:
        """Bypass OS-level DNS using Google's DNS-over-HTTP (DoH) API."""
        try:
            # Query Google DNS API (JSON)
            url = f"https://dns.google/resolve?name={hostname}&type=A"
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                for answer in data.get("Answer", []):
                    if answer.get("type") == 1: # A Record
                        return answer.get("data")
        except Exception as e:
            print(f"[DoH] API Failure: {e}")
        return None

    def check_dns(self):
        """Ultra-Resilient DNS check for diagnostics."""
        hostname = "demo.tradelocker.com"
        try:
            import socket
            self.resolved_ip = socket.gethostbyname(hostname)
            self.last_dns_check = f"Sys: {self.resolved_ip}"
            self.dns_mode = "Native"
            return True
        except Exception:
            # Fallback to DoH
            ip = self.resolve_doh(hostname)
            if ip:
                self.resolved_ip = ip
                self.last_dns_check = f"DoH: {self.resolved_ip}"
                self.dns_mode = "Bridge"
                return True
            else:
                self.last_dns_check = "Fail (DNS+DoH)"
                self.dns_mode = "Locked"
                return False

    def get_token(self) -> Optional[str]:
        # Fast exit if valid
        if self.token and self.token_expiry and datetime.utcnow() < self.token_expiry:
            return self.token

        with self._lock:
            if self._is_refreshing:
                # Someone else is refreshing, return stale or None to avoid block
                return self.token
            self._is_refreshing = True

        try:
            if not self.email or not self.password:
                self.last_error = "Missing Credentials"
                return None

            url = f"{self.base_url}/auth/jwt/token"
            
            # Ensure DNS is primed before request
            if not self.resolved_ip:
                self.check_dns()

            payload = {"email": self.email, "password": self.password, "server": self.server}

            # Network call performed OUTSIDE of lock wait to prevent Eventlet starvation
            resp = self.session.post(url, json=payload, timeout=20)
            resp.raise_for_status()
            
            data = resp.json()
            new_token = data.get("accessToken") or data.get("access_token")
            
            with self._lock:
                self.token = new_token
                self.token_expiry = datetime.utcnow() + timedelta(minutes=25)
                self.last_error = None
                return self.token
        except Exception as e:
            err_msg = str(e)
            print(f"[TradeLocker] Auth failed: {err_msg}")
            with self._lock:
                self.last_error = f"Auth Error: {err_msg}"
                self.token = None # Clear on hard failure
            return None
        finally:
            with self._lock:
                self._is_refreshing = False

    def place_order(self, account_id, acc_num, tradable_id, route_id, side, qty, stop_loss=None, take_profit=None):
        token = self.get_token()
        if not token: 
            return {"success": False, "error": self.last_error or "Auth failed"}

        url = f"{self.base_url}/trade/accounts/{account_id}/orders"
        headers = {
            "Authorization": f"Bearer {token}",
            "accNum": str(acc_num)
        }
        payload = {
            "tradableInstrumentId": tradable_id,
            "type": "market",
            "side": side.lower(),
            "qty": str(qty),
            "routeId": route_id,
            "validity": "IOC",
        }
        if stop_loss: payload["stopLoss"] = stop_loss
        if take_profit: payload["takeProfit"] = take_profit

        try:
            resp = self.session.post(url, json=payload, headers=headers, timeout=25)
            resp_data = resp.json()
            if resp.status_code in (200, 201, 202):
                order_id = resp_data.get("orderId") or resp_data.get("id")
                return {"success": True, "order_id": str(order_id), "data": resp_data}
            else:
                return {"success": False, "error": f"HTTP {resp.status_code}: {resp_data}"}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def get_candles(self, account_id, tradable_id, resolution="1m", count=100) -> Optional[list]:
        token = self.get_token()
        if not token: return None
        
        url = f"{self.base_url}/trade/accounts/{account_id}/instruments/{tradable_id}/candles"
        headers = {
            "Authorization": f"Bearer {token}",
            "accNum": str(account_id)
        }
        params = {"resolution": resolution, "count": count}

        try:
            resp = self.session.get(url, params=params, headers=headers, timeout=25)
            resp.raise_for_status()
            return resp.json().get("candles", [])
        except Exception as exc:
            print(f"[TradeLocker] Fetch candles failed: {exc}")
            return None

    def get_instruments(self, account_id) -> list:
        token = self.get_token()
        if not token: return []
        
        url = f"{self.base_url}/trade/accounts/{account_id}/instruments"
        headers = {
            "Authorization": f"Bearer {token}",
            "accNum": str(account_id)
        }

        try:
            resp = self.session.get(url, headers=headers, timeout=25)
            resp.raise_for_status()
            return resp.json().get("instruments", [])
        except Exception as exc:
            print(f"[TradeLocker] Fetch instruments failed: {exc}")
            return []

    def get_market_depth(self, account_id, tradable_id, route_id) -> Optional[dict]:
        """Fetch Market Depth (Level 2) snapshot."""
        token = self.get_token()
        if not token: return None
        
        url = f"{self.base_url}/trade/accounts/{account_id}/instruments/{tradable_id}/depth"
        headers = {
            "Authorization": f"Bearer {token}",
            "accNum": str(account_id)
        }
        params = {"routeId": route_id}

        try:
            resp = self.session.get(url, params=params, headers=headers, timeout=15)
            resp_data = resp.json()
            if resp.status_code == 200:
                return resp_data # Expects {'asks': [[price, qty], ...], 'bids': [[price, qty], ...]}
            else:
                print(f"[TradeLocker] Depth failed: HTTP {resp.status_code}")
                return None
        except Exception as exc:
            print(f"[TradeLocker] Fetch depth failed: {exc}")
            return None

    def _get_real_acc_num(self, account_id):
        if account_id in self._real_acc_nums:
            return self._real_acc_nums[account_id]
            
        token = self.get_token()
        if not token: return None
        
        try:
            resp = self.session.get(f"{self.base_url}/auth/jwt/all-accounts", headers={"Authorization": f"Bearer {token}"}, timeout=10)
            if resp.status_code == 200:
                for acc in resp.json().get("accounts", []):
                    self._real_acc_nums[acc["id"]] = acc["accNum"]
            return self._real_acc_nums.get(account_id, "1") # default to 1 if not found
        except:
            return "1"

    def get_open_positions(self, account_id) -> list:
        token = self.get_token()
        if not token: return []
        
        real_acc_num = self._get_real_acc_num(account_id)
        url = f"{self.base_url}/trade/accounts/{account_id}/positions"
        headers = {
            "Authorization": f"Bearer {token}",
            "accNum": str(real_acc_num)
        }
        
        try:
            resp = self.session.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                return resp.json().get("d", [])
            return []
        except:
            return []

    def get_account_state(self, account_id) -> Optional[list]:
        token = self.get_token()
        if not token: return None
        
        real_acc_num = self._get_real_acc_num(account_id)
        url = f"{self.base_url}/trade/accounts/{account_id}/state"
        headers = {
            "Authorization": f"Bearer {token}",
            "accNum": str(real_acc_num)
        }
        
        try:
            resp = self.session.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                return resp.json().get("d", {}).get("accountDetailsData")
            return None
        except:
            return None
