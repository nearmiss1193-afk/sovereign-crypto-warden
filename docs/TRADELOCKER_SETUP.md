# TradeLocker + DNA Funded Setup Guide

## Overview

Sovereign Prime Forex connects to your **DNA Funded** account via the **TradeLocker REST API**.
Orders flow: `Dashboard → TradeLocker API → DNA Funded Account → Live Forex`

---

## Step 1 — Get Your TradeLocker Credentials

1. Log in to your DNA Funded portal
2. Navigate to **Trading Platform → TradeLocker**
3. Note your:
   - **Email** (your DNA Funded login email)
   - **Password** (your TradeLocker password)
   - **Server** (e.g., `OSP-LIVE` for live, `OSP-DEMO` for demo)
   - **Account ID** (the numeric account ID shown in TradeLocker)

---

## Step 2 — Add Environment Variables to Render

In your Render dashboard for `sovereign-prime-forex`:

1. Go to **Environment** tab
2. Add these variables:

| Variable | Value |
|----------|-------|
| `TRADELOCKER_EMAIL` | your@email.com |
| `TRADELOCKER_PASSWORD` | your_password |
| `TRADELOCKER_SERVER` | `OSP-LIVE` (or `OSP-DEMO` for testing) |
| `TRADELOCKER_ACCOUNT_ID` | 123456 (your numeric account ID) |
| `TRADELOCKER_BASE_URL` | `https://live.tradelocker.com/backend-api` (live) |
| `OPENAI_API_KEY` | your_openai_key (for Brain 2.5) |

3. Click **Save Changes** — Render will auto-redeploy

---

## Step 3 — OANDA Practice Fallback (Optional)

For testing without risking real money:

1. Create a free OANDA practice account at [oanda.com](https://www.oanda.com)
2. Generate an API key in **My Account → API Access**
3. Add to Render:

| Variable | Value |
|----------|-------|
| `OANDA_API_KEY` | your_oanda_api_key |
| `OANDA_ACCOUNT_ID` | 123-456-7890123-001 |

---

## Step 4 — Test the Connection

1. Go to your dashboard: `https://sovereign-prime-forex.onrender.com`
2. Click **🔌 CHECK BROKER** — should show TradeLocker as CONFIGURED
3. Go to **TEST SIGNAL** panel
4. Select: **DNA Funded** → **EURUSD** → **BUY**
5. Click **🚀 FIRE TEST ORDER**
6. Check your TradeLocker platform — a 0.01 lot EURUSD BUY should appear
7. Close it immediately

---

## Step 5 — TradingView Alert Setup

**Webhook URL:**
```
https://sovereign-prime-forex.onrender.com/api/signals/live
```

**EURUSD LONG Alert Payload:**
```json
{
  "account_id": "dna_funded",
  "symbol": "EURUSD",
  "direction": "BUY",
  "stop_pips": 12,
  "session": "ICT Silver Bullet"
}
```

**EURUSD SHORT Alert Payload:**
```json
{
  "account_id": "dna_funded",
  "symbol": "EURUSD",
  "direction": "SELL",
  "stop_pips": 12,
  "session": "ICT Silver Bullet"
}
```

**Supported Symbols:** EURUSD, GBPUSD, USDJPY, AUDUSD, USDCAD, USDCHF, NZDUSD, XAUUSD, GBPJPY, EURJPY

---

## DNA Funded Prop Rules (Guard Rails Built In)

| Rule | Limit | System Behavior |
|------|-------|-----------------|
| Daily Loss Limit | $500 | Account halted for the day |
| Max Drawdown | $1,000 | Account disabled |
| Max Lot Size | 0.5 lots | Hard cap on all orders |
| Risk Per Trade | $50 | Dollar-risk sizing applied |

---

## TradeLocker Base URLs

| Environment | URL |
|-------------|-----|
| **Live** | `https://live.tradelocker.com/backend-api` |
| **Demo** | `https://demo.tradelocker.com/backend-api` |

---

**MAX PROFIT.**
