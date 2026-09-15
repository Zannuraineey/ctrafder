def main():
    with open("app/dashboard/web/app.js", "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Update handleSelectSymbol to call fetchSymbolDecision
    old_handle_select = """window.handleSelectSymbol = function(sym) {
  TerminalState.selectedSymbol = sym;
  const navSym = document.getElementById("nav-active-sym");
  const ovTitle = document.getElementById("ov-chart-title");
  const fullTitle = document.getElementById("chart-full-sym-title");
  const ctxSym = document.getElementById("ctx-sym-tag");
  const ticketPill = document.getElementById("ticket-sym-pill");
  const btnExec = document.getElementById("btn-ticket-execute");

  if (navSym) navSym.textContent = sym;
  if (ovTitle) ovTitle.textContent = sym;
  if (fullTitle) fullTitle.textContent = sym;
  if (ctxSym) ctxSym.textContent = sym;
  if (ticketPill) ticketPill.textContent = sym;
  if (btnExec) btnExec.textContent = `EXECUTE ${window.currentTicketSide || "BUY"} ${sym}`;

  fetchChart(sym);
  renderMarketsTable();
  renderOverviewFocusMarkets(TerminalState.prices);
};"""

    new_handle_select = """window.handleSelectSymbol = function(sym) {
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
};"""

    if old_handle_select in content:
        content = content.replace(old_handle_select, new_handle_select)
        print("Updated handleSelectSymbol for Autonomous AI Decision Matrix")

    # 2. Add fetchSymbolDecision and setAiPolicy
    ai_decision_code = """
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
"""

    if "function fetchSymbolDecision" not in content:
        content += ai_decision_code
        print("Added fetchSymbolDecision to app.js")

    # 3. Add fetchSymbolDecision call to fast polling loop and initial sync
    if "fetchSymbolDecision(TerminalState.selectedSymbol);" not in content:
        content = content.replace("fetchChart(TerminalState.selectedSymbol);", "fetchChart(TerminalState.selectedSymbol);\n      fetchSymbolDecision(TerminalState.selectedSymbol);")
        print("Wired fetchSymbolDecision into fast polling loop")

    with open("app/dashboard/web/app.js", "w", encoding="utf-8") as f:
        f.write(content)

    print(f"app.js updated successfully! Length: {len(content)}")

if __name__ == "__main__":
    main()
