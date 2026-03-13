/* ── SOVEREIGN PRIME FOREX — DASHBOARD JS v2.6.5-ULTRA ── */

const socket = io();
let signalCount = 0;
let accounts    = {};

// ── PIP VALUES ────────────────────────────────────────────
const PIP_VALUES = {
  EURUSD: 10.0, GBPUSD: 10.0, AUDUSD: 10.0, NZDUSD: 10.0,
  USDJPY: 9.09, GBPJPY: 9.09, EURJPY: 9.09,
  USDCAD: 7.69, USDCHF: 11.11,
  XAUUSD: 10.0,
};

// ── CLOCK ─────────────────────────────────────────────────
function updateClocks() {
  const now = new Date();
  const et  = new Date(now.toLocaleString("en-US", { timeZone: "America/New_York" }));
  const utc = new Date(now.toLocaleString("en-US", { timeZone: "UTC" }));
  const fmt = d => d.toLocaleTimeString("en-US", { hour12: false });
  const fmtDate = d => d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
  document.getElementById("etClock").textContent  = `ET ${fmt(et)} | ${fmtDate(et)}`;
  document.getElementById("utcClock").textContent = `UTC ${fmt(utc)}`;
  updateSessions(et);
}
setInterval(updateClocks, 1000);
updateClocks();

// ── SESSION TRACKER ───────────────────────────────────────
function updateSessions(etDate) {
  const h = etDate.getHours();
  const m = etDate.getMinutes();
  const t = h * 60 + m;

  const sessions = [
    { id: "sess-london",    start: 2*60,  end: 5*60  },
    { id: "sess-sb-london", start: 3*60,  end: 4*60  },
    { id: "sess-ny",        start: 8*60,  end: 11*60 },
    { id: "sess-sb-ny",     start: 10*60, end: 11*60 },
    { id: "sess-lc",        start: 10*60, end: 12*60 },
  ];

  sessions.forEach(s => {
    const el = document.getElementById(s.id);
    if (!el) return;
    const active = t >= s.start && t < s.end;
    el.classList.toggle("active", active);
    const dot = el.querySelector(".sess-dot");
    if (dot) dot.textContent = active ? "●" : "○";
  });
}

// ── SOCKET.IO ─────────────────────────────────────────────
socket.on("connect", () => {
  const dot   = document.getElementById("connDot");
  const label = document.getElementById("connLabel");
  if (dot)   { dot.className = "sp-status-dot online"; }
  if (label) { label.textContent = "ONLINE — TradeLocker"; }
  socket.emit("get_initial_data");
});

socket.on("disconnect", () => {
  const dot   = document.getElementById("connDot");
  const label = document.getElementById("connLabel");
  if (dot)   { dot.className = "sp-status-dot offline"; }
  if (label) { label.textContent = "DISCONNECTED"; }
});

socket.on("full_update", data => {
  if (data.accounts)    { accounts = data.accounts; renderAccounts(data.accounts); renderPropGuard(data.accounts); }
  if (data.brain_stats) renderBrainStats(data.brain_stats);
  if (data.signals)     data.signals.forEach(s => addSignalCard(s));
  if (data.weekly)      renderWeekly(data.weekly);
});

socket.on("new_signal",    s  => addSignalCard(s));
socket.on("brain_update",  bs => renderBrainStats(bs));
socket.on("account_update", d => {
  if (accounts[d.account_id]) {
    accounts[d.account_id].enabled = d.enabled;
    renderAccounts(accounts);
    renderPropGuard(accounts);
  }
});
socket.on("emergency_stop", () => {
  Object.keys(accounts).forEach(k => { accounts[k].enabled = false; accounts[k].halted = true; });
  renderAccounts(accounts);
  alert("⛔ EMERGENCY STOP — All accounts halted");
});

