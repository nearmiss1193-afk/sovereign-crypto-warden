# ============================================================
#  SOVEREIGN PRIME — FOREX TRADER v1.0
#  restart-sovereign-forex.ps1
#  One-click restart + browser open
#  DNA Funded | TradeLocker | OANDA Practice
# ============================================================

Write-Host ""
Write-Host "  ╔══════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "  ║   SOVEREIGN PRIME — FOREX TRADER v1.0       ║" -ForegroundColor Cyan
Write-Host "  ║   TradeLocker → DNA Funded                   ║" -ForegroundColor Cyan
Write-Host "  ╚══════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# ── ACCOUNTS ──────────────────────────────────────────────
Write-Host "  ACTIVE ACCOUNTS:" -ForegroundColor Yellow
Write-Host "  ✅  DNA Funded     — TradeLocker (Live)" -ForegroundColor Green
Write-Host "  🔵  OANDA Practice — Fallback/Testing" -ForegroundColor Blue
Write-Host ""

# ── OPEN DASHBOARD ────────────────────────────────────────
$dashboardUrl = "https://sovereign-prime-forex.onrender.com"
Write-Host "  Opening dashboard: $dashboardUrl" -ForegroundColor Cyan
Start-Process $dashboardUrl

Write-Host ""
Write-Host "  ✅ Dashboard opened. MAX PROFIT." -ForegroundColor Green
Write-Host ""

# ── TRADINGVIEW WEBHOOK URL ───────────────────────────────
Write-Host "  TradingView Webhook URL:" -ForegroundColor Yellow
Write-Host "  https://sovereign-prime-forex.onrender.com/api/signals/live" -ForegroundColor White
Write-Host ""

# ── SAMPLE ALERT PAYLOAD ──────────────────────────────────
Write-Host "  Sample TradingView Alert Payload (EURUSD LONG):" -ForegroundColor Yellow
Write-Host '  {' -ForegroundColor Gray
Write-Host '    "account_id": "dna_funded",' -ForegroundColor Gray
Write-Host '    "symbol": "EURUSD",' -ForegroundColor Gray
Write-Host '    "direction": "BUY",' -ForegroundColor Gray
Write-Host '    "stop_pips": 12,' -ForegroundColor Gray
Write-Host '    "session": "NY Silver Bullet"' -ForegroundColor Gray
Write-Host '  }' -ForegroundColor Gray
Write-Host ""
Write-Host "  MAX PROFIT." -ForegroundColor Magenta
