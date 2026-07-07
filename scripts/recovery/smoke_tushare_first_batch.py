"""Minimal live smoke test for first-batch Tushare candidates.

The script intentionally prints only status, field names, row counts, and short
error categories. It reads TUSHARE_TOKEN from the environment but never prints
or writes the token.
"""

from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


API_URL = "https://api.tushare.pro"
AS_OF = "20260707"
OUTPUT_DIR = Path("docs/recovery/tushare_pro_inventory")
OUTPUT_MD = OUTPUT_DIR / "TUSHARE_PRO_FIRST_BATCH_LIVE_SMOKE_TEST.md"
OUTPUT_CSV = OUTPUT_DIR / "TUSHARE_PRO_FIRST_BATCH_LIVE_SMOKE_TEST.csv"
MAX_ERROR_MESSAGE_LENGTH = 180

ALLOWED_APIS = {
    "stock_basic",
    "daily_basic",
    "balancesheet",
    "cashflow",
    "income",
    "report_rc",
    "moneyflow",
    "moneyflow_dc",
}

EXPECTED_FIELDS: Dict[str, List[str]] = {
    "stock_basic": ["ts_code", "symbol", "name", "area", "industry", "market", "list_date"],
    "daily_basic": [
        "trade_date",
        "close",
        "pe",
        "pe_ttm",
        "pb",
        "ps",
        "ps_ttm",
        "total_mv",
        "circ_mv",
        "turnover_rate",
        "volume_ratio",
        "total_share",
        "float_share",
    ],
    "balancesheet": ["ts_code", "ann_date", "f_ann_date", "end_date", "report_type", "comp_type", "end_type"],
    "cashflow": [
        "ts_code",
        "ann_date",
        "end_date",
        "report_type",
        "comp_type",
        "net_profit",
        "n_cashflow_act",
        "n_cashflow_inv_act",
        "n_cash_flows_fnc_act",
    ],
    "income": ["basic_eps", "total_revenue", "revenue", "total_profit", "n_income", "n_income_attr_p"],
    "report_rc": ["report_date", "quarter", "org_name", "author_name", "eps", "np", "op_rt", "rating"],
    "moneyflow": [
        "trade_date",
        "buy_sm_amount",
        "sell_sm_amount",
        "buy_md_amount",
        "sell_md_amount",
        "buy_lg_amount",
        "sell_lg_amount",
        "buy_elg_amount",
        "sell_elg_amount",
        "net_mf_amount",
    ],
    "moneyflow_dc": [
        "trade_date",
        "net_amount",
        "net_amount_rate",
        "buy_elg_amount",
        "buy_lg_amount",
        "buy_md_amount",
        "buy_sm_amount",
    ],
}


@dataclass
class SmokeResult:
    api: str
    sample: str
    status: str
    row_count: int
    fields: List[str]
    expected_fields_present: List[str]
    expected_fields_missing: List[str]
    permission_available: str
    error_type: str = ""
    note: str = ""


def main() -> int:
    token = os.getenv("TUSHARE_TOKEN", "").strip()
    print("TUSHARE_TOKEN=present" if token else "TUSHARE_TOKEN=missing")
    if not token:
        return 2

    results = run_smoke(token)
    write_outputs(results)
    print_summary(results)
    return 0


def run_smoke(token: str) -> List[SmokeResult]:
    results = [
        test_stock_basic(token),
        test_daily_like(token, "daily_basic", "600519.SH", max_back_days=10),
        test_statement(token, "balancesheet", "600519.SH"),
        test_statement(token, "cashflow", "600519.SH"),
        test_statement(token, "income", "600519.SH"),
        test_report_rc(token),
        test_daily_like(token, "moneyflow", "300750.SZ", max_back_days=10),
        test_daily_like(token, "moneyflow_dc", "300750.SZ", max_back_days=10, note="备用资金流源字段验证"),
    ]
    return results


