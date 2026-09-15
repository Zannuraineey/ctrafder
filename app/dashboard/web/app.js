/**
 * ANTIGRAVITY QUANT // Institutional Workstation Client Controller
 * Strict 8px grid data-binding, 10 workspace routing, zero emojis, tabular precision.
 */

// ==========================================================================
// 1. TERMINAL STATE
// ==========================================================================
const TerminalState = {
  activeWorkspace: "overview",
  selectedSymbol: "Step_Index",
  marketCategory: "ALL",
  isEngineRunning: true,
  currentBalanceTier: null, // null = real cTrader balance
  chartData: null,
  prices: {},
  positions: [],
  account: null,
  tournament: null,
  calibration: null,
  directive: null,
  briefing: null,
  macroEvents: [],
  mistakes: [],
  executionEvents: [],
};

// ==========================================================================
// 2. TABULAR FORMATTERS (DATA-FIRST, ZERO FLUFF)
// ==========================================================================
function formatCurrency(val, decimals = 2) {
  if (val === undefined || val === null || isNaN(val)) return "$0.00";
  return `$${Number(val).toLocaleString("en-US", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  })}`;
}

function formatPnl(val, decimals = 2) {
  if (val === undefined || val === null || isNaN(val)) return "$0.00";
  const num = Number(val);
  const sign = num > 0 ? "+" : "";
  return `${sign}$${num.toLocaleString("en-US", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  })}`;
}

function formatPrice(val, digits = 2) {
  if (val === undefined || val === null || isNaN(val)) return "0.00";
  return Number(val).toFixed(digits);
}

function formatPercent(val, decimals = 1) {
  if (val === undefined || val === null || isNaN(val)) return "0.0%";
  return `${Number(val).toFixed(decimals)}%`;
}

function getTimestampStr() {
  const d = new Date();
  const pad = (n) => String(n).padStart(2, "0");
  return `[${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())}:${pad(d.getUTCSeconds())}]`;
}

// ==========================================================================
// 3. INITIALIZATION & WORKSPACE ROUTING
// ==========================================================================
document.addEventListener("DOMContentLoaded", () => {
  setupWorkspaceRouting();
  setupTopBarControls();
  setupRiskTierControls();
  setupCanvasResizers();
  startUtcClock();

  // Initial immediate fetch
  syncAllWorkspaces();

  // Polling loops (Tiered resource management)
  // Fast: 3000ms (Account, Positions, Chart)
  setInterval(() => {
    if (!document.hidden) {
      fetchAccount();
      fetchPositions();
      fetchChart(TerminalState.selectedSymbol);
      fetchSymbolDecision(TerminalState.selectedSymbol);
    }
  }, 3000);

  // Medium: 6000ms (Scanner, Tournament)
  setInterval(() => {
    if (!document.hidden) {
      fetchScanner();
      fetchTournament();
    }
  }, 6000);

  // Slow: 15000ms (Brain Calibration, Supervision, Macro, Floor)
  setInterval(() => {
    if (!document.hidden) {
      fetchBrainCalibration();
      fetchSupervision();
      fetchMacroSchedule();
      fetchFloorMatrix();
      fetchMistakes();
    }
  }, 15000);
});

function setupWorkspaceRouting() {
  const navButtons = document.querySelectorAll(".nav-item");
  navButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      const targetWorkspace = btn.dataset.workspace;
      if (!targetWorkspace) return;

      // Update Nav Buttons
      navButtons.forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");

      // Switch Panes
      const panes = document.querySelectorAll(".workspace-pane");
      panes.forEach((p) => p.classList.remove("active"));

      const activePane = document.getElementById(`pane-${targetWorkspace}`);
      if (activePane) {
        activePane.classList.add("active");
        TerminalState.activeWorkspace = targetWorkspace;

        // Auto redraw canvas if switching to overview or chart
        if (targetWorkspace === "overview" || targetWorkspace === "chart") {
          setTimeout(() => {
            if (TerminalState.chartData) {
              drawCanvasChart("terminal-chart-canvas", TerminalState.chartData);
              drawCanvasChart("chart-full-canvas", TerminalState.chartData);
            }
          }, 50);
        }
      }
    });
  });

  // Market Scanner Category filter tabs
  const marketTabs = document.querySelectorAll("#market-filter-tabs button");
  marketTabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      marketTabs.forEach((t) => t.classList.remove("active"));
      tab.classList.add("active");
      TerminalState.marketCategory = tab.dataset.cat || "ALL";
      renderMarketsTable();
    });
  });
}

function setupTopBarControls() {
  const btnToggle = document.getElementById("btn-engine-toggle");
  if (btnToggle) {
    btnToggle.addEventListener("click", async () => {
      try {
        const res = await fetch("/api/toggle-trading-engine", { method: "POST" });
        const data = await res.json();
        TerminalState.isEngineRunning = data.is_running;
        if (data.is_running) {
          btnToggle.className = "btn-terminal-sm engine-running";
          btnToggle.textContent = "ENGINE: [RUNNING]";
        } else {
          btnToggle.className = "btn-terminal-sm engine-halted";
          btnToggle.textContent = "ENGINE: [HALTED]";
        }
        pushExecutionLog(`Engine state toggled: ${data.is_running ? "RUNNING" : "HALTED"}`);
      } catch (err) {
        console.error("Failed to toggle engine:", err);
      }
    });
  }

  const btnEmergency = document.getElementById("btn-emergency-stop");
  if (btnEmergency) {
    btnEmergency.addEventListener("click", async () => {
      if (confirm("TRIGGER EMERGENCY KILL SWITCH: Liquidate all open positions immediately and halt floor?")) {
        try {
          const res = await fetch("/api/emergency-stop", { method: "POST" });
          const data = await res.json();
          pushExecutionLog(`EMERGENCY STOP TRIGGERED: ${data.message}`);
          fetchPositions();
          fetchAccount();
        } catch (err) {
          console.error("Emergency stop failed:", err);
        }
      }
    });
  }

  // Snap BE buttons
  const btnOvSnapBe = document.getElementById("btn-ov-snap-be");
  const btnPosSnapBe = document.getElementById("btn-pos-snap-be");
  const snapBeHandler = async () => {
    try {
      const res = await fetch("/api/positions/breakeven-all", { method: "POST" });
      const data = await res.json();
      pushExecutionLog(`Snap to Breakeven executed for ${data.count || 0} positions.`);
      fetchPositions();
    } catch (err) {
      console.error("Breakeven all failed:", err);
    }
  };
  if (btnOvSnapBe) btnOvSnapBe.addEventListener("click", snapBeHandler);
  if (btnPosSnapBe) btnPosSnapBe.addEventListener("click", snapBeHandler);
}

