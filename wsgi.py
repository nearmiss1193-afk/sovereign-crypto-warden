import os
import sys
import threading
import time
import random
import json
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional

# Diagnostic: Confirm Render Environment Status
print(f"BOOT: PYTHON_VERSION = {sys.version}")
print(f"BOOT: WORKER_TYPE = THREADING (NUCLEAR)")

# Flask + SocketIO
from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit

# Sovereign Services
from src.services.tradelocker_service import TradeLockerService
from src.agents.reversion_warden import ReversionWarden
from src.guards.sovereign_warden import SovereignWarden
from src.guards.prop_guards import PropGuards
from src.utils.pip_calibrator import PipCalibrator
from src.database.db_service import DBService
from src.services.state_manager import StateManager
from src.services.resend_email import SovereignMailer

app = Flask(__name__, template_folder="dashboard/templates", static_folder="dashboard/static")
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "sovereign-forex-secret")
socketio = SocketIO(app, 
                   cors_allowed_origins="*", 
                   async_mode="threading",
                   ping_timeout=20,
                   ping_interval=10,
                   max_http_buffer_size=1e7)

# ── INITIALIZE SERVICES ──────────────────────────────────────
tl_service = TradeLockerService(
    base_url=os.environ.get("TRADELOCKER_BASE_URL", "https://demo.tradelocker.com/backend-api"),
    email=os.environ.get("TRADELOCKER_EMAIL", "nearmiss1193@gmail.com"),
    password=os.environ.get("TRADELOCKER_PASSWORD", "la:zD?25"),
    server=os.environ.get("TRADELOCKER_SERVER", "E8")
)

guards = PropGuards(
    prop_firm_mode="E8",
    news_blackout_mins=5,
    daily_profit_cap_pct=40.0
)

warden = SovereignWarden(daily_loss_limit_pct=4.0)
strategy = ReversionWarden(rsi_period=9, overbought=70, oversold=30)
db = DBService()
mailer = SovereignMailer()

acc_id = os.environ.get("TRADELOCKER_ACCOUNT_ID", "2001074")
state_manager = StateManager(tl_service, acc_id)
state_manager.start()

# ── CONFIG ───────────────────────────────────────────────────
AUTO_TRADE = True # Force enable as soon as verified (Sovereign Directive)
SYMBOLS = [
    "BTCUSD", "ETHUSD"             # The Sovereign Crypto Grid
]

# ── SINGLE ACCOUNT REGISTRY ──────────────────────────────────
ACCOUNTS = {
    "e8_eval": {
        "label":            "E8 One Phase 1 — $10k Eval",
        "broker":           "tradelocker",
        "account_id":       os.environ.get("TRADELOCKER_ACCOUNT_ID", "2001074"),
        "balance":          10000.0,
        "daily_pnl":        0.0,
        "weekly_pnl":       0.0,
        "weekly_target":    900.0,    # Target 9%
        "max_lot_size":     0.5,      # Conservative limit
        "enabled":          True,
        "halted":           False,
        "prop_firm":        "e8",
        "daily_loss_limit": 350.0,    # Safe buffer ($400 rule)
        "max_drawdown":     600.0,    # 6% dynamic drawdown
        "risk_per_trade":   50.0,     # 0.5% for 100% 2Y Survival
        "currency":         "USD",
        "consecutive_wins": 0,        # For Phase 30 Scaling
        "consecutive_losses": 0,      # For Phase 30 Scaling
    }
}

# ── MULTI-SYMBOL SCANNER ─────────────────────────────────────
INSTRUMENT_CACHE = {} # {symbol: (tradable_id, route_id)}

