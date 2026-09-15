import urllib.request
import json

def get(url):
    return json.loads(urllib.request.urlopen(url).read().decode())

macro = get('http://127.0.0.1:8000/api/macro')
print('=== MACROECONOMIC INTELLIGENCE & SPREAD SHIELD ===')
print('Shield active:', macro['shield_active'])
for e in macro['events'][:4]:
    d = e.get('dossier') or {}
    aff_c = [c['symbol'] for c in d.get('affected_commodities', [])]
    aff_f = [f['symbol'] for f in d.get('affected_forex', [])]
    print(f"* [{e['currency']}] {e['title']} | Countdown: {e.get('time_badge')} | Forecast: {e.get('forecast')}")
    print(f"  - Affected Commodities: {aff_c}")
    print(f"  - Affected Forex: {aff_f}")
    print(f"  - Safe Synthetics: {d.get('exempt_synthetics', [])[:4]}")
    print(f"  - Actionable Plan: {d.get('actionable_user_guidance', {}).get('immediate_action')}")

mistakes = get('http://127.0.0.1:8000/api/mistakes')
print('\n=== POST-MORTEM ANTI-GREED LOG ===')
print('Total Saved ($):', mistakes.get('summary', {}).get('total_loss_amount'))
print('Interceptions count:', len(mistakes.get('recent', [])))
for m in mistakes.get('recent', [])[:3]:
    print(f"* [{m['time']}] {m['symbol']} - {m['mistake_type']} | Saved: ${m['loss_amount']:.2f} | Action: {m['action_taken']}")
