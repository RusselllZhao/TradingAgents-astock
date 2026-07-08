#!/usr/bin/env python3
"""Probe Tushare Pro interfaces related to second-batch data-source recovery.

This script writes only a compact review matrix. It does not persist raw API
responses, does not print token values, and disables the local Tushare cache.
"""

from __future__ import annotations

import csv
import os
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[2]
OUT_CSV = ROOT / "docs/recovery/SECOND_BATCH_TUSHARE_8000_API_MATRIX.csv"
TEST_SYMBOLS = ("300450.SZ", "600519.SH", "688981.SH")

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tradingagents.dataflows.tushare_client import (  # noqa: E402
    TushareClient,
    TushareClientConfig,
)


@dataclass(frozen=True)
class ProbeSpec:
    api: str
    required_points: str
    cases: tuple[Mapping[str, Any], ...]
    fields: str
    semantic_fit: str
    coverage_fit: str
    notes: str
    stop_after_rows: bool = False


def _load_tushare_token_presence_only() -> None:
    """Load TUSHARE_TOKEN from local env files if needed, without printing it."""

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


def _yyyymmdd(d: date) -> str:
    return d.strftime("%Y%m%d")


def _recent_weekdays(days: int = 14) -> tuple[str, ...]:
    today = date.today()
    values: list[str] = []
    cursor = today
    while len(values) < days:
        if cursor.weekday() < 5:
            values.append(_yyyymmdd(cursor))
        cursor -= timedelta(days=1)
    return tuple(values)


def _dt_text(d: str, end: bool = False) -> str:
    parsed = datetime.strptime(d, "%Y%m%d")
    suffix = "23:59:59" if end else "00:00:00"
    return f"{parsed:%Y-%m-%d} {suffix}"


def _date_range(days: int) -> tuple[str, str]:
    end = date.today()
    start = end - timedelta(days=days)
    return _yyyymmdd(start), _yyyymmdd(end)


def _case_symbols(cases: tuple[Mapping[str, Any], ...]) -> str:
    symbols = sorted({
        str(case.get("ts_code") or case.get("con_code") or "")
        for case in cases
        if case.get("ts_code") or case.get("con_code")
    })
    return ";".join(symbols) if symbols else "N/A"


def _case_dates(cases: tuple[Mapping[str, Any], ...]) -> str:
    dates = []
    for case in cases:
        for key in ("trade_date", "date", "start_date", "end_date"):
            value = case.get(key)
            if value:
                dates.append(str(value))
    unique = list(dict.fromkeys(dates))
    if len(unique) > 8:
        return ";".join(unique[:8]) + f";...(+{len(unique) - 8})"
    return ";".join(unique) if unique else "N/A"


def _row_count(data: Any) -> int:
    if not isinstance(data, Mapping):
        return 0
    items = data.get("items")
    if isinstance(items, list):
        return len(items)
    return 0


def _key_fields(data: Any) -> str:
    if not isinstance(data, Mapping):
        return ""
    fields = data.get("fields")
    if not isinstance(fields, list):
        return ""
    return ";".join(str(field) for field in fields[:12])


def _permission_status(ok_count: int, empty_count: int, errors: list[str]) -> str:
    if ok_count > 0:
        return "available"
    if any(err == "tushare_permission_denied" for err in errors):
        return "no_permission"
    if empty_count > 0 and not errors:
        return "empty"
    if errors:
        return "error"
    return "unknown"