def scanner_loop():
    print(f"🚀 Sovereign Scanner Active | E8 10k Eval | Monitoring {len(SYMBOLS)} symbols")
    
    # Delayed Start to allow Port Binding (v2.6.3)
    print("[Scanner] Delaying 20s for safe port binding...")
    time.sleep(20)
    
    acc_id = ACCOUNTS["e8_eval"]["account_id"]
    
    while True:
        try:
            # Check DNS health occasionally
            tl_service.check_dns()
            
            now = datetime.utcnow()
            date_str = now.strftime("%Y-%m-%d")
            
            # Fetch instrument cache from StateManager (0ms RAM)
            INSTRUMENT_CACHE = state_manager.get_instruments()
            
            # EMERGENCY DIAGNOSTIC PATCH
            print(f"[Scanner] Cycle | Token: {bool(tl_service.token)} | Cache: {len(INSTRUMENT_CACHE)}")
            token = tl_service.get_token()
            if not token:
                print(f"[Scanner] AUTH FAILED: {tl_service.last_error}")
                time.sleep(30)
                continue
            
            print(f"[Scanner] Auth OK | acc_id={acc_id} | type={type(acc_id)}")

            if not INSTRUMENT_CACHE:
                print("[Scanner] Awaiting RAM Cache Instrument Sync...")
                time.sleep(5)
                continue

            # Check News Guard
            news_status = guards.is_news_blackout(now)
            
            for symbol, ids in INSTRUMENT_CACHE.items():
                try:
                    # Switch to 1h candles for Reversion Warden
                    candles_raw = tl_service.get_candles(acc_id, ids[0], resolution="1h", count=50)
                    if not candles_raw or len(candles_raw) < 10:
                        continue
                    
                    df = pd.DataFrame(candles_raw)
                    setup = strategy.detect_setup(df, symbol=symbol)
                    
                    # ── STREAM OF CONSCIOUSNESS TO TERMINAL ──
                    if len(df) > 0:
                        last_close = df.iloc[-1]['Close']
                        # Re-calculate RSI for streaming purely for display
                        delta = df['Close'].diff()
                        up = delta.clip(lower=0)
                        down = -1 * delta.clip(upper=0)
                        ma_up = up.rolling(14).mean()
                        ma_down = down.rolling(14).mean()
                        rs = ma_up / ma_down
                        rsi_val = 100 - (100 / (1 + rs)).iloc[-1]
                        
                        socketio.emit("terminal_log", {
                            "message": f"[{symbol}] Price: {last_close:.2f} | RSI: {rsi_val:.1f} | Awaiting Breakout...",
                            "type": "info"
                        })
                    
                    if setup:
                        # ── SOVEREIGN WARDEN INTERCEPT LAYER (0ms RAM READ) ──
                        open_positions = state_manager.get_open_positions()
                        is_safe_hedge, hedge_reason = warden.check_hedge_violation(
                            target_symbol=symbol,
                            target_direction=setup['type'],
                            open_positions=open_positions,
                            instrument_cache=INSTRUMENT_CACHE
                        )
                        
                        if not is_safe_hedge:
                            print(f"[WARDEN BLOCK] {hedge_reason}")
                            socketio.emit("terminal_log", {"message": f"[WARDEN BLOCK] {hedge_reason}", "type": "error"})
                            mailer.notify_warden_block("Crypto Warden", symbol, setup['type'], hedge_reason)
                            continue
                            
                        account_state = state_manager.get_account_state()
                        is_safe_dd, dd_reason = warden.check_drawdown_violation(
                            account_state=account_state,
                            eod_balance=ACCOUNTS["e8_eval"]["balance"]
                        )
                        
                        if not is_safe_dd:
                            print(f"[WARDEN BLOCK] {dd_reason}")
                            socketio.emit("terminal_log", {"message": f"CRITICAL: {dd_reason}", "type": "error"})
                            mailer.notify_emergency("Crypto Warden", dd_reason)
                            # Halt trading entirely to prevent further DD logic loops
                            global AUTO_TRADE
                            AUTO_TRADE = False
                            continue

                        socketio.emit("new_signal", {
                            "symbol": symbol,
                            "direction": setup["type"],
                            "reason": setup["confidence_reason"],
                            "confidence": 85,
                            "source": "LIVE",
                            "timestamp": now.strftime("%H:%M:%S UTC"),
                            "stop_pips": setup["sl_pips"],
                            "l2_imbalance": setup.get("imbalance", 1.0)
                        })

                        if news_status["blocked"]:
                            continue

                        if AUTO_TRADE:
                            print(f"[AUTO] Executing {setup['type']} on {symbol}")
                            
                            # Fixed 0.25% Crypto Risk Model as Backtested
                            risk_usd = ACCOUNTS["e8_eval"]["balance"] * 0.0025
                            print(f"[Risk] Fixed 0.25% Grid Risk: ${round(risk_usd, 2)}")
                            
                            # ── ABSOLUTE SL/TP CALCULATION (Grinder Mode: 1:2 RR) ──
                            # Multi-Asset Rounding & Math
                            is_jpy = "JPY" in symbol
                            is_index = any(x in symbol.upper() for x in ["NAS", "USTEC", "US30", "USI"])
                            is_crypto = any(x in symbol.upper() for x in ["BTC", "ETH"])
                            
                            precision = 5
                            if is_jpy: precision = 3
                            if is_index: precision = 2
                            if is_crypto: precision = 2
                            
                            pip_size = PipCalibrator.get_pip_size(symbol)
                            sl_dist = setup["sl_pips"] * pip_size
                            tp_dist = sl_dist * 3.0 # R:R is 1:3 for Crypto Reversion
                            
                            entry_price = setup["entry"]
                            if setup["type"] == "BUY":
                                sl_price = round(entry_price - sl_dist, precision)
                                tp_price = round(entry_price + tp_dist, precision)
                            else:
                                sl_price = round(entry_price + sl_dist, precision)
                                tp_price = round(entry_price - tp_dist, precision)
                            
                            point_val = PipCalibrator.get_point_value(symbol)
                            lots = PipCalibrator.calculate_lots(risk_usd, setup["sl_pips"], point_val)
                            
                            res = tl_service.place_order(
                                account_id=acc_id,
                                acc_num=acc_id,
                                tradable_id=ids[0],
                                route_id=ids[1],
                                side=setup["type"].lower(),
                                qty=lots,
                                stop_loss=sl_price,
                                take_profit=tp_price
                            )
                            if res.get("success"):
                                print(f"[WARDEN] Successfully executed Grid Order on {symbol}")
                                socketio.emit("terminal_log", {"message": f"🟢 [EXECUTION] FIRED {setup['type']} on {symbol} at {entry_price}", "type": "success"})
                                mailer.notify_trade_fired("Crypto Warden", symbol, setup["type"], setup["entry"], risk_usd)
                                db.save_trade(res)
                except Exception as sym_err:
                    print(f"[Scanner] Error on {symbol}: {sym_err}")
                            
            time.sleep(60)
        except Exception as e:
            print(f"[Scanner] Global Error: {e}")
            time.sleep(10)

