"""A-stock (China mainland) data vendor for TradingAgents.

Zero third-party data dependency (no akshare). All sources are direct HTTP APIs
or mootdx TCP.

Data sources:
- mootdx (TCP 7709): OHLCV K-lines, financial snapshots, F10 text
- Tencent Finance (HTTP GBK): PE/PB/market cap/turnover
- 东方财富 push2 / datacenter-web (direct HTTP): stock info, dragon-tiger, lockup
- 新浪财经 (direct HTTP): K-line fallback, financial statements
- 同花顺 (direct HTTP): consensus EPS, hot stocks, northbound capital flow
- 财联社 (direct HTTP): global news wire
"""

from __future__ import annotations

from typing import Annotated
from datetime import datetime
from dateutil.relativedelta import relativedelta
import json as _json
import os
import logging
import math
import random
import re as _re
import socket
import time
import uuid
import urllib.request

import pandas as pd
import requests as _requests

from .utils import safe_ticker_component

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers: ticker format & market detection
# ---------------------------------------------------------------------------

def _get_prefix(code: str) -> str:
    """6-digit A-stock code -> market prefix for Tencent API."""
    if code.startswith(("6", "9")):
        return "sh"
    elif code.startswith("8"):
        return "bj"
    return "sz"


def _normalize_ticker(symbol: str) -> str:
    """Strip exchange prefix/suffix, return pure 6-digit code.

    Handles: '688017', 'SH688017', '688017.SH', 'sh688017'
    """
    s = symbol.strip().upper()
    # Remove .SH / .SZ / .BJ suffix
    for suffix in (".SH", ".SZ", ".BJ"):
        if s.endswith(suffix):
            s = s[: -len(suffix)]
            break
    # Remove SH / SZ / BJ prefix
    for prefix in ("SH", "SZ", "BJ"):
        if s.startswith(prefix):
            s = s[len(prefix) :]
            break
    return safe_ticker_component(s)


# ---------------------------------------------------------------------------
# Stock name <-> code mapping (cached)
# ---------------------------------------------------------------------------

_name_to_code: dict[str, str] | None = None
_code_to_name: dict[str, str] | None = None


def _build_name_code_map() -> tuple[dict[str, str], dict[str, str]]:
    """Build name→code and code→name maps via mootdx (both SH & SZ markets)."""
    global _name_to_code, _code_to_name
    if _name_to_code is not None:
        return _name_to_code, _code_to_name

    client = _get_mootdx_client()
    n2c: dict[str, str] = {}
    c2n: dict[str, str] = {}

    try:
        for market in (0, 1):  # 0=SZ, 1=SH
            stocks = client.stocks(market=market)
            if stocks is None or stocks.empty:
                continue
            for _, row in stocks.iterrows():
                code = str(row["code"]).strip()
                name = str(row["name"]).strip()
                if not _re.match(r"^[036]\d{5}$", code):
                    continue
                clean_name = name.replace(" ", "").replace("　", "")
                n2c[clean_name] = code
                c2n[code] = clean_name
    except Exception as e:
        # 网络抖动/通达信不可达时给出明确提示，而非冒泡成风马牛不相及的报错（#46/#66）
        raise ValueError(
            "无法通过 mootdx 解析股票名称（通达信服务暂时不可达）：%s。"
            "请稍后重试，或直接输入 6 位股票代码。" % e
        ) from e

    _name_to_code = n2c
    _code_to_name = c2n
    logger.info("Built stock name-code map: %d entries", len(n2c))
    return _name_to_code, _code_to_name


def resolve_ticker(user_input: str) -> str:
    """Resolve user input (code or Chinese name) to a 6-digit A-stock code.

    Accepts: '600379', 'SH600379', '600379.SH', '宝光股份'
    Returns: '600379'
    Raises: ValueError if not resolvable.
    """
    s = user_input.strip()
    if not s:
        raise ValueError("输入不能为空")

    has_chinese = any("一" <= ch <= "鿿" for ch in s)

    if not has_chinese:
        return _normalize_ticker(s)

    clean = s.replace(" ", "").replace("　", "")
    n2c, _ = _build_name_code_map()

    if clean in n2c:
        return n2c[clean]

    matches = {name: code for name, code in n2c.items() if clean in name}
    if len(matches) == 1:
        return next(iter(matches.values()))
    if len(matches) > 1:
        examples = ", ".join(f"{n}({c})" for n, c in list(matches.items())[:5])
        raise ValueError(f"'{s}' 匹配到多只股票: {examples}，请输入完整名称或代码")

    raise ValueError(f"找不到股票 '{s}'，请检查名称是否正确")


# ---------------------------------------------------------------------------
# mootdx client (singleton)
# ---------------------------------------------------------------------------

_mootdx_client = None

# 实测可用的通达信备选服务器（按延迟排序，2026-06 验证）。用于规避 mootdx
# 0.11.x 全新安装时 BESTIP.HQ 为空串导致的 `ValueError: not enough values to unpack`。
_TDX_SERVERS = [
    ("119.97.185.59", 7709), ("124.70.133.119", 7709), ("116.205.183.150", 7709),
    ("123.60.73.44", 7709), ("116.205.163.254", 7709), ("121.36.225.169", 7709),
    ("123.60.70.228", 7709), ("124.71.9.153", 7709), ("110.41.147.114", 7709),
    ("124.71.187.122", 7709),
]


def _probe_tdx(ip: str, port: int, timeout: float = 2.0) -> bool:
    """TCP 握手探测通达信服务器是否可达。"""
    try:
        with socket.create_connection((ip, port), timeout=timeout):
            return True
    except OSError:
        return False


def _get_mootdx_client():
    """Lazy-init 健壮版 mootdx Quotes client（TCP 连接，可复用）。

    规避 mootdx 0.11.x 全新安装的 BESTIP 空串 bug：先 TCP 探测内置服务器列表、
    用第一个可达的显式 server 绕过 BESTIP；三级 fallback（bestip 测速 → 裸 factory →
    明确 RuntimeError）保证 IP 老化/换网/老用户场景都能工作。
    """
    global _mootdx_client
    if _mootdx_client is not None:
        return _mootdx_client

    from mootdx.quotes import Quotes

    for ip, port in _TDX_SERVERS:
        if _probe_tdx(ip, port):
            _mootdx_client = Quotes.factory(market="std", server=(ip, port))
            return _mootdx_client
    try:
        _mootdx_client = Quotes.factory(market="std", bestip=True)  # fallback 1
        return _mootdx_client
    except Exception:
        pass
    try:
        _mootdx_client = Quotes.factory(market="std")  # fallback 2（老用户 config 已有 IP）
        return _mootdx_client
    except Exception as e:
        raise RuntimeError(
            "mootdx 通达信服务器均不可达（TCP 7709）。海外网络通常全部超时，"
            "请走国内代理或直接使用 6 位股票代码。原始错误：%s" % e
        ) from e


# ---------------------------------------------------------------------------
# Tencent Finance API
# ---------------------------------------------------------------------------

def _tencent_quote(codes: list[str]) -> dict[str, dict]:
    """Batch real-time quotes from Tencent Finance (qt.gtimg.cn).

    Returns dict[code] -> {name, price, pe_ttm, pb, mcap_yi, ...}
    """
    prefixed = [f"{_get_prefix(c)}{c}" for c in codes]
    url = "https://qt.gtimg.cn/q=" + ",".join(prefixed)
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "Mozilla/5.0")
    resp = urllib.request.urlopen(req, timeout=10)
    raw = resp.read().decode("gbk")

    result = {}
    for line in raw.strip().split(";"):
        if not line.strip() or "=" not in line or '"' not in line:
            continue
        key = line.split("=")[0].split("_")[-1]
        vals = line.split('"')[1].split("~")
        if len(vals) < 53:
            continue
        code = key[2:]  # strip sh/sz/bj prefix
        result[code] = {
            "name": vals[1],
            "price": float(vals[3]) if vals[3] else 0,
            "last_close": float(vals[4]) if vals[4] else 0,
            "open": float(vals[5]) if vals[5] else 0,
            "change_pct": float(vals[32]) if vals[32] else 0,
            "high": float(vals[33]) if vals[33] else 0,
            "low": float(vals[34]) if vals[34] else 0,
            "turnover_pct": float(vals[38]) if vals[38] else 0,
            "pe_ttm": float(vals[39]) if vals[39] else 0,
            "mcap_yi": float(vals[44]) if vals[44] else 0,
            "float_mcap_yi": float(vals[45]) if vals[45] else 0,
            "pb": float(vals[46]) if vals[46] else 0,
            "limit_up": float(vals[47]) if vals[47] else 0,
            "limit_down": float(vals[48]) if vals[48] else 0,
            "pe_static": float(vals[52]) if vals[52] else 0,
        }
    return result


# ---------------------------------------------------------------------------
# Eastmoney Datacenter unified helper (龙虎榜/解禁 etc.)
# ---------------------------------------------------------------------------

_DATACENTER_URL = "https://datacenter-web.eastmoney.com/api/data/v1/get"
_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"


# ---------------------------------------------------------------------------
# 东财防封：全局节流 + 会话复用 (Eastmoney anti-ban: throttle + Keep-Alive)
# ---------------------------------------------------------------------------
# 东财系 HTTP 接口（push2 / push2his / datacenter-web / search-api / np-weblist）
# 有风控：每秒 >5 次 / 单 IP 并发 ≥10 / 1 分钟 ≥200 次 / 5 分钟 ≥300 次 → 临时封 IP。
# 多 Agent 投研跑批量分析时会高频请求东财，是被封的头号元凶。所有 eastmoney.com
# 请求一律走 _em_get()：串行限流（最小间隔 + 随机抖动）+ 复用 Keep-Alive 会话 + 默认 UA。
# 注意：仅东财接口走此入口；mootdx(TCP) / 腾讯 / 新浪 / 同花顺 / 财联社 / 百度 等
# 不限流（实测不封 IP 或风控极弱）。批量任务可调大 EM_MIN_INTERVAL 进一步降速。
_EM_SESSION = _requests.Session()
_EM_SESSION.headers.update({"User-Agent": _UA})
# 两次东财请求最小间隔(秒)；批量多 Agent 场景可设环境变量 EM_MIN_INTERVAL=1.5~2 降速。
_EM_MIN_INTERVAL = float(os.environ.get("EM_MIN_INTERVAL", "1.0"))
_em_last_call = [0.0]  # 模块级上次东财请求时间戳


def _em_get(url, params=None, headers=None, timeout=15, **kwargs):
    """东财统一请求入口：自动节流 + 复用 session + 默认 UA。

    所有 eastmoney.com 接口都应通过它请求，避免多 Agent 高频拉数据被封 IP。
    串行限流：与上次东财请求间隔 < EM_MIN_INTERVAL 时 sleep 补足 + 0.1~0.5s 随机抖动。
    传入的 headers 会覆盖 session 默认 UA（用于保留各端点自己的 Referer/Origin）。
    """
    wait = _EM_MIN_INTERVAL - (time.time() - _em_last_call[0])
    if wait > 0:
        time.sleep(wait + random.uniform(0.1, 0.5))
    try:
        return _EM_SESSION.get(
            url, params=params, headers=headers, timeout=timeout, **kwargs
        )
    finally:
        _em_last_call[0] = time.time()


# ---------------------------------------------------------------------------
# String-compatible data source contract helpers
# ---------------------------------------------------------------------------

def _build_data_source_contract_header(
    *,
    status: str,
    source: str,
    data_type: str,
    query_target: str,
    symbol: str,
    as_of: str,
    trade_date: str,
    unit: str,
    coverage: str,
    fallback: str = "none",
    empty_reason: str = "none",
    error_type: str = "none",
    raw_error_suppressed: bool = False,
    limitations: str = "",
    notes: str = "",
) -> str:
    """Build a stable Agent-visible string header for dataflow outputs."""
    lines = [
        "# Data Source Contract",
        f"status: {status}",
        f"source: {source}",
        f"data_type: {data_type}",
        f"query_target: {query_target}",
        f"symbol: {symbol}",
        f"as_of: {as_of}",
        f"trade_date: {trade_date}",
        f"unit: {unit}",
        f"coverage: {coverage}",
        f"fallback: {fallback}",
        f"empty_reason: {empty_reason}",
        f"error_type: {error_type}",
        f"raw_error_suppressed: {str(raw_error_suppressed).lower()}",
    ]
    if limitations:
        lines.append(f"limitations: {limitations}")
    if notes:
        lines.append(f"notes: {notes}")
    lines.append("")
    lines.append("## Data")
    return "\n".join(lines)


def _classify_data_source_error(error: Exception | str) -> str:
    """Classify a technical data-source error without exposing raw details."""
    text = str(error).lower()

    if "rate" in text or "rate_limited" in text or "频率" in text:
        return "rate_limited"
    if any(key in text for key in ("permission", "denied", "权限", "积分", "token_missing")):
        return "vendor_error"
    if "tushare_upstream" in text:
        return "vendor_error"
    if "proxy" in text or isinstance(error, _requests.exceptions.ProxyError):
        return "proxy_error"
    if "<html" in text or "<!doctype" in text or "html" in text:
        return "html_response"
    if "timeout" in text or isinstance(error, _requests.exceptions.Timeout):
        return "timeout"
    if isinstance(error, _requests.exceptions.ConnectionError):
        return "network_error"
    if isinstance(error, _requests.exceptions.HTTPError):
        return "vendor_error"
    if "schema" in text or "missing" in text or "unexpected" in text:
        return "unexpected_schema"
    if isinstance(error, (ValueError, KeyError, TypeError)):
        return "parse_error"
    if "status code" in text or "resultcode" in text or "vendor" in text:
        return "vendor_error"
    return "unknown"


def _eastmoney_datacenter(
    report_name: str,
    columns: str = "ALL",
    filter_str: str = "",
    page_size: int = 50,
    sort_columns: str = "",
    sort_types: str = "-1",
) -> list[dict]:
    """东财数据中心统一查询 — 龙虎榜/解禁 共用."""
    params = {
        "reportName": report_name,
        "columns": columns,
        "filter": filter_str,
        "pageNumber": "1",
        "pageSize": str(page_size),
        "sortColumns": sort_columns,
        "sortTypes": sort_types,
        "source": "WEB",
        "client": "WEB",
    }
    r = _em_get(_DATACENTER_URL, params=params, timeout=15)
    d = r.json()
    if d.get("result") and d["result"].get("data"):
        return d["result"]["data"]
    return []


# ---------------------------------------------------------------------------
# 同花顺 EPS forecast helper (direct HTTP, no akshare)
# ---------------------------------------------------------------------------


def _ths_eps_forecast(code: str) -> pd.DataFrame:
    """Fetch consensus EPS forecast from 同花顺 (direct HTTP).

    Returns DataFrame with columns roughly: 年度, 预测机构数, 最小值, 均值, 最大值.
    """
    url = f"https://basic.10jqka.com.cn/new/{code}/worth.html"
    headers = {
        "User-Agent": _UA,
        "Referer": "https://basic.10jqka.com.cn/",
    }
    r = _requests.get(url, headers=headers, timeout=15)
    r.encoding = "gbk"
    dfs = pd.read_html(r.text)
    # Find the table containing EPS data
    for df in dfs:
        cols = [str(c) for c in df.columns]
        if any("每股收益" in c or "均值" in c for c in cols):
            return df
    # Fallback: return first table if exists
    return dfs[0] if dfs else pd.DataFrame()


# ---------------------------------------------------------------------------
# Sina K-line fallback helper (direct HTTP, no akshare)
# ---------------------------------------------------------------------------


def _sina_kline_fallback(code: str, start_date: str = None, end_date: str = None) -> pd.DataFrame:
    """Fetch daily K-line from Sina HTTP API as mootdx fallback.

    Returns DataFrame with columns: Date, Open, High, Low, Close, Volume.
    """
    prefix = "sh" if code.startswith("6") else "sz"
    url = (
        "http://money.finance.sina.com.cn/quotes_service/api/json_v2.php/"
        "CN_MarketData.getKLineData"
    )
    params = {
        "symbol": f"{prefix}{code}",
        "scale": "240",  # daily
        "ma": "no",
        "datalen": "800",
    }
    r = _requests.get(url, params=params, timeout=15)
    r.raise_for_status()
    data = _json.loads(r.text)

    if not data:
        return pd.DataFrame()

    rows = []
    for item in data:
        rows.append({
            "Date": item["day"],
            "Open": float(item["open"]),
            "High": float(item["high"]),
            "Low": float(item["low"]),
            "Close": float(item["close"]),
            "Volume": int(item["volume"]),
        })

    df = pd.DataFrame(rows)
    df["Date"] = pd.to_datetime(df["Date"])

    if start_date:
        df = df[df["Date"] >= pd.to_datetime(start_date)]
    if end_date:
        df = df[df["Date"] <= pd.to_datetime(end_date)]

    return df