def _run_spec(client: TushareClient, spec: ProbeSpec) -> dict[str, str]:
    total_rows = 0
    key_fields = ""
    ok_count = 0
    empty_count = 0
    errors: list[str] = []
    case_count = 0

    for params in spec.cases:
        case_count += 1
        try:
            response = client.call_api(
                spec.api,
                params=params,
                fields=spec.fields,
                use_cache=False,
            )
        except Exception:
            errors.append("unexpected_probe_error")
            continue

        if response.ok:
            rows = _row_count(response.data)
            total_rows += rows
            if not key_fields:
                key_fields = _key_fields(response.data)
            if rows > 0:
                ok_count += 1
                if spec.stop_after_rows:
                    break
            else:
                empty_count += 1
        else:
            errors.append(response.error or "unknown")

    status = _permission_status(ok_count, empty_count, errors)
    if status == "available":
        stability = f"available; {total_rows} compact rows across {case_count} call(s)"
    elif status == "empty":
        stability = f"permission path callable but returned empty across {case_count} call(s)"
    else:
        unique_errors = ",".join(sorted(set(errors))) or "unknown"
        stability = f"safe short error classification: {unique_errors}"

    return {
        "interface_name": spec.api,
        "required_points": spec.required_points,
        "permission_status": status,
        "tested_symbols": _case_symbols(spec.cases),
        "tested_dates": _case_dates(spec.cases),
        "returned_rows": str(total_rows),
        "key_fields": key_fields or "N/A",
        "semantic_fit": spec.semantic_fit,
        "coverage_fit": spec.coverage_fit,
        "stability_observation": stability,
        "notes": spec.notes,
    }