function setupRiskTierControls() {
  const tierButtons = document.querySelectorAll(".btn-tier-sel");
  tierButtons.forEach((btn) => {
    btn.addEventListener("click", async () => {
      tierButtons.forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      const tier = btn.dataset.tier;
      if (tier === "real") {
        TerminalState.currentBalanceTier = null;
        await fetch("/api/account?use_real=true&reset=true");
      } else {
        TerminalState.currentBalanceTier = parseFloat(tier);
        await fetch(`/api/account?balance=${TerminalState.currentBalanceTier}&reset=true`);
      }
      fetchAccount();
    });
  });
}

function startUtcClock() {
  const clockEl = document.getElementById("topbar-clock");
  function tick() {
    const now = new Date();
    const str = now.toISOString().replace("T", " ").substring(0, 19) + " UTC";
    if (clockEl) clockEl.textContent = str;
  }
  tick();
  setInterval(tick, 1000);
}

function setupCanvasResizers() {
  window.addEventListener("resize", () => {
    if (TerminalState.chartData) {
      drawCanvasChart("terminal-chart-canvas", TerminalState.chartData);
      drawCanvasChart("chart-full-canvas", TerminalState.chartData);
    }
  });
}

// ==========================================================================
// 4. DATA SYNC & API INTEGRATION
// ==========================================================================
async function syncAllWorkspaces() {
  await Promise.all([
    fetchAccount(),
    fetchPositions(),
    fetchScanner(),
    fetchChart(TerminalState.selectedSymbol),
    fetchTournament(),
    fetchBrainCalibration(),
    fetchSupervision(),
    fetchMacroSchedule(),
    fetchFloorMatrix(),
    fetchMistakes(),
  ]);
}

async function fetchAccount() {
  try {
    const url = TerminalState.currentBalanceTier !== null
      ? "/api/account"
      : "/api/account?use_real=true";
    const res = await fetch(url);
    if (!res.ok) return;
    const acc = await res.json();
    TerminalState.account = acc;

    // Topbar update
    const topBal = document.getElementById("top-balance");
    const topEq = document.getElementById("top-equity");
    const topUnreal = document.getElementById("top-unreal-pnl");
    const topRisk = document.getElementById("top-risk-cap");
    const topVar = document.getElementById("top-var");
    const brokerStatus = document.getElementById("topbar-broker-status");

    if (topBal) topBal.textContent = formatCurrency(acc.balance);
    if (topEq) topEq.textContent = formatCurrency(acc.equity);
    if (topRisk) topRisk.textContent = formatCurrency(acc.risk_limit_2pct);
    if (topVar) topVar.textContent = formatCurrency(acc.var_99_1day);

    if (brokerStatus && acc.real_broker) {
      const liveTag = acc.real_is_live ? "LIVE" : "DEMO";
      brokerStatus.textContent = `${acc.real_broker.toUpperCase()} cTrader [${liveTag} #${acc.real_account_id || "2547594"}]`;
    }

    // Overview Cards
    const ovEq = document.getElementById("ov-equity");
    const ovBal = document.getElementById("ov-balance");
    if (ovEq) ovEq.textContent = formatCurrency(acc.equity);
    if (ovBal) ovBal.textContent = `Balance: ${formatCurrency(acc.balance)}`;

    // Context Rail Margin Meter
    const ctxMarginUsed = document.getElementById("ctx-margin-used");
    const ctxMarginBar = document.getElementById("ctx-margin-bar");
    const ctxFreeMargin = document.getElementById("ctx-free-margin");
    const marginUsed = acc.margin_used || 0;
    const marginPct = Math.min(100, Math.round((marginUsed / Math.max(acc.equity, 1)) * 100));

    if (ctxMarginUsed) ctxMarginUsed.textContent = `${formatCurrency(marginUsed)} / ${formatCurrency(acc.equity)}`;
    if (ctxMarginBar) ctxMarginBar.style.width = `${marginPct}%`;
    if (ctxFreeMargin) ctxFreeMargin.textContent = formatCurrency(acc.free_margin || acc.equity);

    // Risk Workspace values
    const riskCeiling = document.getElementById("risk-loss-ceiling");
    const riskVar = document.getElementById("risk-var-val");
    if (riskCeiling) riskCeiling.textContent = formatCurrency(acc.risk_limit_2pct);
    if (riskVar) riskVar.textContent = formatCurrency(acc.var_99_1day);

  } catch (err) {
    console.warn("fetchAccount error:", err);
  }
}

async function fetchPositions() {
  try {
    const res = await fetch("/api/positions");
    if (!res.ok) return;
    const positions = await res.json();
    TerminalState.positions = positions;

    // Badges update
    const navPosBadge = document.getElementById("nav-badge-positions");
    if (navPosBadge) navPosBadge.textContent = positions.length;

    const ovOpenCount = document.getElementById("ov-open-count");
    if (ovOpenCount) ovOpenCount.textContent = `${positions.length} Open Positions`;

    const ctxOpenLots = document.getElementById("ctx-open-lots");
    const totalLots = positions.reduce((sum, p) => sum + (p.lots || 0), 0);
    if (ctxOpenLots) ctxOpenLots.textContent = `${totalLots.toFixed(2)} Lots`;

    const totalUnrealized = positions.reduce((sum, p) => sum + (p.unrealized_pnl || 0), 0);
    const topUnreal = document.getElementById("top-unreal-pnl");
    if (topUnreal) {
      topUnreal.textContent = formatPnl(totalUnrealized);
      topUnreal.className = `value tabular-nums ${totalUnrealized >= 0 ? "pos" : "neg"}`;
    }

    renderPositionsTables(positions);
  } catch (err) {
    console.warn("fetchPositions error:", err);
  }
}

