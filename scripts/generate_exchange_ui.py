import os

INDEX_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>ANTIGRAVITY QUANT // Autonomous Quantitative Trading Workstation</title>
  <style>
/**
 * ANTIGRAVITY QUANT // Institutional Autonomous Trading Terminal
 * Bloomberg / TradingView / Deep Quantitative AI Decision Engine
 * Dark Graphite Foundation, Tabular Typography, Strict Spacing, Zero Emojis.
 */

:root {
  --bg-root: #090a0c;
  --bg-surface: #101216;
  --bg-surface-subtle: #14171e;
  --bg-surface-raised: #1c2029;
  --bg-hover: #222733;
  --bg-active: #282f3d;

  --border-subtle: #1c2027;
  --border-default: #252b36;
  --border-focused: #3b4455;
  --border-highlight: #4f5b72;

  --text-bright: #f0f3f6;
  --text-primary: #d1d7e0;
  --text-secondary: #8b949e;
  --text-muted: #57606a;

  --color-positive: #10b981;
  --color-positive-bg: rgba(16, 185, 129, 0.12);
  --color-negative: #f43f5e;
  --color-negative-bg: rgba(244, 63, 94, 0.12);
  --color-warning: #f59e0b;
  --color-warning-bg: rgba(245, 158, 11, 0.12);
  --color-info: #38bdf8;
  --color-info-bg: rgba(56, 189, 248, 0.12);

  --font-mono: "JetBrains Mono", "SF Mono", "Roboto Mono", "Consolas", monospace;
  --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;

  --header-height: 42px;
  --dock-height: 190px;
  --radius-sharp: 2px;
}

*, *::before, *::after {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

html, body {
  width: 100%;
  height: 100%;
  overflow: hidden;
  background-color: var(--bg-root);
  color: var(--text-primary);
  font-family: var(--font-sans);
  font-size: 11px;
  line-height: 1.4;
  -webkit-font-smoothing: antialiased;
}

.tabular-nums, code, pre, table, .metric-val, .badge-val {
  font-family: var(--font-mono);
  font-feature-settings: "tnum" 1, "zero" 1;
}

#terminal-root {
  display: flex;
  flex-direction: column;
  width: 100vw;
  height: 100vh;
  overflow: hidden;
  background: var(--bg-root);
}

/* ==========================================================================
   1. TOPBAR: BLOOMBERG HEADER WITH INLINED BALANCES & NAV
   ========================================================================== */
.terminal-topbar {
  height: var(--header-height);
  min-height: var(--header-height);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 12px;
  background: var(--bg-surface);
  border-bottom: 1px solid var(--border-subtle);
  user-select: none;
  z-index: 100;
  gap: 12px;
}

.topbar-branding {
  display: flex;
  align-items: center;
  gap: 8px;
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.8px;
  color: var(--text-bright);
  white-space: nowrap;
}

.brand-dot {
  width: 6px;
  height: 6px;
  background-color: var(--color-positive);
  border-radius: 50%;
  animation: pulse-dot 2s infinite ease-in-out;
}

@keyframes pulse-dot {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

.broker-pill {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 6px;
  background: var(--bg-surface-raised);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sharp);
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--text-secondary);
}

.broker-pill.connected {
  color: var(--color-positive);
  border-color: rgba(16, 185, 129, 0.3);
}

/* Header Financial Telemetry */
.topbar-telemetry {
  display: flex;
  align-items: center;
  gap: 14px;
  font-family: var(--font-mono);
  font-size: 11px;
  flex: 1;
  justify-content: center;
  white-space: nowrap;
}

.telemetry-item {
  display: flex;
  align-items: baseline;
  gap: 5px;
}

.telemetry-item .label {
  color: var(--text-muted);
  font-size: 9px;
  letter-spacing: 0.5px;
  font-weight: 600;
}

.telemetry-item .value {
  color: var(--text-bright);
  font-weight: 700;
}

.value.pos { color: var(--color-positive); }
.value.neg { color: var(--color-negative); }
.value.warn { color: var(--color-warning); }
.value.info { color: var(--color-info); }

/* Header Actions & Nav Switcher */
.topbar-right {
  display: flex;
  align-items: center;
  gap: 10px;
  white-space: nowrap;
}

.topbar-nav {
  display: flex;
  align-items: center;
  gap: 2px;
  background: var(--bg-surface-subtle);
  padding: 2px;
  border-radius: var(--radius-sharp);
  border: 1px solid var(--border-subtle);
}

.nav-item {
  background: transparent;
  border: none;
  color: var(--text-secondary);
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 600;
  padding: 3px 8px;
  border-radius: var(--radius-sharp);
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 4px;
  transition: all 0.12s ease;
}

.nav-item:hover {
  background: var(--bg-hover);
  color: var(--text-bright);
}

.nav-item.active {
  background: var(--bg-surface-raised);
  color: var(--text-bright);
  box-shadow: inset 0 0 0 1px var(--border-default);
}

.nav-badge {
  font-size: 8px;
  padding: 1px 4px;
  background: var(--bg-surface);
  border-radius: var(--radius-sharp);
  color: var(--text-muted);
}

.nav-item.active .nav-badge {
  background: var(--color-info-bg);
  color: var(--color-info);
}

