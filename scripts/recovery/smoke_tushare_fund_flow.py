#!/usr/bin/env python3
"""Smoke test for Tushare-backed get_fund_flow.

This script calls only the bottom-level dataflow function. It does not call
LLMs, agents, prompts, graph propagation, or multi-agent workflows.
"""

from __future__ import annotations

import csv
import io
import os
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


AS_OF = "2026-07-07"
CASES = [
    ("300750", True),
    ("600519", False),
    ("300450", True),
    ("688981", False),
]

MONEYFLOW_REQUIRED = {
    "trade_date",
    "buy_sm_amount",
    "sell_sm_amount",
    "buy_md_amount",
    "sell_md_amount",
    "buy_lg_amount",
    "sell_lg_amount",
    "buy_elg_amount",
    "sell_elg_amount",
    "net_mf_amount",
}
MONEYFLOW_DC_REQUIRED = {
    "trade_date",
    "close",
    "pct_change",
    "net_amount",
    "net_amount_rate",
    "buy_elg_amount",
    "buy_lg_amount",
    "buy_md_amount",
    "buy_sm_amount",
}


def main() -> int:
    token_status = "present" if os.getenv("TUSHARE_TOKEN", "").strip() else "missing"
    print(f"TUSHARE_TOKEN={token_status}")

    from tradingagents.dataflows import a_stock

    failures = 0
    for ticker, include_history in CASES:
        text = a_stock.get_fund_flow(ticker, AS_OF, include_history=include_history)
        checks = validate_output(text)
        label = f"{ticker}/history={str(include_history).lower()}"
        if checks["ok"]:
            print(
                f"{label}: ok source={checks['source']} fallback={checks['fallback']} "
                f"rows={checks['rows']} date_range={checks['date_range']}"
            )
        else:
            failures += 1
            print(f"{label}: fail reason={checks['reason']}")

    return 1 if failures else 0


def validate_output(text: str) -> dict[str, object]:
    lowered = text.lower()
    forbidden = [
        "<html",
        "<!doctype",
        "traceback",
        "authorization",
        "set-cookie",
        "proxyerror",
        "bullish",
        "bearish",
        "buy recommendation",
        "sell recommendation",
        "strong buy",
        "strong sell",
        "北向",
        "大盘",
    ]
    for marker in forbidden:
        if marker in lowered:
            return {"ok": False, "reason": f"forbidden_marker:{marker}"}

    required_fragments = [
        "Fund Flow",
        "frequency=daily",
        "scope=individual_stock",
        "api=",
        "fallback=",
    ]
    for fragment in required_fragments:
        if fragment not in text:
            return {"ok": False, "reason": f"missing:{fragment}"}

    source = header_value(text, "Source")
    status = header_value(text, "status")
    api = header_value(text, "api")
    fallback = header_value(text, "fallback")
    date_range = header_value(text, "date_range") or header_value(text, "trade_date")
    if source not in {"Tushare moneyflow", "Tushare moneyflow_dc"}:
        return {"ok": False, "reason": "bad_source"}
    if status not in {"ok", "partial_data", "no_data", "technical_error"}:
        return {"ok": False, "reason": "bad_status"}

    if status in {"no_data", "technical_error"}:
        return {
            "ok": True,
            "source": source,
            "fallback": fallback,
            "rows": 0,
            "date_range": date_range,
        }

    rows, fieldnames = parse_csv_payload(text)
    required = MONEYFLOW_REQUIRED if api == "moneyflow" else MONEYFLOW_DC_REQUIRED
    missing_columns = required.difference(fieldnames)
    if missing_columns:
        return {"ok": False, "reason": f"missing_columns:{','.join(sorted(missing_columns))}"}
    if api == "moneyflow_dc":
        if fallback != "moneyflow_dc" or "net_only=true" not in text:
            return {"ok": False, "reason": "bad_fallback_metadata"}
    if any(row.get("trade_date", "") > AS_OF.replace("-", "") for row in rows):
        return {"ok": False, "reason": "future_trade_date"}

    return {
        "ok": True,
        "source": source,
        "fallback": fallback,
        "rows": len(rows),
        "date_range": date_range,
    }


def header_value(text: str, key: str) -> str:
    pattern = rf"^# {re.escape(key)}[:=]\s*(.+)$"
    match = re.search(pattern, text, flags=re.MULTILINE)
    return match.group(1).strip() if match else ""


def parse_csv_payload(text: str) -> tuple[list[dict[str, str]], set[str]]:
    lines = [line for line in text.splitlines() if line and not line.startswith("#")]
    csv_start = 0
    for index, line in enumerate(lines):
        if line.startswith("ts_code,") or line.startswith("trade_date,"):
            csv_start = index
            break
    csv_text = "\n".join(lines[csv_start:])
    reader = csv.DictReader(io.StringIO(csv_text))
    rows = list(reader)
    return rows, set(reader.fieldnames or [])


if __name__ == "__main__":
    raise SystemExit(main())
