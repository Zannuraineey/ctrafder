Good. I’ve now gone one step further and checked the actual project structure and the key files, rather than treating it as a generic cTrader bot.

The next version should be an **upgrade of your existing system**, not a complete rewrite.

### The V2 direction

I would make these the core additions:

1. **Volume Pressure Engine**

   * Relative volume
   * Volume acceleration
   * Volume Z-score
   * Price/volume confirmation
   * Volume exhaustion/divergence

2. **Advanced Momentum Engine**

   * Momentum strength
   * Momentum acceleration/deceleration
   * ADX/DI expansion
   * ATR expansion
   * Candle expansion
   * Multi-timeframe momentum

3. **Continuation Engine**

   * Answers: *“Does this move still have fuel to continue?”*
   * Produces a continuation score/probability.

4. **Trade Lifecycle Manager**

   * `ENTER`
   * `HOLD`
   * `PROTECT`
   * `EXIT`
   * No more blindly closing a strong trade simply because it reached a fixed number of seconds.

5. **Exhaustion Detector**

   * Detects when volume and momentum are dying.
   * Helps lock profit before a reversal.

6. **AI upgrade**

   * Separate **entry prediction** from **continuation prediction**.
   * Fix the model-validation problem so training accuracy isn't mistaken for live performance.

7. **Better volume profile**

   * Your current `vp_poc` is effectively a rolling midpoint approximation, so we'll make this more meaningful.

8. **Strategy consensus**

   * Strategies generate candidates.
   * The confirmation engines decide whether the candidate has enough market force.
   * AI makes the final probability/risk assessment.

### The new decision should look like this

```text
MARKET
   ↓
REGIME
   ↓
STRATEGY SETUP
   ↓
STRUCTURE
   ↓
MOMENTUM ─────┐
VOLUME ───────┤
VOLATILITY ───┤
HTF ALIGNMENT ┤
               ↓
        CONTINUATION ENGINE
               ↓
          AI CONFIRMATION
               ↓
       ┌───────┴────────┐
       ↓                ↓
    NO TRADE          ENTER
                         ↓
                   LIVE MONITOR
                         ↓
          ┌──────────────┼──────────────┐
          ↓              ↓              ↓
        HOLD          PROTECT          EXIT
```

And importantly, **HOLD** becomes an intelligent decision rather than a timer.

For example:

```text
Trade +$3.20
Momentum       91/100
Volume         88/100
Continuation   86/100
Structure      VALID
Exhaustion     LOW

→ HOLD
```

But:

```text
Trade +$4.10
Momentum       43/100 ↓
Volume         31/100 ↓
Continuation   27/100
Structure      WEAKENING
Exhaustion     HIGH

→ PROTECT / EXIT
```

That is the type of system I think you are actually trying to build.

