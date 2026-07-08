"""Run second-batch minimal Agent regression for selected A-share tickers.

Scope is intentionally narrow:
- tickers: 300450, 600519, 688981
- trade date: 2026-07-07, matching the prior 300450 minimal regression
- analysts: fundamentals + hot_money
- LLM provider: DeepSeek, loaded from project .env without printing secrets
- raw runtime outputs: .cache/recovery/second_batch_min_agent_regression/<run_id>
- committed output: docs/recovery/SECOND_BATCH_MIN_AGENT_REGRESSION_RESULT.csv
"""

from __future__ import annotations

import copy
import csv
import json
import os
import re
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

TRADE_DATE = "2026-07-07"
TICKERS = [
    ("300450", "先导智能"),
    ("600519", "贵州茅台"),
    ("688981", "中芯国际"),
]
SELECTED_ANALYSTS = ["fundamentals", "hot_money"]
RUN_ID = datetime.now().strftime("%Y%m%d_%H%M%S")
OUTPUT_ROOT = REPO_ROOT / ".cache" / "recovery" / "second_batch_min_agent_regression" / RUN_ID
CSV_PATH = REPO_ROOT / "docs" / "recovery" / "SECOND_BATCH_MIN_AGENT_REGRESSION_RESULT.csv"
_ACTIVE_TOOL_CALLS: list[dict[str, Any]] | None = None

SENSITIVE_ENV_NAMES = [
    "TUSHARE_TOKEN",
    "DEEPSEEK_API_KEY",
    "MINIMAX_API_KEY",
    "DASHSCOPE_API_KEY",
    "ZHIPU_API_KEY",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_AUTH_TOKEN",
    "GOOGLE_API_KEY",
    "GEMINI_API_KEY",
    "XAI_API_KEY",
    "OPENROUTER_API_KEY",
]

SECOND_BATCH_FUNCTIONS = {
    "get_industry_comparison",
    "get_northbound_flow",
    "get_concept_blocks",
    "get_hot_stocks",
    "get_dragon_tiger_board",
    "get_insider_transactions",
    "get_global_news",
    "get_news",
}

TUSHARE_BACKED_FUNCTIONS = {
    "get_balance_sheet",
    "get_cashflow",
    "get_income_statement",
    "get_fundamentals",
    "get_fund_flow",
    "get_profit_forecast",
    "get_northbound_flow",
    "get_concept_blocks",
    "get_hot_stocks",
    "get_dragon_tiger_board",
    "get_insider_transactions",
    "get_global_news",
}

POLLUTION_PATTERNS = {
    "html": re.compile(r"<!doctype|<html|</html>|<head|<body", re.IGNORECASE),
    "traceback": re.compile(r"Traceback \(most recent call last\):|\btraceback\b", re.IGNORECASE),
    "proxy_stack": re.compile(r"ProxyError|HTTPSConnectionPool|RemoteDisconnected|Max retries exceeded|proxy stack", re.IGNORECASE),
    "raw_exception": re.compile(r"raw exception|Unhandled exception|Exception:", re.IGNORECASE),
    "anti_scraping": re.compile(r"anti-scraping|反爬", re.IGNORECASE),
    "read_html": re.compile(r"read_html", re.IGNORECASE),
    "bare_no_data": re.compile(r"^No data found\\.?$", re.IGNORECASE | re.MULTILINE),
    "long_error_text": re.compile(
        r"(Error retrieving|Error fetching|Traceback|HTTPSConnectionPool|ProxyError).{1200,}",
        re.IGNORECASE | re.DOTALL,
    ),
}

FORBIDDEN_TERM_PATTERNS = {
    "english_bullish_bearish_term": re.compile(r"\b(bullish|bearish)\b", re.IGNORECASE),
    "evidence_grade_terms": re.compile(
        r"evidence grade|strong evidence|weak evidence|first-hand fact|second-hand information|weak signal",
        re.IGNORECASE,
    ),
    "confidence": re.compile(r"\bconfidence\b", re.IGNORECASE),
    "conclusion_level": re.compile(r"\bconclusion_level\b", re.IGNORECASE),
}

CONTRACT_STATUS_PATTERN = re.compile(
    r"status:\s*(ok|empty|no_event|no_coverage|partial_data|stale_data|technical_error|unsupported|invalid_input)"
)


