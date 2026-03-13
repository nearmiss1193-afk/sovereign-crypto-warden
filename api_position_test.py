import os
import sys
# Add current path so we can import tradelocker_service
sys.path.append("C:/Users/nearm/Desktop/sovereign-prime-forex-trader")

from src.services.tradelocker_service import TradeLockerService

def test_fetch_positions():
    tl_service = TradeLockerService(
        base_url="https://demo.tradelocker.com/backend-api",
        email="nearmiss1193@gmail.com",
        password="la:zD?25",
        server="E8"
    )
    
    print("Authenticating...")
    token = tl_service.get_token()
    if not token:
        print(f"Auth failed: {tl_service.last_error}")
        return
        
    print("Auth Success. Fetching open positions...")
    
    account_id = "2001074"
    acc_num = "1"
    
    account_id = "2001074"
    acc_num = "1"
    
    url = f"{tl_service.base_url}/trade/accounts/{account_id}/state"
    headers = {
        "Authorization": f"Bearer {token}",
        "accNum": acc_num
    }
    
    try:
        resp = tl_service.session.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        print(f"[SUCCESS] Fetched Account State.")
        import json
        print(json.dumps(data, indent=2))
    except Exception as e:
        print(f"Error fetching state: {e}")
        try:
            print("Response:", resp.text)
        except:
            pass

if __name__ == "__main__":
    test_fetch_positions()
