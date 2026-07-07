#!/usr/bin/env python3
"""Stage 2 data-source smoke tests.

This script directly calls dataflow functions. It does not call LLMs, agents,
prompts, graph propagation, or multi-agent workflows.
"""

from __future__ import annotations

import csv
import json
import logging
import os
import re
import shutil
import signal
import tempfile
import time
import traceback
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs" / "recovery"
TODAY = "2026-07-07"
START = "2026-06-01"


FAIL_PATTERNS = [
    "error",
    "no data",
    "not found",
    "failed",
    "failure",
    "warning",
    "获取失败",
    "为空",
    "无数据",
    "不可用",
    "查询失败",
    "未上龙虎榜",
    "无历史",
    "无待解禁",
    "no news",
    "no realtime",
    "api error",
]
FAIL_REGEXES = [
    r"\bno\b.*\bdata\b",
    r"\bno\b.*\bfound\b",
]

JUDGMENT_PATTERNS = [
    "bullish",
    "bearish",
    "signal",
    "inflow",
    "outflow",
    "买入",
    "卖出",
    "利好",
    "利空",
    "主力",
    "净流入",
    "净流出",
    "上榜",
]

SOURCE_PATTERNS = ["source", "data source", "来源", "数据源", "东方财富", "同花顺", "新浪", "mootdx", "腾讯", "财联社", "百度"]
FALLBACK_PATTERNS = ["fallback", "备用", "supplement", "新浪备用", "trying sina"]
AS_OF_PATTERNS = ["retrieved", "data retrieved", "as_of", "showtime", "报告日", "trade_date", "retrieved:"]
UNIT_PATTERNS = ["亿元", "亿", "万元", "万", "元", "%", "cny", "100m", "pe", "pb", "eps", "shares"]


class TimeoutError(Exception):
    pass


def _timeout_handler(signum, frame):  # noqa: ARG001
    raise TimeoutError("call timed out")


def with_timeout(seconds: int, fn: Callable[[], Any]) -> Any:
    old = signal.signal(signal.SIGALRM, _timeout_handler)
    signal.alarm(seconds)
    try:
        return fn()
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old)


def text_value(value: Any) -> str:
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, ensure_ascii=False, default=str)
    except TypeError:
        return repr(value)


def first_lines(s: str, max_chars: int = 360) -> str:
    clean = re.sub(r"\s+", " ", s).strip()
    return clean[:max_chars]


def contains_any(s: str, patterns: list[str]) -> bool:
    lower = s.lower()
    return any(p.lower() in lower for p in patterns)


def contains_failure(s: str) -> bool:
    lower = s.lower()
    return contains_any(lower, FAIL_PATTERNS) or any(
        re.search(pattern, lower) for pattern in FAIL_REGEXES
    )


def md_escape(s: Any) -> str:
    text = str(s).replace("\n", "<br>")
    return text.replace("|", "\\|")


@dataclass
class SmokeCall:
    name: str
    func: Callable[..., Any]
    args: tuple[Any, ...]
    kwargs: dict[str, Any]
    purpose: str
    timeout: int = 45


def classify_risk(row: dict[str, Any]) -> str:
    if row["exception"] or row["failure_hint"]:
        return "高" if row["markdown_or_natural"] else "中"
    if row["judgment_terms"]:
        return "高"
    if row["possible_agent_misread"]:
        return "高"
    if not row["exposes_source"] or not row["exposes_unit"]:
        return "中"
    return "低"