// ── INITIAL DATA FETCH ────────────────────────────────────
fetch("/api/initial-data")
  .then(r => r.json())
  .then(data => {
    if (data.accounts)    { accounts = data.accounts; renderAccounts(data.accounts); renderPropGuard(data.accounts); }
    if (data.brain_stats) renderBrainStats(data.brain_stats);
    if (data.signals)     data.signals.slice().reverse().forEach(s => addSignalCard(s));
    if (data.weekly)      renderWeekly(data.weekly);
  })
  .catch(err => console.error("Initial data fetch failed:", err));

// ── RENDER ACCOUNTS ───────────────────────────────────────
function renderAccounts(accts) {
  const container = document.getElementById("accountsList");
  if (!container) return;

  const enabled = Object.values(accts).filter(a => a.enabled).length;
  const badge   = document.getElementById("acctBadge");
  if (badge) badge.textContent = `${Object.keys(accts).length} CONFIGURED`;

  container.innerHTML = Object.entries(accts).map(([key, acc]) => {
    const isLive     = acc.broker === "tradelocker";
    const cardClass  = isLive ? "live" : "";
    const brokerTag  = `<span class="acct-tag tag-tl">TradeLocker</span><span class="acct-tag tag-live">E8 EVALUATION</span>`;

    const pnlClass = (acc.daily_pnl || 0) >= 0 ? "green" : "red";
    const wPnlClass = (acc.weekly_pnl || 0) >= 0 ? "green" : "red";

    return `
      <div class="acct-card ${cardClass}" id="card-${key}">
        <div class="acct-top">
          <span class="acct-name">${acc.label}</span>
          <button class="acct-toggle ${acc.enabled ? 'on' : ''}"
            onclick="toggleAccount('${key}', ${!acc.enabled})"
            title="${acc.enabled ? 'Click to disable' : 'Click to enable'}"></button>
        </div>
        <div class="broker-row">
          <div class="broker-name">TradeLocker (E8)</div>
          <div class="broker-status-dot" id="tlDot">●</div>
          <div class="broker-msg" id="tlMsg">Checking E8 Handshake...</div>
        </div>
        <div class="acct-grid">
          <div class="acct-field">
            <span class="af-label">BALANCE</span>
            <span class="af-val">$${(acc.balance || 0).toLocaleString("en-US", {minimumFractionDigits: 0})}</span>
          </div>
          <div class="acct-field">
            <span class="af-label">DAILY P&L</span>
            <span class="af-val ${pnlClass}">$${(acc.daily_pnl || 0).toFixed(2)}</span>
          </div>
          <div class="acct-field">
            <span class="af-label">MAX LOT</span>
            <span class="af-val">${acc.max_lot_size || 0.5}</span>
          </div>
        </div>
      </div>`;
  }).join("");
}

// ── RENDER BRAIN STATS ────────────────────────────────────
function renderBrainStats(bs) {
  const set = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
  set("brainEvals",    bs.evals    || 0);
  set("brainApproved", bs.approved || 0);
  set("brainRate",     bs.rate     || "0%");
  set("brainStatus",   bs.status   || "ACTIVE");
}

// ── RENDER WEEKLY TRACKER ─────────────────────────────────
function renderWeekly(w) {
  const set = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
  const pnl   = w.weekly_pnl  || 0;
  const pct   = w.pct         || 0;
  const days  = w.days_left   || 0;

  set("weeklyPnl",  `$${pnl.toFixed(2)}`);
  set("weeklyPct",  `${pct}%`);
  set("weeklyDays", days);

  const fill  = document.getElementById("weeklyBarFill");
  const badge = document.getElementById("weeklyBadge");
  if (fill)  fill.style.width = `${Math.min(pct, 100)}%`;
  if (badge) {
    badge.textContent = w.on_track ? "ON TRACK" : "BEHIND";
    badge.className   = `weekly-badge${w.on_track ? "" : " behind"}`;
  }

  const pnlEl = document.getElementById("weeklyPnl");
  if (pnlEl) pnlEl.className = `ws-val ${pnl >= 0 ? "green" : "red"}`;
}

