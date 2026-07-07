#!/usr/bin/env python3
"""First-batch Tushare dataflow regression smoke test.

This script calls only bottom-level dataflow functions. It does not call LLMs,
agents, prompts, graph propagation, or multi-agent workflows.
"""

from __future__ import annotations

import csv
import io
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

AS_OF = "2026-07-07"
AS_OF_COMPACT = AS_OF.replace("-", "")
OUTPUT_DIR = ROOT / "docs" / "recovery" / "tushare_pro_inventory"
OUTPUT_MD = OUTPUT_DIR / "TUSHARE_PRO_FIRST_BATCH_REGRESSION_RESULT.md"
OUTPUT_CSV = OUTPUT_DIR / "TUSHARE_PRO_FIRST_BATCH_REGRESSION_RESULT.csv"


@dataclass(frozen=True)
class Case:
    function: str
    args: tuple[object, ...]
    kwargs: dict[str, object]
    expected_api: str
    category: str

    @property
    def input_repr(self) -> str:
        args = ", ".join(repr(arg) for arg in self.args)
        kwargs = ", ".join(f"{key}={value!r}" for key, value in self.kwargs.items())
        joined = ", ".join(part for part in (args, kwargs) if part)
        return f"{self.function}({joined})"


CASES = [
    Case("get_balance_sheet", ("600519", "quarterly", AS_OF), {}, "balancesheet", "financial"),
    Case("get_balance_sheet", ("600519", "annual", AS_OF), {}, "balancesheet", "financial"),
    Case("get_cashflow", ("600519", "quarterly", AS_OF), {}, "cashflow", "financial"),
    Case("get_cashflow", ("300750", "annual", AS_OF), {}, "cashflow", "financial"),
    Case("get_income_statement", ("600519", "quarterly", AS_OF), {}, "income", "financial"),
    Case("get_income_statement", ("300750", "annual", AS_OF), {}, "income", "financial"),
    Case("get_fundamentals", ("600519", AS_OF), {}, "daily_basic,stock_basic", "fundamentals"),
    Case("get_fundamentals", ("300750", AS_OF), {}, "daily_basic,stock_basic", "fundamentals"),
    Case("get_fundamentals", ("300450", AS_OF), {}, "daily_basic,stock_basic", "fundamentals"),
    Case("get_fundamentals", ("688981", AS_OF), {}, "daily_basic,stock_basic", "fundamentals"),
    Case("get_fund_flow", ("300750", AS_OF), {"include_history": True}, "moneyflow", "fund_flow"),
    Case("get_fund_flow", ("600519", AS_OF), {"include_history": False}, "moneyflow", "fund_flow"),
    Case("get_fund_flow", ("300450", AS_OF), {"include_history": True}, "moneyflow", "fund_flow"),
    Case("get_fund_flow", ("688981", AS_OF), {"include_history": False}, "moneyflow", "fund_flow"),
    Case("get_profit_forecast", ("600519", AS_OF), {}, "report_rc", "profit_forecast"),
    Case("get_profit_forecast", ("300750", AS_OF), {}, "report_rc", "profit_forecast"),
    Case("get_profit_forecast", ("300450", AS_OF), {}, "report_rc", "profit_forecast"),
    Case("get_profit_forecast", ("688981", AS_OF), {}, "report_rc", "profit_forecast"),
]


def main() -> int:
    token_status = "present" if os.getenv("TUSHARE_TOKEN", "").strip() else "missing"
    commit = current_commit()
    tested_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    from tradingagents.dataflows import a_stock

    results = []
    for case in CASES:
        fn: Callable[..., str] = getattr(a_stock, case.function)
        try:
            output = fn(*case.args, **case.kwargs)
        except Exception as exc:  # pragma: no cover - defensive smoke boundary
            output = f"technical_error: {type(exc).__name__}"
        result = validate_case(case, output)
        results.append(result)
        print(
            f"{case.input_repr}: {'PASS' if result['passed'] else 'FAIL'} "
            f"status={result['status']} api={result['api']} note={result['notes']}"
        )

    write_csv(results)
    write_markdown(results, tested_at, commit, token_status)

    print(f"Wrote {OUTPUT_MD.relative_to(ROOT)}")
    print(f"Wrote {OUTPUT_CSV.relative_to(ROOT)}")
    return 0 if all(row["passed"] for row in results) else 1


