#!/usr/bin/env python3
"""Smoke test for get_news data-source contract.

This calls only the bottom-level dataflow function. It does not call Tushare,
LLMs, agents, graph propagation, prompts, or multi-agent workflows.
"""

from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CASES = (
    ("300450", "normal"),
    ("600519", "normal"),
    ("688981", "normal"),
    ("BADCODE", "invalid"),
)

REQUIRED_HEADER_KEYS = {
    "status",
    "source",
    "data_type",
    "query_target",
    "symbol",
    "as_of",
    "trade_date",
    "unit",
    "coverage",
    "fallback",
    "empty_reason",
    "error_type",
    "raw_error_suppressed",
}

VALID_STATUSES = {
    "ok",
    "partial_data",
    "empty",
    "no_coverage",
    "invalid_input",
    "technical_error",
}

FORBIDDEN_PATTERNS = {
    "<html": "html",
    "<!doctype": "html",
    "traceback": "traceback",
    "httpsconnectionpool": "raw_network_stack",
    "proxyerror": "proxy_stack",
    "proxy stack": "proxy_stack",
    "raw exception": "raw_exception",
    "anti-scraping": "anti_scraping_text",
    "反爬": "anti_scraping_text",
    "bullish": "directional_language",
    "bearish": "directional_language",
    "confidence": "forbidden_label",
    "conclusion_level": "forbidden_label",
    "strong evidence": "forbidden_label",
    "weak evidence": "forbidden_label",
    "first-hand fact": "forbidden_label",
    "second-hand information": "forbidden_label",
    "global_news": "wrong_scope_claim",
    "major_news": "wrong_scope_claim",
    "company announcement": "wrong_data_type_claim",
}

RAW_ERROR_HINTS = {
    "requestexception",
    "connectionerror",
    "readtimeout",
    "jsondecodeerror",
    "status code",
    "indexerror",
    "valueerror",
}


@dataclass
class SmokeResult:
    ticker: str
    passed: bool
    status: str
    output_length: int
    notes: str


def main() -> int:
    from tradingagents.dataflows.a_stock import get_news

    end_date = date.today()
    start_date = end_date - timedelta(days=365)
    results: list[SmokeResult] = []
    for ticker, case_type in CASES:
        try:
            output = get_news(
                ticker,
                start_date.strftime("%Y-%m-%d"),
                end_date.strftime("%Y-%m-%d"),
            )
        except Exception as exc:  # pragma: no cover - defensive smoke boundary
            output = f"uncaught_exception: {type(exc).__name__}"
        result = validate_output(ticker, case_type, output)
        results.append(result)
        print(
            f"{ticker}: {'PASS' if result.passed else 'FAIL'} "
            f"status={result.status or 'missing'} "
            f"len={result.output_length} note={result.notes}"
        )

    passed = sum(1 for result in results if result.passed)
    print(f"SUMMARY: {passed}/{len(results)} PASS")
    return 0 if all(result.passed for result in results) else 1


def validate_output(ticker: str, case_type: str, output: str) -> SmokeResult:
    notes: list[str] = []
    if not isinstance(output, str):
        return SmokeResult(ticker, False, "", 0, "output_not_string")

    if "# Data Source Contract" not in output:
        notes.append("missing_contract_header")

    header = parse_header(output)
    missing = sorted(REQUIRED_HEADER_KEYS - set(header))
    if missing:
        notes.append("missing_header_keys=" + ",".join(missing))

    status = header.get("status", "")
    if status not in VALID_STATUSES:
        notes.append(f"bad_status={status or 'missing'}")

    if header.get("source") != "Eastmoney stock news + Sina fallback":
        notes.append(f"bad_source={header.get('source', 'missing')}")
    if header.get("data_type") != "news":
        notes.append(f"bad_data_type={header.get('data_type', 'missing')}")
    if header.get("query_target") != "stock":
        notes.append(f"bad_query_target={header.get('query_target', 'missing')}")

    expected_coverage = "symbol_unresolved" if case_type == "invalid" else "individual_stock"
    if header.get("coverage") != expected_coverage:
        notes.append(f"bad_coverage={header.get('coverage', 'missing')}")

    raw_error_suppressed = header.get("raw_error_suppressed", "")
    if status == "technical_error":
        if raw_error_suppressed != "true":
            notes.append("technical_error_without_raw_suppression")
        if len(output) > 2500:
            notes.append("technical_error_too_long")
        if "Data source request failed; raw technical details suppressed." not in output:
            notes.append("missing_short_technical_error_message")
    elif status == "partial_data":
        if header.get("fallback") != "Eastmoney->Sina":
            notes.append(f"bad_partial_fallback={header.get('fallback', 'missing')}")
    else:
        if raw_error_suppressed != "false":
            notes.append("non_error_raw_suppression_not_false")

    if status in {"ok", "partial_data"}:
        for field in ("pub_time", "source", "title"):
            if field not in output:
                notes.append(f"missing_news_field={field}")
        if "Stock-Specific News" not in output:
            notes.append("missing_stock_specific_title")
    elif status in {"empty", "no_coverage"}:
        if not header.get("empty_reason") or header.get("empty_reason") == "none":
            notes.append("empty_without_empty_reason")
    elif status == "invalid_input":
        if header.get("empty_reason") != "invalid_or_unresolved_ticker":
            notes.append(
                f"bad_invalid_empty_reason={header.get('empty_reason', 'missing')}"
            )
        if "| pub_time |" in output or "Stock-Specific News" in output:
            notes.append("invalid_input_returned_news_table")

    raw_hint_matches = find_raw_error_hints(output)
    if raw_hint_matches:
        notes.append("raw_error_hint=" + ",".join(raw_hint_matches))

    forbidden = find_forbidden(output)
    if forbidden:
        notes.append("forbidden_output=" + ",".join(forbidden))

    leaked = find_sensitive_value_leaks(output)
    if leaked:
        notes.append("sensitive_value_leak=" + ",".join(leaked))

    return SmokeResult(
        ticker=ticker,
        passed=not notes,
        status=status,
        output_length=len(output),
        notes="ok" if not notes else "; ".join(notes),
    )


def parse_header(output: str) -> dict[str, str]:
    header: dict[str, str] = {}
    for line in output.splitlines():
        if line == "## Data":
            break
        match = re.match(r"^([a-z_]+):\s*(.*)$", line)
        if match:
            header[match.group(1)] = match.group(2).strip()
    return header


def find_forbidden(output: str) -> list[str]:
    lowered = output.lower()
    return [
        label
        for pattern, label in FORBIDDEN_PATTERNS.items()
        if pattern in lowered
    ]


def find_raw_error_hints(output: str) -> list[str]:
    lowered = output.lower()
    return [hint for hint in RAW_ERROR_HINTS if hint in lowered]


def find_sensitive_value_leaks(output: str) -> list[str]:
    leaked: list[str] = []
    sensitive_names = [
        "TUSHARE_TOKEN",
        "OPENAI_API_KEY",
        "DEEPSEEK_API_KEY",
        "ANTHROPIC_API_KEY",
        "ALPHA_VANTAGE_API_KEY",
    ]
    for name in sensitive_names:
        value = os.getenv(name, "").strip()
        if value and len(value) >= 8 and value in output:
            leaked.append(name)
    return leaked


if __name__ == "__main__":
    raise SystemExit(main())
