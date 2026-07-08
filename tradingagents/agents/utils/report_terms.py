"""Helpers for final report wording normalization."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any


REPORT_TEXT_FIELDS = (
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
)

INVEST_DEBATE_TEXT_FIELDS = (
    "bull_history",
    "bear_history",
    "history",
    "current_response",
    "judge_decision",
)

RISK_DEBATE_TEXT_FIELDS = (
    "aggressive_history",
    "conservative_history",
    "neutral_history",
    "history",
    "current_aggressive_response",
    "current_conservative_response",
    "current_neutral_response",
    "judge_decision",
)

_REPORT_TERM_REPLACEMENTS = (
    (re.compile(r"\bbullish\s+arguments?\b", re.IGNORECASE), "偏多论据"),
    (re.compile(r"\bbearish\s+arguments?\b", re.IGNORECASE), "偏空论据"),
    (re.compile(r"\bbullish\s+thes(?:is|es)\b", re.IGNORECASE), "偏多逻辑"),
    (re.compile(r"\bbearish\s+thes(?:is|es)\b", re.IGNORECASE), "偏空逻辑"),
    (re.compile(r"\bbullish\s+risks?\b", re.IGNORECASE), "偏多风险"),
    (re.compile(r"\bbearish\s+risks?\b", re.IGNORECASE), "偏空风险"),
    (re.compile(r"\bbullish\b", re.IGNORECASE), "偏多"),
    (re.compile(r"\bbearish\b", re.IGNORECASE), "偏空"),
)


def normalize_chinese_report_terms(text: str) -> str:
    """Normalize residual English direction terms in Chinese final reports."""
    normalized = text
    for pattern, replacement in _REPORT_TERM_REPLACEMENTS:
        normalized = pattern.sub(replacement, normalized)
    return normalized


def normalize_chinese_report_state(final_state: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize report text fields after agent reasoning has completed."""
    normalized_state = dict(final_state)

    for field in REPORT_TEXT_FIELDS:
        value = normalized_state.get(field)
        if isinstance(value, str):
            normalized_state[field] = normalize_chinese_report_terms(value)

    _normalize_nested_text_fields(
        normalized_state,
        "investment_debate_state",
        INVEST_DEBATE_TEXT_FIELDS,
    )
    _normalize_nested_text_fields(
        normalized_state,
        "risk_debate_state",
        RISK_DEBATE_TEXT_FIELDS,
    )

    return normalized_state


def _normalize_nested_text_fields(
    state: dict[str, Any],
    key: str,
    fields: tuple[str, ...],
) -> None:
    nested = state.get(key)
    if not isinstance(nested, Mapping):
        return

    normalized_nested = dict(nested)
    for field in fields:
        value = normalized_nested.get(field)
        if isinstance(value, str):
            normalized_nested[field] = normalize_chinese_report_terms(value)
    state[key] = normalized_nested