def _build_specs() -> list[ProbeSpec]:
    recent_dates = _recent_weekdays()
    last_trade_date = recent_dates[0]
    start_30, end_today = _date_range(30)
    start_90, _ = _date_range(90)
    start_365, _ = _date_range(365)

    symbol_cases = tuple({"ts_code": symbol, "is_new": "Y"} for symbol in TEST_SYMBOLS)
    symbol_date_cases = tuple({"ts_code": symbol, "start_date": start_30, "end_date": end_today} for symbol in TEST_SYMBOLS)
    recent_trade_cases = tuple({"trade_date": d} for d in recent_dates)

    return [
        ProbeSpec(
            "index_classify",
            "2000",
            ({"src": "SW2021", "level": "L1"}, {"src": "SW2021", "level": "L2"}),
            "index_code,industry_name,parent_code,level,industry_code,is_pub,src",
            "partial_match",
            "broad",
            "SW industry taxonomy; supports industry naming but not peer metrics by itself.",
        ),
        ProbeSpec(
            "index_member_all",
            "2000",
            symbol_cases,
            "l1_code,l1_name,l2_code,l2_name,l3_code,l3_name,ts_code,name,in_date,out_date,is_new",
            "exact_match",
            "broad",
            "Can resolve symbol to SW industry hierarchy; useful for true industry-comparison upgrade.",
        ),
        ProbeSpec(
            "ci_index_member",
            "5000",
            symbol_cases,
            "l1_code,l1_name,l2_code,l2_name,l3_code,l3_name,ts_code,name,in_date,out_date,is_new",
            "partial_match",
            "broad",
            "CITIC industry membership; supplemental industry mapping.",
        ),
        ProbeSpec(
            "ths_index",
            "6000",
            ({"exchange": "A", "type": "I"}, {"exchange": "A", "type": "N"}),
            "ts_code,name,count,exchange,list_date,type",
            "partial_match",
            "broad",
            "THS industry/concept index list; can support sector/concept catalog.",
        ),
        ProbeSpec(
            "ths_member",
            "6000",
            tuple({"con_code": symbol} for symbol in TEST_SYMBOLS),
            "ts_code,con_code,con_name,weight,in_date,out_date,is_new",
            "partial_match",
            "partial",
            "THS concept/industry membership by component stock, if permission and data are available.",
        ),
        ProbeSpec(
            "dc_concept_cons",
            "6000",
            tuple({"ts_code": symbol, "start_date": start_30, "end_date": end_today} for symbol in TEST_SYMBOLS),
            "ts_code,trade_date,name,theme_code,industry_code,industry,reason,hot_num",
            "exact_match",
            "broad",
            "Daily Eastmoney concept membership by stock; candidate replacement for concept blocks.",
        ),
        ProbeSpec(
            "dc_index",
            "6000",
            recent_trade_cases,
            "ts_code,trade_date,name,leading,leading_code,pct_change,leading_pct",
            "partial_match",
            "market_wide",
            "Daily concept board performance; supplemental to concept membership.",
            stop_after_rows=True,
        ),
        ProbeSpec(
            "news",
            "unclear",
            ({"src": "sina", "start_date": _dt_text(last_trade_date), "end_date": _dt_text(last_trade_date, end=True)},),
            "datetime,title,content,channels",
            "partial_match",
            "market_wide",
            "News wire by source/time; not symbol-specific in this probe.",
        ),
        ProbeSpec(
            "major_news",
            "unclear",
            ({"start_date": _dt_text(last_trade_date), "end_date": _dt_text(last_trade_date, end=True)},),
            "title,pub_time,src",
            "partial_match",
            "market_wide",
            "Long-form news feed; suitable for global/market news, not company news replacement alone.",
        ),
        ProbeSpec(
            "anns_d",
            "unclear",
            tuple({"ts_code": symbol, "start_date": start_90, "end_date": end_today} for symbol in TEST_SYMBOLS),
            "ann_date,ts_code,name,title,url,rec_time",
            "partial_match",
            "broad",
            "Company announcements; should not be treated as ordinary news without data_type correction.",
        ),
        ProbeSpec(
            "cctv_news",
            "unclear",
            ({"date": last_trade_date},),
            "date,title,content",
            "partial_match",
            "market_wide",
            "Macro/news text; only a global-news supplement.",
        ),
        ProbeSpec(
            "moneyflow_hsgt",
            "2000",
            ({"start_date": start_30, "end_date": end_today},),
            "trade_date,hgt,sgt,north_money,south_money",
            "exact_match",
            "market_wide",
            "Daily northbound/southbound flow; market-level fit.",
        ),
        ProbeSpec(
            "hsgt_top10",
            "unclear",
            tuple({"ts_code": symbol, "start_date": start_30, "end_date": end_today} for symbol in TEST_SYMBOLS),
            "trade_date,ts_code,name,rank,market_type,amount,net_amount,buy,sell",
            "partial_match",
            "partial",
            "Stock-connect top turnover list; only partial stock-level northbound context.",
        ),
        ProbeSpec(
            "hk_hold",
            "120",
            symbol_date_cases,
            "code,trade_date,ts_code,name,vol,ratio,exchange",
            "partial_match",
            "broad",
            "Stock-connect holding detail; holdings are not the same as same-day flow.",
        ),
        ProbeSpec(
            "limit_list_d",
            "5000",
            recent_trade_cases,
            "trade_date,ts_code,industry,name,close,pct_chg,amount,limit_amount,fd_amount,first_time,last_time,open_times,limit_type",
            "partial_match",
            "market_wide",
            "Limit-up/down list; supplement for hot stocks but lacks THS editorial hot reason.",
            stop_after_rows=True,
        ),
        ProbeSpec(
            "ths_hot",
            "6000",
            tuple({"trade_date": d, "market": "热股", "is_new": "Y"} for d in recent_dates),
            "trade_date,data_type,ts_code,ts_name,rank,pct_change,current_price,concept,rank_reason",
            "exact_match",
            "market_wide",
            "THS hot ranking; closest Tushare fit for get_hot_stocks if available.",
            stop_after_rows=True,
        ),
        ProbeSpec(
            "limit_list_ths",
            "8000",
            tuple({"trade_date": d, "limit_type": "涨停池", "market": "HS"} for d in recent_dates),
            "trade_date,ts_code,name,price,pct_chg,open_num,lu_desc,limit_type,industry",
            "partial_match",
            "market_wide",
            "8000-point THS limit-up pool with reason text; supplement/replacement candidate for hot stocks.",
            stop_after_rows=True,
        ),
        ProbeSpec(
            "limit_step",
            "8000",
            ({"start_date": start_30, "end_date": end_today},),
            "ts_code,name,trade_date,nums",
            "partial_match",
            "market_wide",
            "Consecutive limit-up ladder; supplement for market heat/hot-stock route.",
        ),
        ProbeSpec(
            "top_list",
            "2000",
            tuple({"trade_date": d} for d in recent_dates),
            "trade_date,ts_code,name,close,pct_change,turnover_rate,amount,l_sell,l_buy,l_amount,net_amount,reason",
            "exact_match",
            "event_lookup",
            "Dragon-tiger daily list; exact event source, symbol filtering can be applied later.",
            stop_after_rows=True,
        ),
        ProbeSpec(
            "top_inst",
            "5000",
            tuple({"trade_date": d} for d in recent_dates),
            "trade_date,ts_code,exalter,side,buy,buy_rate,sell,sell_rate,net_buy",
            "partial_match",
            "event_lookup",
            "Institution/seat detail; supplement for dragon-tiger board when top_list has events.",
            stop_after_rows=True,
        ),
        ProbeSpec(
            "stk_holdernumber",
            "600",
            tuple({"ts_code": symbol, "start_date": start_365, "end_date": end_today} for symbol in TEST_SYMBOLS),
            "ts_code,ann_date,end_date,holder_num",
            "partial_match",
            "broad",
            "Shareholder count; fits shareholder_f10 but not US-style insider transactions.",
        ),
        ProbeSpec(
            "stk_holdertrade",
            "2000",
            tuple({"ts_code": symbol, "start_date": start_365, "end_date": end_today} for symbol in TEST_SYMBOLS),
            "ts_code,ann_date,holder_name,holder_type,in_de,change_vol,change_ratio,after_share,after_ratio,begin_date,close_date",
            "exact_match",
            "partial",
            "Important shareholder increase/decrease data; closest A-share insider-like source.",
        ),
        ProbeSpec(
            "top10_holders",
            "2000",
            tuple({"ts_code": symbol} for symbol in TEST_SYMBOLS),
            "ts_code,ann_date,end_date,holder_name,hold_amount,hold_ratio,hold_float_ratio",
            "partial_match",
            "broad",
            "Top ten shareholders; stable replacement/supplement for F10 shareholder text.",
        ),
        ProbeSpec(
            "top10_floatholders",
            "2000",
            tuple({"ts_code": symbol} for symbol in TEST_SYMBOLS),
            "ts_code,ann_date,end_date,holder_name,hold_amount,hold_ratio,hold_float_ratio",
            "partial_match",
            "broad",
            "Top ten float shareholders; stable replacement/supplement for F10 shareholder text.",
        ),
        ProbeSpec(
            "stk_managers",
            "2000",
            tuple({"ts_code": symbol, "start_date": start_365, "end_date": end_today} for symbol in TEST_SYMBOLS),
            "ts_code,ann_date,name,gender,lev,title,begin_date,end_date",
            "partial_match",
            "broad",
            "Management roster; not transaction data but can support F10-style context.",
        ),
        ProbeSpec(
            "stk_rewards",
            "2000",
            tuple({"ts_code": symbol} for symbol in TEST_SYMBOLS),
            "ts_code,ann_date,end_date,name,title,reward,hold_vol",
            "partial_match",
            "broad",
            "Management compensation/holding; not equivalent to transactions.",
        ),
    ]


