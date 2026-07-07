"""Small Tushare Pro client foundation for A-share data recovery.

This module intentionally stays independent from a_stock.py.  It centralizes
token lookup, short error normalization, optional JSON cache access, and a
lightweight request boundary for future data-source replacements.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Mapping, Optional


TUSHARE_API_URL = "https://api.tushare.pro"
DEFAULT_CACHE_DIR = ".cache/tushare"
DEFAULT_MAX_RPM = 100
DEFAULT_TIMEOUT_SECONDS = 15
MAX_ERROR_MESSAGE_LENGTH = 240


TECHNICAL_ERROR = "technical_error"
ERROR_TOKEN_MISSING = "tushare_token_missing"
ERROR_PERMISSION_DENIED = "tushare_permission_denied"
ERROR_RATE_LIMITED = "tushare_rate_limited"
ERROR_NETWORK = "network_error"
ERROR_UPSTREAM = "tushare_upstream_error"
ERROR_PARSE = "parse_error"


_SENSITIVE_MARKERS = (
    "token",
    "authorization",
    "cookie",
    "set-cookie",
    "access_token",
    "api_key",
)


@dataclass(frozen=True)
class TushareClientConfig:
    """Runtime configuration read from environment variables."""

    token: Optional[str]
    cache_dir: Path
    enable_cache: bool = True
    max_rpm: int = DEFAULT_MAX_RPM
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS
    api_url: str = TUSHARE_API_URL

    @classmethod
    def from_env(cls) -> "TushareClientConfig":
        return cls(
            token=_nonempty_env("TUSHARE_TOKEN"),
            cache_dir=Path(os.getenv("TUSHARE_CACHE_DIR", DEFAULT_CACHE_DIR)),
            enable_cache=_env_bool("TUSHARE_ENABLE_CACHE", default=True),
            max_rpm=_env_int("TUSHARE_MAX_RPM", DEFAULT_MAX_RPM),
            timeout_seconds=_env_int("TUSHARE_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS),
        )


@dataclass
class TushareResponse:
    """Normalized result returned by TushareClient.call_api."""

    status: str
    api: str
    data: Optional[Any] = None
    error: Optional[str] = None
    message: Optional[str] = None
    cache_hit: bool = False
    meta: Dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.status == "ok"

    def to_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "status": self.status,
            "api": self.api,
            "cache_hit": self.cache_hit,
        }
        if self.data is not None:
            result["data"] = self.data
        if self.error:
            result["error"] = self.error
        if self.message:
            result["message"] = self.message
        if self.meta:
            result["meta"] = self.meta
        return result


class TushareClient:
    """Minimal Tushare Pro HTTP client with safe errors and JSON cache."""

    def __init__(self, config: Optional[TushareClientConfig] = None) -> None:
        self.config = config or TushareClientConfig.from_env()
        self._last_request_at = 0.0

    def has_token(self) -> bool:
        """Return whether a non-empty token is configured without exposing it."""

        return bool(self.config.token)

    def call_api(
        self,
        api_name: str,
        params: Optional[Mapping[str, Any]] = None,
        cache_key: Optional[str] = None,
        use_cache: bool = True,
        fields: Optional[str] = None,
    ) -> TushareResponse:
        """Call a Tushare API and return a normalized response.

        This is not wired into business functions in this stage.  Future
        callers pass an API name, plain params, and an optional cache key.
        """

        clean_api_name = _safe_identifier(api_name)
        clean_params = dict(params or {})

        if not self.has_token():
            return self._error(clean_api_name, ERROR_TOKEN_MISSING)

        effective_cache_key = cache_key or _default_cache_key(clean_api_name, clean_params, fields)
        if use_cache and self.config.enable_cache:
            cached = self._read_cache(clean_api_name, effective_cache_key)
            if cached is not None:
                return TushareResponse(
                    status="ok",
                    api=clean_api_name,
                    data=cached,
                    cache_hit=True,
                    meta={"source": "cache"},
                )

        try:
            import requests
        except ImportError:
            return self._error(clean_api_name, ERROR_UPSTREAM, "requests_dependency_missing")

        try:
            self._respect_rate_limit()
            payload: Dict[str, Any] = {
                "api_name": clean_api_name,
                "token": self.config.token,
                "params": clean_params,
            }
            if fields:
                payload["fields"] = fields

            response = requests.post(
                self.config.api_url,
                json=payload,
                timeout=self.config.timeout_seconds,
            )
            response.raise_for_status()
        except requests.Timeout:
            return self._error(clean_api_name, ERROR_NETWORK, "request_timeout")
        except requests.RequestException as exc:
            return self._error(clean_api_name, ERROR_NETWORK, _sanitize_text(str(exc)))

        try:
            body = response.json()
        except ValueError:
            return self._error(clean_api_name, ERROR_PARSE, "invalid_json_response")

        normalized = self._normalize_tushare_body(clean_api_name, body)
        if normalized.ok and use_cache and self.config.enable_cache:
            self._write_cache(clean_api_name, effective_cache_key, normalized.data)
        return normalized

    def _normalize_tushare_body(self, api_name: str, body: Mapping[str, Any]) -> TushareResponse:
        code = body.get("code")
        message = _sanitize_text(str(body.get("msg") or body.get("message") or ""))

        if code == 0:
            return TushareResponse(
                status="ok",
                api=api_name,
                data=body.get("data"),
                cache_hit=False,
                meta={"source": "tushare"},
            )

        error = _classify_tushare_error(message)
        return self._error(api_name, error, message or "tushare_nonzero_response")

    def _respect_rate_limit(self) -> None:
        """Tiny per-client throttle; not a full queue or cross-process limiter."""

        max_rpm = max(1, self.config.max_rpm)
        min_interval = 60.0 / max_rpm
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < min_interval:
            time.sleep(min_interval - elapsed)
        self._last_request_at = time.monotonic()

    def _read_cache(self, api_name: str, cache_key: str) -> Optional[Any]:
        path = self._cache_path(api_name, cache_key)
        if not path.exists():
            return None
        try:
            with path.open("r", encoding="utf-8") as fp:
                wrapper = json.load(fp)
        except (OSError, json.JSONDecodeError):
            return None
        return wrapper.get("data")

    def _write_cache(self, api_name: str, cache_key: str, data: Any) -> None:
        path = self._cache_path(api_name, cache_key)
        wrapper = {
            "created_at": int(time.time()),
            "source_api": api_name,
            "data": data,
        }
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("w", encoding="utf-8") as fp:
                json.dump(wrapper, fp, ensure_ascii=False, separators=(",", ":"))
        except OSError:
            # Cache failure must not break the data path.
            return

    def _cache_path(self, api_name: str, cache_key: str) -> Path:
        safe_api = _safe_path_part(api_name)
        safe_key = "/".join(_safe_path_part(part) for part in cache_key.split("/"))
        if not safe_key.endswith(".json"):
            safe_key = f"{safe_key}.json"
        if cache_key_is_hash(cache_key):
            safe_key = f"{safe_api}/{safe_key}"
        return self.config.cache_dir / safe_key

    def _error(self, api_name: str, error: str, detail: Optional[str] = None) -> TushareResponse:
        message = f"{TECHNICAL_ERROR}: {error}"
        sanitized_detail = _sanitize_text(detail or "")
        if sanitized_detail:
            message = f"{message} ({sanitized_detail})"
        return TushareResponse(
            status=TECHNICAL_ERROR,
            api=api_name,
            error=error,
            message=message[:MAX_ERROR_MESSAGE_LENGTH],
            cache_hit=False,
        )


def get_tushare_client() -> TushareClient:
    """Create a client from process environment variables."""

    return TushareClient()


def get_token_status() -> str:
    """Return only token presence state for diagnostics."""

    return "present" if bool(_nonempty_env("TUSHARE_TOKEN")) else "missing"


def _nonempty_env(name: str) -> Optional[str]:
    value = os.getenv(name)
    if value and value.strip():
        return value.strip()
    return None


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        parsed = int(value)
    except ValueError:
        return default
    return parsed if parsed > 0 else default


def _classify_tushare_error(message: str) -> str:
    lower = message.lower()
    if any(key in lower for key in ("permission", "权限", "积分", "无权", "未开通")):
        return ERROR_PERMISSION_DENIED
    if any(key in lower for key in ("rate", "limit", "频率", "每分钟", "超过")):
        return ERROR_RATE_LIMITED
    return ERROR_UPSTREAM


def _default_cache_key(api_name: str, params: Mapping[str, Any], fields: Optional[str]) -> str:
    payload = {"api_name": api_name, "params": params, "fields": fields or ""}
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def cache_key_is_hash(cache_key: str) -> bool:
    return len(cache_key) == 64 and all(char in "0123456789abcdef" for char in cache_key.lower())


def _safe_identifier(value: str) -> str:
    stripped = (value or "").strip()
    return stripped if stripped else "unknown_api"


def _safe_path_part(value: str) -> str:
    safe = []
    for char in str(value):
        if char.isalnum() or char in {"-", "_", "."}:
            safe.append(char)
        else:
            safe.append("_")
    result = "".join(safe).strip("._")
    return result or "cache"


def _sanitize_text(value: str) -> str:
    text = value.replace("\n", " ").replace("\r", " ").strip()
    if not text:
        return ""
    lower = text.lower()
    if "<html" in lower or "<!doctype" in lower:
        return "upstream_html_or_challenge"
    for marker in _SENSITIVE_MARKERS:
        if marker in lower:
            return "sensitive_detail_redacted"
    if len(text) > MAX_ERROR_MESSAGE_LENGTH:
        return f"{text[:MAX_ERROR_MESSAGE_LENGTH].rstrip()}..."
    return text
