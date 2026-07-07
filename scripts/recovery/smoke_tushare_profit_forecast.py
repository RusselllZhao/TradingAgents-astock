#!/usr/bin/env python3
"""Smoke test for Tushare-backed get_profit_forecast.

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
AS_OF_COMPACT = AS_OF.replace("-", "")
CASES = ["600519", "300750", "300450", "688981"]


def main() -> int:
    token_status = "present" if os.getenv("TUSHARE_TOKEN", "").strip() else "missing"
    print(f"TUSHARE_TOKEN={token_status}")

    from tradingagents.dataflows import a_stock

    failures = 0
    for ticker in CASES:
        text = a_stock.get_profit_forecast(ticker, AS_OF)
        checks = validate_output(text)
        if checks["ok"]:
            print(
                f"{ticker}: ok status={checks['status']} "
                f"source_count={checks['source_count']} "
                f"source_org_count={checks['source_org_count']} "
                f"report_date_range={checks['report_date_range']}"
            )
        else:
            failures += 1
            print(f"{ticker}: fail reason={checks['reason']}")

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
        "api=forecast",
        "api=express",
        "api=fina_indicator",
    ]
    for marker in forbidden:
        if marker in lowered:
            return {"ok": False, "reason": f"forbidden_marker:{marker}"}

    required_fragments = [
        "Consensus EPS Forecast",
        "Source: Tushare report_rc sell-side forecast aggregation",
        "forecast_type=sell_side_forecast",
        "not_company_guidance=true",
        "as_of_field=report_date",
        "api=report_rc",
    ]
    for fragment in required_fragments:
        if fragment not in text:
            return {"ok": False, "reason": f"missing:{fragment}"}

    status = header_value(text, "status")
    source_count = int(header_value(text, "source_count") or "0")
    source_org_count = int(header_value(text, "source_org_count") or "0")
    report_date_range = header_value(text, "report_date_range")

    if status not in {"ok", "no_coverage", "no_data", "technical_error", "partial_data"}:
        return {"ok": False, "reason": "bad_status"}

    if status != "ok":
        if "no_coverage:" in text or "no_data:" in text or "technical_error:" in text:
            return {
                "ok": True,
                "status": status,
                "source_count": source_count,
                "source_org_count": source_org_count,
                "report_date_range": report_date_range,
            }
        return {"ok": False, "reason": "bad_short_error"}

    for key in ("source_count", "source_org_count", "report_date_range", "low_coverage"):
        if header_value(text, key) == "":
            return {"ok": False, "reason": f"missing_header:{key}"}

    rows, fieldnames = parse_csv_payload(text)
    required_columns = {
        "forecast_period",
        "quarter",
        "institution_count",
        "latest_report_date",
        "eps_count",
        "eps_mean",
        "eps_median",
        "eps_min",
        "eps_max",
    }
    missing_columns = required_columns.difference(fieldnames)
    if missing_columns:
        return {"ok": False, "reason": f"missing_columns:{','.join(sorted(missing_columns))}"}
    if not rows:
        return {"ok": False, "reason": "empty_aggregation"}
    if any(row.get("latest_report_date", "") > AS_OF_COMPACT for row in rows):
        return {"ok": False, "reason": "future_report_date"}

    return {
        "ok": True,
        "status": status,
        "source_count": source_count,
        "source_org_count": source_org_count,
        "report_date_range": report_date_range,
    }


def header_value(text: str, key: str) -> str:
    match = re.search(rf"^# {re.escape(key)}[:=]\s*(.+)$", text, flags=re.MULTILINE)
    return match.group(1).strip() if match else ""


def parse_csv_payload(text: str) -> tuple[list[dict[str, str]], set[str]]:
    lines = [line for line in text.splitlines() if line and not line.startswith("#")]
    csv_start = 0
    for index, line in enumerate(lines):
        if line.startswith("forecast_period,"):
            csv_start = index
            break
    csv_text = "\n".join(lines[csv_start:])
    reader = csv.DictReader(io.StringIO(csv_text))
    rows = list(reader)
    return rows, set(reader.fieldnames or [])


if __name__ == "__main__":
    raise SystemExit(main())
