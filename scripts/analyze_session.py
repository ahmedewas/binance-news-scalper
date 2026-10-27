import json
from collections import defaultdict
from datetime import datetime

with open('data/state-paper.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

trades = d.get('trade_history', [])
print(f"Total Trades: {len(trades)}")
if trades:
    print(f"Start: {trades[0]['timestamp']}")
    print(f"End:   {trades[-1]['timestamp']}")

# Distribution by Exit Reason
reasons = defaultdict(lambda: {'count': 0, 'pnl': 0.0})
for t in trades:
    r = t.get('reason', '').split('(')[0].strip()
    reasons[r]['count'] += 1
    reasons[r]['pnl'] += t.get('pnl_usd', 0.0)

print("\n=== Exit Reasons Breakdown ===")
for r, data in sorted(reasons.items(), key=lambda x: x[1]['pnl'], reverse=True):
    print(f"{r:35} | Count: {data['count']:2d} | Net PnL: {data['pnl']:+.4f} USD")

# Performance by Symbol
by_sym = defaultdict(lambda: {'count': 0, 'wins': 0, 'losses': 0, 'pnl': 0.0})
for t in trades:
    s = t.get('symbol', 'UNKNOWN')
    by_sym[s]['count'] += 1
    pnl = t.get('pnl_usd', 0.0)
    by_sym[s]['pnl'] += pnl
    if pnl > 0:
        by_sym[s]['wins'] += 1
    elif pnl < 0:
        by_sym[s]['losses'] += 1

print("\n=== Performance by Symbol ===")
for s, st in sorted(by_sym.items(), key=lambda x: x[1]['pnl'], reverse=True):
    wr = (st['wins'] / st['count']) * 100
    print(f"{s:12} | Trades: {st['count']:2d} | Wins: {st['wins']:2d} | Losses: {st['losses']:2d} | WinRate: {wr:5.1f}% | Net PnL: {st['pnl']:+.4f} USD")

# Chronological Phases (Breakdown by 4-hour windows or major market shifts)
print("\n=== Chronological Breakdown (By Time Windows) ===")
# Parse trades by timestamp
parsed_trades = []
for t in trades:
    dt = datetime.fromisoformat(t['timestamp'])
    parsed_trades.append((dt, t))

# Sort by dt
parsed_trades.sort(key=lambda x: x[0])

# Group into phases
phases = [
    ("Phase 1: Launch & Initial Momentum (16:00 - 20:00 UTC Oct 25)", datetime.fromisoformat("2026-10-25T16:00:00+00:00"), datetime.fromisoformat("2026-10-25T20:00:00+00:00")),
    ("Phase 2: Night Choppiness & SL Adjustments (20:00 Oct 25 - 00:00 UTC Oct 26)", datetime.fromisoformat("2026-10-25T20:00:00+00:00"), datetime.fromisoformat("2026-10-26T00:00:00+00:00")),
    ("Phase 3: The ERA/USDT Star Breakout (00:00 - 04:00 UTC Oct 26)", datetime.fromisoformat("2026-10-26T00:00:00+00:00"), datetime.fromisoformat("2026-10-26T04:00:00+00:00")),
    ("Phase 4: Positive Breakeven Machine (04:00 - 08:00 UTC Oct 26)", datetime.fromisoformat("2026-10-26T04:00:00+00:00"), datetime.fromisoformat("2026-10-26T08:00:00+00:00")),
    ("Phase 5: Trailing Momentum & Final Harvest (08:00 - 13:00 UTC Oct 26)", datetime.fromisoformat("2026-10-26T08:00:00+00:00"), datetime.fromisoformat("2026-10-26T13:00:00+00:00")),
]

for name, start, end in phases:
    p_trades = [t for dt, t in parsed_trades if start <= dt < end]
    p_wins = [t for t in p_trades if t.get('pnl_usd', 0) > 0]
    p_pnl = sum(t.get('pnl_usd', 0) for t in p_trades)
    wr = len(p_wins) / len(p_trades) * 100 if p_trades else 0
    print(f"\n>> {name}")
    print(f"   Trades: {len(p_trades)} | Wins: {len(p_wins)} ({wr:.1f}%) | Net PnL: {p_pnl:+.4f} USD")
    for t in p_trades:
        sym = t['symbol']
        pnl = t.get('pnl_usd', 0)
        rsn = t.get('reason', '').split('(')[0].strip()
        time_str = datetime.fromisoformat(t['timestamp']).strftime('%H:%M:%S')
        print(f"     [{time_str}] {sym:10} -> {pnl:+.4f} USD ({rsn})")

print("\n=== AI Evolution State ===")
critic = d.get('adaptive_ai', {})
print(f"Critic Penalties: {critic.get('penalized_symbols')}")
print(f"Critic Summary:   {critic.get('critic_summary')}")
print(f"Genetic TP:       {critic.get('fittest_tp')}")
print(f"Genetic SL:       {critic.get('fittest_sl')}")
print(f"Memory Wins:      {critic.get('memory_wins')}")
print(f"Memory Losses:    {critic.get('memory_losses')}")