def build_calls() -> tuple[list[SmokeCall], list[dict[str, str]]]:
    from tradingagents.dataflows import a_stock
    from tradingagents.dataflows.interface import route_to_vendor
    from tradingagents.dataflows import y_finance
    from tradingagents.dataflows import yfinance_news

    calls = [
        SmokeCall("a_stock.get_stock_data", a_stock.get_stock_data, ("600519", START, TODAY), {}, "主板白马 K 线"),
        SmokeCall("a_stock.get_stock_data", a_stock.get_stock_data, ("688981", START, TODAY), {}, "科创板 K 线"),
        SmokeCall("a_stock.get_stock_data", a_stock.get_stock_data, ("999999", START, TODAY), {}, "错误代码 K 线失败表现"),
        SmokeCall("a_stock.get_indicators", a_stock.get_indicators, ("300750", "rsi", TODAY, 10), {}, "创业板权重技术指标"),
        SmokeCall("a_stock.get_indicators", a_stock.get_indicators, ("999999", "rsi", TODAY, 10), {}, "错误代码技术指标失败表现"),
        SmokeCall("a_stock.get_fundamentals", a_stock.get_fundamentals, ("600519", TODAY), {}, "主板白马基本面"),
        SmokeCall("a_stock.get_fundamentals", a_stock.get_fundamentals, ("999999", TODAY), {}, "错误代码基本面失败表现"),
        SmokeCall("a_stock.get_balance_sheet", a_stock.get_balance_sheet, ("600519", "quarterly", TODAY), {}, "资产负债表"),
        SmokeCall("a_stock.get_cashflow", a_stock.get_cashflow, ("600519", "quarterly", TODAY), {}, "现金流量表"),
        SmokeCall("a_stock.get_income_statement", a_stock.get_income_statement, ("600519", "quarterly", TODAY), {}, "利润表"),
        SmokeCall("a_stock.get_news", a_stock.get_news, ("600519", START, TODAY), {}, "个股新闻"),
        SmokeCall("a_stock.get_news", a_stock.get_news, ("999999", START, TODAY), {}, "错误代码新闻失败表现"),
        SmokeCall("a_stock.get_global_news", a_stock.get_global_news, (TODAY, 7, 5), {}, "宏观/市场新闻"),
        SmokeCall("a_stock.get_insider_transactions", a_stock.get_insider_transactions, ("600519",), {}, "股东研究/F10"),
        SmokeCall("a_stock.get_insider_transactions", a_stock.get_insider_transactions, ("999999",), {}, "错误代码 F10 失败表现"),
        SmokeCall("a_stock.get_profit_forecast", a_stock.get_profit_forecast, ("600519", TODAY), {}, "一致预期"),
        SmokeCall("a_stock.get_hot_stocks", a_stock.get_hot_stocks, (TODAY,), {}, "当日强势股"),
        SmokeCall("a_stock.get_northbound_flow", a_stock.get_northbound_flow, (TODAY, False), {}, "北向资金"),
        SmokeCall("a_stock.get_concept_blocks", a_stock.get_concept_blocks, ("300450",), {}, "创业板制造成长概念"),
        SmokeCall("a_stock.get_concept_blocks", a_stock.get_concept_blocks, ("999999",), {}, "错误代码概念失败表现"),
        SmokeCall("a_stock.get_fund_flow", a_stock.get_fund_flow, ("300750", TODAY, True), {}, "创业板权重资金流"),
        SmokeCall("a_stock.get_fund_flow", a_stock.get_fund_flow, ("999999", TODAY, True), {}, "错误代码资金流失败表现"),
        SmokeCall("a_stock.get_dragon_tiger_board", a_stock.get_dragon_tiger_board, ("300450", TODAY, 30), {}, "龙虎榜"),
        SmokeCall("a_stock.get_lockup_expiry", a_stock.get_lockup_expiry, ("688981", TODAY, 90), {}, "科创板解禁"),
        SmokeCall("a_stock.get_industry_comparison", a_stock.get_industry_comparison, ("000001", TODAY, 10), {}, "深市主板行业横向对比"),
        SmokeCall("interface.route_to_vendor", route_to_vendor, ("get_stock_data", "000001", START, TODAY), {}, "路由层正常返回"),
        SmokeCall("interface.route_to_vendor", route_to_vendor, ("get_news", "999999", START, TODAY), {}, "路由层错误文本是否视为成功"),
        SmokeCall("y_finance.get_YFin_data_online", y_finance.get_YFin_data_online, ("600519.SS", START, TODAY), {}, "Yahoo A 股后缀行情兼容性"),
        SmokeCall("y_finance.get_fundamentals", y_finance.get_fundamentals, ("600519.SS", TODAY), {}, "Yahoo A 股后缀基本面兼容性"),
        SmokeCall("yfinance_news.get_news_yfinance", yfinance_news.get_news_yfinance, ("600519.SS", START, TODAY), {}, "Yahoo A 股新闻兼容性"),
        SmokeCall("yfinance_news.get_global_news_yfinance", yfinance_news.get_global_news_yfinance, (TODAY, 7, 5), {}, "Yahoo 全球新闻"),
    ]

    skipped = [
        {
            "function": "alpha_vantage_stock.get_stock",
            "reason": "需要 ALPHA_VANTAGE_API_KEY；本轮不提交或配置密钥，且该源不适配 A 股主线。",
        },
        {
            "function": "alpha_vantage_indicator.get_indicator",
            "reason": "需要 ALPHA_VANTAGE_API_KEY；本轮不提交或配置密钥，且该源不适配 A 股主线。",
        },
        {
            "function": "alpha_vantage_fundamentals.*",
            "reason": "需要 ALPHA_VANTAGE_API_KEY；返回类型与 A 股主线不同，本轮仅记录为无法直接实测。",
        },
        {
            "function": "alpha_vantage_news.*",
            "reason": "需要 ALPHA_VANTAGE_API_KEY；海外新闻/情绪源，不适配本轮 A 股 smoke 主线。",
        },
        {
            "function": "y_finance.get_balance_sheet/get_cashflow/get_income_statement/get_insider_transactions",
            "reason": "Yahoo 代表性 A 股兼容调用已触发限流；这些函数不是 A 股主线，本轮不继续扩大非主线外部请求。",
        },
        {
            "function": "TradingAgentsGraph._fetch_returns",
            "reason": "实例方法依赖 TradingAgentsGraph 初始化，可能牵涉 LLM/图配置；本轮禁止运行完整投资分析流程。",
        },
        {
            "function": "cli.announcements.fetch_announcements / cli.utils._fetch_openrouter_models",
            "reason": "运维/模型元数据，不进入投研 Agent 上下文；不纳入本轮底层金融数据 smoke。",
        },
    ]
    return calls, skipped


