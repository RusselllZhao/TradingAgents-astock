"""Run a minimal single-stock agent regression for 300450.

This script is intentionally narrow:
- one ticker only: 300450
- one trade date only: 2026-07-07
- minimal analyst set: fundamentals + hot_money
- DeepSeek provider, loaded from the project .env without printing secrets
- runtime outputs under .cache/recovery, which is ignored by git
"""

from __future__ import annotations

import copy
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

TICKER = "300450"
TRADE_DATE = "2026-07-07"
RUN_ID = datetime.now().strftime("%Y%m%d_%H%M%S")
OUTPUT_ROOT = REPO_ROOT / ".cache" / "recovery" / "min_agent_regression_300450" / RUN_ID

FIRST_BATCH_FUNCTIONS = {
    "get_balance_sheet",
    "get_cashflow",
    "get_income_statement",
    "get_fundamentals",
    "get_fund_flow",
    "get_profit_forecast",
}

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

SAFETY_PATTERNS = {
    "html": re.compile(r"<!doctype|<html|</html>|<head|<body", re.IGNORECASE),
    "traceback": re.compile(r"Traceback \(most recent call last\):"),
    "proxy_stack": re.compile(r"ProxyError|HTTPSConnectionPool|RemoteDisconnected|Max retries exceeded"),
    "long_error_text": re.compile(
        r"(Error retrieving|Error fetching|Traceback|HTTPSConnectionPool|ProxyError).{1200,}",
        re.IGNORECASE | re.DOTALL,
    ),
    "bare_no_data": re.compile(r"^No .*data.*found", re.IGNORECASE | re.MULTILINE),
    "bare_error": re.compile(r"^Error (retrieving|fetching|calculating)", re.IGNORECASE | re.MULTILINE),
}


def presence(name: str) -> str:
    return "present" if bool(os.getenv(name)) else "missing"


def load_environment() -> dict[str, str]:
    load_dotenv(dotenv_path=REPO_ROOT / ".env", override=True)
    return {name: presence(name) for name in SENSITIVE_ENV_NAMES}