# ── ROUTES ───────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("dashboard.html")

@app.route("/api/status")
def status():
    return jsonify({
        "engine": "Sovereign v2.9.0-DEPTH",
        "auto_trade": AUTO_TRADE,
        "account": "E8 10k Eval",
        "status": "Scanning",
        "dns": tl_service.last_dns_check or "Pending",
        "dns_mode": tl_service.dns_mode
    })

@app.after_request
def add_cache_headers(response):
    if request.path == '/' or request.path.endswith('.html'):
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    return response

@app.route("/api/initial-data")
def initial_data():
    return jsonify({
        "accounts": ACCOUNTS,
        "brain_stats": {"evals": 0, "approved": 0, "rate": "100%", "status": "ACTIVE"},
        "signals": [],
        "weekly": {"weekly_pnl": 0.0, "pct": 0, "days_left": 5, "on_track": True}
    })

@app.route("/api/guards/status")
def get_guards_status():
    return jsonify({
        "prop_firm_mode": guards.mode,
        "news_blackout_mins": guards.news_blackout_mins,
        "news_guard": guards.is_news_blackout(),
        "profit_cap_guard": {}, # Populate if needed
        "any_blocked": guards.is_news_blackout()["blocked"]
    })

@app.route("/api/guards/news-events")
def get_news_events():
    return jsonify({
        "events_today": [] # Placeholder for real news feed
    })

# ── SOCKET HANDLERS ──────────────────────────────────────────
@socketio.on("connect")
def handle_connect():
    print(f"🔌 Client Connected: {request.sid}")
    emit("brain_update", {"evals": 0, "approved": 0, "rate": "100%", "status": "ACTIVE"})

@socketio.on("get_initial_data")
def handle_get_initial_data():
    print(f"📊 Sending Initial Data to {request.sid}")
    
    # Internal broker status check
    if tl_service.token and tl_service.token_expiry and datetime.utcnow() < tl_service.token_expiry:
        configured = True
        msg = "Authenticated"
    else:
        token = tl_service.get_token()
        configured = token is not None
        msg = "Authenticated" if configured else (tl_service.last_error or "Auth Failed")

    broker_status = {
        "configured": configured,
        "account_id": ACCOUNTS["e8_eval"]["account_id"],
        "server": tl_service.server,
        "message": msg,
        "dns_mode": tl_service.dns_mode
    }

    emit("full_update", {
        "accounts": ACCOUNTS,
        "brain_stats": {"evals": 0, "approved": 0, "rate": "100%", "status": "ACTIVE"},
        "signals": [],
        "weekly": {"weekly_pnl": 0.0, "pct": 0, "days_left": 5, "on_track": True},
        "broker_status": broker_status
    })