/// ── RENDER PROP GUARD (Daily Loss per account) ────────────────────
function renderPropGuard(accts) {
  const container = document.getElementById("propGuardList");
  if (!container) return;

  container.innerHTML = Object.entries(accts).map(([key, acc]) => {
    const dailyPnl  = acc.daily_pnl || 0;
    const dailyLim  = acc.daily_loss_limit || 500;
    const dailyUsed = Math.abs(Math.min(dailyPnl, 0));
    const dailyPct  = Math.min((dailyUsed / dailyLim) * 100, 100).toFixed(0);
    const pnlClass  = dailyPnl >= 0 ? "green" : "red";
    const barColor  = dailyPct > 80 ? "#ff4444" : dailyPct > 50 ? "#ffaa00" : "#00ff88";
    const isHalted  = acc.halted;

    return `
      <div class="pg-card ${isHalted ? 'halted' : ''}">
        <div class="pg-name">${acc.label.replace(" — TradeLocker LIVE", "").replace(" — Fallback/Testing", "")}</div>
        <div class="broker-info-row">
          <span class="bi-label">TradeLocker Account</span>
          <span class="bi-val" id="tlAcctId">—</span>
        </div>
        <div class="broker-info-row">
          <span class="bi-label">Server</span>
          <span class="bi-val" id="tlServer">E8</span>
        </div>
        <div class="pg-row">
          <span class="pg-row-label">Daily P&L</span>
          <span class="pg-row-val ${pnlClass}">$${dailyPnl.toFixed(2)}</span>
        </div>
        <div class="pg-row">
          <span class="pg-row-label">Loss Used</span>
          <span class="pg-row-val">${dailyPct}% of $${dailyLim}</span>
        </div>
        <div style="height:4px;background:rgba(255,255,255,0.1);border-radius:2px;margin:4px 0">
          <div style="height:4px;width:${dailyPct}%;background:${barColor};border-radius:2px;transition:width 0.5s"></div>
        </div>
        ${isHalted ? '<div style="color:#ff4444;font-size:10px;text-align:center;margin-top:4px">⛔ HALTED</div>' : ''}
      </div>`;
  }).join("");

  // Update loss guard status badge
  const anyHalted = Object.values(accts).some(a => a.halted);
  const lossStatus = document.getElementById("lossGuardStatus");
  if (lossStatus) {
    lossStatus.textContent = anyHalted ? "⛔ HALTED" : "✅ CLEAR";
    lossStatus.style.color = anyHalted ? "#ff4444" : "#00ff88";
  }
}