def _last_ohlcv_date(df: pd.DataFrame) -> pd.Timestamp | None:
    """Return the latest OHLCV Date in a normalized dataframe."""
    if df is None or df.empty or "Date" not in df.columns:
        return None
    dates = pd.to_datetime(df["Date"], errors="coerce")
    if dates.dropna().empty:
        return None
    return dates.max().normalize()


def _normalize_ohlcv_dates(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize OHLCV Date values to daily granularity."""
    if df is None or df.empty or "Date" not in df.columns:
        return df
    df = df.copy()
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce").dt.normalize()
    return df.dropna(subset=["Date"])


def _needs_sina_supplement(df: pd.DataFrame, target_date: str | None) -> bool:
    """True when mootdx/cache data is older than the requested cutoff date."""
    if not target_date:
        return False
    last_date = _last_ohlcv_date(df)
    if last_date is None:
        return True
    target = pd.to_datetime(target_date).normalize()
    return last_date < target


def _merge_ohlcv(primary: pd.DataFrame, supplement: pd.DataFrame) -> pd.DataFrame:
    """Merge OHLCV frames, preferring supplement rows on duplicate dates."""
    frames = [frame for frame in (primary, supplement) if frame is not None and not frame.empty]
    if not frames:
        return pd.DataFrame(columns=["Date", "Open", "High", "Low", "Close", "Volume"])
    combined = pd.concat(frames, ignore_index=True)
    combined = _normalize_ohlcv_dates(combined)
    combined = combined.drop_duplicates(subset=["Date"], keep="last")
    combined = combined.sort_values("Date").reset_index(drop=True)
    return combined


def _supplement_stale_ohlcv_with_sina(
    code: str,
    df: pd.DataFrame,
    target_date: str | None,
    start_date: str | None = None,
) -> tuple[pd.DataFrame, bool]:
    """Use Sina daily K-line to fill dates missing from mootdx/cache data."""
    if not _needs_sina_supplement(df, target_date):
        return df, False
    try:
        sina_df = _sina_kline_fallback(code, start_date, target_date)
    except Exception as e:
        logger.warning("sina K-line supplement failed for %s: %s", code, e)
        return df, False
    if sina_df.empty:
        return df, False
    merged = _merge_ohlcv(df, sina_df)
    return merged, _last_ohlcv_date(merged) != _last_ohlcv_date(df)


# ---------------------------------------------------------------------------
# OHLCV loading with cache (mootdx -> CSV)
# ---------------------------------------------------------------------------

def _load_ohlcv_astock(symbol: str, curr_date: str) -> pd.DataFrame:
    """Fetch OHLCV via mootdx, cache to CSV, filter by curr_date.

    Mirrors stockstats_utils.load_ohlcv but uses mootdx instead of yfinance.
    Returns DataFrame with columns: Date, Open, High, Low, Close, Volume
    """
    from .config import get_config

    code = _normalize_ticker(symbol)
    config = get_config()
    cache_dir = config.get(
        "data_cache_dir", os.path.expanduser("~/.tradingagents/cache")
    )
    os.makedirs(cache_dir, exist_ok=True)

    cache_file = os.path.join(cache_dir, f"{code}-astock-daily.csv")

    if os.path.exists(cache_file):
        mtime = datetime.fromtimestamp(os.path.getmtime(cache_file))
        if mtime.date() == datetime.now().date():
            data = pd.read_csv(cache_file, on_bad_lines="skip", encoding="utf-8")
            data = _normalize_ohlcv_dates(data)
            data, supplemented = _supplement_stale_ohlcv_with_sina(
                code, data, curr_date, start_date=None
            )
            if supplemented:
                data.to_csv(cache_file, index=False, encoding="utf-8")
            cutoff = pd.to_datetime(curr_date)
            return data[data["Date"] <= cutoff]

    # Fetch from mootdx — 800 daily bars (~3 years of trading days)
    try:
        client = _get_mootdx_client()
        df = client.bars(symbol=code, category=4, offset=800)

        if df is None or df.empty:
            raise ValueError(f"No OHLCV data from mootdx for {code}")

        # mootdx returns index named 'datetime' AND a column named 'datetime'
        # (plus year/month/day/hour/minute/volume). Drop duplicates before reset.
        df = df.drop(columns=["datetime", "year", "month", "day", "hour", "minute"], errors="ignore")
        df = df.reset_index()  # moves index 'datetime' → column 'datetime'
        rename_map = {
            "datetime": "Date",
            "open": "Open",
            "close": "Close",
            "high": "High",
            "low": "Low",
            "volume": "Volume",
        }
        df = df.rename(columns=rename_map)
        df = df[["Date", "Open", "High", "Low", "Close", "Volume"]]
        df = _normalize_ohlcv_dates(df)
    except Exception as e:
        logger.warning("mootdx OHLCV failed for %s: %s, trying sina HTTP fallback", code, e)
        # Fallback: Sina direct HTTP API
        try:
            df = _sina_kline_fallback(code)
            if df.empty:
                raise ValueError(f"No OHLCV data from sina for {code}")
        except Exception:
            raise ValueError(f"No OHLCV data from mootdx/sina for {code}")

    df, _ = _supplement_stale_ohlcv_with_sina(code, df, curr_date, start_date=None)

    # Cache to disk
    df.to_csv(cache_file, index=False, encoding="utf-8")

    # Filter by curr_date to prevent look-ahead bias
    cutoff = pd.to_datetime(curr_date)
    return df[df["Date"] <= cutoff]


# ===========================================================================
# 9 Vendor Methods (matching interface.py VENDOR_METHODS signatures)
# ===========================================================================


# ---- 1. get_stock_data ----


def get_stock_data(
    symbol: Annotated[str, "A-stock code (e.g. 688017, SH688017)"],
    start_date: Annotated[str, "Start date in yyyy-mm-dd format"],
    end_date: Annotated[str, "End date in yyyy-mm-dd format"],
) -> str:
    """Get OHLCV stock price data via mootdx."""
    code = _normalize_ticker(symbol)

    data_source = "mootdx (TCP)"
    try:
        client = _get_mootdx_client()
        df = client.bars(symbol=code, category=4, offset=800)

        if df is None or df.empty:
            raise ValueError(f"No data from mootdx for {code}")

        # Drop duplicate datetime column + extra columns before reset_index
        df = df.drop(
            columns=["datetime", "year", "month", "day", "hour", "minute"],
            errors="ignore",
        )
        df = df.reset_index()  # index 'datetime' → column 'datetime'
        df = df.rename(
            columns={
                "datetime": "Date",
                "open": "Open",
                "close": "Close",
                "high": "High",
                "low": "Low",
                "volume": "Volume",
                "amount": "Amount",
            }
        )
        df = _normalize_ohlcv_dates(df)

    except Exception as e:
        logger.warning("mootdx K-line failed for %s: %s, trying sina HTTP fallback", code, e)
        # Fallback: Sina direct HTTP API
        try:
            df = _sina_kline_fallback(code, start_date, end_date)
            if df.empty:
                return "K线数据获取失败：mootdx和新浪备用源均不可用，请检查网络连接"
            data_source = "sina HTTP (fallback)"
        except Exception:
            return "K线数据获取失败：mootdx和新浪备用源均不可用，请检查网络连接"

    df, supplemented = _supplement_stale_ohlcv_with_sina(code, df, end_date, start_date)
    if supplemented:
        data_source = f"{data_source} + sina HTTP supplement"

    # Filter by date range
    start_dt = pd.to_datetime(start_date)
    end_dt = pd.to_datetime(end_date)
    df = df[(df["Date"] >= start_dt) & (df["Date"] <= end_dt)]

    if df.empty:
        return (
            f"No data found for A-stock '{code}' "
            f"between {start_date} and {end_date}"
        )

    for col in ["Open", "High", "Low", "Close"]:
        if col in df.columns:
            df[col] = df[col].round(2)

    df["Date"] = df["Date"].dt.strftime("%Y-%m-%d")
    csv_out = df[["Date", "Open", "High", "Low", "Close", "Volume"]].to_csv(
        index=False
    )

    header = f"# Stock data for {code} (A-stock) from {start_date} to {end_date}\n"
    header += f"# Total records: {len(df)}\n"
    header += f"# Data source: {data_source}\n"
    header += (
        f"# Data retrieved on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    )

    return header + csv_out


# ---- 2. get_indicators ----

# Supported technical indicators with descriptions
_INDICATOR_DESCRIPTIONS = {
    "close_50_sma": "50 SMA: Medium-term trend indicator.",
    "close_200_sma": "200 SMA: Long-term trend benchmark.",
    "close_10_ema": "10 EMA: Responsive short-term average.",
    "macd": "MACD: Momentum via EMA differences.",
    "macds": "MACD Signal: EMA smoothing of MACD line.",
    "macdh": "MACD Histogram: Gap between MACD and signal.",
    "rsi": "RSI: Momentum overbought/oversold indicator (70/30 thresholds).",
    "boll": "Bollinger Middle: 20 SMA basis for Bollinger Bands.",
    "boll_ub": "Bollinger Upper Band: 2 std devs above middle.",
    "boll_lb": "Bollinger Lower Band: 2 std devs below middle.",
    "atr": "ATR: Average True Range volatility measure.",
    "vwma": "VWMA: Volume-weighted moving average.",
    "mfi": "MFI: Money Flow Index (volume + price momentum).",
}


def get_indicators(
    symbol: Annotated[str, "A-stock code"],
    indicator: Annotated[
        str, "technical indicator (e.g. rsi, macd, close_50_sma)"
    ],
    curr_date: Annotated[str, "Current trading date, YYYY-mm-dd"],
    look_back_days: Annotated[int, "how many days to look back"],
) -> str:
    """Get technical indicators using stockstats on mootdx OHLCV data."""
    from stockstats import wrap

    code = _normalize_ticker(symbol)

    if indicator not in _INDICATOR_DESCRIPTIONS:
        raise ValueError(
            f"Indicator {indicator} not supported. "
            f"Choose from: {list(_INDICATOR_DESCRIPTIONS.keys())}"
        )

    try:
        data = _load_ohlcv_astock(code, curr_date)
        df = wrap(data)
        df["Date"] = df["Date"].dt.strftime("%Y-%m-%d")

        # Trigger stockstats calculation
        df[indicator]

        # Build date -> value lookup
        ind_dict = {}
        for _, row in df.iterrows():
            d = row["Date"]
            v = row[indicator]
            ind_dict[d] = "N/A" if pd.isna(v) else str(round(float(v), 4))

        # Generate output for look_back window
        curr_dt = datetime.strptime(curr_date, "%Y-%m-%d")
        before = curr_dt - relativedelta(days=look_back_days)

        lines = []
        dt = curr_dt
        while dt >= before:
            ds = dt.strftime("%Y-%m-%d")
            val = ind_dict.get(ds, "N/A: Not a trading day (weekend or holiday)")
            lines.append(f"{ds}: {val}")
            dt -= relativedelta(days=1)

        result = (
            f"## {indicator} values for {code} "
            f"from {before.strftime('%Y-%m-%d')} to {curr_date}:\n\n"
            + "\n".join(lines)
            + "\n\n"
            + _INDICATOR_DESCRIPTIONS.get(indicator, "")
        )
        return result

    except Exception as e:
        return f"Error calculating {indicator} for {code}: {str(e)}"


# ---- 3. get_fundamentals ----

_FUNDAMENTALS_STOCK_BASIC_FIELDS = [
    "ts_code",
    "symbol",
    "name",
    "industry",
    "market",
    "list_date",
]

_FUNDAMENTALS_DAILY_BASIC_FIELDS = [
    "ts_code",
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
]


def _fundamentals_error_header(
    code: str,
    ts_code: str,
    as_of: str,
    status: str,
    reason: str,
    trade_date: str = "N/A",
) -> str:
    header = f"# Company Fundamentals for {code} (A-stock)\n"
    header += "# Source: Tushare daily_basic + stock_basic\n"
    header += f"# status: {status}\n"
    header += "# realtime=false\n"
    header += f"# as_of: {as_of}\n"
    header += f"# trade_date: {trade_date}\n"
    header += "# api=daily_basic,stock_basic\n"
    header += f"# ts_code: {ts_code}\n"
    header += f"# empty_reason: {reason}\n\n"
    return header + f"{status}: {reason}"


def _fundamentals_clean_value(value: object) -> str:
    if value is None:
        return "N/A"
    try:
        if pd.isna(value):
            return "N/A"
    except TypeError:
        pass
    text = str(value).strip()
    return text if text else "N/A"


def _first_tushare_row(data: object) -> dict[str, object]:
    df = _tushare_data_to_frame(data)
    if df.empty:
        return {}
    return df.iloc[0].to_dict()


def _fetch_stock_basic_row(client, ts_code: str) -> tuple[dict[str, object], str]:
    fields = ",".join(_FUNDAMENTALS_STOCK_BASIC_FIELDS)
    response = client.call_api(
        "stock_basic",
        params={"list_status": "L"},
        fields=fields,
        cache_key="stock_basic/list_status_L.json",
    )
    if not response.ok:
        return {}, response.error or "tushare_upstream_error"

    df = _tushare_data_to_frame(response.data)
    if df.empty or "ts_code" not in df.columns:
        return {}, "no_stock_basic_match"

    matched = df[df["ts_code"].astype(str) == ts_code]
    if matched.empty:
        return {}, "no_stock_basic_match"
    return matched.iloc[0].to_dict(), ""


def _fetch_daily_basic_row(
    client,
    ts_code: str,
    as_of: str,
    lookback_days: int = 10,
) -> tuple[dict[str, object], str]:
    fields = ",".join(_FUNDAMENTALS_DAILY_BASIC_FIELDS)
    try:
        as_of_date = pd.to_datetime(as_of).normalize()
    except Exception:
        return {}, "parse_error"

    for days_back in range(lookback_days + 1):
        trade_date = (as_of_date - pd.Timedelta(days=days_back)).strftime("%Y%m%d")
        response = client.call_api(
            "daily_basic",
            params={"ts_code": ts_code, "trade_date": trade_date},
            fields=fields,
            cache_key=f"daily_basic/{ts_code}/{trade_date}.json",
        )
        if not response.ok:
            return {}, response.error or "tushare_upstream_error"
        row = _first_tushare_row(response.data)
        if row:
            return row, ""

    return {}, "no_daily_basic_before_as_of"


def get_fundamentals(
    ticker: Annotated[str, "A-stock code"],
    curr_date: Annotated[str, "current date"] = None,
) -> str:
    """Get core fundamentals from Tushare daily_basic + stock_basic."""
    code = _normalize_ticker(ticker)
    ts_code = _tushare_ts_code(code)
    as_of = curr_date or datetime.now().strftime("%Y-%m-%d")

    try:
        from .tushare_client import get_tushare_client

        client = get_tushare_client()
        stock_row, stock_error = _fetch_stock_basic_row(client, ts_code)
        daily_row, daily_error = _fetch_daily_basic_row(client, ts_code, as_of)

        stock_ok = bool(stock_row)
        daily_ok = bool(daily_row)
        if not stock_ok and not daily_ok:
            reason = daily_error if daily_error.startswith("no_") else daily_error or stock_error
            status = "no_data" if reason.startswith("no_") else "technical_error"
            if stock_error and not stock_error.startswith("no_"):
                reason = stock_error
                status = "technical_error"
            return _fundamentals_error_header(code, ts_code, as_of, status, reason)

        missing_sources = []
        empty_reasons = []
        if not stock_ok:
            missing_sources.append("stock_basic")
            empty_reasons.append(stock_error or "no_stock_basic_match")
        if not daily_ok:
            missing_sources.append("daily_basic")
            empty_reasons.append(daily_error or "no_daily_basic_before_as_of")

        status = "ok" if stock_ok and daily_ok else "partial_data"
        trade_date = _fundamentals_clean_value(daily_row.get("trade_date"))

        header = f"# Company Fundamentals for {code} (A-stock)\n"
        header += "# Source: Tushare daily_basic + stock_basic\n"
        header += f"# status: {status}\n"
        header += "# realtime=false\n"
        header += f"# as_of: {as_of}\n"
        header += f"# trade_date: {trade_date}\n"
        header += "# api=daily_basic,stock_basic\n"
        header += f"# ts_code: {ts_code}\n"
        if missing_sources:
            header += f"# missing_source: {','.join(missing_sources)}\n"
            header += f"# empty_reason: {','.join(empty_reasons)}\n"
        header += (
            f"# Data retrieved on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        )

        lines = [
            f"Stock Code: {ts_code}",
            f"Name: {_fundamentals_clean_value(stock_row.get('name'))}",
            f"Industry: {_fundamentals_clean_value(stock_row.get('industry'))}",
            f"Market: {_fundamentals_clean_value(stock_row.get('market'))}",
            f"List Date: {_fundamentals_clean_value(stock_row.get('list_date'))}",
            f"Trade Date: {trade_date}",
            f"Close: {_fundamentals_clean_value(daily_row.get('close'))}",
            f"PE: {_fundamentals_clean_value(daily_row.get('pe'))}",
            f"PE (TTM): {_fundamentals_clean_value(daily_row.get('pe_ttm'))}",
            f"PB: {_fundamentals_clean_value(daily_row.get('pb'))}",
            f"PS: {_fundamentals_clean_value(daily_row.get('ps'))}",
            f"PS (TTM): {_fundamentals_clean_value(daily_row.get('ps_ttm'))}",
            f"Market Cap (10K CNY): {_fundamentals_clean_value(daily_row.get('total_mv'))}",
            f"Float Market Cap (10K CNY): {_fundamentals_clean_value(daily_row.get('circ_mv'))}",
            f"Turnover Rate: {_fundamentals_clean_value(daily_row.get('turnover_rate'))}",
            f"Volume Ratio: {_fundamentals_clean_value(daily_row.get('volume_ratio'))}",
            f"Total Shares (10K): {_fundamentals_clean_value(daily_row.get('total_share'))}",
            f"Float Shares (10K): {_fundamentals_clean_value(daily_row.get('float_share'))}",
        ]

        return header + "\n".join(lines)

    except Exception:
        return _fundamentals_error_header(
            code, ts_code, as_of, "technical_error", "parse_error"
        )


# ---- 4. get_balance_sheet ----


def _sina_stock_code(code: str) -> str:
    """Pure 6-digit code → sina format (sh688017 / sz000001 / bj832000)."""
    return f"{_get_prefix(code)}{code}"


def _get_financial_report_sina(
    code: str, report_type: str, freq: str, curr_date: str = None,
) -> pd.DataFrame:
    """Shared helper: fetch financial report via Sina direct HTTP API.

    report_type: '资产负债表' | '利润表' | '现金流量表'
    """
    _report_type_map = {
        "资产负债表": "fzb",
        "利润表": "lrb",
        "现金流量表": "llb",
    }
    source_type = _report_type_map.get(report_type, "lrb")

    prefix = "sh" if code.startswith("6") else "sz"
    paper_code = f"{prefix}{code}"
    url = "https://quotes.sina.cn/cn/api/openapi.php/CompanyFinanceService.getFinanceReport2022"
    params = {
        "paperCode": paper_code,
        "source": source_type,
        "type": "0",
        "page": "1",
        "num": "20",
    }
    r = _requests.get(url, params=params, headers={"User-Agent": _UA}, timeout=15)
    d = r.json()

    result = d.get("result", {}).get("data", {})
    items = result.get(source_type, [])
    if not isinstance(items, list) or not items:
        return pd.DataFrame()

    df = pd.DataFrame(items)

    # Filter by curr_date
    if curr_date and "报告日" in df.columns:
        df["报告日"] = pd.to_datetime(df["报告日"], errors="coerce")
        cutoff = pd.to_datetime(curr_date)
        df = df[df["报告日"] <= cutoff]

    # Filter by frequency (annual = month 12 reports only)
    if freq.lower() == "annual" and "报告日" in df.columns:
        months = pd.to_datetime(df["报告日"], errors="coerce").dt.month
        df = df[months == 12]

    return df.head(8)


def _tushare_ts_code(code: str) -> str:
    """Pure 6-digit A-share code -> Tushare ts_code."""
    if code.startswith(("6", "9")):
        return f"{code}.SH"
    if code.startswith("8"):
        return f"{code}.BJ"
    return f"{code}.SZ"


def _tushare_data_to_frame(data: object) -> pd.DataFrame:
    """Convert a Tushare Pro data payload into a DataFrame."""
    if not isinstance(data, dict):
        return pd.DataFrame()
    fields = data.get("fields")
    items = data.get("items")
    if not isinstance(fields, list) or not isinstance(items, list):
        return pd.DataFrame()
    return pd.DataFrame(items, columns=fields)


_FINANCIAL_COMMON_FIELDS = [
    "ts_code",
    "ann_date",
    "f_ann_date",
    "end_date",
    "report_type",
    "comp_type",
    "end_type",
]

_FINANCIAL_CORE_FIELDS = {
    "balancesheet": [
        "total_share",
        "money_cap",
        "accounts_receiv",
        "inventories",
        "total_assets",
        "total_liab",
        "total_hldr_eqy_exc_min_int",
    ],
    "cashflow": [
        "net_profit",
        "c_fr_sale_sg",
        "n_cashflow_act",
        "n_cashflow_inv_act",
        "n_cash_flows_fnc_act",
        "c_cash_equ_end_period",
    ],
    "income": [
        "basic_eps",
        "total_revenue",
        "revenue",
        "oper_profit",
        "total_profit",
        "n_income",
        "n_income_attr_p",
    ],
}


def _financial_statement_fields(api_name: str) -> str:
    fields = _FINANCIAL_COMMON_FIELDS + _FINANCIAL_CORE_FIELDS.get(api_name, [])
    return ",".join(dict.fromkeys(fields))


def _short_tushare_statement_error(
    title: str,
    code: str,
    ts_code: str,
    freq: str,
    curr_date: str,
    api_name: str,
    status: str,
    reason: str,
) -> str:
    header = f"# {title} for {code} (A-stock, {freq})\n"
    header += "# Data source: Tushare\n"
    header += f"# API: {api_name}\n"
    header += f"# status: {status}\n"
    header += "# as_of_field: ann_date\n"
    header += "# period_field: end_date\n"
    header += "# statement_scope: consolidated_only\n"
    header += "# report_type_filter: unverified\n"
    header += "# quarterly_policy: cumulative_period\n"
    header += f"# as_of: {curr_date}\n"
    header += f"# ts_code: {ts_code}\n\n"
    return header + f"{status}: {reason}"


def _get_financial_statement_tushare(
    code: str,
    api_name: str,
    title: str,
    freq: str,
    curr_date: str = None,
) -> str:
    from .tushare_client import get_tushare_client

    normalized_freq = (freq or "quarterly").lower()
    as_of = curr_date or datetime.now().strftime("%Y-%m-%d")
    as_of_compact = as_of.replace("-", "")
    ts_code = _tushare_ts_code(code)
    fields = _financial_statement_fields(api_name)

    response = get_tushare_client().call_api(
        api_name,
        params={"ts_code": ts_code},
        fields=fields,
        cache_key=f"{api_name}/{ts_code}/latest.json",
    )

    if not response.ok:
        return _short_tushare_statement_error(
            title,
            code,
            ts_code,
            normalized_freq,
            as_of,
            api_name,
            "technical_error",
            response.error or "tushare_upstream_error",
        )

    try:
        df = _tushare_data_to_frame(response.data)
        if df.empty:
            return _short_tushare_statement_error(
                title,
                code,
                ts_code,
                normalized_freq,
                as_of,
                api_name,
                "no_data",
                "no_statement_before_as_of",
            )

        for column in ("ann_date", "f_ann_date", "end_date"):
            if column in df.columns:
                df[column] = df[column].astype(str).str.replace("-", "", regex=False)

        if "ann_date" in df.columns:
            df = df[df["ann_date"].str.len().eq(8)]
            df = df[df["ann_date"] <= as_of_compact]
        if "end_date" in df.columns:
            df = df[df["end_date"].str.len().eq(8)]
            if normalized_freq == "annual":
                df = df[df["end_date"].str.endswith("1231")]
            else:
                df = df[df["end_date"].str[-4:].isin(["0331", "0630", "0930", "1231"])]

        if df.empty:
            return _short_tushare_statement_error(
                title,
                code,
                ts_code,
                normalized_freq,
                as_of,
                api_name,
                "no_data",
                "no_statement_before_as_of",
            )

        sort_cols = [col for col in ("ann_date", "end_date") if col in df.columns]
        if sort_cols:
            df = df.sort_values(sort_cols, ascending=[False] * len(sort_cols))
        df = df.head(8).reset_index(drop=True)

        preferred = _FINANCIAL_COMMON_FIELDS + _FINANCIAL_CORE_FIELDS.get(api_name, [])
        ordered_cols = [col for col in preferred if col in df.columns]
        remaining_cols = [col for col in df.columns if col not in ordered_cols]
        csv_string = df[ordered_cols + remaining_cols].to_csv(index=False)

    except Exception:
        return _short_tushare_statement_error(
            title,
            code,
            ts_code,
            normalized_freq,
            as_of,
            api_name,
            "technical_error",
            "parse_error",
        )

    header = f"# {title} for {code} (A-stock, {normalized_freq})\n"
    header += "# Data source: Tushare\n"
    header += f"# API: {api_name}\n"
    header += "# status: ok\n"
    header += "# as_of_field: ann_date\n"
    header += "# period_field: end_date\n"
    header += "# statement_scope: consolidated_only\n"
    header += "# report_type_filter: unverified\n"
    header += "# quarterly_policy: cumulative_period\n"
    header += f"# as_of: {as_of}\n"
    header += f"# ts_code: {ts_code}\n"
    header += f"# rows: {len(df)}\n"
    header += f"# cache_hit: {str(response.cache_hit).lower()}\n"
    header += (
        f"# Data retrieved on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    )

    return header + csv_string


def get_balance_sheet(
    ticker: Annotated[str, "A-stock code"],
    freq: Annotated[str, "frequency: 'annual' or 'quarterly'"] = "quarterly",
    curr_date: Annotated[str, "current date in YYYY-MM-DD format"] = None,
) -> str:
    """Get balance sheet via Tushare Pro balancesheet."""
    code = _normalize_ticker(ticker)
    return _get_financial_statement_tushare(
        code, "balancesheet", "Balance Sheet", freq, curr_date
    )


# ---- 5. get_cashflow ----


def get_cashflow(
    ticker: Annotated[str, "A-stock code"],
    freq: Annotated[str, "frequency: 'annual' or 'quarterly'"] = "quarterly",
    curr_date: Annotated[str, "current date in YYYY-MM-DD format"] = None,
) -> str:
    """Get cash flow statement via Tushare Pro cashflow."""
    code = _normalize_ticker(ticker)
    return _get_financial_statement_tushare(
        code, "cashflow", "Cash Flow", freq, curr_date
    )


# ---- 6. get_income_statement ----


def get_income_statement(
    ticker: Annotated[str, "A-stock code"],
    freq: Annotated[str, "frequency: 'annual' or 'quarterly'"] = "quarterly",
    curr_date: Annotated[str, "current date in YYYY-MM-DD format"] = None,
) -> str:
    """Get income statement via Tushare Pro income."""
    code = _normalize_ticker(ticker)
    return _get_financial_statement_tushare(
        code, "income", "Income Statement", freq, curr_date
    )


# ---- 7. get_news ----

_STOCK_NEWS_FIELDS = ["pub_time", "source", "title", "summary", "url"]


def _fetch_news_eastmoney(code: str, page_size: int = 20) -> list[dict]:
    """Direct East Money search API for individual stock news."""
    url = "https://search-api-web.eastmoney.com/search/jsonp"
    inner_param = {
        "uid": "",
        "keyword": code,
        "type": ["cmsArticleWebOld"],
        "client": "web",
        "clientType": "web",
        "clientVersion": "curr",
        "param": {
            "cmsArticleWebOld": {
                "searchScope": "default",
                "sort": "default",
                "pageIndex": 1,
                "pageSize": page_size,
                "preTag": "",
                "postTag": "",
            }
        },
    }
    params = {
        "cb": "callback",
        "param": _json.dumps(inner_param, ensure_ascii=False),
        "_": "1",
    }
    headers = {
        "Referer": "https://so.eastmoney.com/",
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36"
        ),
    }

    resp = _em_get(url, params=params, headers=headers, timeout=15)
    resp.raise_for_status()
    text = resp.text
    text = text[text.index("(") + 1 : text.rindex(")")]
    data = _json.loads(text)

    articles: list[dict] = []
    for item in data.get("result", {}).get("cmsArticleWebOld", []):
        articles.append({
            "title": item.get("title", ""),
            "content": item.get("content", ""),
            "time": item.get("date", ""),
            "source": item.get("mediaName", "东方财富"),
            "url": item.get("url", ""),
        })
    return articles


def _fetch_news_sina(code: str, page_size: int = 20) -> list[dict]:
    """Sina Finance stock news API (backup source)."""
    prefix = "sh" if code.startswith(("6", "9")) else "sz"
    url = (
        f"https://vip.stock.finance.sina.com.cn/corp/view/"
        f"vCB_AllNewsStock.php?symbol={prefix}{code}&Page=1"
    )
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36"
        ),
        "Referer": "https://finance.sina.com.cn/",
    }

    resp = _requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    resp.encoding = "gb2312"
    html = resp.text

    articles: list[dict] = []
    rows = _re.findall(
        r"(\d{4}-\d{2}-\d{2})\s*(?:&nbsp;)*(\d{2}:\d{2})\s*(?:&nbsp;)*"
        r"<a[^>]+href='([^']+)'[^>]*>([^<]+)</a>",
        html,
    )
    for date_str, time_str, link, title in rows[:page_size]:
        articles.append({
            "title": title.strip(),
            "content": "",
            "time": f"{date_str} {time_str}",
            "source": "新浪财经",
            "url": link,
        })
    return articles


def _stock_news_contract_header(
    *,
    status: str,
    symbol: str,
    as_of: str,
    trade_date: str,
    coverage: str = "individual_stock",
    fallback: str = "none",
    empty_reason: str = "none",
    error_type: str = "none",
    raw_error_suppressed: bool = False,
    notes: str = "",
) -> str:
    return _build_data_source_contract_header(
        status=status,
        source="Eastmoney stock news + Sina fallback",
        data_type="news",
        query_target="stock",
        symbol=symbol,
        as_of=as_of,
        trade_date=trade_date,
        unit="news_items",
        coverage=coverage,
        fallback=fallback,
        empty_reason=empty_reason,
        error_type=error_type,
        raw_error_suppressed=raw_error_suppressed,
        limitations="stock-specific news only; no market-wide, macro, or filing feed used",
        notes=notes,
    )


def _stock_news_short_message(
    *,
    status: str,
    symbol: str,
    as_of: str,
    trade_date: str = "N/A",
    coverage: str = "individual_stock",
    fallback: str = "none",
    empty_reason: str = "none",
    error_type: str = "none",
    raw_error_suppressed: bool = False,
    message: str,
) -> str:
    header = _stock_news_contract_header(
        status=status,
        symbol=symbol,
        as_of=as_of,
        trade_date=trade_date,
        coverage=coverage,
        fallback=fallback,
        empty_reason=empty_reason,
        error_type=error_type,
        raw_error_suppressed=raw_error_suppressed,
    )
    return f"{header}\n\n{message}"


def _stock_news_code(ticker: str) -> tuple[str, bool]:
    try:
        code = _normalize_ticker(str(ticker))
    except Exception:
        return str(ticker or "N/A"), False
    if not _re.fullmatch(r"\d{6}", code):
        return code or "N/A", False
    return code, True


def _stock_news_window(start_date: str, end_date: str) -> tuple[str, datetime, datetime]:
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    if start_dt > end_dt:
        raise ValueError("start_date after end_date")
    return end_dt.strftime("%Y-%m-%d"), start_dt, end_dt


def _stock_news_fetch_source(
    source: str,
    code: str,
    limit: int,
) -> tuple[list[dict], str]:
    try:
        if source == "eastmoney":
            return _fetch_news_eastmoney(code, page_size=limit), ""
        if source == "sina":
            return _fetch_news_sina(code, page_size=limit), ""
    except Exception as exc:
        return [], _classify_data_source_error(exc)
    return [], "unknown"


def _filter_stock_news_by_date(
    articles: list[dict],
    start_dt: datetime,
    end_dt: datetime,
) -> list[dict]:
    filtered: list[dict] = []
    for article in articles:
        pub_time = str(article.get("time", "") or "")
        try:
            pub_dt = datetime.strptime(pub_time[:10], "%Y-%m-%d")
            if pub_dt < start_dt or pub_dt > end_dt:
                continue
        except (ValueError, IndexError):
            pass
        filtered.append(article)
    return filtered


def _dedupe_stock_news(articles: list[dict]) -> list[dict]:
    seen: set[str] = set()
    unique: list[dict] = []
    for article in articles:
        title = str(article.get("title", "") or "").strip()
        if not title or title in seen:
            continue
        seen.add(title)
        unique.append(article)
    return unique


def _stock_news_markdown_table(articles: list[dict]) -> str:
    lines = [
        "| " + " | ".join(_STOCK_NEWS_FIELDS) + " |",
        "| " + " | ".join("---" for _ in _STOCK_NEWS_FIELDS) + " |",
    ]
    for article in articles:
        values: list[str] = []
        for field in _STOCK_NEWS_FIELDS:
            source_key = "time" if field == "pub_time" else "content" if field == "summary" else field
            text = str(article.get(source_key, "") or "").replace("\n", " ").replace("|", "/")
            if len(text) > 220:
                text = text[:217] + "..."
            values.append(text)
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def _format_stock_news_output(
    *,
    status: str,
    code: str,
    as_of: str,
    start_date: str,
    end_date: str,
    articles: list[dict],
    fallback: str,
    raw_error_suppressed: bool,
    notes: str,
) -> str:
    pub_dates = [
        str(article.get("time", ""))[:10]
        for article in articles
        if str(article.get("time", ""))[:10]
    ]
    trade_date = max(pub_dates) if pub_dates else "N/A"
    header = _stock_news_contract_header(
        status=status,
        symbol=code,
        as_of=as_of,
        trade_date=trade_date,
        fallback=fallback,
        raw_error_suppressed=raw_error_suppressed,
        notes=f"query_window={start_date}-{end_date}; rows={len(articles)}; {notes}".rstrip("; "),
    )
    lines = [
        f"# Stock-Specific News for {code}",
        "",
        _stock_news_markdown_table(articles),
    ]
    return f"{header}\n\n" + "\n".join(lines)


def get_news(
    ticker: Annotated[str, "A-stock code"],
    start_date: Annotated[str, "Start date yyyy-mm-dd"],
    end_date: Annotated[str, "End date yyyy-mm-dd"],
) -> str:
    """Get stock-specific news via East Money direct API (Sina as fallback)."""
    code, valid_symbol = _stock_news_code(ticker)
    if not valid_symbol:
        return _stock_news_short_message(
            status="invalid_input",
            symbol=code,
            as_of=str(end_date),
            coverage="symbol_unresolved",
            empty_reason="invalid_or_unresolved_ticker",
            message="Invalid or unresolved A-share ticker for stock news query.",
        )

    try:
        as_of, start_dt, end_dt = _stock_news_window(start_date, end_date)
    except Exception:
        return _stock_news_short_message(
            status="invalid_input",
            symbol=code,
            as_of=str(end_date),
            empty_reason="not_applicable",
            message="Invalid date window for stock news query.",
        )

    eastmoney_articles, eastmoney_error = _stock_news_fetch_source(
        "eastmoney", code, 20
    )
    eastmoney_filtered = _dedupe_stock_news(
        _filter_stock_news_by_date(eastmoney_articles, start_dt, end_dt)
    )
    if eastmoney_filtered:
        return _format_stock_news_output(
            status="ok",
            code=code,
            as_of=as_of,
            start_date=start_date,
            end_date=end_date,
            articles=eastmoney_filtered,
            fallback="none",
            raw_error_suppressed=False,
            notes="source_used=Eastmoney",
        )

    sina_articles, sina_error = _stock_news_fetch_source("sina", code, 20)
    sina_filtered = _dedupe_stock_news(
        _filter_stock_news_by_date(sina_articles, start_dt, end_dt)
    )
    if sina_filtered:
        fallback_reason = "Eastmoney unavailable" if eastmoney_error else "Eastmoney empty_or_filtered"
        return _format_stock_news_output(
            status="partial_data",
            code=code,
            as_of=as_of,
            start_date=start_date,
            end_date=end_date,
            articles=sina_filtered,
            fallback="Eastmoney->Sina",
            raw_error_suppressed=bool(eastmoney_error),
            notes=f"{fallback_reason}; source_used=Sina",
        )

    if eastmoney_error and sina_error:
        error_type = (
            eastmoney_error
            if eastmoney_error == sina_error
            else "mixed_source_error"
        )
        return _stock_news_short_message(
            status="technical_error",
            symbol=code,
            as_of=as_of,
            fallback="Eastmoney->Sina",
            error_type=error_type,
            raw_error_suppressed=True,
            message="Data source request failed; raw technical details suppressed.",
        )

    empty_reason = "filtered_out" if eastmoney_articles or sina_articles else "source_empty"
    return _stock_news_short_message(
        status="empty",
        symbol=code,
        as_of=as_of,
        fallback="Eastmoney->Sina",
        empty_reason=empty_reason,
        message=(
            "Stock-specific news sources returned no rows for the requested "
            "stock and date window."
        ),
    )


# ---- 8. get_global_news ----

_GLOBAL_NEWS_TUSHARE_FIELDS = [
    "title",
    "pub_time",
    "src",
]


def _global_news_contract_header(
    *,
    status: str,
    as_of: str,
    trade_date: str,
    empty_reason: str = "none",
    error_type: str = "none",
    raw_error_suppressed: bool = False,
    notes: str = "",
) -> str:
    return _build_data_source_contract_header(
        status=status,
        source="CLS + Eastmoney 7x24 + Tushare major_news",
        data_type="global_news",
        query_target="market",
        symbol="N/A",
        as_of=as_of,
        trade_date=trade_date,
        unit="news_items",
        coverage="market_wide",
        fallback="mixed_sources",
        empty_reason=empty_reason,
        error_type=error_type,
        raw_error_suppressed=raw_error_suppressed,
        limitations="market/global/macro news scope; no symbol query",
        notes=notes,
    )


def _global_news_short_message(
    *,
    status: str,
    as_of: str,
    trade_date: str = "N/A",
    empty_reason: str = "none",
    error_type: str = "none",
    raw_error_suppressed: bool = False,
    message: str,
) -> str:
    header = _global_news_contract_header(
        status=status,
        as_of=as_of,
        trade_date=trade_date,
        empty_reason=empty_reason,
        error_type=error_type,
        raw_error_suppressed=raw_error_suppressed,
    )
    return f"{header}\n\n{message}"


def _global_news_window(curr_date: str, look_back_days: int) -> tuple[str, str]:
    as_of_dt = pd.to_datetime(curr_date).normalize()
    days = max(0, int(look_back_days))
    start_dt = as_of_dt - pd.Timedelta(days=days)
    return as_of_dt.strftime("%Y-%m-%d"), start_dt.strftime("%Y-%m-%d")


def _global_news_markdown_table(rows: list[dict], limit: int) -> str:
    columns = ["pub_time", "source", "title", "summary"]
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for row in rows[:limit]:
        values: list[str] = []
        for column in columns:
            text = str(row.get(column, "") or "").replace("\n", " ").replace("|", "/")
            if len(text) > 220:
                text = text[:217] + "..."
            values.append(text)
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def _fetch_cls_market_news(limit: int) -> tuple[list[dict], str]:
    try:
        cls_url = "https://www.cls.cn/nodeapi/telegraphList"
        cls_params = {"rn": str(limit), "page": "1"}
        cls_headers = {"User-Agent": _UA, "Referer": "https://www.cls.cn/"}
        r_cls = _requests.get(cls_url, params=cls_params, headers=cls_headers, timeout=10)
        r_cls.raise_for_status()
        d_cls = r_cls.json()
        rows: list[dict] = []
        for item in d_cls.get("data", {}).get("roll_data", []):
            title = item.get("title", "") or item.get("brief", "")
            content = item.get("content", "") or item.get("brief", "")
            ctime = item.get("ctime", "")
            pub_time = ""
            if ctime:
                try:
                    pub_time = datetime.fromtimestamp(int(ctime)).strftime("%Y-%m-%d %H:%M")
                except (ValueError, TypeError, OSError):
                    pub_time = str(ctime)
            if title:
                rows.append({
                    "title": title,
                    "summary": content,
                    "pub_time": pub_time,
                    "source": "CLS Wire",
                })
        return rows, ""
    except Exception as exc:
        logger.debug("CLS news fetch failed")
        return [], _classify_data_source_error(exc)


def _fetch_eastmoney_market_news(limit: int) -> tuple[list[dict], str]:
    try:
        em_url = "https://np-weblist.eastmoney.com/comm/web/getFastNewsList"
        em_params = {
            "client": "web",
            "biz": "web_724",
            "fastColumn": "102",
            "sortEnd": "",
            "pageSize": str(limit),
            "req_trace": str(uuid.uuid4()),
        }
        em_headers = {"User-Agent": _UA, "Referer": "https://kuaixun.eastmoney.com/"}
        r_em = _em_get(em_url, params=em_params, headers=em_headers, timeout=10)
        r_em.raise_for_status()
        d_em = r_em.json()
        rows: list[dict] = []
        for item in d_em.get("data", {}).get("fastNewsList", []):
            title = item.get("title", "")
            if title:
                rows.append({
                    "title": title,
                    "summary": item.get("summary", ""),
                    "pub_time": item.get("showTime", ""),
                    "source": "Eastmoney 7x24",
                })
        return rows, ""
    except Exception as exc:
        logger.debug("Eastmoney global news fetch failed")
        return [], _classify_data_source_error(exc)


def _fetch_tushare_major_news(
    as_of: str,
    start_date: str,
    limit: int,
) -> tuple[list[dict], str]:
    try:
        from .tushare_client import get_tushare_client

        client = get_tushare_client()
        response = client.call_api(
            "major_news",
            params={
                "start_date": f"{start_date} 00:00:00",
                "end_date": f"{as_of} 23:59:59",
            },
            fields=",".join(_GLOBAL_NEWS_TUSHARE_FIELDS),
            cache_key=f"major_news/{start_date}_{as_of}.json",
            use_cache=False,
        )
        if not response.ok:
            return [], _classify_data_source_error(response.error or response.message or "")

        df = _tushare_data_to_frame(response.data)
        if df.empty:
            return [], ""
        rows: list[dict] = []
        for _, row in df.head(limit).iterrows():
            title = row.get("title", "")
            if title:
                rows.append({
                    "title": title,
                    "summary": "",
                    "pub_time": row.get("pub_time", ""),
                    "source": row.get("src", "") or "Tushare major_news",
                })
        return rows, ""
    except Exception as exc:
        return [], _classify_data_source_error(exc)


def _dedupe_global_news(rows: list[dict]) -> list[dict]:
    seen: set[str] = set()
    unique: list[dict] = []
    for row in rows:
        title = str(row.get("title", "")).strip()
        if not title or title in seen:
            continue
        seen.add(title)
        unique.append(row)
    return unique


def _format_global_news_output(
    *,
    status: str,
    as_of: str,
    start_date: str,
    cls_em_rows: list[dict],
    tushare_rows: list[dict],
    unavailable_sources: list[str],
    raw_error_suppressed: bool,
    limit: int,
) -> str:
    pub_dates = [
        str(row.get("pub_time", ""))[:10]
        for row in cls_em_rows + tushare_rows
        if str(row.get("pub_time", ""))[:10]
    ]
    trade_date = max(pub_dates) if pub_dates else "N/A"
    available_sources = []
    if cls_em_rows:
        available_sources.append("CLS/Eastmoney")
    if tushare_rows:
        available_sources.append("Tushare major_news")
    notes = (
        f"query_window={start_date}-{as_of}; "
        f"available_sources={','.join(available_sources) if available_sources else 'none'}; "
        f"unavailable_sources={','.join(unavailable_sources) if unavailable_sources else 'none'}"
    )
    header = _global_news_contract_header(
        status=status,
        as_of=as_of,
        trade_date=trade_date,
        raw_error_suppressed=raw_error_suppressed,
        notes=notes,
    )
    lines = ["# Global / Market News", ""]
    if cls_em_rows:
        lines.extend([
            "## CLS / Eastmoney Market News",
            "",
            _global_news_markdown_table(cls_em_rows, limit),
            "",
        ])
    if tushare_rows:
        lines.extend([
            "## Tushare Major News",
            "",
            _global_news_markdown_table(tushare_rows, limit),
            "",
        ])
    return f"{header}\n\n" + "\n".join(lines).rstrip()


def get_global_news(
    curr_date: Annotated[str, "Current date yyyy-mm-dd"],
    look_back_days: Annotated[int, "Days to look back"] = 7,
    limit: Annotated[int, "Max articles"] = 10,
) -> str:
    """Get market/global financial news via CLS, Eastmoney, and Tushare."""
    try:
        as_of, start_date = _global_news_window(curr_date, look_back_days)
    except Exception:
        as_of = str(curr_date)
        return _global_news_short_message(
            status="technical_error",
            as_of=as_of,
            error_type="parse_error",
            raw_error_suppressed=True,
            message="Data source request failed; raw technical details suppressed.",
        )

    cls_rows, cls_error = _fetch_cls_market_news(limit)
    em_rows, em_error = _fetch_eastmoney_market_news(limit)
    tushare_rows, tushare_error = _fetch_tushare_major_news(as_of, start_date, limit)

    cls_em_rows = _dedupe_global_news(cls_rows + em_rows)
    tushare_rows = _dedupe_global_news(tushare_rows)
    unavailable_sources = []
    source_errors = []
    if cls_error:
        unavailable_sources.append("CLS")
        source_errors.append(cls_error)
    if em_error:
        unavailable_sources.append("Eastmoney 7x24")
        source_errors.append(em_error)
    if tushare_error:
        unavailable_sources.append("Tushare major_news")
        source_errors.append(tushare_error)

    if cls_em_rows or tushare_rows:
        status = "partial_data" if unavailable_sources else "ok"
        return _format_global_news_output(
            status=status,
            as_of=as_of,
            start_date=start_date,
            cls_em_rows=cls_em_rows,
            tushare_rows=tushare_rows,
            unavailable_sources=unavailable_sources,
            raw_error_suppressed=bool(unavailable_sources),
            limit=limit,
        )

    if source_errors:
        error_type = source_errors[0] if len(set(source_errors)) == 1 else "mixed_source_error"
        return _global_news_short_message(
            status="technical_error",
            as_of=as_of,
            error_type=error_type,
            raw_error_suppressed=True,
            message="Data source request failed; raw technical details suppressed.",
        )

    return _global_news_short_message(
        status="empty",
        as_of=as_of,
        empty_reason="source_empty",
        message=(
            "Global/market news sources returned no rows for the requested "
            "date window."
        ),
    )


# ---- 9. get_insider_transactions ----

_SHAREHOLDER_TRADE_FIELDS = [
    "ts_code",
    "ann_date",
    "holder_name",
    "holder_type",
    "in_de",
    "change_vol",
    "change_ratio",
    "after_share",
    "after_ratio",
    "begin_date",
    "close_date",
]

_SHAREHOLDER_NUMBER_FIELDS = [
    "ts_code",
    "ann_date",
    "end_date",
    "holder_num",
]

_TOP10_HOLDER_FIELDS = [
    "ts_code",
    "ann_date",
    "end_date",
    "holder_name",
    "hold_amount",
    "hold_ratio",
    "hold_float_ratio",
]


def _shareholder_contract_header(
    *,
    status: str,
    symbol: str,
    as_of: str,
    trade_date: str,
    coverage: str = "individual_stock",
    empty_reason: str = "none",
    error_type: str = "none",
    raw_error_suppressed: bool = False,
    notes: str = "",
) -> str:
    return _build_data_source_contract_header(
        status=status,
        source="Tushare stk_holdertrade + top10_holders + top10_floatholders + stk_holdernumber",
        data_type="shareholder_f10",
        query_target="stock",
        symbol=symbol,
        as_of=as_of,
        trade_date=trade_date,
        unit="shares; percent; holder_num households; other fields raw Tushare",
        coverage=coverage,
        fallback="none",
        empty_reason=empty_reason,
        error_type=error_type,
        raw_error_suppressed=raw_error_suppressed,
        limitations=(
            "compatible function name retained; output is A-share shareholder/F10 "
            "and holder-change data, not US-style insider transaction data"
        ),
        notes=notes,
    )


def _shareholder_short_message(
    *,
    status: str,
    symbol: str,
    as_of: str,
    trade_date: str = "N/A",
    coverage: str = "individual_stock",
    empty_reason: str = "none",
    error_type: str = "none",
    raw_error_suppressed: bool = False,
    message: str,
) -> str:
    header = _shareholder_contract_header(
        status=status,
        symbol=symbol,
        as_of=as_of,
        trade_date=trade_date,
        coverage=coverage,
        empty_reason=empty_reason,
        error_type=error_type,
        raw_error_suppressed=raw_error_suppressed,
    )
    return f"{header}\n\n{message}"


def _shareholder_ts_code(ticker: str) -> tuple[str, bool]:
    try:
        code = _normalize_ticker(str(ticker))
    except Exception:
        return str(ticker or "N/A"), False
    if not _re.fullmatch(r"\d{6}", code):
        return code or "N/A", False
    return _tushare_ts_code(code), True


def _shareholder_date_window(as_of: str, days: int = 365) -> tuple[str, str, str]:
    as_of_dt = pd.to_datetime(as_of).normalize()
    start_date = (as_of_dt - pd.Timedelta(days=days)).strftime("%Y%m%d")
    end_date = as_of_dt.strftime("%Y%m%d")
    return as_of_dt.strftime("%Y-%m-%d"), start_date, end_date


def _shareholder_frame(data: object, fields: list[str], ts_code: str) -> pd.DataFrame:
    df = _tushare_data_to_frame(data)
    if df.empty:
        return df
    if "ts_code" not in df.columns:
        raise ValueError("unexpected_schema: shareholder data missing ts_code")

    df = df.copy()
    df["ts_code"] = df["ts_code"].astype(str).str.upper()
    df = df[df["ts_code"] == ts_code.upper()]
    if df.empty:
        return df

    available_columns = [field for field in fields if field in df.columns]
    return df[available_columns].reset_index(drop=True)


def _latest_report_rows(df: pd.DataFrame, date_field: str, limit: int) -> pd.DataFrame:
    if df.empty or date_field not in df.columns:
        return df.head(limit).reset_index(drop=True)
    df = df.copy()
    df[date_field] = df[date_field].astype(str).str.replace("-", "", regex=False)
    valid = df[df[date_field].str.len().eq(8)]
    if valid.empty:
        return df.head(limit).reset_index(drop=True)
    latest = valid[date_field].max()
    latest_rows = valid[valid[date_field] == latest]
    return latest_rows.head(limit).reset_index(drop=True)


def _recent_rows(df: pd.DataFrame, date_field: str, limit: int) -> pd.DataFrame:
    if df.empty or date_field not in df.columns:
        return df.head(limit).reset_index(drop=True)
    df = df.copy()
    df[date_field] = df[date_field].astype(str).str.replace("-", "", regex=False)
    return df.sort_values(date_field, ascending=False).head(limit).reset_index(drop=True)


def _shareholder_markdown_table(df: pd.DataFrame, columns: list[str]) -> str:
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for _, row in df.iterrows():
        values: list[str] = []
        for column in columns:
            value = row.get(column, "")
            if pd.isna(value):
                values.append("")
            elif isinstance(value, float):
                values.append(f"{value:.2f}")
            else:
                text = str(value).replace("\n", " ").replace("|", "/")
                if len(text) > 180:
                    text = text[:177] + "..."
                values.append(text)
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def _format_shareholder_output(
    *,
    status: str,
    ts_code: str,
    as_of: str,
    start_date: str,
    end_date: str,
    sections: list[tuple[str, pd.DataFrame, list[str]]],
    error_apis: list[str],
) -> str:
    date_values: list[str] = []
    for _, df, _ in sections:
        for column in ("ann_date", "end_date", "close_date"):
            if column in df.columns:
                date_values.extend(df[column].dropna().astype(str).tolist())
    trade_date = max([value.replace("-", "") for value in date_values if len(value.replace("-", "")) == 8], default="N/A")
    notes = f"query_window={start_date}-{end_date}; sections={len(sections)}"
    if error_apis:
        notes += f"; unavailable_apis={','.join(error_apis)}"
    header = _shareholder_contract_header(
        status=status,
        symbol=ts_code,
        as_of=as_of,
        trade_date=trade_date,
        notes=notes,
    )
    lines = ["# A-share Shareholder / F10 Data", ""]
    for title, df, fields in sections:
        columns = [field for field in fields if field in df.columns]
        lines.extend([
            f"## {title}",
            "",
            _shareholder_markdown_table(df, columns),
            "",
        ])
    return f"{header}\n\n" + "\n".join(lines).rstrip()


def get_insider_transactions(
    ticker: Annotated[str, "A-stock code"],
) -> str:
    """Get A-share shareholder/F10 data via Tushare shareholder APIs."""
    as_of_input = datetime.now().strftime("%Y-%m-%d")
    ts_code, valid_symbol = _shareholder_ts_code(ticker)
    if not valid_symbol:
        return _shareholder_short_message(
            status="invalid_input",
            symbol=ts_code,
            as_of=as_of_input,
            coverage="symbol_unresolved",
            empty_reason="invalid_or_unresolved_ticker",
            message="Invalid or unresolved A-share ticker for shareholder/F10 query.",
        )

    try:
        as_of, start_date, end_date = _shareholder_date_window(as_of_input)
    except Exception:
        return _shareholder_short_message(
            status="invalid_input",
            symbol=ts_code,
            as_of=as_of_input,
            empty_reason="not_applicable",
            message="Invalid date input for shareholder/F10 query.",
        )

    try:
        from .tushare_client import get_tushare_client

        client = get_tushare_client()
        sections: list[tuple[str, pd.DataFrame, list[str]]] = []
        error_apis: list[str] = []
        api_errors: list[str] = []

        api_specs = [
            (
                "stk_holdertrade",
                {"ts_code": ts_code, "start_date": start_date, "end_date": end_date},
                _SHAREHOLDER_TRADE_FIELDS,
                "Important Shareholder Increase / Decrease Records",
                lambda df: _recent_rows(df, "ann_date", 10),
            ),
            (
                "stk_holdernumber",
                {"ts_code": ts_code, "start_date": start_date, "end_date": end_date},
                _SHAREHOLDER_NUMBER_FIELDS,
                "Shareholder Count",
                lambda df: _recent_rows(df, "end_date", 8),
            ),
            (
                "top10_holders",
                {"ts_code": ts_code},
                _TOP10_HOLDER_FIELDS,
                "Top 10 Shareholders",
                lambda df: _latest_report_rows(df, "end_date", 10),
            ),
            (
                "top10_floatholders",
                {"ts_code": ts_code},
                _TOP10_HOLDER_FIELDS,
                "Top 10 Floating Shareholders",
                lambda df: _latest_report_rows(df, "end_date", 10),
            ),
        ]

        for api_name, params, fields, title, reducer in api_specs:
            response = client.call_api(
                api_name,
                params=params,
                fields=",".join(fields),
                cache_key=f"{api_name}/{ts_code}.json",
                use_cache=False,
            )
            if not response.ok:
                error_apis.append(api_name)
                api_errors.append(response.error or response.message or "")
                continue

            df = _shareholder_frame(response.data, fields, ts_code)
            if not df.empty:
                reduced = reducer(df)
                if not reduced.empty:
                    sections.append((title, reduced, fields))

        if sections:
            status = "partial_data" if error_apis else "ok"
            return _format_shareholder_output(
                status=status,
                ts_code=ts_code,
                as_of=as_of,
                start_date=start_date,
                end_date=end_date,
                sections=sections,
                error_apis=error_apis,
            )

        if error_apis:
            error_type = _classify_data_source_error(api_errors[0] if api_errors else "")
            return _shareholder_short_message(
                status="technical_error",
                symbol=ts_code,
                as_of=as_of,
                error_type=error_type,
                raw_error_suppressed=True,
                message="Data source request failed; raw technical details suppressed.",
            )

        return _shareholder_short_message(
            status="empty",
            symbol=ts_code,
            as_of=as_of,
            empty_reason="no_coverage",
            message=(
                "Tushare shareholder APIs returned no shareholder/F10 rows for "
                "the requested stock."
            ),
        )

    except Exception as exc:
        error_type = _classify_data_source_error(exc)
        return _shareholder_short_message(
            status="technical_error",
            symbol=ts_code,
            as_of=as_of_input,
            error_type=error_type,
            raw_error_suppressed=True,
            message="Data source request failed; raw technical details suppressed.",
        )


# ---- 10. get_profit_forecast ----

_REPORT_RC_FIELDS = [
    "ts_code",
    "report_date",
    "quarter",
    "org_name",
    "author_name",
    "eps",
    "np",
    "op_rt",
    "rating",
]


def _profit_forecast_error_header(
    code: str,
    ts_code: str,
    as_of: str,
    status: str,
    reason: str,
    stale_forecast_window: bool = False,
) -> str:
    header = f"# Consensus EPS Forecast for {code} (A-stock)\n"
    header += "# Source: Tushare report_rc sell-side forecast aggregation\n"
    header += f"# status: {status}\n"
    header += "# api=report_rc\n"
    header += "# forecast_type=sell_side_forecast\n"
    header += "# not_company_guidance=true\n"
    header += f"# as_of: {as_of}\n"
    header += "# as_of_field=report_date\n"
    header += "# report_date_range: N/A\n"
    header += "# source_count: 0\n"
    header += "# source_org_count: 0\n"
    header += "# low_coverage=true\n"
    header += f"# stale_forecast_window={str(stale_forecast_window).lower()}\n"
    header += f"# ts_code: {ts_code}\n"
    header += f"# empty_reason: {reason}\n"
    header += "# note: sell-side forecast aggregation; not company guidance, earnings preview, earnings flash, or historical financial indicators\n\n"
    return header + f"{status}: {reason}"


def _report_rc_frame(data: object, as_of: str) -> pd.DataFrame:
    df = _tushare_data_to_frame(data)
    if df.empty or "report_date" not in df.columns:
        return pd.DataFrame()
    as_of_compact = _compact_date(as_of)
    df = df.copy()
    df["report_date"] = df["report_date"].astype(str).str.replace("-", "", regex=False)
    df = df[df["report_date"].str.len().eq(8)]
    df = df[df["report_date"] <= as_of_compact]
    if "quarter" in df.columns:
        df = df[df["quarter"].notna()]
        df = df[df["quarter"].astype(str).str.strip() != ""]
    return df.reset_index(drop=True)


def _fetch_report_rc(client, ts_code: str, as_of: str, window_days: int) -> tuple[pd.DataFrame, str]:
    fields = ",".join(_REPORT_RC_FIELDS)
    try:
        as_of_date = pd.to_datetime(as_of).normalize()
    except Exception:
        return pd.DataFrame(), "parse_error"
    start_date = (as_of_date - pd.Timedelta(days=window_days)).strftime("%Y%m%d")
    end_date = as_of_date.strftime("%Y%m%d")
    response = client.call_api(
        "report_rc",
        params={"ts_code": ts_code, "start_date": start_date, "end_date": end_date},
        fields=fields,
        cache_key=f"report_rc/{ts_code}/{start_date}_{end_date}.json",
    )
    if not response.ok:
        return pd.DataFrame(), response.error or "tushare_upstream_error"
    df = _report_rc_frame(response.data, as_of)
    if df.empty:
        return df, "no_sell_side_forecast"
    return df, ""


def _dedupe_report_rc(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    work = df.copy()
    for col in ("org_name", "quarter"):
        if col not in work.columns:
            work[col] = ""
        work[col] = work[col].astype(str).str.strip()
    work = work.sort_values("report_date", ascending=False)
    return work.drop_duplicates(subset=["org_name", "quarter"], keep="first").reset_index(drop=True)


def _numeric_stats(series: pd.Series) -> dict[str, object]:
    values = pd.to_numeric(series, errors="coerce").dropna()
    if values.empty:
        return {"count": 0, "mean": "N/A", "median": "N/A", "min": "N/A", "max": "N/A"}
    return {
        "count": int(values.count()),
        "mean": round(float(values.mean()), 4),
        "median": round(float(values.median()), 4),
        "min": round(float(values.min()), 4),
        "max": round(float(values.max()), 4),
    }


def _period_label(value: object) -> str:
    text = str(value).strip()
    match = _re.search(r"(20\d{2})", text)
    return f"FY{match.group(1)}" if match else text


def _aggregate_report_rc(df: pd.DataFrame) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    if df.empty or "quarter" not in df.columns:
        return rows
    for quarter, group in df.groupby("quarter", dropna=True):
        org_count = group["org_name"].nunique() if "org_name" in group.columns else len(group)
        latest_report_date = group["report_date"].max() if "report_date" in group.columns else ""
        eps_stats = _numeric_stats(group["eps"] if "eps" in group.columns else pd.Series(dtype=float))
        np_stats = _numeric_stats(group["np"] if "np" in group.columns else pd.Series(dtype=float))
        op_rt_stats = _numeric_stats(group["op_rt"] if "op_rt" in group.columns else pd.Series(dtype=float))
        rows.append({
            "forecast_period": _period_label(quarter),
            "quarter": quarter,
            "institution_count": int(org_count),
            "latest_report_date": latest_report_date,
            "eps_count": eps_stats["count"],
            "eps_mean": eps_stats["mean"],
            "eps_median": eps_stats["median"],
            "eps_min": eps_stats["min"],
            "eps_max": eps_stats["max"],
            "net_profit_count": np_stats["count"],
            "net_profit_mean": np_stats["mean"],
            "net_profit_median": np_stats["median"],
            "net_profit_min": np_stats["min"],
            "net_profit_max": np_stats["max"],
            "revenue_count": op_rt_stats["count"],
            "revenue_mean": op_rt_stats["mean"],
            "revenue_median": op_rt_stats["median"],
            "revenue_min": op_rt_stats["min"],
            "revenue_max": op_rt_stats["max"],
        })
    return sorted(rows, key=lambda row: str(row["forecast_period"]))


def get_profit_forecast(
    ticker: Annotated[str, "A-stock code"],
    curr_date: Annotated[str, "current date"] = None,
) -> str:
    """Get sell-side consensus EPS forecasts from Tushare report_rc."""
    code = _normalize_ticker(ticker)
    ts_code = _tushare_ts_code(code)
    as_of = curr_date or datetime.now().strftime("%Y-%m-%d")

    try:
        from .tushare_client import get_tushare_client

        client = get_tushare_client()
        df, error = _fetch_report_rc(client, ts_code, as_of, 365)
        stale_forecast_window = False
        if df.empty and error == "no_sell_side_forecast":
            df, error = _fetch_report_rc(client, ts_code, as_of, 730)
            stale_forecast_window = not df.empty

        if df.empty:
            status = "no_coverage" if error == "no_sell_side_forecast" else "technical_error"
            reason = "no_sell_side_forecast" if status == "no_coverage" else error
            return _profit_forecast_error_header(
                code, ts_code, as_of, status, reason, stale_forecast_window
            )

        deduped = _dedupe_report_rc(df)
        if deduped.empty:
            return _profit_forecast_error_header(
                code,
                ts_code,
                as_of,
                "no_coverage",
                "no_sell_side_forecast",
                stale_forecast_window,
            )

        report_dates = deduped["report_date"].dropna().astype(str)
        report_date_range = (
            f"{report_dates.min()}-{report_dates.max()}" if not report_dates.empty else "N/A"
        )
        source_count = len(deduped)
        source_org_count = deduped["org_name"].nunique() if "org_name" in deduped.columns else source_count
        low_coverage = source_org_count < 3
        aggregates = _aggregate_report_rc(deduped)
        if not aggregates:
            return _profit_forecast_error_header(
                code,
                ts_code,
                as_of,
                "no_coverage",
                "no_sell_side_forecast",
                stale_forecast_window,
            )

        header = f"# Consensus EPS Forecast for {code} (A-stock)\n"
        header += "# Source: Tushare report_rc sell-side forecast aggregation\n"
        header += "# status: ok\n"
        header += "# api=report_rc\n"
        header += "# forecast_type=sell_side_forecast\n"
        header += "# not_company_guidance=true\n"
        header += f"# as_of: {as_of}\n"
        header += "# as_of_field=report_date\n"
        header += f"# report_date_range: {report_date_range}\n"
        header += f"# source_count: {source_count}\n"
        header += f"# source_org_count: {source_org_count}\n"
        header += f"# low_coverage={str(low_coverage).lower()}\n"
        header += f"# stale_forecast_window={str(stale_forecast_window).lower()}\n"
        header += f"# ts_code: {ts_code}\n"
        header += "# note: sell-side forecast aggregation; not company guidance, earnings preview, earnings flash, or historical financial indicators\n"
        header += (
            f"# Data retrieved on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        )

        lines = [
            "This is sell-side forecast aggregation, not company guidance, earnings flash, or disclosed historical financial indicators.",
            "",
            "forecast_period,quarter,institution_count,latest_report_date,eps_count,eps_mean,eps_median,eps_min,eps_max,net_profit_count,net_profit_mean,net_profit_median,net_profit_min,net_profit_max,revenue_count,revenue_mean,revenue_median,revenue_min,revenue_max",
        ]
        for row in aggregates:
            lines.append(",".join(str(row[col]) for col in [
                "forecast_period",
                "quarter",
                "institution_count",
                "latest_report_date",
                "eps_count",
                "eps_mean",
                "eps_median",
                "eps_min",
                "eps_max",
                "net_profit_count",
                "net_profit_mean",
                "net_profit_median",
                "net_profit_min",
                "net_profit_max",
                "revenue_count",
                "revenue_mean",
                "revenue_median",
                "revenue_min",
                "revenue_max",
            ]))

        return header + "\n".join(lines)

    except Exception:
        return _profit_forecast_error_header(
            code, ts_code, as_of, "technical_error", "parse_error"
        )


# ---- 11. get_hot_stocks ----

_HOT_STOCK_FIELDS = [
    "trade_date",
    "data_type",
    "ts_code",
    "ts_name",
    "rank",
    "pct_change",
    "current_price",
    "concept",
    "rank_reason",
]


def _hot_stocks_contract_header(
    *,
    status: str,
    as_of: str,
    trade_date: str,
    empty_reason: str = "none",
    error_type: str = "none",
    raw_error_suppressed: bool = False,
    notes: str = "",
) -> str:
    return _build_data_source_contract_header(
        status=status,
        source="Tushare ths_hot",
        data_type="hot_stocks",
        query_target="market",
        symbol="N/A",
        as_of=as_of,
        trade_date=trade_date,
        unit="rank; pct_change percent; current_price CNY; other fields raw Tushare",
        coverage="market_wide",
        fallback="none",
        empty_reason=empty_reason,
        error_type=error_type,
        raw_error_suppressed=raw_error_suppressed,
        limitations="market-wide hot-stock ranking only; no limit-up pool or consecutive limit-up ladder included",
        notes=notes,
    )


def _hot_stocks_short_message(
    *,
    status: str,
    as_of: str,
    trade_date: str = "N/A",
    empty_reason: str = "none",
    error_type: str = "none",
    raw_error_suppressed: bool = False,
    message: str,
) -> str:
    header = _hot_stocks_contract_header(
        status=status,
        as_of=as_of,
        trade_date=trade_date,
        empty_reason=empty_reason,
        error_type=error_type,
        raw_error_suppressed=raw_error_suppressed,
    )
    return f"{header}\n\n{message}"


def _hot_stocks_query_dates(as_of: str, max_weekdays: int = 15) -> tuple[str, list[str]]:
    as_of_dt = pd.to_datetime(as_of).normalize()
    dates: list[str] = []
    cursor = as_of_dt
    while len(dates) < max_weekdays:
        if cursor.weekday() < 5:
            dates.append(cursor.strftime("%Y%m%d"))
        cursor -= pd.Timedelta(days=1)
    return as_of_dt.strftime("%Y-%m-%d"), dates


def _hot_stocks_frame(data: object, as_of: str) -> pd.DataFrame:
    df = _tushare_data_to_frame(data)
    if df.empty:
        return df
    if "trade_date" not in df.columns or "ts_code" not in df.columns:
        raise ValueError("unexpected_schema: ths_hot missing trade_date/ts_code")

    as_of_compact = as_of.replace("-", "")
    df = df.copy()
    df["trade_date"] = df["trade_date"].astype(str).str.replace("-", "", regex=False)
    df = df[df["trade_date"].str.len().eq(8)]
    df = df[df["trade_date"] <= as_of_compact]
    if df.empty:
        return df

    latest_trade_date = df["trade_date"].max()
    df = df[df["trade_date"] == latest_trade_date]
    available_columns = [field for field in _HOT_STOCK_FIELDS if field in df.columns]
    df = df[available_columns]
    if "rank" in df.columns:
        df = df.sort_values("rank")
    return df.reset_index(drop=True)


def _hot_stocks_markdown_table(df: pd.DataFrame, columns: list[str]) -> str:
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for _, row in df.iterrows():
        values: list[str] = []
        for column in columns:
            value = row.get(column, "")
            if pd.isna(value):
                values.append("")
            elif isinstance(value, float):
                values.append(f"{value:.2f}")
            else:
                text = str(value).replace("\n", " ").replace("|", "/")
                if len(text) > 180:
                    text = text[:177] + "..."
                values.append(text)
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def _format_hot_stocks_output(
    as_of: str,
    attempted_dates: list[str],
    df: pd.DataFrame,
) -> str:
    columns = [field for field in _HOT_STOCK_FIELDS if field in df.columns]
    trade_date = str(df["trade_date"].iloc[0]) if "trade_date" in df.columns else "N/A"
    header = _hot_stocks_contract_header(
        status="ok",
        as_of=as_of,
        trade_date=trade_date,
        notes=f"attempted_trade_dates={','.join(attempted_dates)}; rows={len(df)}",
    )
    lines = [
        "# Market Hot-Stock Ranking",
        "",
        _hot_stocks_markdown_table(df, columns),
    ]
    return f"{header}\n\n" + "\n".join(lines)


def get_hot_stocks(
    curr_date: Annotated[str, "Date YYYY-MM-DD, empty string for today"] = "",
) -> str:
    """Get market-wide hot-stock ranking via Tushare ths_hot."""
    if not curr_date or curr_date.strip() == "":
        curr_date = datetime.now().strftime("%Y-%m-%d")

    try:
        as_of, candidate_dates = _hot_stocks_query_dates(curr_date)
    except Exception:
        as_of = str(curr_date)
        return _hot_stocks_short_message(
            status="invalid_input",
            as_of=as_of,
            empty_reason="not_applicable",
            message="Invalid date input for hot-stock ranking query.",
        )

    try:
        from .tushare_client import get_tushare_client

        client = get_tushare_client()
        technical_errors: list[str] = []
        empty_dates: list[str] = []
        attempted_dates: list[str] = []

        for trade_date in candidate_dates:
            attempted_dates.append(trade_date)
            response = client.call_api(
                "ths_hot",
                params={"trade_date": trade_date, "market": "热股", "is_new": "Y"},
                fields=",".join(_HOT_STOCK_FIELDS),
                cache_key=f"ths_hot/{trade_date}_hot_new.json",
                use_cache=False,
            )
            if not response.ok:
                technical_errors.append(response.error or response.message or "")
                continue

            df = _hot_stocks_frame(response.data, as_of)
            if df.empty:
                empty_dates.append(trade_date)
                continue

            return _format_hot_stocks_output(as_of, attempted_dates, df)

        if technical_errors and not empty_dates:
            error_type = _classify_data_source_error(technical_errors[0])
            return _hot_stocks_short_message(
                status="technical_error",
                as_of=as_of,
                error_type=error_type,
                raw_error_suppressed=True,
                message="Data source request failed; raw technical details suppressed.",
            )

        return _hot_stocks_short_message(
            status="empty",
            as_of=as_of,
            empty_reason="source_empty",
            message=(
                "Tushare ths_hot returned no hot-stock ranking rows for the "
                "recent trade-date query window."
            ),
        )

    except Exception as exc:
        error_type = _classify_data_source_error(exc)
        return _hot_stocks_short_message(
            status="technical_error",
            as_of=as_of,
            error_type=error_type,
            raw_error_suppressed=True,
            message="Data source request failed; raw technical details suppressed.",
        )


# ---- 12. get_northbound_flow ----

_NORTHBOUND_FLOW_FIELDS = [
    "trade_date",
    "hgt",
    "sgt",
    "north_money",
    "south_money",
]


def _northbound_contract_header(
    *,
    status: str,
    as_of: str,
    trade_date: str,
    empty_reason: str = "none",
    error_type: str = "none",
    raw_error_suppressed: bool = False,
    notes: str = "",
) -> str:
    return _build_data_source_contract_header(
        status=status,
        source="Tushare moneyflow_hsgt",
        data_type="northbound_flow",
        query_target="market",
        symbol="N/A",
        as_of=as_of,
        trade_date=trade_date,
        unit="CNY million (Tushare moneyflow_hsgt raw fields)",
        coverage="market_wide",
        fallback="none",
        empty_reason=empty_reason,
        error_type=error_type,
        raw_error_suppressed=raw_error_suppressed,
        limitations="market-level flow only; no stock-level holding data included",
        notes=notes,
    )


def _northbound_short_message(
    *,
    status: str,
    as_of: str,
    trade_date: str = "N/A",
    empty_reason: str = "none",
    error_type: str = "none",
    raw_error_suppressed: bool = False,
    message: str,
) -> str:
    header = _northbound_contract_header(
        status=status,
        as_of=as_of,
        trade_date=trade_date,
        empty_reason=empty_reason,
        error_type=error_type,
        raw_error_suppressed=raw_error_suppressed,
    )
    return f"{header}\n\n{message}"


def _northbound_query_window(as_of: str, include_history: bool) -> tuple[str, str, str]:
    as_of_dt = pd.to_datetime(as_of).normalize()
    lookback_days = 45 if include_history else 10
    start_date = (as_of_dt - pd.Timedelta(days=lookback_days)).strftime("%Y%m%d")
    end_date = as_of_dt.strftime("%Y%m%d")
    return as_of_dt.strftime("%Y-%m-%d"), start_date, end_date


def _northbound_flow_frame(data: object, as_of: str, include_history: bool) -> pd.DataFrame:
    df = _tushare_data_to_frame(data)
    if df.empty or "trade_date" not in df.columns:
        return pd.DataFrame()

    as_of_compact = as_of.replace("-", "")
    df = df.copy()
    df["trade_date"] = df["trade_date"].astype(str).str.replace("-", "", regex=False)
    df = df[df["trade_date"].str.len().eq(8)]
    df = df[df["trade_date"] <= as_of_compact]
    if df.empty:
        return df

    limit = 20 if include_history else 1
    df = df.sort_values("trade_date", ascending=False).head(limit)
    return df.sort_values("trade_date").reset_index(drop=True)


def _markdown_table(df: pd.DataFrame, columns: list[str]) -> str:
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for _, row in df.iterrows():
        values: list[str] = []
        for column in columns:
            value = row.get(column, "")
            if pd.isna(value):
                values.append("")
            elif isinstance(value, float):
                values.append(f"{value:.2f}")
            else:
                values.append(str(value))
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def _format_northbound_flow_output(
    as_of: str,
    start_date: str,
    end_date: str,
    df: pd.DataFrame,
    include_history: bool,
) -> str:
    trade_dates = df["trade_date"].astype(str).tolist()
    trade_date = trade_dates[-1] if trade_dates else "N/A"
    missing = [field for field in _NORTHBOUND_FLOW_FIELDS if field not in df.columns]
    if missing:
        return _northbound_short_message(
            status="technical_error",
            as_of=as_of,
            trade_date=trade_date,
            error_type="unexpected_schema",
            raw_error_suppressed=True,
            message="Data source request failed; raw technical details suppressed.",
        )

    header = _northbound_contract_header(
        status="ok",
        as_of=as_of,
        trade_date=trade_date,
        notes=(
            f"query_window={start_date}-{end_date}; "
            f"rows={len(df)}; include_history={str(include_history).lower()}"
        ),
    )
    lines = [
        "# Northbound / Southbound Capital Flow",
        "",
        _markdown_table(df, _NORTHBOUND_FLOW_FIELDS),
    ]
    return f"{header}\n\n" + "\n".join(lines)


def get_northbound_flow(
    curr_date: Annotated[str, "Date YYYY-MM-DD"],
    include_history: Annotated[
        bool, "Include historical daily data (last 20 trading days)"
    ] = False,
) -> str:
    """Get market-level northbound/southbound capital flow via Tushare."""
    as_of_input = curr_date or datetime.now().strftime("%Y-%m-%d")
    try:
        as_of, start_date, end_date = _northbound_query_window(
            as_of_input, include_history
        )
    except Exception:
        return _northbound_short_message(
            status="invalid_input",
            as_of=str(as_of_input),
            empty_reason="invalid_or_unresolved_ticker",
            message="Invalid date input for northbound flow query.",
        )

    try:
        from .tushare_client import get_tushare_client

        client = get_tushare_client()
        response = client.call_api(
            "moneyflow_hsgt",
            params={"start_date": start_date, "end_date": end_date},
            fields=",".join(_NORTHBOUND_FLOW_FIELDS),
            cache_key=f"moneyflow_hsgt/{start_date}_{end_date}.json",
            use_cache=False,
        )
        if not response.ok:
            error_type = _classify_data_source_error(response.error or response.message or "")
            return _northbound_short_message(
                status="technical_error",
                as_of=as_of,
                error_type=error_type,
                raw_error_suppressed=True,
                message="Data source request failed; raw technical details suppressed.",
            )

        df = _northbound_flow_frame(response.data, as_of, include_history)
        if df.empty:
            return _northbound_short_message(
                status="empty",
                as_of=as_of,
                empty_reason="source_empty",
                message="Tushare moneyflow_hsgt returned no rows for the query window.",
            )

        return _format_northbound_flow_output(
            as_of, start_date, end_date, df, include_history
        )

    except Exception as exc:
        error_type = _classify_data_source_error(exc)
        return _northbound_short_message(
            status="technical_error",
            as_of=as_of,
            error_type=error_type,
            raw_error_suppressed=True,
            message="Data source request failed; raw technical details suppressed.",
        )


# ---- 13. get_concept_blocks ----

_CONCEPT_BLOCK_FIELDS = [
    "ts_code",
    "trade_date",
    "name",
    "theme_code",
    "industry_code",
    "industry",
    "reason",
    "hot_num",
]


def _concept_blocks_contract_header(
    *,
    status: str,
    symbol: str,
    as_of: str,
    trade_date: str,
    coverage: str = "individual_stock",
    empty_reason: str = "none",
    error_type: str = "none",
    raw_error_suppressed: bool = False,
    notes: str = "",
) -> str:
    return _build_data_source_contract_header(
        status=status,
        source="Tushare dc_concept_cons",
        data_type="concept_blocks",
        query_target="stock",
        symbol=symbol,
        as_of=as_of,
        trade_date=trade_date,
        unit="membership rows; hot_num is raw Tushare field",
        coverage=coverage,
        fallback="none",
        empty_reason=empty_reason,
        error_type=error_type,
        raw_error_suppressed=raw_error_suppressed,
        limitations="stock concept membership only; no board-level market data included",
        notes=notes,
    )


def _concept_blocks_short_message(
    *,
    status: str,
    symbol: str,
    as_of: str,
    trade_date: str = "N/A",
    coverage: str = "individual_stock",
    empty_reason: str = "none",
    error_type: str = "none",
    raw_error_suppressed: bool = False,
    message: str,
) -> str:
    header = _concept_blocks_contract_header(
        status=status,
        symbol=symbol,
        as_of=as_of,
        trade_date=trade_date,
        coverage=coverage,
        empty_reason=empty_reason,
        error_type=error_type,
        raw_error_suppressed=raw_error_suppressed,
    )
    return f"{header}\n\n{message}"


def _concept_blocks_ts_code(ticker: str) -> tuple[str, bool]:
    try:
        code = _normalize_ticker(str(ticker))
    except Exception:
        return str(ticker or "N/A"), False
    if not _re.fullmatch(r"\d{6}", code):
        return code or "N/A", False
    return _tushare_ts_code(code), True


def _concept_blocks_query_window(as_of: str) -> tuple[str, str, str]:
    as_of_dt = pd.to_datetime(as_of).normalize()
    start_date = (as_of_dt - pd.Timedelta(days=30)).strftime("%Y%m%d")
    end_date = as_of_dt.strftime("%Y%m%d")
    return as_of_dt.strftime("%Y-%m-%d"), start_date, end_date


def _concept_blocks_frame(data: object, ts_code: str, as_of: str) -> pd.DataFrame:
    df = _tushare_data_to_frame(data)
    if df.empty:
        return df
    if "ts_code" not in df.columns or "trade_date" not in df.columns:
        raise ValueError("unexpected_schema: dc_concept_cons missing ts_code/trade_date")

    as_of_compact = as_of.replace("-", "")
    df = df.copy()
    df["ts_code"] = df["ts_code"].astype(str).str.upper()
    df["trade_date"] = df["trade_date"].astype(str).str.replace("-", "", regex=False)
    df = df[(df["ts_code"] == ts_code.upper()) & df["trade_date"].str.len().eq(8)]
    df = df[df["trade_date"] <= as_of_compact]
    if df.empty:
        return df

    latest_trade_date = df["trade_date"].max()
    df = df[df["trade_date"] == latest_trade_date]
    available_columns = [field for field in _CONCEPT_BLOCK_FIELDS if field in df.columns]
    df = df[available_columns]
    sort_columns = [column for column in ("hot_num", "name") if column in available_columns]
    if sort_columns:
        df = df.sort_values(sort_columns)
    return df.reset_index(drop=True)


def _concept_blocks_markdown_table(df: pd.DataFrame, columns: list[str]) -> str:
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for _, row in df.iterrows():
        values: list[str] = []
        for column in columns:
            value = row.get(column, "")
            if pd.isna(value):
                values.append("")
            elif isinstance(value, float):
                values.append(f"{value:.2f}")
            else:
                text = str(value).replace("\n", " ").replace("|", "/")
                if len(text) > 160:
                    text = text[:157] + "..."
                values.append(text)
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def _format_concept_blocks_output(
    ts_code: str,
    as_of: str,
    start_date: str,
    end_date: str,
    df: pd.DataFrame,
) -> str:
    columns = [field for field in _CONCEPT_BLOCK_FIELDS if field in df.columns]
    trade_date = str(df["trade_date"].iloc[0]) if "trade_date" in df.columns else "N/A"
    header = _concept_blocks_contract_header(
        status="ok",
        symbol=ts_code,
        as_of=as_of,
        trade_date=trade_date,
        notes=f"query_window={start_date}-{end_date}; rows={len(df)}",
    )
    lines = [
        "# Stock Concept Membership",
        "",
        _concept_blocks_markdown_table(df, columns),
    ]
    return f"{header}\n\n" + "\n".join(lines)


def get_concept_blocks(
    ticker: Annotated[str, "A-stock code (e.g. 688017)"],
) -> str:
    """Get stock-to-concept membership via Tushare dc_concept_cons."""
    as_of_input = datetime.now().strftime("%Y-%m-%d")
    try:
        as_of, start_date, end_date = _concept_blocks_query_window(as_of_input)
    except Exception:
        as_of = as_of_input
        start_date = "N/A"
        end_date = "N/A"

    ts_code, valid_symbol = _concept_blocks_ts_code(ticker)
    if not valid_symbol:
        return _concept_blocks_short_message(
            status="invalid_input",
            symbol=ts_code,
            as_of=as_of,
            coverage="symbol_unresolved",
            empty_reason="invalid_or_unresolved_ticker",
            message="Invalid or unresolved A-share ticker for concept membership query.",
        )

    try:
        from .tushare_client import get_tushare_client

        client = get_tushare_client()
        response = client.call_api(
            "dc_concept_cons",
            params={
                "ts_code": ts_code,
                "start_date": start_date,
                "end_date": end_date,
            },
            fields=",".join(_CONCEPT_BLOCK_FIELDS),
            cache_key=f"dc_concept_cons/{ts_code}_{start_date}_{end_date}.json",
            use_cache=False,
        )
        if not response.ok:
            error_type = _classify_data_source_error(response.error or response.message or "")
            return _concept_blocks_short_message(
                status="technical_error",
                symbol=ts_code,
                as_of=as_of,
                error_type=error_type,
                raw_error_suppressed=True,
                message="Data source request failed; raw technical details suppressed.",
            )

        df = _concept_blocks_frame(response.data, ts_code, as_of)
        if df.empty:
            return _concept_blocks_short_message(
                status="empty",
                symbol=ts_code,
                as_of=as_of,
                empty_reason="no_coverage",
                message=(
                    "Tushare dc_concept_cons returned no concept membership rows "
                    "for the requested stock and query window."
                ),
            )

        return _format_concept_blocks_output(ts_code, as_of, start_date, end_date, df)

    except Exception as exc:
        error_type = _classify_data_source_error(exc)
        return _concept_blocks_short_message(
            status="technical_error",
            symbol=ts_code,
            as_of=as_of,
            error_type=error_type,
            raw_error_suppressed=True,
            message="Data source request failed; raw technical details suppressed.",
        )


# ---- 14. get_fund_flow ----

_MONEYFLOW_FIELDS = [
    "ts_code",
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
    "buy_sm_vol",
    "sell_sm_vol",
    "buy_md_vol",
    "sell_md_vol",
    "buy_lg_vol",
    "sell_lg_vol",
    "buy_elg_vol",
    "sell_elg_vol",
]

_MONEYFLOW_DC_FIELDS = [
    "ts_code",
    "trade_date",
    "close",
    "pct_change",
    "net_amount",
    "net_amount_rate",
    "buy_elg_amount",
    "buy_lg_amount",
    "buy_md_amount",
    "buy_sm_amount",
]


def _fund_flow_error_header(
    code: str,
    ts_code: str,
    as_of: str,
    status: str,
    reason: str,
    api_name: str = "moneyflow",
    fallback: str = "none",
) -> str:
    source = f"Tushare {api_name}"
    header = f"# Fund Flow for {code} (A-stock)\n"
    header += f"# Source: {source}\n"
    header += f"# status: {status}\n"
    header += "# frequency=daily\n"
    header += "# scope=individual_stock\n"
    header += f"# as_of: {as_of}\n"
    header += "# trade_date: N/A\n"
    header += f"# api={api_name}\n"
    header += f"# fallback={fallback}\n"
    header += f"# ts_code: {ts_code}\n"
    header += f"# empty_reason: {reason}\n\n"
    return header + f"{status}: {reason}"


def _compact_date(date_str: str) -> str:
    return str(date_str).replace("-", "")


def _moneyflow_frame(data: object, as_of: str, limit: int) -> pd.DataFrame:
    df = _tushare_data_to_frame(data)
    if df.empty or "trade_date" not in df.columns:
        return pd.DataFrame()
    as_of_compact = _compact_date(as_of)
    df = df.copy()
    df["trade_date"] = df["trade_date"].astype(str).str.replace("-", "", regex=False)
    df = df[df["trade_date"].str.len().eq(8)]
    df = df[df["trade_date"] <= as_of_compact]
    if df.empty:
        return df
    df = df.sort_values("trade_date", ascending=False).head(limit)
    return df.sort_values("trade_date").reset_index(drop=True)


def _fund_flow_query_params(ts_code: str, as_of: str, include_history: bool) -> list[dict[str, str]]:
    as_of_date = pd.to_datetime(as_of).normalize()
    if include_history:
        start_date = (as_of_date - pd.Timedelta(days=45)).strftime("%Y%m%d")
        return [
            {
                "ts_code": ts_code,
                "start_date": start_date,
                "end_date": as_of_date.strftime("%Y%m%d"),
            }
        ]
    return [
        {
            "ts_code": ts_code,
            "trade_date": (as_of_date - pd.Timedelta(days=days_back)).strftime("%Y%m%d"),
        }
        for days_back in range(11)
    ]


def _fetch_tushare_fund_flow(
    client,
    api_name: str,
    ts_code: str,
    as_of: str,
    include_history: bool,
) -> tuple[pd.DataFrame, str]:
    fields = ",".join(_MONEYFLOW_FIELDS if api_name == "moneyflow" else _MONEYFLOW_DC_FIELDS)
    limit = 20 if include_history else 1
    try:
        queries = _fund_flow_query_params(ts_code, as_of, include_history)
    except Exception:
        return pd.DataFrame(), "parse_error"

    last_empty_reason = "no_moneyflow_before_as_of"
    for params in queries:
        if include_history:
            cache_key = f"{api_name}/{ts_code}/{params['start_date']}_{params['end_date']}.json"
        else:
            cache_key = f"{api_name}/{ts_code}/{params['trade_date']}.json"
        response = client.call_api(
            api_name,
            params=params,
            fields=fields,
            cache_key=cache_key,
        )
        if not response.ok:
            return pd.DataFrame(), response.error or "tushare_upstream_error"
        df = _moneyflow_frame(response.data, as_of, limit)
        if not df.empty:
            return df, ""
    return pd.DataFrame(), last_empty_reason


def _add_moneyflow_net_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    pairs = [
        ("small_order_net_amount", "buy_sm_amount", "sell_sm_amount"),
        ("medium_order_net_amount", "buy_md_amount", "sell_md_amount"),
        ("large_order_net_amount", "buy_lg_amount", "sell_lg_amount"),
        ("extra_large_order_net_amount", "buy_elg_amount", "sell_elg_amount"),
    ]
    for target, buy_col, sell_col in pairs:
        if buy_col in df.columns and sell_col in df.columns:
            buy = pd.to_numeric(df[buy_col], errors="coerce")
            sell = pd.to_numeric(df[sell_col], errors="coerce")
            df[target] = buy - sell
    return df


def _fund_flow_summary(df: pd.DataFrame, amount_col: str) -> str:
    if df.empty or amount_col not in df.columns:
        return "Data summary: no strong interpretation attached"
    value = pd.to_numeric(df.iloc[-1].get(amount_col), errors="coerce")
    if pd.isna(value) or value == 0:
        return "Data summary: no strong interpretation attached"
    direction = "positive" if value > 0 else "negative"
    return f"Data summary: {amount_col} {direction}"


def _format_fund_flow_output(
    code: str,
    ts_code: str,
    as_of: str,
    api_name: str,
    df: pd.DataFrame,
    include_history: bool,
    status: str = "ok",
    fallback: str = "none",
) -> str:
    source = f"Tushare {api_name}"
    date_values = df["trade_date"].astype(str).tolist() if "trade_date" in df.columns else []
    trade_date = date_values[-1] if date_values else "N/A"
    date_range = f"{date_values[0]}-{date_values[-1]}" if len(date_values) > 1 else trade_date
    net_only = api_name == "moneyflow_dc"

    if api_name == "moneyflow":
        df = _add_moneyflow_net_columns(df)
        preferred_cols = _MONEYFLOW_FIELDS + [
            "small_order_net_amount",
            "medium_order_net_amount",
            "large_order_net_amount",
            "extra_large_order_net_amount",
        ]
        summary = _fund_flow_summary(df, "net_mf_amount")
    else:
        preferred_cols = _MONEYFLOW_DC_FIELDS
        summary = _fund_flow_summary(df, "net_amount")

    ordered_cols = [col for col in preferred_cols if col in df.columns]
    remaining_cols = [col for col in df.columns if col not in ordered_cols]
    csv_string = df[ordered_cols + remaining_cols].to_csv(index=False)

    header = f"# Fund Flow for {code} (A-stock)\n"
    header += f"# Source: {source}\n"
    header += f"# status: {status}\n"
    header += "# frequency=daily\n"
    header += "# scope=individual_stock\n"
    header += f"# as_of: {as_of}\n"
    header += f"# trade_date: {trade_date}\n"
    header += f"# date_range: {date_range}\n"
    header += f"# api={api_name}\n"
    header += f"# fallback={fallback}\n"
    header += f"# source_api={api_name}\n"
    header += f"# net_only={str(net_only).lower()}\n"
    header += f"# ts_code: {ts_code}\n"
    header += f"# rows: {len(df)}\n"
    header += f"# include_history: {str(include_history).lower()}\n"
    header += "# note: individual stock daily fund flow only\n"
    header += (
        f"# Data retrieved on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    )

    return header + f"{summary}\n\n" + csv_string


def get_fund_flow(
    ticker: Annotated[str, "A-stock code"],
    curr_date: Annotated[str, "Date YYYY-MM-DD"],
    include_history: Annotated[
        bool, "Include historical daily fund flow (last 20 days)"
    ] = True,
) -> str:
    """Get individual stock daily fund flow from Tushare moneyflow."""
    code = _normalize_ticker(ticker)
    ts_code = _tushare_ts_code(code)
    as_of = curr_date or datetime.now().strftime("%Y-%m-%d")

    try:
        from .tushare_client import get_tushare_client

        client = get_tushare_client()
        main_df, main_error = _fetch_tushare_fund_flow(
            client, "moneyflow", ts_code, as_of, include_history
        )
        if not main_df.empty:
            return _format_fund_flow_output(
                code,
                ts_code,
                as_of,
                "moneyflow",
                main_df,
                include_history,
                status="ok",
                fallback="none",
            )

        fallback_df, fallback_error = _fetch_tushare_fund_flow(
            client, "moneyflow_dc", ts_code, as_of, include_history
        )
        if not fallback_df.empty:
            return _format_fund_flow_output(
                code,
                ts_code,
                as_of,
                "moneyflow_dc",
                fallback_df,
                include_history,
                status="partial_data",
                fallback="moneyflow_dc",
            )

        reason = fallback_error or main_error or "no_moneyflow_before_as_of"
        if reason.startswith("no_") and (not main_error or main_error.startswith("no_")):
            status = "no_data"
        else:
            status = "technical_error"
            reason = main_error if main_error and not main_error.startswith("no_") else reason
        return _fund_flow_error_header(
            code,
            ts_code,
            as_of,
            status,
            reason,
            api_name="moneyflow",
            fallback="moneyflow_dc",
        )

    except Exception:
        return _fund_flow_error_header(
            code,
            ts_code,
            as_of,
            "technical_error",
            "parse_error",
            api_name="moneyflow",
            fallback="moneyflow_dc",
        )


# ---------------------------------------------------------------------------
# 15. Dragon Tiger Board (龙虎榜)
# ---------------------------------------------------------------------------

_DRAGON_TIGER_EVENT_FIELDS = [
    "trade_date",
    "ts_code",
    "name",
    "close",
    "pct_change",
    "turnover_rate",
    "amount",
    "l_sell",
    "l_buy",
    "l_amount",
    "net_amount",
    "reason",
]

_DRAGON_TIGER_INST_FIELDS = [
    "trade_date",
    "ts_code",
    "exalter",
    "side",
    "buy",
    "buy_rate",
    "sell",
    "sell_rate",
    "net_buy",
]


def _dragon_tiger_contract_header(
    *,
    status: str,
    symbol: str,
    as_of: str,
    trade_date: str,
    coverage: str = "event_lookup",
    empty_reason: str = "none",
    error_type: str = "none",
    raw_error_suppressed: bool = False,
    notes: str = "",
) -> str:
    return _build_data_source_contract_header(
        status=status,
        source="Tushare top_list + top_inst",
        data_type="dragon_tiger_event",
        query_target="event",
        symbol=symbol,
        as_of=as_of,
        trade_date=trade_date,
        unit="CNY 10k for amount fields where provided by Tushare; ratio fields percent",
        coverage=coverage,
        fallback="none",
        empty_reason=empty_reason,
        error_type=error_type,
        raw_error_suppressed=raw_error_suppressed,
        limitations="dragon-tiger event lookup only; no investment interpretation attached",
        notes=notes,
    )


def _dragon_tiger_short_message(
    *,
    status: str,
    symbol: str,
    as_of: str,
    trade_date: str = "N/A",
    coverage: str = "event_lookup",
    empty_reason: str = "none",
    error_type: str = "none",
    raw_error_suppressed: bool = False,
    message: str,
) -> str:
    header = _dragon_tiger_contract_header(
        status=status,
        symbol=symbol,
        as_of=as_of,
        trade_date=trade_date,
        coverage=coverage,
        empty_reason=empty_reason,
        error_type=error_type,
        raw_error_suppressed=raw_error_suppressed,
    )
    return f"{header}\n\n{message}"


def _dragon_tiger_ts_code(ticker: str) -> tuple[str, bool]:
    try:
        code = _normalize_ticker(str(ticker))
    except Exception:
        return str(ticker or "N/A"), False
    if not _re.fullmatch(r"\d{6}", code):
        return code or "N/A", False
    return _tushare_ts_code(code), True


def _dragon_tiger_query_dates(as_of: str, look_back_days: int) -> tuple[str, str, list[str]]:
    as_of_dt = pd.to_datetime(as_of).normalize()
    days = int(look_back_days)
    if days < 1:
        raise ValueError("look_back_days must be positive")
    start_dt = as_of_dt - pd.Timedelta(days=days)
    dates: list[str] = []
    cursor = as_of_dt
    while cursor >= start_dt:
        if cursor.weekday() < 5:
            dates.append(cursor.strftime("%Y%m%d"))
        cursor -= pd.Timedelta(days=1)
    return as_of_dt.strftime("%Y-%m-%d"), start_dt.strftime("%Y%m%d"), dates


def _dragon_tiger_filter_frame(
    data: object,
    fields: list[str],
    ts_code: str,
    as_of: str,
) -> pd.DataFrame:
    df = _tushare_data_to_frame(data)
    if df.empty:
        return df
    if "trade_date" not in df.columns or "ts_code" not in df.columns:
        raise ValueError("unexpected_schema: dragon-tiger data missing trade_date/ts_code")

    as_of_compact = as_of.replace("-", "")
    df = df.copy()
    df["ts_code"] = df["ts_code"].astype(str).str.upper()
    df["trade_date"] = df["trade_date"].astype(str).str.replace("-", "", regex=False)
    df = df[(df["ts_code"] == ts_code.upper()) & df["trade_date"].str.len().eq(8)]
    df = df[df["trade_date"] <= as_of_compact]
    if df.empty:
        return df

    available_columns = [field for field in fields if field in df.columns]
    return df[available_columns].reset_index(drop=True)


def _dragon_tiger_markdown_table(df: pd.DataFrame, columns: list[str]) -> str:
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for _, row in df.iterrows():
        values: list[str] = []
        for column in columns:
            value = row.get(column, "")
            if pd.isna(value):
                values.append("")
            elif isinstance(value, float):
                values.append(f"{value:.2f}")
            else:
                text = str(value).replace("\n", " ").replace("|", "/")
                if len(text) > 180:
                    text = text[:177] + "..."
                values.append(text)
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def _format_dragon_tiger_output(
    *,
    status: str,
    ts_code: str,
    as_of: str,
    start_date: str,
    queried_dates: list[str],
    events_df: pd.DataFrame,
    inst_df: pd.DataFrame,
    detail_note: str,
) -> str:
    event_columns = [field for field in _DRAGON_TIGER_EVENT_FIELDS if field in events_df.columns]
    inst_columns = [field for field in _DRAGON_TIGER_INST_FIELDS if field in inst_df.columns]
    event_dates = events_df["trade_date"].astype(str).tolist() if "trade_date" in events_df.columns else []
    latest_trade_date = max(event_dates) if event_dates else "N/A"
    notes = (
        f"query_window={start_date}-{as_of.replace('-', '')}; "
        f"queried_trade_dates={len(queried_dates)}; events={len(events_df)}"
    )
    if detail_note:
        notes += f"; {detail_note}"

    header = _dragon_tiger_contract_header(
        status=status,
        symbol=ts_code,
        as_of=as_of,
        trade_date=latest_trade_date,
        notes=notes,
    )
    lines = [
        "# Dragon-Tiger Board Events",
        "",
        "## Event List",
        "",
        _dragon_tiger_markdown_table(events_df, event_columns),
    ]
    if not inst_df.empty:
        lines.extend([
            "",
            "## Seat / Institution Details",
            "",
            _dragon_tiger_markdown_table(inst_df, inst_columns),
        ])
    elif detail_note:
        lines.extend([
            "",
            "## Seat / Institution Details",
            "",
            "Seat / institution details unavailable for the matched event rows.",
        ])
    return f"{header}\n\n" + "\n".join(lines)


def get_dragon_tiger_board(
    ticker: str,
    trade_date: str,
    look_back_days: int = 30,
) -> str:
    """Get dragon-tiger board event rows and optional seat details via Tushare."""
    as_of_input = trade_date or datetime.now().strftime("%Y-%m-%d")
    ts_code, valid_symbol = _dragon_tiger_ts_code(ticker)
    if not valid_symbol:
        return _dragon_tiger_short_message(
            status="invalid_input",
            symbol=ts_code,
            as_of=str(as_of_input),
            coverage="symbol_unresolved",
            empty_reason="invalid_or_unresolved_ticker",
            message="Invalid or unresolved A-share ticker for dragon-tiger event query.",
        )

    try:
        as_of, start_date, query_dates = _dragon_tiger_query_dates(
            as_of_input, look_back_days
        )
    except Exception:
        return _dragon_tiger_short_message(
            status="invalid_input",
            symbol=ts_code,
            as_of=str(as_of_input),
            empty_reason="not_applicable",
            message="Invalid date or lookback input for dragon-tiger event query.",
        )

    try:
        from .tushare_client import get_tushare_client

        client = get_tushare_client()
        event_frames: list[pd.DataFrame] = []
        technical_errors: list[str] = []

        for query_date in query_dates:
            response = client.call_api(
                "top_list",
                params={"trade_date": query_date},
                fields=",".join(_DRAGON_TIGER_EVENT_FIELDS),
                cache_key=f"top_list/{query_date}.json",
                use_cache=False,
            )
            if not response.ok:
                technical_errors.append(response.error or response.message or "")
                continue
            frame = _dragon_tiger_filter_frame(
                response.data, _DRAGON_TIGER_EVENT_FIELDS, ts_code, as_of
            )
            if not frame.empty:
                event_frames.append(frame)

        if not event_frames:
            if technical_errors:
                error_type = _classify_data_source_error(technical_errors[0])
                return _dragon_tiger_short_message(
                    status="technical_error",
                    symbol=ts_code,
                    as_of=as_of,
                    error_type=error_type,
                    raw_error_suppressed=True,
                    message="Data source request failed; raw technical details suppressed.",
                )
            return _dragon_tiger_short_message(
                status="no_event",
                symbol=ts_code,
                as_of=as_of,
                trade_date="N/A",
                empty_reason="no_event",
                message=(
                    "No dragon-tiger board event found for the requested symbol "
                    "and lookback window."
                ),
            )

        events_df = pd.concat(event_frames, ignore_index=True)
        events_df = events_df.sort_values("trade_date", ascending=False).reset_index(drop=True)
        event_dates = events_df["trade_date"].astype(str).drop_duplicates().tolist()
        inst_frames: list[pd.DataFrame] = []
        inst_errors: list[str] = []

        for event_date in event_dates:
            response = client.call_api(
                "top_inst",
                params={"trade_date": event_date},
                fields=",".join(_DRAGON_TIGER_INST_FIELDS),
                cache_key=f"top_inst/{event_date}.json",
                use_cache=False,
            )
            if not response.ok:
                inst_errors.append(response.error or response.message or "")
                continue
            inst_frame = _dragon_tiger_filter_frame(
                response.data, _DRAGON_TIGER_INST_FIELDS, ts_code, as_of
            )
            if not inst_frame.empty:
                inst_frames.append(inst_frame)

        inst_df = (
            pd.concat(inst_frames, ignore_index=True)
            .sort_values("trade_date", ascending=False)
            .reset_index(drop=True)
            if inst_frames
            else pd.DataFrame()
        )
        detail_note = ""
        status = "ok"
        if inst_df.empty:
            status = "partial_data"
            detail_note = "seat/institution details unavailable"
        elif inst_errors:
            status = "partial_data"
            detail_note = "some seat/institution detail dates unavailable"

        return _format_dragon_tiger_output(
            status=status,
            ts_code=ts_code,
            as_of=as_of,
            start_date=start_date,
            queried_dates=query_dates,
            events_df=events_df,
            inst_df=inst_df,
            detail_note=detail_note,
        )

    except Exception as exc:
        error_type = _classify_data_source_error(exc)
        return _dragon_tiger_short_message(
            status="technical_error",
            symbol=ts_code,
            as_of=as_of,
            error_type=error_type,
            raw_error_suppressed=True,
            message="Data source request failed; raw technical details suppressed.",
        )


# ---------------------------------------------------------------------------
# 16. Lockup Expiry Calendar (限售解禁日历)
# ---------------------------------------------------------------------------

def get_lockup_expiry(
    ticker: str,
    trade_date: str,
    forward_days: int = 90,
) -> str:
    """Get lockup expiry schedule for a stock.

    Args:
        ticker: 6-digit A-share code
        trade_date: YYYY-MM-DD
        forward_days: how many days forward to check (default 90)

    Returns:
        Formatted text with historical unlock records and upcoming
        expiry calendar with impact metrics.
    """
    code = safe_ticker_component(ticker)
    lines = [f"# 限售解禁日历 | {code} | {trade_date}"]

    # 1. 历史解禁记录 — eastmoney datacenter direct HTTP
    try:
        history_data = _eastmoney_datacenter(
            "RPT_LIFT_STAGE",
            filter_str=f"(SECURITY_CODE=\"{code}\")",
            page_size=15,
            sort_columns="FREE_DATE",
            sort_types="-1",
        )
        if history_data:
            lines.append(f"\n## 个股解禁记录 (共 {len(history_data)} 批)")
            lines.append("解禁时间 | 类型 | 解禁数量 | 占比")
            for row in history_data:
                lines.append(
                    f"  {str(row.get('FREE_DATE', ''))[:10]} "
                    f"| {row.get('LIMITED_STOCK_TYPE', '')} "
                    f"| {row.get('FREE_SHARES_NUM', '')} "
                    f"| {row.get('FREE_RATIO', '')}"
                )
        else:
            lines.append("\n无历史解禁记录。")
    except Exception as e:
        lines.append(f"个股解禁查询失败: {e}")

    # 2. 未来待解禁 — eastmoney datacenter direct HTTP
    try:
        end_dt = datetime.strptime(trade_date, "%Y-%m-%d") + pd.Timedelta(
            days=forward_days
        )
        end_str = end_dt.strftime("%Y-%m-%d")
        upcoming_data = _eastmoney_datacenter(
            "RPT_LIFT_STAGE",
            filter_str=(
                f"(SECURITY_CODE=\"{code}\")"
                f"(FREE_DATE>='{trade_date}')"
                f"(FREE_DATE<='{end_str}')"
            ),
            page_size=20,
            sort_columns="FREE_DATE",
            sort_types="1",
        )
        if upcoming_data:
            lines.append(f"\n## 未来 {forward_days} 天待解禁")
            for row in upcoming_data:
                lines.append(
                    f"  {str(row.get('FREE_DATE', ''))[:10]} "
                    f"| {row.get('LIMITED_STOCK_TYPE', '')} "
                    f"| 数量 {row.get('FREE_SHARES_NUM', '')} "
                    f"| 占比 {row.get('FREE_RATIO', '')}"
                )
        else:
            lines.append(f"\n未来 {forward_days} 天无待解禁。")
    except Exception as e:
        lines.append(f"解禁日历查询失败: {e}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 17. Industry Comparison (行业横向对比)
# ---------------------------------------------------------------------------

def get_industry_comparison(
    ticker: str,
    trade_date: str,
    top_n: int = 20,
) -> str:
    """Get Eastmoney all-market industry ranking.

    Args:
        ticker: 6-digit A-share code. The current implementation keeps this
            symbol in the contract header but does not resolve its industry.
        trade_date: YYYY-MM-DD
        top_n: number of top/bottom industries to show (default 20)

    Returns:
        String-compatible contract header plus industry ranking body.
    """
    code = safe_ticker_component(ticker)
    source = "Eastmoney push2"
    data_type = "industry_ranking"
    query_target = "market"
    coverage = "market_wide"
    unit = "pct_change=percent; count=stocks; rank=ordinal"
    limitations = "target stock industry is not resolved by current implementation"
    notes = (
        "function requested industry comparison; current body is "
        "all-market industry ranking"
    )

    # 东财 push2 行业板块排名 (direct HTTP, replaces 同花顺 which has 401)
    try:
        url = "https://push2.eastmoney.com/api/qt/clist/get"
        params = {
            "pn": "1",
            "pz": "100",
            "po": "1",
            "np": "1",
            "fltt": "2",
            "invt": "2",
            "fs": "m:90+t:2",
            "fields": "f2,f3,f4,f12,f13,f14,f104,f105,f128,f136,f140,f141,f207",
        }
        r = _em_get(url, params=params, timeout=15)
        if "<html" in r.text.lower() or "<!doctype" in r.text.lower():
            raise RuntimeError("html_response")
        r.raise_for_status()
        d = r.json()
        items = d.get("data", {}).get("diff", [])

        if items:
            lines = [f"# 行业排名 | {code} | {trade_date}"]
            lines.append(
                f"\n## 全行业表现 (东财 {len(items)} 个行业)"
            )
            lines.append(
                "排名 | 行业 | 涨跌幅 | 上涨 | 下跌 | 领涨股"
            )
            for i, item in enumerate(items):
                name = item.get("f14", "")
                change_pct = item.get("f3", 0)
                up_count = item.get("f104", 0)
                down_count = item.get("f105", 0)
                leader = item.get("f140", "")
                lines.append(
                    f"  {i+1}. {name} "
                    f"| {change_pct}% "
                    f"| {up_count} "
                    f"| {down_count} "
                    f"| {leader}"
                )
                if i >= top_n * 2 - 1:
                    lines.append(f"  ... (showing top/bottom {top_n})")
                    break
            header = _build_data_source_contract_header(
                status="ok",
                source=source,
                data_type=data_type,
                query_target=query_target,
                symbol=code,
                as_of=trade_date,
                trade_date=trade_date,
                unit=unit,
                coverage=coverage,
                fallback="none",
                empty_reason="none",
                error_type="none",
                raw_error_suppressed=False,
                limitations=limitations,
                notes=notes,
            )
            return f"{header}\n\n" + "\n".join(lines)
        else:
            header = _build_data_source_contract_header(
                status="empty",
                source=source,
                data_type=data_type,
                query_target=query_target,
                symbol=code,
                as_of=trade_date,
                trade_date=trade_date,
                unit=unit,
                coverage=coverage,
                fallback="none",
                empty_reason="source_empty",
                error_type="none",
                raw_error_suppressed=False,
                limitations=limitations,
                notes=notes,
            )
            return f"{header}\n\nNo industry ranking rows returned for the requested date."
    except Exception as e:
        error_type = _classify_data_source_error(e)
        logger.warning(
            "Industry comparison source failed for %s; raw technical details suppressed",
            code,
        )
        header = _build_data_source_contract_header(
            status="technical_error",
            source=source,
            data_type=data_type,
            query_target=query_target,
            symbol=code,
            as_of=trade_date,
            trade_date=trade_date,
            unit=unit,
            coverage=coverage,
            fallback="none",
            empty_reason="none",
            error_type=error_type,
            raw_error_suppressed=True,
            limitations=limitations,
            notes=notes,
        )
        return (
            f"{header}\n\n"
            "Data source request failed; raw technical details suppressed."
        )
