#!/usr/bin/env python3
"""Smoke test for Tushare-backed get_fundamentals.

This script calls only the bottom-level dataflow function. It does not call
LLMs, agents, prompts, graph propagation, or multi-agent workflows.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


AS_OF = "2026-07-07"
CASES = ["600519", "300750", "300450", "688981"]
CORE_LABELS = [
    "Name:",
    "Industry:",
    "Market:",
    "List Date:",
    "Trade Date:",
    "Close:",
    "PE:",
    "PE (TTM):",
    "PB:",
    "Market Cap (10K CNY):",
    "Float Market Cap (10K CNY):",
    "Total Shares (10K):",
    "Float Shares (10K):",
]


def main() -> int:
    token_status = "present" if os.getenv("TUSHARE_TOKEN", "").strip() else "missing"
    print(f"TUSHARE_TOKEN={token_status}")

    from tradingagents.dataflows import a_stock

    failures = 0
    for ticker in CASES:
        text = a_stock.get_fundamentals(ticker, AS_OF)
        checks = validate_output(text)
        if checks["ok"]:
            print(
                f"{ticker}: ok status={checks['status']} "
                f"trade_date={checks['trade_date']} core_fields={checks['core_fields']}"
            )
        else:
            failures += 1
            print(f"{ticker}: fail reason={checks['reason']}")

    return 1 if failures else 0


def validate_output(text: str) -> dict[str, object]:
    lowered = text.lower()
    forbidden = ["<html", "<!doctype", "traceback", "authorization", "set-cookie"]
    for marker in forbidden:
        if marker in lowered:
            return {"ok": False, "reason": f"forbidden_marker:{marker}"}

    required_fragments = [
        "Company Fundamentals",
        "Source: Tushare daily_basic + stock_basic",
        "realtime=false",
        "api=daily_basic,stock_basic",
    ]
    for fragment in required_fragments:
        if fragment not in text:
            return {"ok": False, "reason": f"missing:{fragment}"}

    status_match = re.search(r"^# status: (.+)$", text, flags=re.MULTILINE)
    trade_date_match = re.search(r"^# trade_date: (.+)$", text, flags=re.MULTILINE)
    status = status_match.group(1).strip() if status_match else ""
    trade_date = trade_date_match.group(1).strip() if trade_date_match else ""
    if status not in {"ok", "partial_data", "no_data", "technical_error"}:
        return {"ok": False, "reason": "bad_status"}
    if status in {"ok", "partial_data"} and not re.fullmatch(r"\d{8}", trade_date):
        return {"ok": False, "reason": "missing_trade_date"}

    core_fields = sum(1 for label in CORE_LABELS if label in text)
    if status == "ok" and core_fields < 10:
        return {"ok": False, "reason": "too_few_core_fields"}
    if "Float Shares (10K):" in text and core_fields <= 2:
        return {"ok": False, "reason": "shares_only_without_explanation"}

    return {
        "ok": True,
        "reason": "",
        "status": status,
        "trade_date": trade_date,
        "core_fields": core_fields,
    }


if __name__ == "__main__":
    raise SystemExit(main())