def presence(name: str) -> str:
    return "present" if bool(os.getenv(name)) else "missing"


def load_environment() -> dict[str, str]:
    load_dotenv(dotenv_path=REPO_ROOT / ".env", override=True)
    return {name: presence(name) for name in SENSITIVE_ENV_NAMES}


def build_config(ticker_output_root: Path) -> dict[str, Any]:
    from tradingagents.default_config import DEFAULT_CONFIG

    config = copy.deepcopy(DEFAULT_CONFIG)
    config.update(
        {
            "llm_provider": "deepseek",
            "deep_think_llm": "deepseek-chat",
            "quick_think_llm": "deepseek-chat",
            "output_language": "Chinese",
            "max_debate_rounds": 1,
            "max_risk_discuss_rounds": 0,
            "checkpoint_enabled": False,
            "results_dir": str(ticker_output_root / "graph_results"),
            "data_cache_dir": str(ticker_output_root / "data_cache"),
            "memory_log_path": str(ticker_output_root / "memory" / "trading_memory.md"),
            "memory_log_max_entries": 10,
            "data_vendors": {
                "core_stock_apis": "a_stock",
                "technical_indicators": "a_stock",
                "fundamental_data": "a_stock",
                "news_data": "a_stock",
                "signal_data": "a_stock",
            },
            "tool_vendors": {},
        }
    )
    return config


def install_tool_call_logger(calls: list[dict[str, Any]]) -> None:
    """Patch route_to_vendor in the tool wrapper modules once per process."""
    from tradingagents.agents.utils import fundamental_data_tools, signal_data_tools

    global _ACTIVE_TOOL_CALLS
    _ACTIVE_TOOL_CALLS = calls

    def wrap_module(module: Any) -> None:
        if getattr(module.route_to_vendor, "_second_batch_logged", False):
            return
        original = module.route_to_vendor

        def logged_route_to_vendor(method: str, *args: Any, **kwargs: Any) -> Any:
            started = time.time()
            record: dict[str, Any] = {
                "method": method,
                "args": [str(arg) for arg in args],
                "kwargs": {key: str(value) for key, value in kwargs.items()},
                "status": "started",
            }
            try:
                value = original(method, *args, **kwargs)
                record["status"] = "ok"
                record["elapsed_seconds"] = round(time.time() - started, 3)
                record["result_length"] = len(value) if isinstance(value, str) else None
                record["result_head"] = value[:2500] if isinstance(value, str) else repr(type(value))
                record["contract_status_values"] = (
                    sorted(set(CONTRACT_STATUS_PATTERN.findall(value)))
                    if isinstance(value, str)
                    else []
                )
                return value
            except Exception as exc:
                record["status"] = "exception"
                record["elapsed_seconds"] = round(time.time() - started, 3)
                record["error_type"] = type(exc).__name__
                record["error"] = str(exc)[:500]
                raise
            finally:
                if _ACTIVE_TOOL_CALLS is not None:
                    _ACTIVE_TOOL_CALLS.append(record)

        logged_route_to_vendor._second_batch_logged = True  # type: ignore[attr-defined]
        module.route_to_vendor = logged_route_to_vendor

    wrap_module(fundamental_data_tools)
    wrap_module(signal_data_tools)


def collect_report_text(final_state: dict[str, Any]) -> str:
    fields = [
        "market_report",
        "sentiment_report",
        "news_report",
        "fundamentals_report",
        "policy_report",
        "hot_money_report",
        "lockup_report",
        "investment_plan",
        "trader_investment_plan",
        "final_trade_decision",
    ]
    chunks: list[str] = []
    for field in fields:
        value = final_state.get(field)
        if value:
            chunks.append(f"\n\n## {field}\n\n{value}")

    debate = final_state.get("investment_debate_state") or {}
    for field in ["bull_history", "bear_history", "judge_decision"]:
        value = debate.get(field)
        if value:
            chunks.append(f"\n\n## investment_debate_state.{field}\n\n{value}")

    risk = final_state.get("risk_debate_state") or {}
    for field in ["aggressive_history", "conservative_history", "neutral_history", "judge_decision"]:
        value = risk.get(field)
        if value:
            chunks.append(f"\n\n## risk_debate_state.{field}\n\n{value}")
    return "".join(chunks).strip()