// ── FETCH & RENDER GUARDS STATUS ────────────────────────────────
function fetchGuardsStatus() {
  fetch("/api/guards/status")
    .then(r => r.json())
    .then(g => {
      const set = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
      const setColor = (id, color) => { const el = document.getElementById(id); if (el) el.style.color = color; };

      // Prop firm mode
      set("propFirmMode", g.prop_firm_mode || "E8");
      set("newsBlackoutMins", g.news_blackout_mins || 5);

      // News Guard
      const news = g.news_guard || {};
      const newsStatus = document.getElementById("newsGuardStatus");
      const newsDetail = document.getElementById("newsGuardDetail");
      if (newsStatus) {
        newsStatus.textContent = news.blocked ? `⛔ BLOCKED` : "✅ CLEAR";
        newsStatus.style.color = news.blocked ? "#ff4444" : "#00ff88";
      }
      if (newsDetail) {
        newsDetail.textContent = news.blocked
          ? (news.reason || "News blackout active")
          : (news.event ? `Next: ${news.event}` : "No high-impact news in window");
        newsDetail.style.color = news.blocked ? "#ffaa00" : "rgba(255,255,255,0.5)";
      }

      // Profit Cap Guard
      const caps = g.profit_cap_guard || {};
      const anyCapBlocked = Object.values(caps).some(c => c.blocked);
      const capStatus = document.getElementById("capGuardStatus");
      const capDetail = document.getElementById("capGuardDetail");
      if (capStatus) {
        capStatus.textContent = anyCapBlocked ? "⛔ BLOCKED" : "✅ CLEAR";
        capStatus.style.color = anyCapBlocked ? "#ff4444" : "#00ff88";
      }
      if (capDetail) {
        if (anyCapBlocked) {
          const blocked = Object.values(caps).find(c => c.blocked);
          capDetail.textContent = blocked ? blocked.reason : "Daily profit cap reached";
          capDetail.style.color = "#ffaa00";
        } else {
          const active = Object.values(caps).find(c => c.total_profit > 10);
          if (active) {
            capDetail.textContent = `Today: $${active.day_profit.toFixed(2)} of $${active.cap_amount.toFixed(2)} cap (${active.pct_used}% used)`;
          } else {
            capDetail.textContent = "Cap not yet active (no profit recorded)";
          }
          capDetail.style.color = "rgba(255,255,255,0.5)";
        }
      }

      // Master badge
      const badge = document.getElementById("pgBadge");
      if (badge) {
        const anyBlocked = g.any_blocked;
        badge.textContent = anyBlocked ? "⛔ BLOCKED" : "ALL CLEAR";
        badge.style.background = anyBlocked ? "rgba(255,68,68,0.2)" : "rgba(0,255,136,0.15)";
        badge.style.color = anyBlocked ? "#ff4444" : "#00ff88";
      }
    })
    .catch(() => {});
}

// ── FETCH TODAY'S NEWS EVENTS ─────────────────────────────────
function fetchNewsEvents() {
  fetch("/api/guards/news-events")
    .then(r => r.json())
    .then(data => {
      const list = document.getElementById("newsEventsList");
      const count = document.getElementById("newsEventCount");
      if (!list) return;

      const events = data.events_today || [];
      if (count) count.textContent = events.length ? `${events.length} events` : "none";

      if (!events.length) {
        list.innerHTML = '<span style="color:rgba(255,255,255,0.4);font-size:11px">No scheduled high-impact events today</span>';
        return;
      }

      list.innerHTML = events.map(ev => `
        <div class="news-event-item ${ev.active ? 'active' : ''}">
          <span class="ne-time">${ev.time_utc}</span>
          <span class="ne-label">${ev.label}</span>
          <span class="ne-window">${ev.window_start}–${ev.window_end}</span>
          ${ev.active ? '<span class="ne-active">⛔ LIVE</span>' : ''}
        </div>`).join("");
    })
    .catch(() => {});
}

// ── ADD SIGNAL CARD ───────────────────────────────────────
function addSignalCard(sig) {
  const feed = document.getElementById("signalsFeed");
  if (!feed) return;

  const empty = feed.querySelector(".sig-empty");
  if (empty) empty.remove();

  signalCount++;
  const cntEl = document.getElementById("sigCount");
  if (cntEl) cntEl.textContent = signalCount;

  const cardClass = sig.source === "TEST" ? "test" : sig.approved ? "approved" : "rejected";
  const dirClass  = (sig.direction || "").toLowerCase();
  const confColor = sig.confidence >= 80 ? "#10b981" : sig.confidence >= 72 ? "#f59e0b" : "#ef4444";
  const srcClass  = sig.source === "LIVE" ? "live" : "";

  const card = document.createElement("div");
  card.className = `sig-card ${cardClass}`;
  card.innerHTML = `
    <div class="sig-top">
      <span class="sig-symbol">${sig.symbol || "—"}</span>
      <span class="sig-dir ${dirClass}">${sig.direction || "—"}</span>
      <span class="sig-conf" style="color:${confColor}">${sig.confidence || 0}%</span>
      <span class="sig-source ${srcClass}">${sig.source || "DEMO"}</span>
      <span class="sig-time">${sig.timestamp || ""}</span>
    </div>
    <div class="sig-reason">${sig.reason || ""}</div>
    <div class="sig-meta">
      <span>Stop: ${sig.stop_pips || 0} pips</span>
      <span>Lot: ${sig.lot_size || 0}</span>
      ${sig.order_id ? `<span>Order: ${sig.order_id}</span>` : ""}
    </div>`;

  feed.insertBefore(card, feed.firstChild);

  // Keep last 20 cards
  while (feed.children.length > 20) feed.removeChild(feed.lastChild);

  // Update brain live text
  const liveText = document.getElementById("brainLiveText");
  if (liveText) liveText.textContent = sig.reason || "";
}