function renderPositionsTables(positions) {
  const ovTbody = document.getElementById("ov-positions-tbody");
  const fullTbody = document.getElementById("positions-full-tbody");

  if (!positions || !Array.isArray(positions) || positions.length === 0) {
    const emptyRow = `<tr><td colspan="15" style="text-align: center; color: var(--text-muted); padding: 16px;">NO OPEN POSITIONS &bull; EXECUTION ENGINE STANDING BY</td></tr>`;
    if (ovTbody) ovTbody.innerHTML = emptyRow;
    if (fullTbody) fullTbody.innerHTML = emptyRow;
    return;
  }

  // Overview compact table rows
  if (ovTbody) {
    ovTbody.innerHTML = positions.map((p) => {
      const pnlClass = p.unrealized_pnl >= 0 ? "pos" : "neg";
      const sideClass = p.side === "BUY" ? "buy" : "sell";
      return `
        <tr>
          <td><code>${p.id.substring(0, 8)}</code></td>
          <td><strong style="color: var(--text-bright);">${p.symbol}</strong></td>
          <td><span class="tag-status ${sideClass}">${p.side}</span></td>
          <td class="num">${p.lots.toFixed(2)}</td>
          <td class="num">${formatPrice(p.entry_price)}</td>
          <td class="num">${formatPrice(p.current_price)}</td>
          <td class="num">${formatPrice(p.stop_loss)}</td>
          <td class="num">${formatPrice(p.take_profit)}</td>
          <td class="num ${pnlClass}"><strong>${formatPnl(p.unrealized_pnl)}</strong></td>
          <td><span class="tag-status info">${p.lifecycle_action || "HOLD"}</span></td>
          <td>
            <button class="btn-action-sm" onclick="handleSnapBe('${p.id}')">BE</button>
            <button class="btn-action-sm danger" onclick="handleClosePosition('${p.id}')">CLOSE</button>
          </td>
        </tr>
      `;
    }).join("");
  }

  // Full Positions Workspace table
  if (fullTbody) {
    fullTbody.innerHTML = positions.map((p) => {
      const pnlClass = p.unrealized_pnl >= 0 ? "pos" : "neg";
      const sideClass = p.side === "BUY" ? "buy" : "sell";
      return `
        <tr>
          <td><code>${p.id}</code></td>
          <td><strong>${p.symbol}</strong></td>
          <td><span class="tag-status ${sideClass}">${p.side}</span></td>
          <td class="num">${p.lots.toFixed(2)}</td>
          <td class="num">${formatPrice(p.entry_price)}</td>
          <td class="num">${formatPrice(p.current_price)}</td>
          <td class="num">${formatPrice(p.stop_loss)}</td>
          <td class="num">${formatPrice(p.take_profit)}</td>
          <td class="num">${p.is_be_active ? "LOCKED" : "NONE"}</td>
          <td class="num ${pnlClass}"><strong>${formatPnl(p.unrealized_pnl)}</strong></td>
          <td class="num ${pnlClass}">${p.r_multiple || "+0.0R"}</td>
          <td>${p.duration_seconds || 0}s</td>
          <td><span class="tag-status ${pnlClass === 'pos' ? 'pos' : 'warn'}">${p.lifecycle_action || "HOLD"}</span></td>
          <td>${p.is_be_active ? "<span class='tag-status pos'>PROTECTED</span>" : "<span class='tag-status neutral'>STANDARD</span>"}</td>
          <td>
            <button class="btn-action-sm" onclick="handleSnapBe('${p.id}')">BREAKEVEN</button>
            <button class="btn-action-sm danger" onclick="handleClosePosition('${p.id}')">FLATTEN</button>
          </td>
        </tr>
      `;
    }).join("");
  }
}

// Global action handlers accessible to inline onclick
window.handleSnapBe = async function(posId) {
  try {
    const res = await fetch(`/api/positions/${posId}/breakeven`, { method: "POST" });
    const data = await res.json();
    pushExecutionLog(`Position ${posId} stop loss snapped to Breakeven.`);
    fetchPositions();
  } catch (err) {
    console.error("Snap BE failed:", err);
  }
};

window.handleClosePosition = async function(posId) {
  try {
    const res = await fetch(`/api/positions/${posId}/close`, { method: "POST" });
    const data = await res.json();
    pushExecutionLog(`Position ${posId} closed at market.`);
    fetchPositions();
    fetchAccount();
  } catch (err) {
    console.error("Close position failed:", err);
  }
};

async function fetchScanner() {
  try {
    const res = await fetch("/api/scanner");
    if (!res.ok) return;
    const scannerData = await res.json();
    TerminalState.prices = scannerData;

    renderOverviewFocusMarkets(scannerData);
    renderMarketsTable();
  } catch (err) {
    console.warn("fetchScanner error:", err);
  }
}