def validate_case(case: Case, output: str) -> dict[str, object]:
    status = get_status(output)
    source_ok = has_tushare_source(output)
    api = get_api(output)
    api_ok = validate_api(case, api, output)
    date_ok, date_note = validate_dates(case, output)
    security_ok, security_note = validate_security(output)
    semantic_ok, semantic_note = validate_semantics(case, output)
    format_ok = validate_format(output)

    notes = "; ".join(
        note
        for note in [date_note, security_note, semantic_note, "" if format_ok else "bad_output_format"]
        if note
    )
    passed = (
        status in {"ok", "partial_data", "no_data", "no_coverage", "technical_error"}
        and source_ok
        and api_ok
        and date_ok
        and security_ok
        and semantic_ok
        and format_ok
    )
    return {
        "function": case.function,
        "input": case.input_repr,
        "status": status or "missing",
        "output_length": len(output),
        "source_ok": source_ok,
        "api": api,
        "api_ok": api_ok,
        "date_ok": date_ok,
        "security_ok": security_ok,
        "semantic_ok": semantic_ok,
        "format_ok": format_ok,
        "passed": passed,
        "notes": notes or "ok",
    }


def get_status(text: str) -> str:
    value = header_value(text, "status")
    if value:
        return value
    for status in ("technical_error", "no_coverage", "no_data", "partial_data"):
        if f"{status}:" in text:
            return status
    return ""


def get_api(text: str) -> str:
    return header_value(text, "API") or header_value(text, "api")


def header_value(text: str, key: str) -> str:
    match = re.search(rf"^# {re.escape(key)}[:=]\s*(.+)$", text, flags=re.MULTILINE)
    return match.group(1).strip() if match else ""


def has_tushare_source(text: str) -> bool:
    return "Source: Tushare" in text or "Data source: Tushare" in text


def validate_api(case: Case, api: str, output: str) -> bool:
    if case.category == "fund_flow":
        return api in {"moneyflow", "moneyflow_dc"}
    return case.expected_api == api or f"API: {case.expected_api}" in output


def parse_csv_payload(text: str, startswith: str) -> tuple[list[dict[str, str]], set[str]]:
    lines = [line for line in text.splitlines() if line and not line.startswith("#")]
    csv_start = -1
    for index, line in enumerate(lines):
        if line.startswith(startswith):
            csv_start = index
            break
    if csv_start < 0:
        return [], set()
    reader = csv.DictReader(io.StringIO("\n".join(lines[csv_start:])))
    rows = list(reader)
    return rows, set(reader.fieldnames or [])


def validate_dates(case: Case, output: str) -> tuple[bool, str]:
    if get_status(output) in {"no_data", "no_coverage", "technical_error"}:
        return True, ""
    if case.category == "financial":
        rows, _ = parse_csv_payload(output, "ts_code,")
        bad = [row.get("ann_date", "") for row in rows if row.get("ann_date", "") > AS_OF_COMPACT]
        return (not bad, "future_ann_date" if bad else "")
    if case.category == "fundamentals":
        trade_date = header_value(output, "trade_date")
        return (not trade_date or trade_date <= AS_OF_COMPACT, "future_trade_date" if trade_date > AS_OF_COMPACT else "")
    if case.category == "fund_flow":
        rows, _ = parse_csv_payload(output, "ts_code,")
        bad = [row.get("trade_date", "") for row in rows if row.get("trade_date", "") > AS_OF_COMPACT]
        return (not bad, "future_trade_date" if bad else "")
    if case.category == "profit_forecast":
        rows, _ = parse_csv_payload(output, "forecast_period,")
        bad = [
            row.get("latest_report_date", "")
            for row in rows
            if row.get("latest_report_date", "") > AS_OF_COMPACT
        ]
        return (not bad, "future_report_date" if bad else "")
    return True, ""


def validate_security(output: str) -> tuple[bool, str]:
    lowered = output.lower()
    forbidden = {
        "<html": "html",
        "<!doctype": "html",
        "traceback": "traceback",
        "proxyerror": "proxy_error",
        "authorization": "sensitive_header",
        "set-cookie": "sensitive_header",
        "tushare_token": "token_name",
        "api_key": "sensitive_marker",
        "access_token": "sensitive_marker",
        "error fetching": "bare_error",
        "error retrieving": "bare_error",
        "no data found": "bare_no_data",
    }
    for marker, reason in forbidden.items():
        if marker in lowered:
            return False, reason
    return True, ""