// ── TOGGLE ACCOUNT ────────────────────────────────────────
function toggleAccount(accountId, enabled) {
  fetch("/api/account/toggle", {
    method:  "POST",
    headers: { "Content-Type": "application/json" },
    body:    JSON.stringify({ account_id: accountId, enabled }),
  })
  .then(r => r.json())
  .then(data => {
    if (data.success && accounts[accountId]) {
      accounts[accountId].enabled = enabled;
      renderAccounts(accounts);
    }
  })
  .catch(err => console.error("Toggle failed:", err));
}

// ── EMERGENCY STOP ────────────────────────────────────────
function emergencyStop() {
  if (!confirm("⛔ EMERGENCY STOP — Halt ALL accounts? This will prevent any new orders.")) return;
  fetch("/api/emergency-stop", { method: "POST" })
    .then(r => r.json())
    .then(() => {
      Object.keys(accounts).forEach(k => { accounts[k].enabled = false; accounts[k].halted = true; });
      renderAccounts(accounts);
      alert("All accounts halted.");
    });
}

// ── CHECK BROKER STATUS ───────────────────────────────────
function checkBroker(retryCount) {
  retryCount = retryCount || 0;
  const badge = document.getElementById("brokerBadge");
  if (badge && retryCount === 0) {
    badge.textContent = "CHECKING...";
    badge.style.color = "";
  }

  fetch("/api/broker/status")
    .then(r => {
      if (!r.ok) throw new Error("HTTP " + r.status);
      return r.json();
    })
    .then(data => {
      const tl = data.tradelocker || {};

      // Update TradeLocker rows (global and in-card)
      const tlDots = document.querySelectorAll("[id='tlDot']");
      const tlMsgs = document.querySelectorAll("[id='tlMsg']");
      const tlId   = document.getElementById("tlAcctId");
      const tlSrv  = document.getElementById("tlServer");

      tlDots.forEach(dot => {
        dot.className = "broker-status-dot " + (tl.configured ? "online" : "offline");
        dot.textContent = "●";
      });

      const msgText = tl.configured
        ? "E8 Markets — Account " + (tl.account_id || "?") + " | Server: " + (tl.server || "E8")
        : (tl.message || "Not configured");
      
      tlMsgs.forEach(msg => {
        msg.textContent = msgText;
      });

      if (tlId)  tlId.textContent  = tl.account_id || "not set";
      if (tlSrv) tlSrv.textContent = tl.server     || "E8";

      const allOk = tl.configured;
      if (badge) {
        badge.textContent = allOk ? "READY" : "NOT CONFIGURED";
        badge.style.color = allOk ? "var(--accent-green)" : "var(--accent-red)";
      }
    })
    .catch(err => {
      console.error("Broker status check failed (attempt " + (retryCount+1) + "):", err);
      if (retryCount < 5) {
        // Retry with exponential backoff: 2s, 4s, 8s, 16s, 32s
        setTimeout(() => checkBroker(retryCount + 1), Math.min(2000 * Math.pow(2, retryCount), 30000));
      } else {
        if (badge) { badge.textContent = "ERROR"; badge.style.color = "var(--accent-red)"; }
      }
    });
}