def main() -> int:
    _load_tushare_token_presence_only()
    os.environ["TUSHARE_ENABLE_CACHE"] = "0"
    config = TushareClientConfig.from_env()
    client = TushareClient(config=config)
    token_status = "present" if client.has_token() else "missing"

    rows: list[dict[str, str]] = []
    specs = _build_specs()
    if token_status == "missing":
        for spec in specs:
            rows.append({
                "interface_name": spec.api,
                "required_points": spec.required_points,
                "permission_status": "unknown",
                "tested_symbols": _case_symbols(spec.cases),
                "tested_dates": _case_dates(spec.cases),
                "returned_rows": "0",
                "key_fields": "N/A",
                "semantic_fit": spec.semantic_fit,
                "coverage_fit": spec.coverage_fit,
                "stability_observation": "TUSHARE_TOKEN missing; no external call made",
                "notes": spec.notes,
            })
    else:
        for spec in specs:
            rows.append(_run_spec(client, spec))

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "interface_name",
        "required_points",
        "permission_status",
        "tested_symbols",
        "tested_dates",
        "returned_rows",
        "key_fields",
        "semantic_fit",
        "coverage_fit",
        "stability_observation",
        "notes",
    ]
    with OUT_CSV.open("w", encoding="utf-8", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    status_counts: dict[str, int] = {}
    for row in rows:
        status_counts[row["permission_status"]] = status_counts.get(row["permission_status"], 0) + 1

    print(f"TUSHARE_TOKEN: {token_status}")
    print(f"wrote: {OUT_CSV.relative_to(ROOT)}")
    print("permission_status counts:")
    for key in sorted(status_counts):
        print(f"  {key}: {status_counts[key]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