@app.route("/api/broker/status")
def get_broker_status():
    # Direct check to avoid any potential recursion in tl_service
    # if it's already authenticated, just return success
    if tl_service.token and tl_service.token_expiry and datetime.utcnow() < tl_service.token_expiry:
        configured = True
        msg = "Authenticated"
    else:
        # One-shot attempt
        token = tl_service.get_token()
        configured = token is not None
        msg = "Authenticated" if configured else (tl_service.last_error or "Auth Failed")

    return jsonify({
        "tradelocker": {
            "configured": configured,
            "account_id": ACCOUNTS["e8_eval"]["account_id"],
            "server": tl_service.server,
            "message": msg,
            "dns_mode": tl_service.dns_mode
        }
    })

@app.route("/api/signals/test-signal", methods=["POST"])
def test_signal():
    data = request.json
    acc_id = data.get("account_id", "e8_eval")
    symbol = data.get("symbol", "EURUSD")
    direction = data.get("direction", "BUY").upper()
    
    print(f"[UI] Fire Test Signal: {symbol} {direction}")
    
    # Check if symbol is in INSTRUMENT_CACHE
    if symbol not in INSTRUMENT_CACHE:
        # One-shot refresh
        insts = tl_service.get_instruments(ACCOUNTS["e8_eval"]["account_id"])
        for inst in insts:
            sym = inst.get("symbol")
            if sym in SYMBOLS:
                INSTRUMENT_CACHE[sym] = (inst.get("id"), inst.get("routeId"))

    if symbol not in INSTRUMENT_CACHE:
        return jsonify({"success": False, "error": f"Symbol {symbol} not found in TradeLocker"})

    ids = INSTRUMENT_CACHE[symbol]
    res = tl_service.place_order(
        account_id=ACCOUNTS["e8_eval"]["account_id"],
        acc_num=ACCOUNTS["e8_eval"]["account_id"],
        tradable_id=ids[0],
        route_id=ids[1],
        side=direction,
        qty=0.01  # Force 0.01 for tests
    )
    
    if res.get("success"):
        return jsonify({
            "success": True, 
            "order_id": res.get("order_id"), 
            "instrument": symbol, 
            "message": "Order placed successfully (0.01 lot)"
        })
    return jsonify({"success": False, "error": res.get("error", "Unknown Error")})

@app.route("/api/signals/manual", methods=["POST"])
def manual_signal():
    data = request.json
    symbol = data.get("symbol")
    direction = data.get("direction", "BUY").upper()
    stop_pips = data.get("stop_pips", 10)
    
    print(f"[UI] Manual Signal: {symbol} {direction}")
    
    if symbol not in INSTRUMENT_CACHE:
        return jsonify({"success": False, "error": f"Symbol {symbol} not found"})

    ids = INSTRUMENT_CACHE[symbol]
    risk_usd = ACCOUNTS["e8_eval"]["risk_per_trade"]
    lots = PipCalibrator.calculate_lots(risk_usd, stop_pips, 10.0)

    res = tl_service.place_order(
        account_id=ACCOUNTS["e8_eval"]["account_id"],
        acc_num=ACCOUNTS["e8_eval"]["account_id"],
        tradable_id=ids[0],
        route_id=ids[1],
        side=direction,
        qty=lots,
        stop_loss=stop_pips # Note: TradeLocker might expect price or pips depending on account
    )
    
    if res.get("success"):
        return jsonify({"success": True, "order_id": res.get("order_id"), "lot_size": lots})
    return jsonify({"success": False, "error": res.get("error", "Unknown Error")})

@app.route("/api/emergency-stop", methods=["POST"])
def emergency_stop():
    global AUTO_TRADE
    AUTO_TRADE = False
    for acc in ACCOUNTS.values():
        acc["enabled"] = False
        acc["halted"] = True
    print("⛔ EMERGENCY STOP TRIGGERED")
    socketio.emit("terminal_log", {"message": "⛔ EMERGENCY STOP TRIGGERED BY USER", "type": "error"})
    mailer.notify_emergency("Crypto Warden", "User-Triggered Dashboard Emergency Stop")
    socketio.emit("emergency_stop")
    return jsonify({"success": True})

# Start scanner loop as a daemon thread
threading.Thread(target=scanner_loop, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host="0.0.0.0", port=port)