// ── FIRE TEST SIGNAL ──────────────────────────────────────
function fireTestSignal() {
  const accountId = document.getElementById("testAccount").value;
  const symbol    = document.getElementById("testSymbol").value;
  const direction = document.getElementById("testDirection").value;
  const resultEl  = document.getElementById("testResult");

  if (resultEl) { resultEl.style.display = "block"; resultEl.className = "test-result"; resultEl.textContent = "⏳ Sending order..."; }

  fetch("/api/signals/test-signal", {
    method:  "POST",
    headers: { "Content-Type": "application/json" },
    body:    JSON.stringify({ account_id: accountId, symbol, direction }),
  })
  .then(r => r.json())
  .then(data => {
    if (!resultEl) return;
    if (data.success) {
      resultEl.className = "test-result success";
      resultEl.textContent = `✅ ORDER SENT — ${data.instrument || symbol} ${direction} 0.01L | Order: ${data.order_id} | ${data.message || ""}`;
    } else {
      resultEl.className = "test-result error";
      resultEl.textContent = `❌ FAILED: ${data.error || "Unknown error"}`;
    }
  })
  .catch(err => {
    if (resultEl) { resultEl.className = "test-result error"; resultEl.textContent = `❌ Network error: ${err}`; }
  });
}

// ── FIRE MANUAL SIGNAL ────────────────────────────────────
function fireManualSignal() {
  const accountId = document.getElementById("manualAccount").value;
  const symbol    = document.getElementById("manualSymbol").value;
  const direction = document.getElementById("manualDirection").value;
  const stopPips  = parseFloat(document.getElementById("manualStopPips").value) || 10;
  const resultEl  = document.getElementById("manualResult");

  if (resultEl) { resultEl.style.display = "block"; resultEl.className = "manual-result"; resultEl.textContent = "⏳ Sending..."; }

  fetch("/api/signals/manual", {
    method:  "POST",
    headers: { "Content-Type": "application/json" },
    body:    JSON.stringify({ account_id: accountId, symbol, direction, stop_pips: stopPips }),
  })
  .then(r => r.json())
  .then(data => {
    if (!resultEl) return;
    if (data.success) {
      resultEl.className = "manual-result success";
      resultEl.textContent = `✅ ${data.message || "Order sent"} | Lot: ${data.lot_size} | Order: ${data.order_id}`;
    } else {
      resultEl.className = "manual-result error";
      resultEl.textContent = `❌ FAILED: ${data.error || "Unknown error"}`;
    }
  })
  .catch(err => {
    if (resultEl) { resultEl.className = "manual-result error"; resultEl.textContent = `❌ Network error: ${err}`; }
  });
}

// ── LOT SIZE CALCULATOR ───────────────────────────────────
function calcLotSize() {
  const risk    = parseFloat(document.getElementById("rcRisk").value)  || 100;
  const stop    = parseFloat(document.getElementById("rcStop").value)  || 10;
  const symbol  = document.getElementById("rcSymbol").value;
  const pipVal  = PIP_VALUES[symbol] || 10.0;
  const rawLots = risk / (stop * pipVal);
  const lots    = Math.max(0.01, Math.round(rawLots * 100) / 100);
  const resultEl = document.getElementById("rcResult");
  if (resultEl) {
    resultEl.textContent = `${lots} lots  (Risk $${risk} ÷ ${stop} pips × $${pipVal}/pip)`;
  }
}

// ── INIT ─────────────────────────────────────────────────────
// Delay initial broker check slightly to ensure DOM is fully ready
setTimeout(() => checkBroker(), 500);

// Auto-refresh broker status every 15 seconds
setInterval(() => checkBroker(), 15000);

// Initial guards fetch
fetchGuardsStatus();
fetchNewsEvents();

// Poll guards every 30 seconds
setInterval(fetchGuardsStatus, 30000);

// Refresh news events every 5 minutes
setInterval(fetchNewsEvents, 300000);