def install_tool_call_logger() -> list[dict[str, Any]]:
    """Patch tool wrapper modules so route_to_vendor calls are logged."""
    from tradingagents.agents.utils import fundamental_data_tools, signal_data_tools

    calls: list[dict[str, Any]] = []

    def wrap_module(module: Any) -> None:
        original = module.route_to_vendor

        def logged_route_to_vendor(method: str, *args: Any, **kwargs: Any) -> Any:
            started = time.time()
            record = {
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
                record["result_head"] = value[:500] if isinstance(value, str) else repr(type(value))
                return value
            except Exception as exc:
                record["status"] = "exception"
                record["elapsed_seconds"] = round(time.time() - started, 3)
                record["error_type"] = type(exc).__name__
                record["error"] = str(exc)[:500]
                raise
            finally:
                calls.append(record)

        module.route_to_vendor = logged_route_to_vendor

    wrap_module(fundamental_data_tools)
    wrap_module(signal_data_tools)
    return calls


def build_config() -> dict[str, Any]:
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
            "results_dir": str(OUTPUT_ROOT / "graph_results"),
            "data_cache_dir": str(OUTPUT_ROOT / "data_cache"),
            "memory_log_path": str(OUTPUT_ROOT / "memory" / "trading_memory.md"),
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


def scan_text(name: str, text: str, env_status: dict[str, str]) -> dict[str, Any]:
    result: dict[str, Any] = {"name": name, "length": len(text)}
    for key, pattern in SAFETY_PATTERNS.items():
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
    return result


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
    chunks = []
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


def write_outputs(
    final_state: dict[str, Any] | None,
    decision: Any,
    env_status: dict[str, str],
    config: dict[str, Any],
    tool_calls: list[dict[str, Any]],
    started: float,
    error: str | None = None,
) -> dict[str, Any]:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    report_text = collect_report_text(final_state or {})
    if report_text:
        (OUTPUT_ROOT / "agent_report_sections.md").write_text(report_text, encoding="utf-8")

    final_state_summary: dict[str, Any] = {}
    if final_state:
        for key in [
            "company_of_interest",
            "trade_date",
            "market_report",
            "fundamentals_report",
            "hot_money_report",
            "investment_plan",
            "trader_investment_plan",
            "final_trade_decision",
        ]:
            value = final_state.get(key)
            if isinstance(value, str):
                final_state_summary[key] = value[:8000]
            else:
                final_state_summary[key] = value
        for state_key in ["investment_debate_state", "risk_debate_state"]:
            state_value = final_state.get(state_key)
            if isinstance(state_value, dict):
                final_state_summary[state_key] = {
                    key: value[:8000] if isinstance(value, str) else value
                    for key, value in state_value.items()
                }

    safety_scans = []
    if report_text:
        safety_scans.append(scan_text("agent_report_sections.md", report_text, env_status))
    for call in tool_calls:
        head = call.get("result_head")
        if isinstance(head, str):
            safety_scans.append(scan_text(f"tool:{call['method']}", head, env_status))

    invoked = sorted({call["method"] for call in tool_calls})
    first_batch_invoked = sorted(set(invoked) & FIRST_BATCH_FUNCTIONS)

    summary = {
        "run_id": RUN_ID,
        "ticker": TICKER,
        "company": "先导智能",
        "trade_date": TRADE_DATE,
        "started_at": datetime.fromtimestamp(started).isoformat(timespec="seconds"),
        "finished_at": datetime.now().isoformat(timespec="seconds"),
        "duration_seconds": round(time.time() - started, 3),
        "success": bool(final_state) and error is None,
        "error": error,
        "decision_type": type(decision).__name__,
        "decision_text": str(decision)[:1000] if decision is not None else "",
        "env_status": env_status,
        "config": {
            "llm_provider": config["llm_provider"],
            "deep_think_llm": config["deep_think_llm"],
            "quick_think_llm": config["quick_think_llm"],
            "selected_analysts": ["fundamentals", "hot_money"],
            "max_debate_rounds": config["max_debate_rounds"],
            "max_risk_discuss_rounds": config["max_risk_discuss_rounds"],
            "checkpoint_enabled": config["checkpoint_enabled"],
            "output_language": config["output_language"],
            "data_vendors": config["data_vendors"],
            "results_dir": config["results_dir"],
            "data_cache_dir": config["data_cache_dir"],
            "memory_log_path": config["memory_log_path"],
        },
        "output_root": str(OUTPUT_ROOT),
        "tool_calls": tool_calls,
        "invoked_data_functions": invoked,
        "first_batch_invoked": first_batch_invoked,
        "called_tushare": bool(set(first_batch_invoked)),
        "safety_scans": safety_scans,
        "final_state_summary": final_state_summary,
    }
    (OUTPUT_ROOT / "run_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({
        "success": summary["success"],
        "output_root": summary["output_root"],
        "duration_seconds": summary["duration_seconds"],
        "invoked_data_functions": invoked,
        "first_batch_invoked": first_batch_invoked,
        "called_tushare": summary["called_tushare"],
        "error": error,
    }, ensure_ascii=False, indent=2))
    return summary


def main() -> int:
    os.chdir(REPO_ROOT)
    env_status = load_environment()
    if env_status["DEEPSEEK_API_KEY"] != "present":
        print(json.dumps({"success": False, "error": "DEEPSEEK_API_KEY=missing"}, ensure_ascii=False))
        return 2
    if env_status["TUSHARE_TOKEN"] != "present":
        print(json.dumps({"success": False, "error": "TUSHARE_TOKEN=missing"}, ensure_ascii=False))
        return 2

    os.environ.setdefault("TUSHARE_CACHE_DIR", str(OUTPUT_ROOT / "tushare_cache"))
    os.environ.setdefault("TUSHARE_ENABLE_CACHE", "1")

    tool_calls = install_tool_call_logger()
    config = build_config()
    started = time.time()

    try:
        from tradingagents.graph.trading_graph import TradingAgentsGraph

        graph = TradingAgentsGraph(
            selected_analysts=["fundamentals", "hot_money"],
            debug=False,
            config=config,
        )
        final_state, decision = graph.propagate(TICKER, TRADE_DATE)
        write_outputs(final_state, decision, env_status, config, tool_calls, started)
        return 0
    except Exception as exc:
        error = f"{type(exc).__name__}: {str(exc)[:1000]}"
        write_outputs(
            None,
            None,
            env_status,
            config,
            tool_calls,
            started,
            error=error,
        )
        tb = traceback.format_exc(limit=5)
        (OUTPUT_ROOT / "failure_traceback.txt").write_text(tb, encoding="utf-8")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