def validate_semantics(case: Case, output: str) -> tuple[bool, str]:
    lowered = output.lower()
    if case.category == "financial":
        required = ["Data source: Tushare", f"API: {case.expected_api}", "ann_date", "end_date"]
        if not all(fragment in output for fragment in required):
            return False, "financial_header_or_fields_missing"
        if "quarterly" in case.input_repr and "quarterly_policy: cumulative_period" not in output:
            return False, "quarterly_policy_missing"
        if "report_type_filter: unverified" not in output:
            return False, "report_type_filter_note_missing"
    elif case.category == "fundamentals":
        required = [
            "Company Fundamentals",
            "Source: Tushare daily_basic + stock_basic",
            "realtime=false",
            "trade_date",
        ]
        if not all(fragment in output for fragment in required):
            return False, "fundamentals_header_missing"
        core_labels = [
            "Name:",
            "Industry:",
            "Market:",
            "List Date:",
            "Trade Date:",
            "Close:",
            "PE:",
            "PB:",
            "Market Cap",
            "Float Market Cap",
            "Total Shares",
            "Float Shares",
        ]
        core_count = sum(1 for label in core_labels if label in output)
        if core_count < 10:
            return False, "too_few_core_fields"
    elif case.category == "fund_flow":
        required = ["Fund Flow", "frequency=daily", "scope=individual_stock"]
        if not all(fragment in output for fragment in required):
            return False, "fund_flow_header_missing"
        if any(marker in lowered for marker in ("bullish", "bearish", "buy recommendation", "sell recommendation")):
            return False, "investment_advice_marker"
        if any(marker in output for marker in ("北向", "大盘")):
            return False, "market_or_northbound_marker"
        if "api=moneyflow_dc" in output and not ("fallback=moneyflow_dc" in output and "net_only=true" in output):
            return False, "fallback_metadata_missing"
    elif case.category == "profit_forecast":
        required = [
            "Consensus EPS Forecast",
            "Source: Tushare report_rc sell-side forecast aggregation",
            "forecast_type=sell_side_forecast",
            "not_company_guidance=true",
            "as_of_field=report_date",
            "source_count",
            "source_org_count",
            "report_date_range",
        ]
        if not all(fragment in output for fragment in required):
            return False, "profit_forecast_header_missing"
        bad_sources = ("api=forecast", "api=express", "api=fina_indicator")
        if any(source in lowered for source in bad_sources):
            return False, "wrong_profit_forecast_source"
        if any(marker in lowered for marker in ("bullish", "bearish", "buy recommendation", "sell recommendation")):
            return False, "investment_advice_marker"
    return True, ""


def validate_format(output: str) -> bool:
    return output.startswith("# ") and "\n" in output and len(output) < 300_000


def write_csv(results: list[dict[str, object]]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    fields = [
        "function",
        "input",
        "status",
        "output_length",
        "source_ok",
        "api",
        "api_ok",
        "date_ok",
        "security_ok",
        "semantic_ok",
        "format_ok",
        "passed",
        "notes",
    ]
    with OUTPUT_CSV.open("w", encoding="utf-8", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(results)


def write_markdown(
    results: list[dict[str, object]],
    tested_at: str,
    commit: str,
    token_status: str,
) -> None:
    passed = sum(1 for row in results if row["passed"])
    overall = "passed" if passed == len(results) else "failed"
    lines = [
        "# Tushare Pro First Batch Regression Result",
        "",
        f"- Test time: {tested_at}",
        f"- Commit: `{commit}`",
        f"- TUSHARE_TOKEN: `{token_status}`",
        f"- Overall: `{overall}` ({passed}/{len(results)} passed)",
        "- Scope: bottom-level dataflow functions only; no LLM, no multi-agent workflow.",
        "",
        "## Tested Functions",
        "",
        "- `get_balance_sheet`",
        "- `get_cashflow`",
        "- `get_income_statement`",
        "- `get_fundamentals`",
        "- `get_fund_flow`",
        "- `get_profit_forecast`",
        "",
        "## Test Cases",
        "",
    ]
    for case in CASES:
        lines.append(f"- `{case.input_repr}`")
    lines.extend([
        "",
        "## Results",
        "",
        "| Function | Input | Status | Length | Source/API | Date | Safety | Semantics | Pass | Notes |",
        "|---|---|---:|---:|---|---|---|---|---|---|",
    ])
    for row in results:
        lines.append(
            "| {function} | `{input}` | {status} | {output_length} | {source_api} | {date} | {safety} | {semantics} | {passed} | {notes} |".format(
                function=row["function"],
                input=str(row["input"]).replace("|", "\\|"),
                status=row["status"],
                output_length=row["output_length"],
                source_api="ok" if row["source_ok"] and row["api_ok"] else "fail",
                date="ok" if row["date_ok"] else "fail",
                safety="ok" if row["security_ok"] else "fail",
                semantics="ok" if row["semantic_ok"] and row["format_ok"] else "fail",
                passed="yes" if row["passed"] else "no",
                notes=str(row["notes"]).replace("|", "\\|"),
            )
        )
    problem_rows = [row for row in results if not row["passed"]]
    lines.extend(["", "## Conclusion", ""])
    if problem_rows:
        lines.append("- Overall result: failed.")
        for row in problem_rows:
            lines.append(f"- `{row['input']}`: {row['notes']}")
    else:
        lines.append("- Overall result: passed.")
        lines.append("- No future-date leakage was detected.")
        lines.append("- No HTML, traceback, token value, proxy stack, or oversized error text was detected.")
        lines.append("- No first-batch business semantic violations were detected.")
    lines.append("")
    OUTPUT_MD.write_text("\n".join(lines), encoding="utf-8")


def current_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=ROOT,
            text=True,
        ).strip()
    except Exception:
        return "unknown"


if __name__ == "__main__":
    raise SystemExit(main())