def scan_text(name: str, text: str, env_status: dict[str, str]) -> dict[str, Any]:
    result: dict[str, Any] = {"name": name, "length": len(text)}
    for key, pattern in POLLUTION_PATTERNS.items():
        result[key] = bool(pattern.search(text))
    for key, pattern in FORBIDDEN_TERM_PATTERNS.items():
        result[key] = bool(pattern.search(text))

    token_leak = False
    for env_name, status in env_status.items():
        if status != "present":
            continue
        value = os.getenv(env_name)
        if value and len(value) >= 8 and value in text:
            token_leak = True
            break
    result["token_or_key_value"] = token_leak
    result["status_values"] = sorted(set(CONTRACT_STATUS_PATTERN.findall(text)))
    return result


def scan_contract_consumption(report_text: str) -> dict[str, bool]:
    lower = report_text.lower()
    return {
        "technical_error_as_fact_marker": "technical_error" in lower or "status: technical_error" in lower,
        "no_event_as_investment_marker": "no_event" in lower or "未上龙虎榜" in report_text,
        "industry_ranking_peer_confusion_marker": (
            "industry_ranking" in lower
            or "market_wide" in lower
            or ("行业同业对比" in report_text and "行业排名" not in report_text)
        ),
        "global_news_as_stock_news_marker": "global_news" in lower,
        "shareholder_f10_as_us_insider_marker": (
            "shareholder_f10" in lower
            or "us-style insider" in lower
            or "insider transaction" in lower
        ),
        "market_flow_as_stock_holding_marker": "个股北向持股" in report_text,
        "generic_news_marker": "major_news" in lower,
    }


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def run_one_ticker(ticker: str, company: str, env_status: dict[str, str]) -> dict[str, Any]:
    from tradingagents.graph.trading_graph import TradingAgentsGraph

    ticker_root = OUTPUT_ROOT / ticker
    ticker_root.mkdir(parents=True, exist_ok=True)
    os.environ["TUSHARE_CACHE_DIR"] = str(ticker_root / "tushare_cache")
    os.environ["TUSHARE_ENABLE_CACHE"] = "1"

    calls: list[dict[str, Any]] = []
    install_tool_call_logger(calls)
    config = build_config(ticker_root)
    started = time.time()
    final_state: dict[str, Any] | None = None
    decision: Any = None
    error: str | None = None

    try:
        graph = TradingAgentsGraph(
            selected_analysts=SELECTED_ANALYSTS,
            debug=False,
            config=config,
        )
        final_state, decision = graph.propagate(ticker, TRADE_DATE)
    except Exception as exc:
        error = f"{type(exc).__name__}: {str(exc)[:1000]}"
        (ticker_root / "failure_traceback.txt").write_text(
            traceback.format_exc(limit=8),
            encoding="utf-8",
        )

    report_text = collect_report_text(final_state or {})
    report_path = ""
    if report_text:
        report_file = ticker_root / "agent_report_sections.md"
        report_file.write_text(report_text, encoding="utf-8")
        report_path = str(report_file.relative_to(REPO_ROOT))

    safety_scans: list[dict[str, Any]] = []
    if report_text:
        safety_scans.append(scan_text("agent_report_sections.md", report_text, env_status))
    for call in calls:
        head = call.get("result_head")
        if isinstance(head, str):
            safety_scans.append(scan_text(f"tool:{call['method']}", head, env_status))

    invoked = sorted({str(call.get("method", "")) for call in calls if call.get("method")})
    status_values = sorted({
        status
        for call in calls
        for status in call.get("contract_status_values", [])
    })
    pollution_flags = sorted({
        key
        for scan in safety_scans
        for key, value in scan.items()
        if key not in {"name", "length", "status_values"} and value is True
    })
    consumption_flags = scan_contract_consumption(report_text)
    consumption_risk_flags = sorted([key for key, value in consumption_flags.items() if value])

    success = bool(final_state) and error is None
    summary = {
        "run_id": RUN_ID,
        "ticker": ticker,
        "company": company,
        "trade_date": TRADE_DATE,
        "run_status": "passed" if success else "failed",
        "success": success,
        "error": error,
        "started_at": datetime.fromtimestamp(started).isoformat(timespec="seconds"),
        "finished_at": datetime.now().isoformat(timespec="seconds"),
        "elapsed_seconds": round(time.time() - started, 3),
        "llm_used": "yes",
        "llm_provider": "deepseek",
        "tushare_used": "yes" if set(invoked) & TUSHARE_BACKED_FUNCTIONS else "not_observed",
        "selected_analysts": SELECTED_ANALYSTS,
        "max_debate_rounds": config["max_debate_rounds"],
        "max_risk_discuss_rounds": config["max_risk_discuss_rounds"],
        "tool_calls_count": len(calls),
        "called_tool_names": invoked,
        "second_batch_tools_called": sorted(set(invoked) & SECOND_BATCH_FUNCTIONS),
        "contract_status_values_observed": status_values,
        "pollution_flags": pollution_flags,
        "contamination_scan_result": "clean" if not pollution_flags else "flagged",
        "contract_consumption_flags": consumption_risk_flags,
        "contract_consumption_scan_result": "clean" if not consumption_risk_flags else "needs_manual_review",
        "final_report_path": report_path,
        "runtime_output_root": str(ticker_root.relative_to(REPO_ROOT)),
        "decision_type": type(decision).__name__,
        "decision_text_head": str(decision)[:1000] if decision is not None else "",
        "env_status": env_status,
        "safety_scans": safety_scans,
        "tool_calls": calls,
    }
    write_json(ticker_root / "run_summary.json", summary)
    print(json.dumps({
        "ticker": ticker,
        "success": success,
        "elapsed_seconds": summary["elapsed_seconds"],
        "tool_calls_count": len(calls),
        "called_tool_names": invoked,
        "status_values": status_values,
        "contamination_scan_result": summary["contamination_scan_result"],
        "contract_consumption_scan_result": summary["contract_consumption_scan_result"],
        "error": error,
    }, ensure_ascii=False))
    return summary