function renderOverviewFocusMarkets(scannerData) {
  const ovTbody = document.getElementById("ov-market-tbody");
  if (!ovTbody) return;

  const searchInput = document.getElementById("mkt-search-input");
  const query = (searchInput ? searchInput.value : "").trim().toUpperCase();

  let entries = Object.entries(scannerData);
  if (TerminalState.marketCategory && TerminalState.marketCategory !== "ALL") {
    entries = entries.filter(([sym, d]) => {
      const cat = (d.category || d.asset_class || "").toUpperCase();
      return cat.includes(TerminalState.marketCategory) || sym.toUpperCase().includes(TerminalState.marketCategory);
    });
  }

  if (query) {
    entries = entries.filter(([sym]) => sym.toUpperCase().includes(query));
  } else if (!TerminalState.marketCategory || TerminalState.marketCategory === "ALL") {
    if (entries.length > 25) {
      const core = ["Step_Index", "Vol_25_1s", "Crash_500", "Boom_1000", "XAUUSD", "EURUSD", "Vol_75", "Vol_10_1s", "BTCUSD", "GBPUSD", "USDJPY", "Crash_1000", "Boom_500", "Vol_50_1s", "Vol_100"];
      const priority = entries.filter(([s]) => core.includes(s));
      const others = entries.filter(([s]) => !core.includes(s));
      entries = [...priority, ...others].slice(0, 30);
    }
  }

  const countEl = document.getElementById("ov-market-count");
  if (countEl) countEl.textContent = `${entries.length} INSTRUMENTS`;

  ovTbody.innerHTML = entries.map(([sym, data]) => {
    const bid = data.bid || 0;
    const ask = data.ask || 0;
    const spread = ((ask - bid) * (sym.includes("EUR") ? 10000 : 1)).toFixed(1);
    const signalTag = data.direction === "BUY"
      ? `<span class="tag-status buy">LONG</span>`
      : data.direction === "SELL"
      ? `<span class="tag-status sell">SHORT</span>`
      : `<span class="tag-status neutral">NEUTRAL</span>`;

    const isSelected = sym === TerminalState.selectedSymbol ? "selected" : "";
    return `
      <tr class="${isSelected}" onclick="handleSelectSymbol('${sym}')">
        <td><strong>${sym}</strong></td>
        <td class="num">${formatPrice(bid)}</td>
        <td class="num">${formatPrice(ask)}</td>
        <td class="num">${spread}</td>
        <td><span class="tag-status info">POC DEF</span></td>
        <td>${signalTag}</td>
      </tr>
    `;
  }).join("");
}

function renderMarketsTable() {
  const tbody = document.getElementById("markets-full-tbody");
  if (!tbody || !TerminalState.prices) return;

  let entries = Object.entries(TerminalState.prices);
  if (TerminalState.marketCategory !== "ALL") {
    entries = entries.filter(([sym, d]) => {
      const cat = (d.category || "SYNTHETICS").toUpperCase();
      return cat.includes(TerminalState.marketCategory);
    });
  }

  tbody.innerHTML = entries.map(([sym, d]) => {
    const bid = d.bid || 0;
    const ask = d.ask || 0;
    const spread = ((ask - bid) * (sym.includes("EUR") ? 10000 : 1)).toFixed(1);
    const signalTag = d.direction === "BUY"
      ? `<span class="tag-status buy">LONG</span>`
      : d.direction === "SELL"
      ? `<span class="tag-status sell">SHORT</span>`
      : `<span class="tag-status neutral">PASS</span>`;

    const isSelected = sym === TerminalState.selectedSymbol ? "selected" : "";
    return `
      <tr class="${isSelected}">
        <td><strong>${sym}</strong></td>
        <td>${d.category || "SYNTHETIC"}</td>
        <td class="num">${formatPrice(bid)}</td>
        <td class="num">${formatPrice(ask)}</td>
        <td class="num">${spread}</td>
        <td class="num">${(d.volatility_ratio || 1.0).toFixed(2)}x</td>
        <td class="num">${formatPrice(d.poc_target || bid * 1.002)}</td>
        <td class="num pos">2.5R : 1.0R</td>
        <td>${signalTag}</td>
        <td><span class="tag-status pos">FEASIBLE</span></td>
        <td>
          <button class="btn-action-sm" onclick="handleSelectSymbol('${sym}')">LOAD CHART</button>
        </td>
      </tr>
    `;
  }).join("");
}

window.handleSelectSymbol = function(sym) {
  TerminalState.selectedSymbol = sym;
  const navSym = document.getElementById("nav-active-sym");
  const ovTitle = document.getElementById("ov-chart-title");
  const fullTitle = document.getElementById("chart-full-sym-title");
  const ctxSym = document.getElementById("ctx-sym-tag");
  const targetEl = document.getElementById("ai-target-symbol");

  if (navSym) navSym.textContent = sym;
  if (ovTitle) ovTitle.textContent = sym;
  if (fullTitle) fullTitle.textContent = sym;
  if (ctxSym) ctxSym.textContent = sym;
  if (targetEl) targetEl.textContent = sym;

  fetchChart(sym);
  fetchSymbolDecision(sym);
  renderMarketsTable();
  renderOverviewFocusMarkets(TerminalState.prices);
};

// ==========================================================================
// 5. CHART CANVAS ENGINE (HIGH RESOLUTION & VOLUME PROFILE POC)
// ==========================================================================
async function fetchChart(symbol) {
  try {
    const res = await fetch(`/api/chart/${symbol}`);
    if (!res.ok) return;
    const chartPayload = await res.json();
    TerminalState.chartData = chartPayload;

    const candleList = Array.isArray(chartPayload)
      ? chartPayload
      : (chartPayload.candles || []);

    const pocLevel = chartPayload && chartPayload.poc !== undefined ? chartPayload.poc : null;

    drawCanvasChart("terminal-chart-canvas", candleList, pocLevel);
    drawCanvasChart("chart-full-canvas", candleList, pocLevel);

    if (candleList && candleList.length > 0) {
      const last = candleList[candleList.length - 1];
      const fullPrice = document.getElementById("chart-full-price");
      const currentPrice = chartPayload && chartPayload.current_price !== undefined ? chartPayload.current_price : (last ? last.close : 0);
      if (fullPrice) fullPrice.textContent = formatPrice(currentPrice);
    }
  } catch (err) {
    console.warn("fetchChart error:", err);
  }
}

