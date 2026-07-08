#!/usr/bin/env python3
"""Smoke test for get_hot_stocks data-source contract.

This calls only the bottom-level dataflow function. It does not call LLMs,
agents, graph propagation, prompts, or multi-agent workflows.
"""

from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

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
    "limit_list_ths": "mixed_limit_source",
    "limit_step": "mixed_limit_source",
    "limit_list_d": "mixed_limit_source",
}

EXPECTED_FIELDS = {"trade_date", "ts_code", "rank"}


@dataclass
class SmokeResult:
    passed: bool
    status: str
    output_length: int
    notes: str


def _load_tushare_token_presence_only() -> None:
    """Load local token env if needed, but never print its value."""

    if os.getenv("TUSHARE_TOKEN"):
        return

    for env_path in (ROOT / ".env.local", ROOT / ".env"):
        if not env_path.exists():
            continue
        try:
            for raw_line in env_path.read_text(encoding="utf-8").splitlines():
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                if key.strip() == "TUSHARE_TOKEN" and value.strip():
                    os.environ["TUSHARE_TOKEN"] = value.strip().strip("\"'")
                    return
        except OSError:
            return


def main() -> int:
    _load_tushare_token_presence_only()
    os.environ["TUSHARE_ENABLE_CACHE"] = "0"
    token_status = "present" if os.getenv("TUSHARE_TOKEN", "").strip() else "missing"
    print(f"TUSHARE_TOKEN={token_status}")

    from tradingagents.dataflows.a_stock import get_hot_stocks

    curr_date = date.today().strftime("%Y-%m-%d")
    try:
        output = get_hot_stocks(curr_date)
    except Exception as exc:  # pragma: no cover - defensive smoke boundary
        output = f"uncaught_exception: {type(exc).__name__}"

    result = validate_output(output)
    print(
        f"hot_stocks: {'PASS' if result.passed else 'FAIL'} "
        f"status={result.status or 'missing'} "
        f"len={result.output_length} note={result.notes}"
    )
    print(f"SUMMARY: {1 if result.passed else 0}/1 PASS")
    return 0 if result.passed else 1


def validate_output(output: str) -> SmokeResult:
    notes: list[str] = []
    if not isinstance(output, str):
        return SmokeResult(False, "", 0, "output_not_string")

    if "# Data Source Contract" not in output:
        notes.append("missing_contract_header")

    header = parse_header(output)
    missing = sorted(REQUIRED_HEADER_KEYS - set(header))
    if missing:
        notes.append("missing_header_keys=" + ",".join(missing))

    status = header.get("status", "")
    if status not in VALID_STATUSES:
        notes.append(f"bad_status={status or 'missing'}")

    if header.get("source") != "Tushare ths_hot":
        notes.append(f"bad_source={header.get('source', 'missing')}")
    if header.get("data_type") != "hot_stocks":
        notes.append(f"bad_data_type={header.get('data_type', 'missing')}")
    if header.get("query_target") != "market":
        notes.append(f"bad_query_target={header.get('query_target', 'missing')}")
    if header.get("coverage") != "market_wide":
        notes.append(f"bad_coverage={header.get('coverage', 'missing')}")
    if header.get("symbol") != "N/A":
        notes.append(f"bad_symbol={header.get('symbol', 'missing')}")
    if header.get("fallback") != "none":
        notes.append(f"bad_fallback={header.get('fallback', 'missing')}")

    raw_error_suppressed = header.get("raw_error_suppressed", "")
    if status == "technical_error":
        if raw_error_suppressed != "true":
            notes.append("technical_error_without_raw_suppression")
        if len(output) > 2500:
            notes.append("technical_error_too_long")
        if "Data source request failed; raw technical details suppressed." not in output:
            notes.append("missing_short_technical_error_message")
    else:
        if raw_error_suppressed != "false":
            notes.append("non_error_raw_suppression_not_false")

    if status == "ok":
        missing_fields = [field for field in EXPECTED_FIELDS if field not in output]
        if missing_fields:
            notes.append("missing_ths_hot_fields=" + ",".join(missing_fields))
    elif status == "empty":
        if not header.get("empty_reason") or header.get("empty_reason") == "none":
            notes.append("empty_without_empty_reason")

    forbidden = find_forbidden(output)
    if forbidden:
        notes.append("forbidden_output=" + ",".join(forbidden))

    leaked = find_sensitive_value_leaks(output)
    if leaked:
        notes.append("sensitive_value_leak=" + ",".join(leaked))

    return SmokeResult(
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