.btn-terminal-sm {
  background: var(--bg-surface-raised);
  border: 1px solid var(--border-default);
  color: var(--text-primary);
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 600;
  padding: 3px 8px;
  border-radius: var(--radius-sharp);
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-terminal-sm:hover {
  background: var(--bg-hover);
  border-color: var(--border-focused);
  color: var(--text-bright);
}

.btn-terminal-sm.engine-running {
  background: var(--color-positive-bg);
  border-color: rgba(16, 185, 129, 0.4);
  color: var(--color-positive);
}

.btn-terminal-sm.engine-halted {
  background: var(--color-warning-bg);
  border-color: rgba(245, 158, 11, 0.4);
  color: var(--color-warning);
}

.btn-kill-switch {
  background: var(--color-negative-bg);
  border: 1px solid rgba(244, 63, 94, 0.5);
  color: var(--color-negative);
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.5px;
  padding: 3px 8px;
  border-radius: var(--radius-sharp);
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-kill-switch:hover {
  background: var(--color-negative);
  color: #000;
}

.clock-item {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--text-muted);
}

/* ==========================================================================
   2. MAIN WORKSPACE CONTAINER
   ========================================================================== */
.terminal-workspace {
  flex: 1;
  min-height: 0;
  position: relative;
  overflow: hidden;
}

.workspace-pane {
  display: none;
  height: 100%;
  width: 100%;
  overflow: hidden;
}

.workspace-pane.active {
  display: flex;
  flex-direction: column;
}

/* ==========================================================================
   3. BLOOMBERG / TRADINGVIEW 4-PANE WORKSTATION
   ========================================================================== */
.exchange-grid {
  display: grid;
  grid-template-rows: 1fr var(--dock-height);
  grid-template-columns: 270px 1fr 340px;
  grid-template-areas:
    "mkt  chart ai"
    "dock dock  dock";
  height: 100%;
  width: 100%;
  overflow: hidden;
  background: var(--bg-root);
}

/* --- Left: Market Watch / Universe Scanner --- */
.exchange-mkt {
  grid-area: mkt;
  border-right: 1px solid var(--border-subtle);
  background: var(--bg-surface);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.mkt-header {
  padding: 8px 10px;
  border-bottom: 1px solid var(--border-subtle);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.mkt-header h3 {
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 700;
  color: var(--text-bright);
  letter-spacing: 0.5px;
  text-transform: uppercase;
}

.mkt-filter-bar {
  display: flex;
  gap: 2px;
  padding: 4px 8px;
  background: var(--bg-surface-subtle);
  border-bottom: 1px solid var(--border-subtle);
}

.mkt-filter-btn {
  background: transparent;
  border: none;
  font-family: var(--font-mono);
  font-size: 9px;
  font-weight: 600;
  color: var(--text-muted);
  padding: 2px 5px;
  border-radius: var(--radius-sharp);
  cursor: pointer;
}

.mkt-filter-btn.active {
  background: var(--bg-surface-raised);
  color: var(--text-bright);
}

.mkt-search-bar {
  padding: 4px 8px;
  border-bottom: 1px solid var(--border-subtle);
  background: var(--bg-surface);
}

.mkt-search-input {
  width: 100%;
  background: var(--bg-root);
  border: 1px solid var(--border-subtle);
  color: var(--text-bright);
  font-family: var(--font-mono);
  font-size: 10px;
  padding: 3px 6px;
  border-radius: var(--radius-sharp);
  outline: none;
}

.mkt-search-input:focus {
  border-color: var(--border-focused);
}

.mkt-table-wrap {
  flex: 1;
  overflow-y: auto;
}

.table-terminal {
  width: 100%;
  border-collapse: collapse;
  font-family: var(--font-mono);
  font-size: 10px;
  line-height: 1.2;
}

.table-terminal th {
  background: var(--bg-surface-subtle);
  color: var(--text-muted);
  font-weight: 600;
  font-size: 9px;
  text-transform: uppercase;
  padding: 4px 6px;
  text-align: left;
  border-bottom: 1px solid var(--border-subtle);
  position: sticky;
  top: 0;
  z-index: 2;
  letter-spacing: 0.3px;
}

.table-terminal th.num, .table-terminal td.num {
  text-align: right;
  font-variant-numeric: tabular-nums;
}

.table-terminal td {
  padding: 4px 6px;
  border-bottom: 1px solid #14171d;
  color: var(--text-primary);
  white-space: nowrap;
}

.table-terminal tbody tr {
  cursor: pointer;
  transition: background 0.08s ease;
}

.table-terminal tbody tr:hover {
  background: var(--bg-hover);
}

.table-terminal tbody tr.selected {
  background: var(--bg-active);
}

/* --- Center: TradingView Chart Centerpiece --- */
.exchange-chart {
  grid-area: chart;
  background: #0d0f13;
  display: flex;
  flex-direction: column;
  position: relative;
  overflow: hidden;
}

.chart-topbar {
  height: 36px;
  min-height: 36px;
  background: var(--bg-surface);
  border-bottom: 1px solid var(--border-subtle);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 12px;
  user-select: none;
}

.chart-symbol-info {
  display: flex;
  align-items: baseline;
  gap: 10px;
  font-family: var(--font-mono);
}

.chart-symbol-name {
  font-size: 13px;
  font-weight: 700;
  color: var(--text-bright);
  letter-spacing: 0.5px;
}

.chart-symbol-price {
  font-size: 13px;
  font-weight: 700;
  color: var(--color-positive);
}

.chart-stat-chip {
  display: flex;
  align-items: baseline;
  gap: 4px;
  font-size: 10px;
  color: var(--text-muted);
}

.chart-stat-chip strong {
  color: var(--text-secondary);
}

.chart-tools-right {
  display: flex;
  align-items: center;
  gap: 6px;
}

.timeframe-group {
  display: flex;
  gap: 1px;
  background: var(--bg-surface-subtle);
  padding: 1px;
  border-radius: var(--radius-sharp);
  border: 1px solid var(--border-subtle);
}

.timeframe-btn {
  background: transparent;
  border: none;
  font-family: var(--font-mono);
  font-size: 9px;
  font-weight: 600;
  color: var(--text-muted);
  padding: 2px 6px;
  border-radius: var(--radius-sharp);
  cursor: pointer;
}

.timeframe-btn.active {
  background: var(--bg-surface-raised);
  color: var(--text-bright);
}

.chart-tag {
  font-family: var(--font-mono);
  font-size: 9px;
  padding: 2px 5px;
  border-radius: var(--radius-sharp);
  background: var(--bg-surface-raised);
  border: 1px solid var(--border-default);
  color: var(--color-warning);
}

.chart-canvas-wrap {
  flex: 1;
  position: relative;
  overflow: hidden;
  width: 100%;
  height: 100%;
}

.chart-canvas-wrap canvas {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  display: block;
}

/* --- Right: AUTONOMOUS AI DECISION MATRIX & COGNITIVE INTERVENTION ENGINE --- */
.exchange-ai-cockpit {
  grid-area: ai;
  border-left: 1px solid var(--border-subtle);
  background: var(--bg-surface);
  display: flex;
  flex-direction: column;
  overflow-y: auto;
}

.ai-cockpit-header {
  padding: 8px 10px;
  border-bottom: 1px solid var(--border-subtle);
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 700;
  color: var(--text-bright);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.ai-cockpit-body {
  padding: 10px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.ai-pipeline-section {
  background: var(--bg-surface-subtle);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sharp);
  padding: 8px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.ai-section-title {
  font-family: var(--font-mono);
  font-size: 9px;
  font-weight: 700;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid #1a1e27;
  padding-bottom: 3px;
  margin-bottom: 2px;
}

.ai-metric-row {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  font-family: var(--font-mono);
  font-size: 10px;
}

.ai-metric-row .k {
  color: var(--text-secondary);
  font-size: 9px;
}

.ai-metric-row .v {
  color: var(--text-bright);
  font-weight: 600;
}

.ai-verdict-banner {
  padding: 8px 10px;
  border-radius: var(--radius-sharp);
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.5px;
  text-align: center;
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.ai-verdict-banner.buy {
  background: var(--color-positive-bg);
  border: 1px solid rgba(16, 185, 129, 0.4);
  color: var(--color-positive);
}

.ai-verdict-banner.sell {
  background: var(--color-negative-bg);
  border: 1px solid rgba(244, 63, 94, 0.4);
  color: var(--color-negative);
}

.ai-verdict-banner.veto {
  background: var(--color-warning-bg);
  border: 1px solid rgba(245, 158, 11, 0.4);
  color: var(--color-warning);
}

.ai-policy-selector {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 3px;
  margin-top: 4px;
}

.policy-btn {
  background: var(--bg-root);
  border: 1px solid var(--border-subtle);
  color: var(--text-muted);
  font-family: var(--font-mono);
  font-size: 8px;
  font-weight: 600;
  padding: 3px 0;
  text-align: center;
  border-radius: var(--radius-sharp);
  cursor: pointer;
}

.policy-btn.active {
  background: var(--bg-surface-raised);
  color: var(--color-info);
  border-color: var(--border-focused);
}

.ai-intervention-feed {
  display: flex;
  flex-direction: column;
  gap: 3px;
  font-family: var(--font-mono);
  font-size: 9px;
  max-height: 70px;
  overflow-y: auto;
  border-top: 1px solid var(--border-subtle);
  padding-top: 4px;
}

.intervention-item {
  color: var(--text-secondary);
  line-height: 1.3;
}

.quick-action-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
  margin-top: 4px;
}

/* --- Bottom: Positions, Orders & Telemetry Dock --- */
.exchange-dock {
  grid-area: dock;
  border-top: 1px solid var(--border-subtle);
  background: var(--bg-surface);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.dock-tab-bar {
  height: 28px;
  min-height: 28px;
  background: var(--bg-surface-subtle);
  border-bottom: 1px solid var(--border-subtle);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 8px;
  user-select: none;
}

.dock-tabs {
  display: flex;
  gap: 2px;
}

.dock-tab {
  background: transparent;
  border: none;
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 600;
  color: var(--text-secondary);
  padding: 4px 8px;
  border-radius: var(--radius-sharp);
  cursor: pointer;
}

.dock-tab.active {
  background: var(--bg-surface);
  color: var(--text-bright);
}

.dock-actions {
  display: flex;
  gap: 4px;
}

.dock-content-area {
  flex: 1;
  overflow-y: auto;
  position: relative;
}

.dock-pane {
  display: none;
  height: 100%;
  width: 100%;
}

.dock-pane.active {
  display: block;
}

/* Generic Utilities */
.btn-action-sm {
  background: transparent;
  border: 1px solid var(--border-default);
  color: var(--text-secondary);
  font-family: var(--font-mono);
  font-size: 9px;
  font-weight: 600;
  padding: 1px 6px;
  border-radius: var(--radius-sharp);
  cursor: pointer;
  transition: all 0.12s ease;
}

.btn-action-sm:hover {
  background: var(--bg-hover);
  color: var(--text-bright);
  border-color: var(--border-focused);
}

.btn-action-sm.danger {
  color: var(--color-negative);
  border-color: rgba(244, 63, 94, 0.4);
}

.btn-action-sm.danger:hover {
  background: var(--color-negative);
  color: #000;
}

.tag-status {
  display: inline-block;
  font-family: var(--font-mono);
  font-size: 9px;
  font-weight: 600;
  padding: 1px 5px;
  border-radius: var(--radius-sharp);
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

.tag-status.buy, .tag-status.win, .tag-status.pos {
  background: var(--color-positive-bg);
  color: var(--color-positive);
  border: 1px solid rgba(16, 185, 129, 0.3);
}

.tag-status.sell, .tag-status.loss, .tag-status.neg {
  background: var(--color-negative-bg);
  color: var(--color-negative);
  border: 1px solid rgba(244, 63, 94, 0.3);
}

.tag-status.warn, .tag-status.hold {
  background: var(--color-warning-bg);
  color: var(--color-warning);
  border: 1px solid rgba(245, 158, 11, 0.3);
}

.tag-status.neutral, .tag-status.info {
  background: var(--color-info-bg);
  color: var(--color-info);
  border: 1px solid rgba(56, 189, 248, 0.3);
}

.dock-feed {
  padding: 6px 10px;
  display: flex;
  flex-direction: column;
  gap: 3px;
  font-family: var(--font-mono);
  font-size: 10px;
}

.dock-feed-item {
  display: flex;
  align-items: baseline;
  gap: 6px;
  color: var(--text-secondary);
}

.dock-feed-item .timestamp {
  color: var(--text-muted);
  font-size: 9px;
}

.dock-feed-item.warn { color: var(--color-warning); }
.dock-feed-item.error { color: var(--color-negative); }
.dock-feed-item.success { color: var(--color-positive); }

/* Full workspace panels */
.full-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: var(--bg-surface);
  overflow: hidden;
  padding: 12px;
  gap: 12px;
}

.full-panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid var(--border-subtle);
  padding-bottom: 8px;
}

.full-panel-header h2 {
  font-family: var(--font-mono);
  font-size: 12px;
  font-weight: 700;
  color: var(--text-bright);
  letter-spacing: 0.5px;
}

::-webkit-scrollbar {
  width: 4px;
  height: 4px;
}

::-webkit-scrollbar-track {
  background: var(--bg-root);
}

::-webkit-scrollbar-thumb {
  background: var(--border-default);
}

::-webkit-scrollbar-thumb:hover {
  background: var(--border-focused);
}
</style>
</head>
<body>
  <div id="terminal-root">

    <!-- ====================================================================
         TOPBAR: BLOOMBERG HEADER WITH INLINED BALANCES & GLOBAL SWITCHERS
         ==================================================================== -->
    <header class="terminal-topbar">
      <div class="topbar-branding">
        <span class="brand-dot"></span>
        <span>ANTIGRAVITY QUANT</span>
        <span class="broker-pill connected" id="topbar-broker-status">DERIV cTrader [LIVE #2547594]</span>
      </div>

      <!-- Live Financial Telemetry in Header -->
      <div class="topbar-telemetry">
        <div class="telemetry-item">
          <span class="label">BALANCE</span>
          <span class="value tabular-nums" id="top-balance">$10,000.00</span>
        </div>
        <div class="telemetry-item">
          <span class="label">EQUITY</span>
          <span class="value tabular-nums" id="top-equity">$10,000.00</span>
        </div>
        <div class="telemetry-item">
          <span class="label">UNREAL P&amp;L</span>
          <span class="value tabular-nums" id="top-unreal-pnl">$0.00</span>
        </div>
        <div class="telemetry-item">
          <span class="label">DAY REALIZED</span>
          <span class="value tabular-nums pos" id="ov-daily-pnl">+$0.00</span>
        </div>
        <div class="telemetry-item">
          <span class="label">2% RISK CAP</span>
          <span class="value tabular-nums warn" id="top-risk-cap">$200.00</span>
        </div>
        <div class="telemetry-item">
          <span class="label">99% VaR</span>
          <span class="value tabular-nums neg" id="top-var">$0.90</span>
        </div>
        <div class="telemetry-item">
          <span class="label">SHIELD</span>
          <span class="value tabular-nums pos" id="top-shield">ARMED</span>
        </div>
      </div>

      <!-- Right: Workspace Switcher & Emergency Actions -->
      <div class="topbar-right">
        <nav class="topbar-nav">
          <button class="nav-item active" data-workspace="overview">
            <span>EXCHANGE</span>
          </button>
          <button class="nav-item" data-workspace="markets">
            <span>UNIVERSE</span>
            <span class="nav-badge" id="nav-badge-markets">57</span>
          </button>
          <button class="nav-item" data-workspace="brain">
            <span>AI BRAIN</span>
            <span class="nav-badge" id="nav-badge-brain">CALIB</span>
          </button>
          <button class="nav-item" data-workspace="strategy">
            <span>TOURNAMENT</span>
            <span class="nav-badge" id="nav-badge-strategy">DSR</span>
          </button>
          <button class="nav-item" data-workspace="models">
            <span>100-AGENTS</span>
            <span class="nav-badge" id="nav-badge-models">100</span>
          </button>
          <button class="nav-item" data-workspace="risk">
            <span>RISK DESK</span>
            <span class="nav-badge" id="nav-badge-risk">2%</span>
          </button>
          <button class="nav-item" data-workspace="system">
            <span>AUDIT</span>
            <span class="nav-badge" id="nav-badge-system">LOGS</span>
          </button>
        </nav>

        <button class="btn-terminal-sm engine-running" id="btn-engine-toggle">
          ENGINE: [RUNNING]
        </button>
        <button class="btn-kill-switch" id="btn-emergency-stop" title="Emergency liquidate & stop trading">
          KILL SWITCH
        </button>
        <div class="clock-item tabular-nums" id="topbar-clock">
          2026-09-15 00:00:00 UTC
        </div>
      </div>
    </header>

    <!-- ====================================================================
         PRIMARY WORKSPACE
         ==================================================================== -->
    <main class="terminal-workspace">

      <!-- [01] EXCHANGE WORKSPACE: 4-PANE BLOOMBERG / TRADINGVIEW LAYOUT -->
      <section class="workspace-pane active" id="pane-overview">
        <div class="exchange-grid">

          <!-- LEFT PANE: MARKET WATCH & INSTRUMENT SCANNER -->
          <aside class="exchange-mkt">
            <div class="mkt-header">
              <h3>MARKET WATCH</h3>
              <span class="badge-val" id="ov-market-count" style="color: var(--text-muted); font-size: 9px;">10 CORE</span>
            </div>
            <div class="mkt-filter-bar" id="market-filter-tabs">
              <button class="mkt-filter-btn active" data-cat="ALL">ALL (57)</button>
              <button class="mkt-filter-btn" data-cat="SYNTHETICS">SYNTH</button>
              <button class="mkt-filter-btn" data-cat="FOREX">FX</button>
              <button class="mkt-filter-btn" data-cat="METALS">METALS</button>
              <button class="mkt-filter-btn" data-cat="CRYPTO">CRYPTO</button>
            </div>
            <div class="mkt-search-bar">
              <input type="text" class="mkt-search-input" id="mkt-search-input" placeholder="Filter instrument...">
            </div>
            <div class="mkt-table-wrap">
              <table class="table-terminal" id="ov-market-table">
                <thead>
                  <tr>
                    <th>Symbol</th>
                    <th class="num">Bid</th>
                    <th class="num">Ask</th>
                    <th class="num">Spread</th>
                    <th>POC</th>
                    <th>Signal</th>
                  </tr>
                </thead>
                <tbody id="ov-market-tbody">
                  <!-- Populated via JS -->
                </tbody>
              </table>
            </div>
          </aside>

          <!-- CENTER PANE: TRADINGVIEW CANDLESTICK CHART CONTAINER -->
          <section class="exchange-chart">
            <div class="chart-topbar">
              <div class="chart-symbol-info">
                <span class="chart-symbol-name" id="ov-chart-title">Step_Index</span>
                <span class="chart-symbol-price tabular-nums" id="chart-full-price">8,421.50</span>
                <div class="chart-stat-chip">24h High: <strong class="tabular-nums" id="chart-high-val">8,450.00</strong></div>
                <div class="chart-stat-chip">24h Low: <strong class="tabular-nums" id="chart-low-val">8,390.00</strong></div>
                <div class="chart-stat-chip">Vol: <strong class="tabular-nums">142.5K</strong></div>
                <div class="chart-stat-chip">Spread: <strong class="tabular-nums" id="chart-spread-val">0.5</strong></div>
              </div>

              <div class="chart-tools-right">
                <div class="timeframe-group">
                  <button class="timeframe-btn">1s</button>
                  <button class="timeframe-btn active">1m</button>
                  <button class="timeframe-btn">5m</button>
                  <button class="timeframe-btn">15m</button>
                  <button class="timeframe-btn">1h</button>
                  <button class="timeframe-btn">4h</button>
                  <button class="timeframe-btn">1d</button>
                </div>
                <span class="chart-tag" id="chart-poc-tag">POC TARGET</span>
                <span class="chart-tag" style="color: var(--color-info);">VOLUME PROFILE</span>
              </div>
            </div>

            <!-- Candlestick Canvas -->
            <div class="chart-canvas-wrap">
              <canvas id="terminal-chart-canvas"></canvas>
            </div>
          </section>

          <!-- RIGHT PANE: AUTONOMOUS AI DECISION MATRIX & COGNITIVE INTERVENTION ENGINE -->
          <aside class="exchange-ai-cockpit">
            <div class="ai-cockpit-header">
              <span>AUTONOMOUS AI DECISION MATRIX</span>
              <span class="tag-status pos" id="ai-status-badge">AI ENGAGED</span>
            </div>

            <div class="ai-cockpit-body">
              <!-- Target Instrument Overview -->
              <div class="ai-pipeline-section">
                <div class="ai-section-title">
                  <span>COGNITIVE INFERENCE TARGET</span>
                  <span class="tag-status info" id="ai-target-symbol">Step_Index</span>
                </div>
                <div class="ai-metric-row">
                  <span class="k">Microstructure Timeframe:</span>
                  <span class="v">1M HIGH-RESOLUTION BARS</span>
                </div>
                <div class="ai-metric-row">
                  <span class="k">Order Book Delta Imbalance:</span>
                  <span class="v tabular-nums pos" id="ai-dom-val">+28.4% BUY ABSORPTION</span>
                </div>
                <div class="ai-metric-row">
                  <span class="k">Flow Velocity:</span>
                  <span class="v tabular-nums" id="ai-vel-val">1.25 ticks/sec</span>
                </div>
                <div class="ai-metric-row">
                  <span class="k">Spread Drag:</span>
                  <span class="v tabular-nums" id="ai-spread-val">0.5 pips (0.04% drag)</span>
                </div>
              </div>

              <!-- Stage 2: Stacking Multi-Model Activations -->
              <div class="ai-pipeline-section">
                <div class="ai-section-title">
                  <span>STAGE 2 &bull; ENSEMBLE BASE PREDICTORS</span>
                  <span style="font-size: 8px; color: var(--text-muted);">STACKING V4</span>
                </div>
                <div class="ai-metric-row">
                  <span class="k">Random Forest:</span>
                  <span class="v tabular-nums pos" id="ai-rf-val">79.9% P(Long)</span>
                </div>
                <div class="ai-metric-row">
                  <span class="k">Gradient Boosting:</span>
                  <span class="v tabular-nums pos" id="ai-gb-val">74.9% P(Long)</span>
                </div>
                <div class="ai-metric-row">
                  <span class="k">Deep Neural Flow:</span>
                  <span class="v tabular-nums pos" id="ai-nn-val">82.0% P(Long)</span>
                </div>
                <div class="ai-metric-row">
                  <span class="k">Meta-Stacking Classifier:</span>
                  <span class="v tabular-nums pos" id="ai-meta-val">77.9% Combined</span>
                </div>
              </div>

              <!-- Stage 3 & 4: Calibration & Conformal Uncertainty Filter -->
              <div class="ai-pipeline-section">
                <div class="ai-section-title">
                  <span>STAGE 3 &amp; 4 &bull; CALIBRATION &amp; CONFORMAL GATE</span>
                  <span class="tag-status pos" id="ai-conformal-gate">PASS</span>
                </div>
                <div class="ai-metric-row">
                  <span class="k">Isotonic Calibrated Win Prob:</span>
                  <span class="v tabular-nums pos" id="ai-calib-val" style="font-size: 12px; font-weight: 700;">74.1% EXPECTED</span>
                </div>
                <div class="ai-metric-row">
                  <span class="k">Conformal Bounds (90% Conf):</span>
                  <span class="v tabular-nums" id="ai-bounds-val">[66.1%, 82.1%]</span>
                </div>
                <div class="ai-metric-row">
                  <span class="k">Uncertainty Spread:</span>
                  <span class="v tabular-nums" id="ai-spread-ratio">16.0% (Cap: &le;30%)</span>
                </div>
                <div class="ai-metric-row">
                  <span class="k">Desk Regime Multiplier:</span>
                  <span class="v tabular-nums info" id="ctx-directive-risk-cap">1.15x MULTIPLIER</span>
                </div>
              </div>

              <!-- Autonomous Decision Verdict Banner -->
              <div class="ai-verdict-banner buy" id="ai-verdict-banner">
                <span style="font-size: 11px;">AUTONOMOUS DECISION: SHORT &bull; 0.04 LOTS</span>
                <span style="font-size: 8px; opacity: 0.85;">2% Risk Budget ($200.00) &bull; Kelly Position Sized &bull; R:R 1:1.80</span>
              </div>

              <!-- Stage 5: Autonomous In-Flight Intervention Telemetry -->
              <div class="ai-pipeline-section">
                <div class="ai-section-title">
                  <span>AUTONOMOUS INTERVENTION TELEMETRY</span>
                  <span class="tag-status info">LIVE WATCH</span>
                </div>
                <div class="ai-metric-row">
                  <span class="k">Auto-Breakeven Engine:</span>
                  <span class="v tag-status pos">ARMED (+2.50 R-MULT)</span>
                </div>
                <div class="ai-metric-row">
                  <span class="k">Dynamic Trailing Stop:</span>
                  <span class="v tag-status info">1.2x ATR VOLATILITY</span>
                </div>
                <div class="ai-metric-row">
                  <span class="k">Stagnation Exit Veto:</span>
                  <span class="v tag-status warn">ARMED (&gt;45s FLAT DELTA)</span>
                </div>
                <div class="ai-metric-row">
                  <span class="k">Post-Mortem Mistake Penalties:</span>
                  <span class="v tag-status pos" id="ai-mistake-penalties">0 ACTIVE COOLDOWNS</span>
                </div>

                <!-- Live Interventions Feed -->
                <div class="ai-intervention-feed" id="ai-intervention-feed">
                  <div class="intervention-item">&bull; [18:02:15] Step_Index: Calibrated edge 74.1% exceeds 60% threshold. Sized 0.04 lots.</div>
                  <div class="intervention-item">&bull; [18:01:40] Vol_25_1s: Trailing stop secured at BE+0.4 pips (+1.2 R-Multiple).</div>
                  <div class="intervention-item">&bull; [17:59:10] EURUSD: Vetoed trade. Spread friction drag exceeds expected edge.</div>
                </div>
              </div>

              <!-- Autonomous Policy & Supervisory Overrides -->
              <div class="ai-pipeline-section">
                <div class="ai-section-title">
                  <span>AUTONOMOUS POLICY CONTROL</span>
                  <span style="color: var(--text-muted); font-size: 8px;">GOVERNANCE</span>
                </div>
                <div class="ai-policy-selector">
                  <button class="policy-btn active" id="btn-policy-cons" onclick="setAiPolicy('CONSERVATIVE')">CONSERVATIVE</button>
                  <button class="policy-btn" id="btn-policy-bal" onclick="setAiPolicy('BALANCED')">BALANCED</button>
                  <button class="policy-btn" id="btn-policy-agg" onclick="setAiPolicy('AGGRESSIVE')">AGGRESSIVE</button>
                </div>

                <div class="quick-action-row">
                  <button class="btn-action-sm" id="btn-ov-snap-be" onclick="handleBreakevenAll()">SNAP ALL BREAKEVEN</button>
                  <button class="btn-action-sm danger" onclick="handleCloseAll()">EMERGENCY HALT</button>
                </div>
              </div>

            </div>
          </aside>

          <!-- BOTTOM PANE: POSITIONS, ORDERS & TELEMETRY DOCK -->
          <footer class="exchange-dock">
            <div class="dock-tab-bar">
              <div class="dock-tabs">
                <button class="dock-tab active" data-docktab="positions" onclick="switchDockTab('positions')">
                  OPEN POSITIONS (<span id="nav-badge-positions">0</span>)
                </button>
                <button class="dock-tab" data-docktab="postmortem" onclick="switchDockTab('postmortem')">
                  POST-MORTEM &amp; ADAPTIVE LEARNING (<span id="dock-pm-status">0 LESSONS</span>)
                </button>
                <button class="dock-tab" data-docktab="tournament" onclick="switchDockTab('tournament')">
                  STRATEGY TOURNAMENT (DSR)
                </button>
                <button class="dock-tab" data-docktab="logs" onclick="switchDockTab('logs')">
                  SYSTEM TELEMETRY &amp; HEALTH
                </button>
              </div>

              <div class="dock-actions">
                <button class="btn-action-sm" onclick="handleBreakevenAll()">BREAKEVEN ALL</button>
                <button class="btn-action-sm danger" onclick="handleCloseAll()">CLOSE ALL POSITIONS</button>
              </div>
            </div>

            <div class="dock-content-area">
              <!-- Dock Tab 1: Positions -->
              <div class="dock-pane active" id="dockpane-positions">
                <table class="table-terminal">
                  <thead>
                    <tr>
                      <th>ID</th>
                      <th>Symbol</th>
                      <th>Side</th>
                      <th class="num">Lots</th>
                      <th class="num">Entry</th>
                      <th class="num">Current</th>
                      <th class="num">SL</th>
                      <th class="num">TP</th>
                      <th class="num">Unrealized P&amp;L</th>
                      <th>Lifecycle</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody id="ov-positions-tbody">
                    <!-- Populated via JS -->
                  </tbody>
                </table>
              </div>

              <!-- Dock Tab 2: Post-Mortem -->
              <div class="dock-pane" id="dockpane-postmortem">
                <table class="table-terminal">
                  <thead>
                    <tr>
                      <th>Time</th>
                      <th>Symbol</th>
                      <th>Anomaly Type</th>
                      <th class="num">Loss Amount</th>
                      <th>Online ML Adaptation Applied</th>
                    </tr>
                  </thead>
                  <tbody id="sys-postmortem-tbody">
                    <!-- Populated via JS -->
                  </tbody>
                </table>
              </div>

              <!-- Dock Tab 3: Tournament -->
              <div class="dock-pane" id="dockpane-tournament">
                <table class="table-terminal">
                  <thead>
                    <tr>
                      <th>Rank</th>
                      <th>Strategy</th>
                      <th class="num">Trades</th>
                      <th class="num">Win Rate</th>
                      <th class="num">Net PnL</th>
                      <th class="num">Profit Factor</th>
                      <th class="num">Sharpe</th>
                      <th class="num">Deflated Sharpe</th>
                      <th class="num">Max DD</th>
                      <th class="num">Multiplier</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody id="tournament-full-tbody">
                    <!-- Populated via JS -->
                  </tbody>
                </table>
              </div>

              <!-- Dock Tab 4: System Logs -->
              <div class="dock-pane" id="dockpane-logs">
                <div class="dock-feed" id="dock-sys-feed">
                  <div class="dock-feed-item success">
                    <span class="timestamp">[18:00:00]</span>
                    <span>Institutional Execution Terminal connected to Deriv cTrader. Latency: 38ms</span>
                  </div>
                  <div class="dock-feed-item">
                    <span class="timestamp">[18:00:00]</span>
                    <span>Reconciliation worker active. Polling interval: 5s. Circuit breaker: ARMED</span>
                  </div>
                </div>
              </div>

            </div>
          </footer>

        </div>
      </section>

      <!-- [02] FULL UNIVERSE SCANNER (57 INSTRUMENTS) -->
      <section class="workspace-pane" id="pane-markets">
        <div class="full-panel">
          <div class="full-panel-header">
            <h2>QUANTITATIVE UNIVERSE SCANNER (57 INSTRUMENTS)</h2>
            <div style="display: flex; gap: 4px;">
              <button class="btn-terminal-sm" onclick="document.querySelector('[data-workspace=overview]').click();">RETURN TO EXCHANGE</button>
            </div>
          </div>
          <div style="flex: 1; overflow-y: auto;">
            <table class="table-terminal">
              <thead>
                <tr>
                  <th>Symbol</th>
                  <th>Class</th>
                  <th class="num">Bid</th>
                  <th class="num">Ask</th>
                  <th class="num">Spread (Pips)</th>
                  <th class="num">Volatility</th>
                  <th class="num">POC Target</th>
                  <th class="num">R:R Ratio</th>
                  <th>ML Signal</th>
                  <th>Feasibility</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody id="markets-full-tbody">
                <!-- Populated via JS -->
              </tbody>
            </table>
          </div>
        </div>
      </section>

      <!-- [03] AI BRAIN & CALIBRATION WORKSPACE -->
      <section class="workspace-pane" id="pane-brain">
        <div class="full-panel">
          <div class="full-panel-header">
            <h2>AI BRAIN &bull; PROBABILITY CALIBRATION &amp; UNCERTAINTY ESTIMATOR</h2>
            <button class="btn-terminal-sm" onclick="document.querySelector('[data-workspace=overview]').click();">RETURN TO EXCHANGE</button>
          </div>
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; flex: 1; overflow: hidden;">
            <div style="display: flex; flex-direction: column; gap: 8px;">
              <div class="ticket-preview-box" style="background: var(--bg-surface-subtle); padding: 8px; border: 1px solid var(--border-subtle);">
                <div class="ai-metric-row"><span>Model:</span><strong>STACKING ENSEMBLE CLASSIFIER</strong></div>
                <div class="ai-metric-row"><span>Calibrator:</span><strong id="brain-cal-method">ISOTONIC REGRESSION</strong></div>
                <div class="ai-metric-row"><span>Conformal Coverage:</span><strong id="brain-coverage">90.0% COVERAGE</strong></div>
                <div class="ai-metric-row"><span>Tolerance Interval:</span><strong id="brain-interval">[42.3%, 89.1%]</strong></div>
              </div>
            </div>
            <div style="flex: 1; overflow-y: auto;">
              <table class="table-terminal">
                <thead>
                  <tr>
                    <th>Feature</th>
                    <th class="num">Weight</th>
                    <th class="num">Importance</th>
                    <th>Role</th>
                  </tr>
                </thead>
                <tbody id="brain-weights-tbody">
                  <!-- Populated via JS -->
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </section>

      <!-- [04] STRATEGY LAB / TOURNAMENT WORKSPACE -->
      <section class="workspace-pane" id="pane-strategy">
        <div class="full-panel">
          <div class="full-panel-header">
            <h2>STRATEGY RESEARCH TOURNAMENT &bull; DEFLATED SHARPE (DSR) ALLOCATOR</h2>
            <button class="btn-terminal-sm" onclick="document.querySelector('[data-workspace=overview]').click();">RETURN TO EXCHANGE</button>
          </div>
          <div style="flex: 1; overflow-y: auto;">
            <table class="table-terminal">
              <thead>
                <tr>
                  <th>Rank</th>
                  <th>Strategy</th>
                  <th class="num">Trades</th>
                  <th class="num">Win Rate</th>
                  <th class="num">Net PnL</th>
                  <th class="num">Profit Factor</th>
                  <th class="num">Sharpe</th>
                  <th class="num">Deflated Sharpe</th>
                  <th class="num">Max DD</th>
                  <th class="num">Multiplier</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody id="tournament-full-tbody-alt">
                <!-- Reuses tournament data -->
              </tbody>
            </table>
          </div>
        </div>
      </section>

      <!-- [05] 100-AGENT TRADING FLOOR WORKSPACE -->
      <section class="workspace-pane" id="pane-models">
        <div class="full-panel">
          <div class="full-panel-header">
            <h2>100-AGENT INSTITUTIONAL TRADING FLOOR MATRIX</h2>
            <button class="btn-terminal-sm" onclick="document.querySelector('[data-workspace=overview]').click();">RETURN TO EXCHANGE</button>
          </div>
          <div style="flex: 1; overflow-y: auto;">
            <table class="table-terminal">
              <thead>
                <tr>
                  <th>Pod Name</th>
                  <th>Strategy Focus</th>
                  <th class="num">Active Agents</th>
                  <th class="num">Benched (Penalty Box)</th>
                  <th class="num">Capital Weight</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody id="models-pods-tbody">
                <!-- Populated via JS -->
              </tbody>
            </table>
          </div>
        </div>
      </section>

      <!-- [06] RISK DESK WORKSPACE -->
      <section class="workspace-pane" id="pane-risk">
        <div class="full-panel">
          <div class="full-panel-header">
            <h2>INSTITUTIONAL RISK GOVERNANCE &amp; MACRO SPREAD SHIELD</h2>
            <button class="btn-terminal-sm" onclick="document.querySelector('[data-workspace=overview]').click();">RETURN TO EXCHANGE</button>
          </div>
          <div style="flex: 1; overflow-y: auto;">
            <table class="table-terminal">
              <thead>
                <tr>
                  <th>Event</th>
                  <th>Currency</th>
                  <th>Impact</th>
                  <th class="num">Forecast</th>
                  <th class="num">Previous</th>
                  <th>Schedule</th>
                  <th>Spread Shield State</th>
                </tr>
              </thead>
              <tbody id="risk-macro-tbody">
                <!-- Populated via JS -->
              </tbody>
            </table>
          </div>
        </div>
      </section>

      <!-- [07] SYSTEM AUDIT & POST-MORTEM WORKSPACE -->
      <section class="workspace-pane" id="pane-system">
        <div class="full-panel">
          <div class="full-panel-header">
            <h2>SUPERVISORY AUDIT &amp; CONTINUOUS POST-MORTEM LEARNING</h2>
            <button class="btn-terminal-sm" onclick="document.querySelector('[data-workspace=overview]').click();">RETURN TO EXCHANGE</button>
          </div>
          <div style="flex: 1; overflow-y: auto;">
            <div class="dock-feed" id="dock-exec-feed">
              <!-- Populated via JS -->
            </div>
          </div>
        </div>
      </section>

    </main>
  </div>

  <script src="/static/app.js?v=20260915_v108"></script>
</body>
</html>
"""

def main():
    target_path = os.path.join("app", "dashboard", "web", "index.html")
    with open(target_path, "w", encoding="utf-8") as f:
        f.write(INDEX_HTML)
    print(f"Written {len(INDEX_HTML)} bytes to {target_path}")

    # Synchronize style.css
    start = INDEX_HTML.find("<style>") + len("<style>")
    end = INDEX_HTML.find("</style>")
    css = INDEX_HTML[start:end].strip()
    css_path = os.path.join("app", "dashboard", "web", "style.css")
    with open(css_path, "w", encoding="utf-8") as f:
        f.write(css)
    print(f"Written {len(css)} bytes to {css_path}")

if __name__ == "__main__":
    main()