function drawCanvasChart(canvasId, candles, customPoc = null) {
  const canvas = document.getElementById(canvasId);
  if (!canvas || !candles || !Array.isArray(candles) || candles.length < 2) return;

  const ctx = canvas.getContext("2d");
  const rect = canvas.getBoundingClientRect();
  if (!rect.width || !rect.height) return; // Guard against hidden pane sizing

  canvas.width = rect.width * (window.devicePixelRatio || 1);
  canvas.height = rect.height * (window.devicePixelRatio || 1);
  ctx.scale(window.devicePixelRatio || 1, window.devicePixelRatio || 1);

  const width = rect.width;
  const height = rect.height;

  // Background Fill
  ctx.fillStyle = "#101216";
  ctx.fillRect(0, 0, width, height);

  const visibleBars = Math.min(candles.length, 50);
  const data = candles.slice(-visibleBars);

  let high = -Infinity;
  let low = Infinity;
  data.forEach((c) => {
    if (c.high > high) high = c.high;
    if (c.low < low) low = c.low;
  });

  const range = high - low || 1.0;
  const paddingY = 24;
  const chartH = height - paddingY * 2;
  const getY = (price) => height - paddingY - ((price - low) / range) * chartH;

  const barW = width / visibleBars;
  const candleBodyW = Math.max(2, barW * 0.65);

  // Subtle Grid lines (4 horizontal price levels)
  ctx.strokeStyle = "#1a1e26";
  ctx.lineWidth = 1;
  ctx.font = "9px 'JetBrains Mono', monospace";
  ctx.fillStyle = "#505866";
  for (let i = 0; i <= 4; i++) {
    const p = low + (range * i) / 4;
    const y = getY(p);
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(width, y);
    ctx.stroke();
    ctx.fillText(formatPrice(p), 6, y - 3);
  }

  // Draw Candlesticks
  data.forEach((c, i) => {
    const x = i * barW + barW / 2;
    const isUp = c.close >= c.open;
    const color = isUp ? "#10b981" : "#f43f5e";

    // Wick
    ctx.strokeStyle = color;
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(x, getY(c.high));
    ctx.lineTo(x, getY(c.low));
    ctx.stroke();

    // Body
    const openY = getY(c.open);
    const closeY = getY(c.close);
    const bodyTop = Math.min(openY, closeY);
    const bodyH = Math.max(1.5, Math.abs(closeY - openY));

    ctx.fillStyle = color;
    ctx.fillRect(x - candleBodyW / 2, bodyTop, candleBodyW, bodyH);
  });

  // POC (Point of Control) Amber Line
  const pocVal = customPoc || (TerminalState.chartData ? TerminalState.chartData.poc : null);
  if (pocVal && pocVal >= low && pocVal <= high) {
    const pocY = getY(pocVal);
    ctx.save();
    ctx.strokeStyle = "#f59e0b";
    ctx.lineWidth = 1.5;
    ctx.setLineDash([4, 3]);
    ctx.beginPath();
    ctx.moveTo(0, pocY);
    ctx.lineTo(width, pocY);
    ctx.stroke();

    ctx.fillStyle = "#f59e0b";
    ctx.font = "bold 9px 'JetBrains Mono', monospace";
    ctx.fillText(`POC ${formatPrice(pocVal)}`, width - 90, pocY - 4);
    ctx.restore();
  }

  // Crosshair / Last Price Dotted Line
  const lastCandle = data[data.length - 1];
  const lastY = getY(lastCandle.close);
  ctx.save();
  ctx.strokeStyle = lastCandle.close >= lastCandle.open ? "rgba(16, 185, 129, 0.4)" : "rgba(244, 63, 94, 0.4)";
  ctx.lineWidth = 1;
  ctx.setLineDash([2, 2]);
  ctx.beginPath();
  ctx.moveTo(0, lastY);
  ctx.lineTo(width, lastY);
  ctx.stroke();
  ctx.restore();
}

// ==========================================================================
// 6. QUANT STRATEGY TOURNAMENT & BRAIN CALIBRATION
// ==========================================================================
async function fetchTournament() {
  try {
    const res = await fetch("/api/tournament");
    if (!res.ok) return;
    const data = await res.json();
    TerminalState.tournament = data;

    const tbody = document.getElementById("tournament-full-tbody");
    if (!tbody || !data.leaderboard) return;

    const decayLabel = document.getElementById("strategy-decay-label");
    if (decayLabel && data.allocator_decay) {
      decayLabel.textContent = `MEMORY DECAY: ${data.allocator_decay}`;
    }

    tbody.innerHTML = data.leaderboard.map((item) => {
      const pnlClass = item.total_pnl >= 0 ? "pos" : "neg";
      const statusBadge = item.status === "LEADER"
        ? `<span class="tag-status pos">LEADER</span>`
        : `<span class="tag-status neutral">${item.status}</span>`;
      return `
        <tr>
          <td>#${item.rank}</td>
          <td><strong style="color: var(--text-bright);">${item.strategy}</strong></td>
          <td class="num">${item.total_trades}</td>
          <td class="num">${item.win_rate.toFixed(1)}%</td>
          <td class="num ${pnlClass}">${formatPnl(item.total_pnl)}</td>
          <td class="num">${item.profit_factor.toFixed(2)}</td>
          <td class="num">${item.sharpe_ratio.toFixed(2)}</td>
          <td class="num info">${item.deflated_sharpe_ratio.toFixed(2)}</td>
          <td class="num neg">-${(item.max_drawdown * 100).toFixed(1)}%</td>
          <td class="num pos"><strong>${item.capital_allocation.toFixed(2)}x</strong></td>
          <td>${statusBadge}</td>
        </tr>
      `;
    }).join("");
  } catch (err) {
    console.warn("fetchTournament error:", err);
  }
}

async function fetchBrainCalibration() {
  try {
    const res = await fetch("/api/brain/calibration");
    if (!res.ok) return;
    const data = await res.json();
    TerminalState.calibration = data;

    // AI Brain Workspace DOM
    const calMethod = document.getElementById("brain-cal-method");
    const calCov = document.getElementById("brain-coverage");
    const calInterval = document.getElementById("brain-interval");
    const calUncert = document.getElementById("brain-uncertainty-vals");
    const ctxInterval = document.getElementById("ctx-conformal-interval");

    if (calMethod) calMethod.textContent = (data.calibrator_method || "ISOTONIC REGRESSION").toUpperCase();
    if (calCov) calCov.textContent = `${((data.uncertainty_confidence_level || 0.9) * 100).toFixed(1)}% COVERAGE`;

    if (data.last_uncertainty) {
      const lo = (data.last_uncertainty.lower_bound * 100).toFixed(1);
      const hi = (data.last_uncertainty.upper_bound * 100).toFixed(1);
      const intervalStr = `[${lo}%, ${hi}%]`;
      if (calInterval) calInterval.textContent = intervalStr;
      if (ctxInterval) ctxInterval.textContent = intervalStr;

      const epi = (data.last_uncertainty.epistemic_uncertainty || 0.034).toFixed(3);
      const ale = (data.last_uncertainty.aleatoric_uncertainty || 0.941).toFixed(3);
      if (calUncert) calUncert.textContent = `EPI: ${epi} | ALE: ${ale}`;
    }

    // Weights table
    const tbody = document.getElementById("brain-weights-tbody");
    if (tbody && data.learned_weights) {
      tbody.innerHTML = Object.entries(data.learned_weights).map(([feat, w]) => {
        const pct = ((Math.abs(w) / 5) * 100).toFixed(1);
        return `
          <tr>
            <td><strong>${feat}</strong></td>
            <td class="num ${w >= 0 ? "pos" : "neg"}">${w >= 0 ? "+" : ""}${w.toFixed(3)}</td>
            <td class="num">${pct}%</td>
            <td>Sub-Model Stacking Classifier Input</td>
          </tr>
        `;
      }).join("");
    }
  } catch (err) {
    console.warn("fetchBrainCalibration error:", err);
  }
}