def test_stock_basic(token: str) -> SmokeResult:
    fields = ",".join(EXPECTED_FIELDS["stock_basic"])
    payload = call_tushare(token, "stock_basic", {"ts_code": "600519.SH"}, fields=fields)
    return result_from_payload("stock_basic", "600519.SH", payload, "基础股票信息可用性")


def test_daily_like(
    token: str,
    api: str,
    ts_code: str,
    max_back_days: int,
    note: str = "最近可用交易日",
) -> SmokeResult:
    fields = ",".join(EXPECTED_FIELDS[api])
    last_payload: Optional[Mapping[str, Any]] = None
    for trade_date in back_dates(AS_OF, max_back_days):
        payload = call_tushare(token, api, {"ts_code": ts_code, "trade_date": trade_date}, fields=fields)
        last_payload = payload
        rows = rows_from_payload(payload)
        if rows:
            return result_from_payload(api, f"{ts_code}@{trade_date}", payload, note)
        if payload.get("status") == "technical_error":
            return result_from_payload(api, f"{ts_code}@{trade_date}", payload, "请求失败，停止回看")
        time.sleep(0.2)
    assert last_payload is not None
    result = result_from_payload(api, f"{ts_code}@{AS_OF}-back{max_back_days}d", last_payload, "回看窗口内无数据")
    if result.status == "ok" and result.row_count == 0:
        result.status = "no_data"
    return result


def test_statement(token: str, api: str, ts_code: str) -> SmokeResult:
    fields = ",".join(EXPECTED_FIELDS[api])
    payload = call_tushare(token, api, {"ts_code": ts_code}, fields=fields)
    result = result_from_payload(api, ts_code, payload, "最近已公告报表字段验证")
    if result.status == "ok":
        rows = rows_from_payload(payload)
        filtered = [row for row in rows if not row.get("ann_date") or str(row.get("ann_date")) <= AS_OF]
        result.row_count = len(filtered)
        if rows and not filtered:
            result.status = "no_data"
            result.note = "返回记录均晚于 as_of，已按 ann_date 过滤为 0"
    return result


def test_report_rc(token: str) -> SmokeResult:
    fields = ",".join(EXPECTED_FIELDS["report_rc"])
    start_date = date_minus_days(AS_OF, 365)
    for ts_code in ("600519.SH", "300750.SZ"):
        payload = call_tushare(
            token,
            "report_rc",
            {"ts_code": ts_code, "start_date": start_date, "end_date": AS_OF},
            fields=fields,
        )
        result = result_from_payload("report_rc", f"{ts_code}@{start_date}-{AS_OF}", payload, "近一年卖方盈利预测")
        if result.status == "ok" and result.row_count > 0:
            return result
        if result.status == "technical_error":
            return result
        time.sleep(0.2)
    if result.status == "ok" and result.row_count == 0:
        result.status = "no_coverage"
        result.note = "600519.SH 与 300750.SZ 近一年未返回卖方预测记录"
    return result


def call_tushare(token: str, api_name: str, params: Mapping[str, Any], fields: str = "") -> Mapping[str, Any]:
    if api_name not in ALLOWED_APIS:
        return short_error(api_name, "tushare_upstream_error", "api_not_allowed")

    payload: Dict[str, Any] = {"api_name": api_name, "token": token, "params": dict(params)}
    if fields:
        payload["fields"] = fields
    body_or_error = post_with_curl(payload)
    if isinstance(body_or_error, Mapping):
        return body_or_error
    body = body_or_error

    try:
        parsed = json.loads(body)
    except json.JSONDecodeError:
        return short_error(api_name, "parse_error", "invalid_json_response")
    return normalize_payload(api_name, parsed)