def write_csv(summaries: list[dict[str, Any]]) -> None:
    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "ticker",
        "company",
        "run_status",
        "elapsed_seconds",
        "llm_used",
        "llm_provider",
        "tushare_used",
        "selected_analysts",
        "tool_calls_count",
        "called_tool_names",
        "second_batch_tools_called",
        "contract_status_values_observed",
        "final_report_path",
        "contamination_scan_result",
        "pollution_flags",
        "contract_consumption_scan_result",
        "contract_consumption_flags",
        "runtime_output_root",
        "error",
    ]
    with CSV_PATH.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for summary in summaries:
            row: dict[str, str] = {}
            for field in fields:
                value = summary.get(field)
                if isinstance(value, (list, dict)):
                    row[field] = json.dumps(value, ensure_ascii=False)
                elif value is None:
                    row[field] = ""
                else:
                    row[field] = str(value)
            writer.writerow(row)


def main() -> int:
    os.chdir(REPO_ROOT)
    env_status = load_environment()
    precheck = {
        "run_id": RUN_ID,
        "trade_date": TRADE_DATE,
        "tickers": TICKERS,
        "selected_analysts": SELECTED_ANALYSTS,
        "TUSHARE_TOKEN": env_status["TUSHARE_TOKEN"],
        "DEEPSEEK_API_KEY": env_status["DEEPSEEK_API_KEY"],
        "output_root": str(OUTPUT_ROOT.relative_to(REPO_ROOT)),
        "csv_path": str(CSV_PATH.relative_to(REPO_ROOT)),
    }
    write_json(OUTPUT_ROOT / "precheck.json", precheck)
    print(json.dumps(precheck, ensure_ascii=False))

    if env_status["DEEPSEEK_API_KEY"] != "present":
        print(json.dumps({"success": False, "error": "DEEPSEEK_API_KEY=missing"}, ensure_ascii=False))
        return 2
    if env_status["TUSHARE_TOKEN"] != "present":
        print(json.dumps({"success": False, "error": "TUSHARE_TOKEN=missing"}, ensure_ascii=False))
        return 2

    summaries: list[dict[str, Any]] = []
    for ticker, company in TICKERS:
        summaries.append(run_one_ticker(ticker, company, env_status))
    write_csv(summaries)
    write_json(OUTPUT_ROOT / "combined_summary.json", summaries)
    return 0 if all(summary["success"] for summary in summaries) else 1


if __name__ == "__main__":
    raise SystemExit(main())
