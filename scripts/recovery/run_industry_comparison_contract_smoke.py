#!/usr/bin/env python3
"""Smoke test for get_industry_comparison string contract.

This calls only the bottom-level dataflow function. It does not call LLMs,
agents, graph propagation, prompts, or multi-agent workflows.
"""

from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

TRADE_DATE = "2026-07-08"
CASES = ("300450", "600519", "688981")

FORBIDDEN_PATTERNS = {
    "<html": "html",
    "<!doctype": "html",
    "traceback": "traceback",
    "httpsconnectionpool": "raw_network_stack",
    "proxyerror": "proxy_stack",
    "proxy stack": "proxy_stack",
    "raw exception": "raw_exception",
    "反爬": "anti_scraping_text",
}

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

VALID_STATUSES = {"ok", "empty", "technical_error"}


@dataclass
class SmokeResult:
    ticker: str
    passed: bool
    status: str
    output_length: int
    notes: str


def main() -> int:
    from tradingagents.dataflows.a_stock import get_industry_comparison

    results: list[SmokeResult] = []
    for ticker in CASES:
        try:
            output = get_industry_comparison(ticker, TRADE_DATE, top_n=10)
        except Exception as exc:  # pragma: no cover - defensive smoke boundary
            output = f"uncaught_exception: {type(exc).__name__}"
        result = validate_output(ticker, output)
        results.append(result)
        print(
            f"{ticker}: {'PASS' if result.passed else 'FAIL'} "
            f"status={result.status or 'missing'} "
            f"len={result.output_length} note={result.notes}"
        )

    return 0 if all(result.passed for result in results) else 1


def validate_output(ticker: str, output: str) -> SmokeResult:
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

    if header.get("data_type") != "industry_ranking":
        notes.append(f"bad_data_type={header.get('data_type', 'missing')}")
    if header.get("query_target") != "market":
        notes.append(f"bad_query_target={header.get('query_target', 'missing')}")
    if header.get("coverage") != "market_wide":
        notes.append(f"bad_coverage={header.get('coverage', 'missing')}")
    if header.get("symbol") != ticker:
        notes.append(f"bad_symbol={header.get('symbol', 'missing')}")

    raw_error_suppressed = header.get("raw_error_suppressed", "")
    if status == "technical_error":
        if raw_error_suppressed != "true":
            notes.append("technical_error_without_raw_suppression")
        if len(output) > 3000:
            notes.append("technical_error_too_long")
        if "Data source request failed; raw technical details suppressed." not in output:
            notes.append("missing_short_technical_error_message")
    elif raw_error_suppressed != "false":
        notes.append("non_error_raw_suppression_not_false")

    if status == "empty" and header.get("empty_reason") != "source_empty":
        notes.append(f"bad_empty_reason={header.get('empty_reason', 'missing')}")

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