def post_with_curl(payload: Mapping[str, Any]) -> str | Mapping[str, Any]:
    data = json.dumps(payload, ensure_ascii=False)
    try:
        proc = subprocess.run(
            [
                "curl",
                "-sS",
                "--max-time",
                "20",
                "-H",
                "Content-Type: application/json",
                "--data-binary",
                "@-",
                API_URL,
            ],
            input=data,
            text=True,
            capture_output=True,
            check=False,
        )
    except FileNotFoundError:
        return short_error(str(payload.get("api_name") or "unknown_api"), "network_error", "curl_missing")
    except subprocess.SubprocessError:
        return short_error(str(payload.get("api_name") or "unknown_api"), "network_error", "curl_failed")

    if proc.returncode != 0:
        return short_error(str(payload.get("api_name") or "unknown_api"), "network_error", f"curl_exit_{proc.returncode}")
    return proc.stdout


def normalize_payload(api_name: str, payload: Mapping[str, Any]) -> Mapping[str, Any]:
    code = payload.get("code")
    msg = sanitize(str(payload.get("msg") or ""))
    if code == 0:
        return {"status": "ok", "api": api_name, "data": payload.get("data") or {}}
    return short_error(api_name, classify_error(msg), msg or "nonzero_response")


def short_error(api_name: str, error_type: str, detail: str = "") -> Mapping[str, Any]:
    safe_detail = sanitize(detail)
    return {
        "status": "technical_error",
        "api": api_name,
        "error_type": error_type,
        "message": f"technical_error: {error_type}" + (f" ({safe_detail})" if safe_detail else ""),
    }


def result_from_payload(api: str, sample: str, payload: Mapping[str, Any], note: str) -> SmokeResult:
    rows = rows_from_payload(payload)
    fields = fields_from_payload(payload)
    expected = EXPECTED_FIELDS[api]
    present = [field for field in expected if field in fields]
    missing = [field for field in expected if field not in fields]
    status = str(payload.get("status") or "technical_error")
    error_type = str(payload.get("error_type") or "")
    if status == "ok" and not rows:
        status = "no_data"
    if status == "technical_error":
        permission = "no" if error_type == "tushare_permission_denied" else "unknown"
    else:
        permission = "yes"
    return SmokeResult(
        api=api,
        sample=sample,
        status=status,
        row_count=len(rows),
        fields=fields,
        expected_fields_present=present,
        expected_fields_missing=missing,
        permission_available=permission,
        error_type=error_type,
        note=note,
    )


def rows_from_payload(payload: Mapping[str, Any]) -> List[Dict[str, Any]]:
    data = payload.get("data") if isinstance(payload, Mapping) else None
    if not isinstance(data, Mapping):
        return []
    fields = data.get("fields") or []
    items = data.get("items") or []
    rows = []
    for item in items:
        if isinstance(item, Sequence):
            rows.append(dict(zip(fields, item)))
    return rows


def fields_from_payload(payload: Mapping[str, Any]) -> List[str]:
    data = payload.get("data") if isinstance(payload, Mapping) else None
    if not isinstance(data, Mapping):
        return []
    fields = data.get("fields") or []
    return [str(field) for field in fields]


