"""Unified presentation status mapping for PTR comparison outputs."""

from __future__ import annotations

from typing import Any


_STATUS_META: dict[str, dict[str, Any]] = {
    "match": {
        "label": "一致",
        "variant": "success",
        "is_failure": False,
        "explanation": "",
    },
    "differ": {
        "label": "不一致",
        "variant": "danger",
        "is_failure": True,
        "explanation": "正文提取结果与技术要求不一致。",
    },
    "missing": {
        "label": "缺失",
        "variant": "danger",
        "is_failure": True,
        "explanation": "当前报告正文中未提取到对应条款。",
    },
    "group_clause": {
        "label": "分组条款",
        "variant": "accent",
        "is_failure": False,
        "explanation": "该条款属于父级/分组条款，已由下级条款单独判定。",
    },
    "out_of_scope_in_current_report": {
        "label": "范围外",
        "variant": "warn",
        "is_failure": False,
        "explanation": "该条款不在当前报告本次检验范围内。",
    },
    "external_reference": {
        "label": "引用外部报告",
        "variant": "info",
        "is_failure": False,
        "explanation": "该条款结果引用外部报告，当前报告未重复列出完整数据。",
    },
    "pending_evidence": {
        "label": "待补证",
        "variant": "warn",
        "is_failure": False,
        "explanation": "该条款当前材料待补证，暂不按不一致处理。",
    },
    "excluded": {
        "label": "已排除",
        "variant": "info",
        "is_failure": False,
        "explanation": "该条款已从本次正文一致性统计中排除。",
    },
}


def get_clause_presentation_status(
    result: str,
    comparison_status: str = "",
    match_reason: str = "",
) -> dict[str, Any]:
    """Map backend comparison result/status to a unified presentation status."""
    normalized_status = (comparison_status or "").strip()
    normalized_reason = (match_reason or "").strip()
    normalized_result = (result or "").strip()

    if normalized_status in _STATUS_META:
        status = normalized_status
    elif normalized_result == "match":
        status = "match"
    elif normalized_result == "differ":
        status = "differ"
    elif normalized_result == "missing":
        status = "missing"
    elif normalized_result == "excluded":
        if normalized_reason == "group_clause_with_children":
            status = "group_clause"
        elif normalized_reason == "out_of_scope_third_page":
            status = "out_of_scope_in_current_report"
        else:
            status = "excluded"
    else:
        status = "excluded"

    meta = _STATUS_META[status]
    return {
        "display_status": status,
        "display_status_label": meta["label"],
        "display_status_variant": meta["variant"],
        "is_failure": meta["is_failure"],
        "display_status_explanation": meta["explanation"],
    }
