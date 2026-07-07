#!/usr/bin/env python3
"""Smoke test for Tushare-backed financial statement dataflow functions.

This script calls only bottom-level dataflow functions. It does not call LLMs,
agents, prompts, graph propagation, or multi-agent workflows.
"""

from __future__ import annotations

import csv
import io
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


CASES = [
    (
        "balance_quarterly",
        "get_balance_sheet",
        "600519",
        "quarterly",
        "2026-07-07",
        "balancesheet",
    ),
    (
        "balance_annual",
        "get_balance_sheet",
        "600519",
        "annual",
        "2026-07-07",
        "balancesheet",
    ),
    (
        "cashflow_quarterly",
        "get_cashflow",
        "600519",
        "quarterly",
        "2026-07-07",
        "cashflow",
    ),
    (
        "cashflow_annual",
        "get_cashflow",
        "300750",
        "annual",
        "2026-07-07",
        "cashflow",
    ),
    (
        "income_quarterly",
        "get_income_statement",
        "600519",
        "quarterly",
        "2026-07-07",
        "income",
    ),
    (
        "income_annual",
        "get_income_statement",
        "300750",
        "annual",
        "2026-07-07",
        "income",
    ),
]

REQUIRED_COLUMNS = {
    "ts_code",
    "ann_date",
    "f_ann_date",
    "end_date",
    "report_type",
    "comp_type",
    "end_type",
}


def main() -> int:
    token_status = "present" if os.getenv("TUSHARE_TOKEN", "").strip() else "missing"
    print(f"TUSHARE_TOKEN={token_status}")

    from tradingagents.dataflows import a_stock

    failures = 0
    for label, fn_name, ticker, freq, as_of, api_name in CASES:
        fn = getattr(a_stock, fn_name)
        text = fn(ticker, freq, as_of)
        checks = validate_output(text, api_name, as_of)
        if checks["ok"]:
            print(
                f"{label}: ok api={api_name} rows={checks['rows']} "
                f"max_ann_date={checks['max_ann_date'] or 'n/a'}"
            )
        else:
            failures += 1
            print(f"{label}: fail api={api_name} reason={checks['reason']}")

    return 1 if failures else 0


def validate_output(text: str, api_name: str, as_of: str) -> dict[str, object]:
    lowered = text.lower()
    forbidden = ["<html", "<!doctype", "traceback", "authorization", "set-cookie"]
    for marker in forbidden:
        if marker in lowered:
            return {
                "ok": False,
                "reason": f"forbidden_marker:{marker}",
                "rows": 0,
                "max_ann_date": "",
            }

    if "Data source: Tushare" not in text:
        return {"ok": False, "reason": "missing_tushare_source", "rows": 0, "max_ann_date": ""}
    if f"API: {api_name}" not in text:
        return {"ok": False, "reason": "missing_api", "rows": 0, "max_ann_date": ""}
    if "ann_date" not in text or "end_date" not in text:
        return {"ok": False, "reason": "missing_date_fields", "rows": 0, "max_ann_date": ""}

    if "technical_error:" in text or "no_data:" in text:
        return {"ok": True, "reason": "", "rows": 0, "max_ann_date": ""}

    csv_text = "\n".join(line for line in text.splitlines() if not line.startswith("#")).strip()
    reader = csv.DictReader(io.StringIO(csv_text))
    rows = list(reader)
    missing_columns = REQUIRED_COLUMNS.difference(reader.fieldnames or [])
    if missing_columns:
        return {
            "ok": False,
            "reason": f"missing_columns:{','.join(sorted(missing_columns))}",
            "rows": len(rows),
            "max_ann_date": "",
        }
    as_of_compact = as_of.replace("-", "")
    ann_dates = [row.get("ann_date", "") for row in rows if row.get("ann_date")]
    if any(ann_date > as_of_compact for ann_date in ann_dates):
        return {
            "ok": False,
            "reason": "future_ann_date",
            "rows": len(rows),
            "max_ann_date": max(ann_dates),
        }

    return {
        "ok": True,
        "reason": "",
        "rows": len(rows),
        "max_ann_date": max(ann_dates) if ann_dates else "",
    }


if __name__ == "__main__":
    raise SystemExit(main())