def write_outputs(results: Sequence[SmokeResult]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    write_csv(results)
    write_markdown(results)


def write_csv(results: Sequence[SmokeResult]) -> None:
    with OUTPUT_CSV.open("w", encoding="utf-8", newline="") as fp:
        writer = csv.DictWriter(
            fp,
            fieldnames=[
                "api",
                "sample",
                "status",
                "row_count",
                "permission_available",
                "expected_fields_present",
                "expected_fields_missing",
                "returned_fields",
                "error_type",
                "note",
            ],
        )
        writer.writeheader()
        for result in results:
            writer.writerow(
                {
                    "api": result.api,
                    "sample": result.sample,
                    "status": result.status,
                    "row_count": result.row_count,
                    "permission_available": result.permission_available,
                    "expected_fields_present": ";".join(result.expected_fields_present),
                    "expected_fields_missing": ";".join(result.expected_fields_missing),
                    "returned_fields": ";".join(result.fields),
                    "error_type": result.error_type,
                    "note": result.note,
                }
            )


def write_markdown(results: Sequence[SmokeResult]) -> None:
    lines = [
        "# Tushare Pro 第一批候选接口最小实测",
        "",
        "阶段：4B-2",
        "",
        "## 执行边界",
        "",
        "- `TUSHARE_TOKEN`：present（未输出 token 值）。",
        "- 仅调用第一批候选接口：`stock_basic`、`daily_basic`、`balancesheet`、`cashflow`、`income`、`report_rc`、`moneyflow`、`moneyflow_dc`。",
        "- 未调用 `forecast` / `express` / `fina_indicator` / 新闻公告 / 北向资金 / 大盘资金 / 同花顺资金流等非第一批接口。",
        "- 未修改 `a_stock.py` / `interface.py`，未接入业务函数。",
        "- 未写入真实缓存，未提交 token。",
        "- 当前 Codex Python 标准库 HTTPS 证书校验不可用，本脚本使用系统 `curl` 并通过 stdin 传递请求体，token 不进入命令行参数或输出。",
        "",
        "## 汇总",
        "",
        "| 接口 | 样例 | 状态 | 行数 | 权限可用 | 缺失核心字段 | 短错误 | 备注 |",
        "|---|---|---:|---:|---|---|---|---|",
    ]
    for result in results:
        lines.append(
            "| {api} | {sample} | {status} | {row_count} | {permission} | {missing} | {error} | {note} |".format(
                api=result.api,
                sample=result.sample,
                status=result.status,
                row_count=result.row_count,
                permission=result.permission_available,
                missing=", ".join(result.expected_fields_missing) or "无",
                error=result.error_type or "无",
                note=result.note,
            )
        )

    lines.extend(["", "## 字段核验", ""])
    for result in results:
        lines.extend(
            [
                f"### `{result.api}`",
                "",
                f"- 样例：`{result.sample}`",
                f"- 状态：`{result.status}`",
                f"- 返回行数：`{result.row_count}`",
                f"- 权限可用：`{result.permission_available}`",
                f"- 已返回核心字段：`{', '.join(result.expected_fields_present) or '无'}`",
                f"- 缺失核心字段：`{', '.join(result.expected_fields_missing) or '无'}`",
                f"- 返回字段：`{', '.join(result.fields) or '无'}`",
                f"- 短错误类型：`{result.error_type or '无'}`",
                "",
            ]
        )
    OUTPUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def print_summary(results: Sequence[SmokeResult]) -> None:
    for result in results:
        print(
            f"{result.api},{result.sample},{result.status},"
            f"rows={result.row_count},permission={result.permission_available},"
            f"error={result.error_type or 'none'}"
        )


def back_dates(yyyymmdd: str, max_back_days: int) -> Iterable[str]:
    start = datetime.strptime(yyyymmdd, "%Y%m%d")
    for offset in range(max_back_days + 1):
        yield (start - timedelta(days=offset)).strftime("%Y%m%d")


def date_minus_days(yyyymmdd: str, days: int) -> str:
    return (datetime.strptime(yyyymmdd, "%Y%m%d") - timedelta(days=days)).strftime("%Y%m%d")


def classify_error(message: str) -> str:
    lower = message.lower()
    if any(term in lower for term in ("权限", "积分", "permission", "无权", "未开通")):
        return "tushare_permission_denied"
    if any(term in lower for term in ("频率", "每分钟", "超过", "rate", "limit")):
        return "tushare_rate_limited"
    return "tushare_upstream_error"


def sanitize(value: str) -> str:
    text = value.replace("\n", " ").replace("\r", " ").strip()
    lower = text.lower()
    if "<html" in lower or "<!doctype" in lower:
        return "upstream_html_or_challenge"
    for marker in ("token", "authorization", "cookie", "access_token", "api_key"):
        if marker in lower:
            return "sensitive_detail_redacted"
    if len(text) > MAX_ERROR_MESSAGE_LENGTH:
        return text[:MAX_ERROR_MESSAGE_LENGTH].rstrip() + "..."
    return text


if __name__ == "__main__":
    sys.exit(main())