def run_calls(calls: list[SmokeCall]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for i, call in enumerate(calls, 1):
        started = time.time()
        exception = ""
        value: Any = None
        try:
            value = with_timeout(call.timeout, lambda c=call: c.func(*c.args, **c.kwargs))
        except Exception as exc:  # intentionally captures live endpoint failures
            exception = f"{type(exc).__name__}: {exc}"
            value = exception + "\n" + traceback.format_exc(limit=2)
        elapsed = time.time() - started
        text = text_value(value)
        failure_hint = bool(exception) or contains_failure(text)
        markdown_or_natural = isinstance(value, str) and (
            text.lstrip().startswith("#")
            or "\n## " in text
            or "\n### " in text
            or bool(re.search(r"[\u4e00-\u9fff]", text))
            or bool(re.search(r"[A-Za-z]{4,}", text))
        )
        judgment_terms = contains_any(text, JUDGMENT_PATTERNS)
        row = {
            "idx": i,
            "function": call.name,
            "purpose": call.purpose,
            "inputs": json.dumps({"args": call.args, "kwargs": call.kwargs}, ensure_ascii=False, default=str),
            "call_ok": not exception,
            "semantic_success": not failure_hint,
            "exception": exception,
            "return_type": type(value).__name__,
            "return_length": len(text),
            "elapsed_sec": round(elapsed, 2),
            "snippet": first_lines(text),
            "failure_hint": failure_hint,
            "markdown_or_natural": markdown_or_natural,
            "judgment_terms": judgment_terms,
            "exposes_source": contains_any(text, SOURCE_PATTERNS),
            "exposes_fallback": contains_any(text, FALLBACK_PATTERNS),
            "exposes_as_of": contains_any(text, AS_OF_PATTERNS) or bool(re.search(r"20\d{2}-\d{2}-\d{2}", text)),
            "exposes_unit": contains_any(text, UNIT_PATTERNS),
            "possible_agent_misread": failure_hint or judgment_terms or (markdown_or_natural and not contains_any(text, ["error", "no data", "获取失败"])),
            "notes": "",
        }
        row["risk_level"] = classify_risk(row)
        if call.name == "interface.route_to_vendor" and row["call_ok"] and row["failure_hint"]:
            row["notes"] = "路由层未抛异常，但返回内容包含失败提示。"
        elif row["exposes_fallback"]:
            row["notes"] = "返回文本暴露 fallback/supplement 字样。"
        elif row["judgment_terms"]:
            row["notes"] = "返回文本包含判断性词语或信号。"
        elif row["failure_hint"]:
            row["notes"] = "返回文本包含失败/空结果提示。"
        rows.append(row)
        print(f"[{i}/{len(calls)}] {call.name} ok={row['call_ok']} semantic={row['semantic_success']} len={row['return_length']} risk={row['risk_level']}")
    return rows


def write_plan(calls: list[SmokeCall], skipped: list[dict[str, str]]) -> None:
    lines = [
        "# DATA_SOURCE_SMOKE_TEST_PLAN",
        "",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## Guardrails",
        "",
        "- Direct dataflow/tool function calls only.",
        "- No LLM calls.",
        "- No Agent graph propagation.",
        "- No prompt, debate, Quality Gate, endpoint, or business-code edits.",
        "- `TRADINGAGENTS_CACHE_DIR` is redirected to a temporary directory and removed after the run.",
        "- Alpha Vantage functions are not called without `ALPHA_VANTAGE_API_KEY`.",
        "",
        "## Sample Universe",
        "",
        "- `600519` / `600519.SH` 贵州茅台：主板白马。",
        "- `300450` / `300450.SZ` 先导智能：创业板制造成长。",
        "- `300750` / `300750.SZ` 宁德时代：创业板权重。",
        "- `000001` / `000001.SZ` 平安银行：深市主板。",
        "- `688981` / `688981.SH` 中芯国际：科创板。",
        "- `999999`：错误代码失败场景。",
        "",
        "## Planned Calls",
        "",
        "| # | Function | Purpose | Inputs |",
        "|---:|---|---|---|",
    ]
    for i, call in enumerate(calls, 1):
        inputs = json.dumps({"args": call.args, "kwargs": call.kwargs}, ensure_ascii=False, default=str)
        lines.append(f"| {i} | `{call.name}` | {md_escape(call.purpose)} | `{md_escape(inputs)}` |")
    lines.extend(["", "## Not Directly Smoke-Tested", "", "| Function | Reason |", "|---|---|"])
    for item in skipped:
        lines.append(f"| `{item['function']}` | {md_escape(item['reason'])} |")
    (DOCS / "DATA_SOURCE_SMOKE_TEST_PLAN.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_results(rows: list[dict[str, Any]], skipped: list[dict[str, str]]) -> None:
    counts = {
        "total_calls": len(rows),
        "call_ok": sum(1 for r in rows if r["call_ok"]),
        "semantic_success": sum(1 for r in rows if r["semantic_success"]),
        "failure_hint": sum(1 for r in rows if r["failure_hint"]),
        "judgment_terms": sum(1 for r in rows if r["judgment_terms"]),
        "fallback": sum(1 for r in rows if r["exposes_fallback"]),
        "misread": sum(1 for r in rows if r["possible_agent_misread"]),
    }
    lines = [
        "# DATA_SOURCE_SMOKE_TEST_RESULTS",
        "",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## Summary",
        "",
        f"- Calls executed: {counts['total_calls']}",
        f"- No Python exception: {counts['call_ok']}",
        f"- Semantic success, no failure hint: {counts['semantic_success']}",
        f"- Contains failure/empty/error hint: {counts['failure_hint']}",
        f"- Contains judgment/signal terms: {counts['judgment_terms']}",
        f"- Exposes fallback/supplement marker: {counts['fallback']}",
        f"- Possible Agent misread risk: {counts['misread']}",
        f"- Skipped groups: {len(skipped)}",
        "",
        "## Result Matrix",
        "",
        "| # | Function | Inputs | Success | Type | Len | Snippet | Fail hint | Markdown/NL | Judgment | Source | Fallback | As-of/date | Unit | Misread | Risk | Notes |",
        "|---:|---|---|---|---|---:|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        success = "yes" if r["semantic_success"] else "no"
        lines.append(
            "| {idx} | `{function}` | `{inputs}` | {success} | `{return_type}` | {return_length} | {snippet} | {failure_hint} | {markdown_or_natural} | {judgment_terms} | {exposes_source} | {exposes_fallback} | {exposes_as_of} | {exposes_unit} | {possible_agent_misread} | {risk_level} | {notes} |".format(
                idx=r["idx"],
                function=md_escape(r["function"]),
                inputs=md_escape(r["inputs"]),
                success=success,
                return_type=md_escape(r["return_type"]),
                return_length=r["return_length"],
                snippet=md_escape(r["snippet"]),
                failure_hint=r["failure_hint"],
                markdown_or_natural=r["markdown_or_natural"],
                judgment_terms=r["judgment_terms"],
                exposes_source=r["exposes_source"],
                exposes_fallback=r["exposes_fallback"],
                exposes_as_of=r["exposes_as_of"],
                exposes_unit=r["exposes_unit"],
                possible_agent_misread=r["possible_agent_misread"],
                risk_level=r["risk_level"],
                notes=md_escape(r["notes"]),
            )
        )
    (DOCS / "DATA_SOURCE_SMOKE_TEST_RESULTS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_failure_cases(rows: list[dict[str, Any]], skipped: list[dict[str, str]]) -> None:
    failures = [r for r in rows if r["failure_hint"] or r["exception"]]
    route_success_failures = [r for r in failures if r["call_ok"]]
    lines = [
        "# DATA_SOURCE_FAILURE_CASES",
        "",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## Failure-Like Returns",
        "",
        f"- Failure-like rows: {len(failures)}",
        f"- Returned without Python exception but contained failure/empty/error text: {len(route_success_failures)}",
        "",
        "| Function | Inputs | Python exception? | Snippet | Why it matters |",
        "|---|---|---|---|---|",
    ]
    for r in failures:
        why = "错误/空结果以普通返回值进入上游，路由或 Agent 可能视为成功工具结果。" if r["call_ok"] else "调用抛出异常或超时，需要上游显式处理。"
        lines.append(f"| `{md_escape(r['function'])}` | `{md_escape(r['inputs'])}` | {bool(r['exception'])} | {md_escape(r['snippet'])} | {why} |")
    lines.extend(["", "## Unable To Directly Test", "", "| Function | Reason |", "|---|---|"])
    for item in skipped:
        lines.append(f"| `{item['function']}` | {md_escape(item['reason'])} |")
    (DOCS / "DATA_SOURCE_FAILURE_CASES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_misread_risks(rows: list[dict[str, Any]]) -> None:
    risky = [r for r in rows if r["possible_agent_misread"]]
    judgment = [r for r in rows if r["judgment_terms"]]
    hidden_fallback = [r for r in rows if (r["function"] == "interface.route_to_vendor" and r["call_ok"] and r["failure_hint"]) or (r["exposes_fallback"] and r["risk_level"] == "高")]
    lines = [
        "# DATA_SOURCE_AGENT_MISREAD_RISKS",
        "",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## Main Findings",
        "",
        f"- Rows with possible Agent misread risk: {len(risky)}",
        f"- Rows with direct judgment/signal terms: {len(judgment)}",
        f"- Rows demonstrating fallback/routing ambiguity: {len(hidden_fallback)}",
        "",
        "## Direct Judgment Or Signal Terms",
        "",
        "| Function | Snippet | Risk |",
        "|---|---|---|",
    ]
    for r in judgment:
        lines.append(f"| `{md_escape(r['function'])}` | {md_escape(r['snippet'])} | 可能把数据源文本中的 signal/买入/卖出/主力等词当作独立投资结论。 |")
    lines.extend(["", "## Failure Text That Can Look Like Normal Tool Output", "", "| Function | Snippet | Risk |", "|---|---|---|"])
    for r in rows:
        if r["call_ok"] and r["failure_hint"]:
            lines.append(f"| `{md_escape(r['function'])}` | {md_escape(r['snippet'])} | 工具未抛异常，失败状态只存在于自然语言文本中。 |")
    lines.extend(["", "## Fallback Or Scope Ambiguity", "", "| Function | Snippet | Risk |", "|---|---|---|"])
    for r in hidden_fallback:
        lines.append(f"| `{md_escape(r['function'])}` | {md_escape(r['snippet'])} | fallback/路由信息不是结构化字段，Agent 难以区分主源、备源、失败源。 |")
    lines.extend(["", "## Highest Misread-Risk Functions", ""])
    for name in [
        "a_stock.get_fundamentals",
        "a_stock.get_news",
        "a_stock.get_global_news",
        "a_stock.get_insider_transactions",
        "a_stock.get_profit_forecast",
        "a_stock.get_hot_stocks",
        "a_stock.get_northbound_flow",
        "a_stock.get_fund_flow",
        "a_stock.get_industry_comparison",
        "interface.route_to_vendor",
    ]:
        matches = [r for r in rows if r["function"] == name]
        if matches:
            lines.append(f"- `{name}`: " + "; ".join(md_escape(m["notes"] or m["snippet"][:120]) for m in matches[:2]))
    (DOCS / "DATA_SOURCE_AGENT_MISREAD_RISKS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    DOCS.mkdir(parents=True, exist_ok=True)
    cache_dir = tempfile.mkdtemp(prefix="ta_astock_smoke_cache_")
    os.environ["TRADINGAGENTS_CACHE_DIR"] = cache_dir
    os.environ.setdefault("PYTHONWARNINGS", "ignore")
    logging.disable(logging.CRITICAL)

    try:
        from tradingagents.dataflows.config import set_config

        set_config({"data_cache_dir": cache_dir})
        calls, skipped = build_calls()
        write_plan(calls, skipped)
        rows = run_calls(calls)
        write_results(rows, skipped)
        write_failure_cases(rows, skipped)
        write_misread_risks(rows)
        print(json.dumps({
            "calls": len(rows),
            "call_ok": sum(1 for r in rows if r["call_ok"]),
            "semantic_success": sum(1 for r in rows if r["semantic_success"]),
            "failure_hint": sum(1 for r in rows if r["failure_hint"]),
            "judgment_terms": sum(1 for r in rows if r["judgment_terms"]),
            "cache_dir": cache_dir,
        }, ensure_ascii=False))
    finally:
        shutil.rmtree(cache_dir, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
