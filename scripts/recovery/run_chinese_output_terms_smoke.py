"""Smoke test final Chinese report direction-term normalization."""

from __future__ import annotations

import re
import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

REPORT_TERMS_PATH = REPO_ROOT / "tradingagents" / "agents" / "utils" / "report_terms.py"
spec = spec_from_file_location("report_terms", REPORT_TERMS_PATH)
assert spec is not None and spec.loader is not None
report_terms = module_from_spec(spec)
spec.loader.exec_module(report_terms)

normalize_chinese_report_state = report_terms.normalize_chinese_report_state
normalize_chinese_report_terms = report_terms.normalize_chinese_report_terms


ENGLISH_DIRECTION_RE = re.compile(r"\b(bullish|bearish)\b", re.IGNORECASE)


def assert_normalized(source: str, expected_terms: tuple[str, ...]) -> None:
    normalized = normalize_chinese_report_terms(source)
    assert not ENGLISH_DIRECTION_RE.search(normalized), normalized
    for term in expected_terms:
        assert term in normalized, normalized


def main() -> int:
    assert_normalized("This is bullish", ("偏多",))
    assert_normalized("This is bearish", ("偏空",))
    assert_normalized("Bullish thesis and bearish risk", ("偏多逻辑", "偏空风险"))

    chinese_text = "普通中文文本保持不变，status: ok。"
    assert normalize_chinese_report_terms(chinese_text) == chinese_text

    contract_text = (
        "Data Source Contract: status: technical_error; "
        "empty_reason=no_event; source_type=vendor; fallback=none"
    )
    assert normalize_chinese_report_terms(contract_text) == contract_text

    state = {
        "market_report": "Market view is BULLISH.",
        "investment_debate_state": {
            "bull_history": "Bullish argument remains visible.",
            "bear_history": "Bearish thesis remains visible.",
            "count": 2,
        },
        "risk_debate_state": {
            "judge_decision": "bearish risk was raised.",
            "count": 1,
        },
        "messages": ["tool output is not a report field: bullish"],
    }
    normalized_state = normalize_chinese_report_state(state)

    report_blob = "\n".join(
        [
            normalized_state["market_report"],
            normalized_state["investment_debate_state"]["bull_history"],
            normalized_state["investment_debate_state"]["bear_history"],
            normalized_state["risk_debate_state"]["judge_decision"],
        ]
    )
    assert not ENGLISH_DIRECTION_RE.search(report_blob), report_blob
    assert "偏多" in normalized_state["market_report"]
    assert "偏多论据" in normalized_state["investment_debate_state"]["bull_history"]
    assert "偏空逻辑" in normalized_state["investment_debate_state"]["bear_history"]
    assert "偏空风险" in normalized_state["risk_debate_state"]["judge_decision"]
    assert normalized_state["messages"] == state["messages"]

    print("chinese_output_terms_smoke: passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