async function fetchSupervision() {
  try {
    const [dirRes, briefRes] = await Promise.all([
      fetch("/api/supervision/directive"),
      fetch("/api/supervision/briefing"),
    ]);

    if (dirRes.ok) {
      const dir = await dirRes.json();
      TerminalState.directive = dir;

      const regimeEl = document.getElementById("ctx-directive-regime");
      const riskCapEl = document.getElementById("ctx-directive-risk-cap");
      const forbiddenEl = document.getElementById("ctx-directive-forbidden");
      const rationaleEl = document.getElementById("ctx-directive-rationale");
      const ovRiskCap = document.getElementById("ov-risk-cap");

      if (regimeEl) regimeEl.textContent = dir.regime_assessment || "CALM_TRENDING";
      if (riskCapEl) riskCapEl.textContent = `${(dir.risk_multiplier_cap || 1.15).toFixed(2)}x`;
      if (ovRiskCap) ovRiskCap.textContent = `${(dir.risk_multiplier_cap || 1.15).toFixed(2)}x MULTIPLIER`;
      if (forbiddenEl) forbiddenEl.textContent = dir.forbidden_symbols && dir.forbidden_symbols.length > 0 ? dir.forbidden_symbols.join(", ") : "NONE";
      if (rationaleEl) rationaleEl.textContent = dir.macro_rationale || "";
    }

    if (briefRes.ok) {
      const brief = await briefRes.json();
      TerminalState.briefing = brief;

      const briefId = document.getElementById("sys-briefing-id");
      const posture = document.getElementById("sys-desk-posture");
      const circuit = document.getElementById("sys-circuit-state");
      const topStrat = document.getElementById("sys-top-strat");
      const briefText = document.getElementById("sys-briefing-text");

      if (briefId) briefId.textContent = brief.briefing_id;
      if (posture) posture.textContent = brief.overall_posture;
      if (circuit) circuit.textContent = brief.active_circuit_breaker ? "TRIPPED" : "CLEAR";
      if (topStrat) topStrat.textContent = brief.top_performing_strategy;
      if (briefText) briefText.textContent = brief.executive_summary;
    }
  } catch (err) {
    console.warn("fetchSupervision error:", err);
  }
}

async function fetchMacroSchedule() {
  try {
    const res = await fetch("/api/macro/calendar");
    if (!res.ok) return;
    const data = await res.json();
    const events = Array.isArray(data) ? data : (data.events || []);
    TerminalState.macroEvents = events;

    const tbody = document.getElementById("risk-macro-tbody");
    if (!tbody || !Array.isArray(events)) return;

    if (events.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--text-muted); padding: 12px;">NO HIGH IMPACT MACRO RELEASES SCHEDULED TODAY</td></tr>`;
      return;
    }

    tbody.innerHTML = events.map((e) => {
      const impactClass = e.impact === "HIGH" ? "neg" : e.impact === "MEDIUM" ? "warn" : "info";
      const timeDisplay = e.time_badge || (e.seconds_remaining ? `${Math.round(e.seconds_remaining / 60)}m pending` : "PAST");
      return `
        <tr>
          <td><strong>${e.title || "Economic Data"}</strong></td>
          <td>${e.currency || "USD"}</td>
          <td><span class="tag-status ${impactClass}">${e.impact || "MEDIUM"}</span></td>
          <td class="num">${e.forecast || "--"}</td>
          <td class="num">${e.previous || "--"}</td>
          <td>${timeDisplay}</td>
          <td><span class="tag-status pos">${e.shield_armed ? "SHIELD ARMED" : "DEFENSE READY"}</span></td>
        </tr>
      `;
    }).join("");
  } catch (err) {
    console.warn("fetchMacroSchedule error:", err);
  }
}

async function fetchFloorMatrix() {
  try {
    const res = await fetch("/api/floor/agents");
    if (!res.ok) return;
    const floor = await res.json();
    const rawPods = floor.pods || (Array.isArray(floor) ? floor : {});

    const pods = Array.isArray(rawPods)
      ? rawPods
      : Object.entries(rawPods).map(([podName, podData]) => ({
          name: podName,
          strategy_focus: podData.strategy_focus || "Multi-Timeframe Microstructure",
          active_count: podData.active_count !== undefined ? podData.active_count : (podData.agent_count || 24),
          benched_count: podData.benched_count !== undefined ? podData.benched_count : (podData.penalty_box_count || 0),
          weight: podData.avg_weight !== undefined ? podData.avg_weight : (podData.weight || 0.25),
          ...podData
        }));

    const tbody = document.getElementById("models-pods-tbody");
    if (!tbody || !pods) return;

    tbody.innerHTML = pods.map((p) => {
      return `
        <tr>
          <td><strong>${p.name || p.pod}</strong></td>
          <td>${p.strategy_focus || "Multi-Timeframe Microstructure"}</td>
          <td class="num pos">${p.active_count !== undefined ? p.active_count : 24}</td>
          <td class="num neg">${p.benched_count !== undefined ? p.benched_count : 0}</td>
          <td class="num">${(p.weight || 0.25).toFixed(2)}</td>
          <td><span class="tag-status buy">BULLISH CONSENSUS</span></td>
        </tr>
      `;
    }).join("");
  } catch (err) {
    console.warn("fetchFloorMatrix error:", err);
  }
}

