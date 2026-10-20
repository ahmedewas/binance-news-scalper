"""Reconcile the legacy paper journal without modifying its evidence.

Usage: python scripts/analyze_journal.py TRADING_JOURNAL.md --output analysis.json
"""
import argparse
import json
import re
from collections import Counter
from pathlib import Path


def analyze(text):
    active, last, trades, duplicates, unmatched = {}, {}, [], [], []
    opened = 0
    for block in re.split(r"(?=^### )", text, flags=re.M):
        symbol = re.search(r"`([A-Z0-9]+/USDT)`", block)
        date = re.search(r"`(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d) UTC`", block)
        if not symbol or not date:
            continue
        sym = symbol[1]
        if "فتح صفقة جديدة:" in block:
            opened += 1
            cost = re.search(r"رأس المال المخصص:\*\* `\$([\d.]+)`", block)
            active[sym] = dict(id=f"legacy-{opened}", opened_at=date[1],
                               cost=float(cost[1]), flow="[SPOT FLOW]" in block)
        elif "إغلاق صفقة:" in block:
            result = re.search(r"النتيجة: `([+\-\d.]+)%` \(\$([+\-\d.]+)\)", block)
            prices = re.search(r"سعر الدخول:\*\* `\$([\d.]+)`.*?`\$([\d.]+)`", block)
            reason = re.search(r"سبب الخروج الموثق:\*\* (.+)", block)[1]
            row = dict(symbol=sym, closed_at=date[1], pct=float(result[1]), pnl=float(result[2]),
                       minutes=float(re.search(r"مدة الصفقة: `([\d.]+)`", block)[1]),
                       reason=reason, entry=float(prices[1]), exit=float(prices[2]))
            signature = tuple(row[k] for k in ("symbol", "pct", "pnl", "minutes", "reason", "entry", "exit"))
            if sym in active:
                if "جزئي" in reason or "PARTIAL" in reason:
                    raise ValueError("Legacy partial exits need manual reconciliation; no automatic deduction")
                row.update(active.pop(sym))
                trades.append(row)
                last[sym] = signature
            elif last.get(sym) == signature:
                duplicates.append(row)
            else:
                unmatched.append(row)
    summary = dict(opens=opened, matched_closes=len(trades), duplicate_closes=len(duplicates),
                   unmatched_closes=len(unmatched), still_open=list(active),
                   wins=sum(t["pnl"] > 0 for t in trades), losses=sum(t["pnl"] < 0 for t in trades),
                   net_pnl=sum(t["pnl"] for t in trades),
                   reasons=dict(Counter(t["reason"] for t in trades)),
                   flow_entries=sum(t["flow"] for t in trades))
    return dict(summary=summary, trades=trades, duplicates=duplicates, unmatched=unmatched)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("journal", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = analyze(args.journal.read_text(encoding="utf-8-sig"))
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result["summary"], ensure_ascii=True))