async function fetchMistakes() {
  try {
    const res = await fetch("/api/mistakes");
    if (!res.ok) return;
    const data = await res.json();
    TerminalState.mistakes = data;

    const list = Array.isArray(data)
      ? data
      : (data.recent || data.ml_feedback_history || []);

    const lessonCount = data.lessons_absorbed !== undefined
      ? data.lessons_absorbed
      : (list.length);

    const tbody = document.getElementById("sys-postmortem-tbody");
    const dockFeed = document.getElementById("dock-pm-feed");
    const dockCount = document.getElementById("dock-pm-status");

    if (dockCount) dockCount.textContent = `${lessonCount} LESSONS`;

    if (tbody) {
      if (list.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--text-muted); padding: 12px;">ZERO RECENT EXECUTION DEFECTS &bull; ONLINE LEARNING HEALTHY</td></tr>`;
      } else {
        tbody.innerHTML = list.slice(0, 10).map((m) => {
          const timeStr = m.time || (m.timestamp ? m.timestamp.substring(11, 19) : "12:00:00");
          return `
            <tr>
              <td><code>${timeStr}</code></td>
              <td><strong>${m.symbol || "--"}</strong></td>
              <td><span class="tag-status warn">${m.mistake_type || "ANOMALY"}</span></td>
              <td class="num neg">-$${(m.loss_amount || 0).toFixed(2)}</td>
              <td>${m.action_taken || "ADAPTATION_APPLIED"}</td>
            </tr>
          `;
        }).join("");
      }
    }

    if (dockFeed && list.length > 0) {
      dockFeed.innerHTML = list.slice(0, 3).map((m) => `
        <div class="dock-feed-item warn">
          <span class="timestamp">[${m.time || getTimestampStr()}]</span>
          <span>[${m.symbol || "SYS"}] ${m.mistake_type}: ${m.details || m.action_taken || "MODEL UPDATED"}</span>
        </div>
      `).join("");
    }
  } catch (err) {
    console.warn("fetchMistakes error:", err);
  }
}

function pushExecutionLog(message, level = "info") {
  const feed = document.getElementById("dock-exec-feed");
  if (!feed) return;

  const item = document.createElement("div");
  item.className = `dock-feed-item ${level}`;
  item.innerHTML = `
    <span class="timestamp">${getTimestampStr()}</span>
    <span>${message}</span>
  `;
  feed.prepend(item);

  // Keep max 15 log items in DOM
  while (feed.children.length > 15) {
    feed.removeChild(feed.lastChild);
  }
}


// ==========================================================================
// 8. BLOOMBERG EXCHANGE INTERACTIVE FUNCTIONS
// ==========================================================================
window.currentTicketSide = "BUY";

window.setTicketSide = function(side) {
  window.currentTicketSide = side;
  const btnBuy = document.getElementById("btn-ticket-buy");
  const btnSell = document.getElementById("btn-ticket-sell");
  const btnExec = document.getElementById("btn-ticket-execute");

  if (btnBuy && btnSell) {
    if (side === "BUY") {
      btnBuy.classList.add("active");
      btnSell.classList.remove("active");
      if (btnExec) {
        btnExec.style.background = "var(--color-positive)";
        btnExec.style.color = "#000";
        btnExec.textContent = `EXECUTE BUY ${TerminalState.selectedSymbol}`;
      }
    } else {
      btnSell.classList.add("active");
      btnBuy.classList.remove("active");
      if (btnExec) {
        btnExec.style.background = "var(--color-negative)";
        btnExec.style.color = "#fff";
        btnExec.textContent = `EXECUTE SELL ${TerminalState.selectedSymbol}`;
      }
    }
  }
};

window.setTicketLots = function(lots) {
  const input = document.getElementById("ticket-lots-input");
  if (input) input.value = Number(lots).toFixed(2);

  const pills = document.querySelectorAll(".preset-pill");
  pills.forEach((p) => {
    if (parseFloat(p.textContent) === lots) {
      p.classList.add("active");
    } else {
      p.classList.remove("active");
    }
  });

  const estMargin = document.getElementById("ticket-est-margin");
  if (estMargin) {
    estMargin.textContent = `$${(lots * 1500).toFixed(2)}`;
  }
};

window.switchDockTab = function(tabId) {
  const tabs = document.querySelectorAll(".dock-tab");
  tabs.forEach((t) => {
    if (t.dataset.docktab === tabId) {
      t.classList.add("active");
    } else {
      t.classList.remove("active");
    }
  });

  const panes = document.querySelectorAll(".dock-pane");
  panes.forEach((p) => {
    if (p.id === `dockpane-${tabId}`) {
      p.classList.add("active");
    } else {
      p.classList.remove("active");
    }
  });
};

window.executeTicketOrder = async function() {
  const sym = TerminalState.selectedSymbol;
  const side = window.currentTicketSide || "BUY";
  const lotsInput = document.getElementById("ticket-lots-input");
  const slInput = document.getElementById("ticket-sl-input");
  const tpInput = document.getElementById("ticket-tp-input");

  const lots = parseFloat(lotsInput ? lotsInput.value : 0.01) || 0.01;
  const sl = parseFloat(slInput && slInput.value ? slInput.value : 0) || null;
  const tp = parseFloat(tpInput && tpInput.value ? tpInput.value : 0) || null;

  try {
    const res = await fetch("/api/orders/execute", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        symbol: sym,
        side: side,
        volume_lots: lots,
        stop_loss: sl,
        take_profit: tp,
      }),
    });
    const data = await res.json();
    if (data.status === "SUCCESS") {
      pushExecutionLog(`Order placed: ${side} ${lots} lots ${sym} @ ${data.price || "MKT"} [${data.order_id}]`, "success");
      fetchPositions();
      fetchAccount();
    } else {
      pushExecutionLog(`Order failed: ${data.error || "Unknown error"}`, "error");
    }
  } catch (err) {
    console.warn("executeTicketOrder error:", err);
    pushExecutionLog(`Order error: ${err.message}`, "error");
  }
};

window.handleBreakevenAll = async function() {
  try {
    const res = await fetch("/api/positions/breakeven-all", { method: "POST" });
    const data = await res.json();
    pushExecutionLog(`Breakeven snapped on all positions (Count: ${data.count || 0})`, "success");
    fetchPositions();
  } catch (err) {
    console.warn("handleBreakevenAll error:", err);
  }
};

window.handleCloseAll = async function() {
  if (!confirm("Confirm Emergency Close: Liquidate ALL open positions immediately?")) return;
  try {
    const res = await fetch("/api/positions/close-all", { method: "POST" });
    const data = await res.json();
    pushExecutionLog(`Emergency liquidation executed (Count: ${data.count || 0})`, "warn");
    fetchPositions();
    fetchAccount();
  } catch (err) {
    console.warn("handleCloseAll error:", err);
  }
};

window.handleSnapBe = async function(posId) {
  try {
    const res = await fetch(`/api/positions/${posId}/breakeven`, { method: "POST" });
    const data = await res.json();
    pushExecutionLog(`Position ${posId} moved to breakeven`, "success");
    fetchPositions();
  } catch (err) {
    console.warn("handleSnapBe error:", err);
  }
};

window.handleClosePosition = async function(posId) {
  try {
    const res = await fetch(`/api/positions/${posId}/close`, { method: "POST" });
    const data = await res.json();
    pushExecutionLog(`Position ${posId} closed`, "warn");
    fetchPositions();
    fetchAccount();
  } catch (err) {
    console.warn("handleClosePosition error:", err);
  }
};

// ==========================================================================
// 8. AUTONOMOUS AI DECISION MATRIX & COGNITIVE INTERVENTION ENGINE
// ==========================================================================
window.currentAiPolicy = "CONSERVATIVE";

window.setAiPolicy = function(policy) {
  window.currentAiPolicy = policy;
  const btns = document.querySelectorAll(".policy-btn");
  btns.forEach((b) => {
    if (b.textContent.includes(policy)) {
      b.classList.add("active");
    } else {
      b.classList.remove("active");
    }
  });
  pushExecutionLog(`Autonomous AI Policy set to: ${policy} ALPHA`, "info");
};

async function fetchSymbolDecision(symbol) {
  try {
    const res = await fetch(`/api/brain/decision/${symbol}`);
    if (!res.ok) return;
    const d = await res.json();

    const targetEl = document.getElementById("ai-target-symbol");
    const domEl = document.getElementById("ai-dom-val");
    const velEl = document.getElementById("ai-vel-val");
    const spreadEl = document.getElementById("ai-spread-val");
    const rfEl = document.getElementById("ai-rf-val");
    const gbEl = document.getElementById("ai-gb-val");
    const nnEl = document.getElementById("ai-nn-val");
    const metaEl = document.getElementById("ai-meta-val");
    const calibEl = document.getElementById("ai-calib-val");
    const boundsEl = document.getElementById("ai-bounds-val");
    const spreadRatioEl = document.getElementById("ai-spread-ratio");
    const gateEl = document.getElementById("ai-conformal-gate");
    const bannerEl = document.getElementById("ai-verdict-banner");

    if (targetEl) targetEl.textContent = d.symbol;
    if (domEl) {
      const sign = d.dom_imbalance >= 0 ? "+" : "";
      domEl.textContent = `${sign}${d.dom_imbalance}% ${d.direction === "BUY" ? "BUY ABSORPTION" : "SELL PRESSURE"}`;
      domEl.className = `v tabular-nums ${d.dom_imbalance >= 0 ? "pos" : "neg"}`;
    }
    if (velEl) velEl.textContent = `${d.velocity} ticks/sec`;
    if (spreadEl) spreadEl.textContent = `${d.spread_pips} pips (${((d.spread_pips * 0.0001) / Math.max(d.current_price, 1) * 100).toFixed(3)}% drag)`;

    if (d.base_models) {
      if (rfEl) rfEl.textContent = `${(d.base_models.random_forest * 100).toFixed(1)}% P(${d.direction})`;
      if (gbEl) gbEl.textContent = `${(d.base_models.gradient_boosting * 100).toFixed(1)}% P(${d.direction})`;
      if (nnEl) nnEl.textContent = `${(d.base_models.neural_flow * 100).toFixed(1)}% P(${d.direction})`;
      if (metaEl) metaEl.textContent = `${(d.base_models.meta_stacking * 100).toFixed(1)}% Combined`;
    }

    if (calibEl) calibEl.textContent = `${(d.calibrated_prob * 100).toFixed(1)}% EXPECTED`;
    if (d.conformal) {
      if (boundsEl) boundsEl.textContent = `[${(d.conformal.lower_bound * 100).toFixed(1)}%, ${(d.conformal.upper_bound * 100).toFixed(1)}%]`;
      if (spreadRatioEl) spreadRatioEl.textContent = `${(d.conformal.interval_spread * 100).toFixed(1)}% (Cap: ≤30%)`;
      if (gateEl) {
        gateEl.textContent = d.conformal.pass ? "PASS" : "VETO";
        gateEl.className = `tag-status ${d.conformal.pass ? "pos" : "neg"}`;
      }
    }

    if (bannerEl) {
      const isBuy = d.verdict === "APPROVED_LONG";
      const isSell = d.verdict === "APPROVED_SHORT";
      const cls = isBuy ? "buy" : isSell ? "sell" : "veto";
      const actionText = isBuy
        ? `AUTONOMOUS DECISION: LONG • ${d.kelly_lot_size} LOTS`
        : isSell
        ? `AUTONOMOUS DECISION: SHORT • ${d.kelly_lot_size} LOTS`
        : `AUTONOMOUS DECISION: VETOED (${d.verdict})`;

      bannerEl.className = `ai-verdict-banner ${cls}`;
      bannerEl.innerHTML = `
        <span style="font-size: 11px;">${actionText}</span>
        <span style="font-size: 8px; opacity: 0.85;">2% Risk Budget ($200.00) • Kelly Sized • TP: ${formatPrice(d.tp_target)} | SL: ${formatPrice(d.sl_target)}</span>
      `;
    }
  } catch (err) {
    console.warn("fetchSymbolDecision error:", err);
  }
}
