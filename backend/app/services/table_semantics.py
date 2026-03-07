"""Shared table semantics helpers.

Centralized token normalization and column role inference for table normalization and
comparison.  This keeps role logic in one place and surfaces unknown-role
statistics for observability.
"""

from __future__ import annotations

import logging
import re


class TableSemantics:
    """Infer and normalize semantic roles for table columns."""

    _ROLE_ALIASES = {
        "parameter": ["参数", "参数名称", "检验项目", "项目", "条目"],
        "model": ["型号", "机型", "规格", "规格型号", "适用型号", "型号规格", "序号型号"],
        "group": ["分组", "类别", "腔室", "部位", "类型", "组别", "适用类型", "型号类型", "部件"],
        "default": ["标准设置", "默认设置", "默认值", "设置值", "目标值", "标准值"],
        "tolerance": ["允许误差", "容差", "误差", "偏差", "公差", "范围上限", "范围下限"],
        "value": ["常规数值", "数值", "范围", "检验结果", "值", "数值范围", "范围值"],
        "remark": ["备注", "说明", "解释"],
    }

    def __init__(self, logger: logging.Logger | None = None) -> None:
        self.logger = logger
        self.unknown_role_count = 0

    def reset(self) -> None:
        """Reset statistics counters."""
        self.unknown_role_count = 0

    @staticmethod
    def normalize_token(text: str) -> str:
        """Normalize tokens for deterministic matching."""
        if not text:
            return ""
        # Keep Chinese characters and alphanumerics, collapse whitespace and punctuation variants.
        normalized = re.sub(r"\s+", "", text)
        normalized = normalized.replace("／", "/").replace("（", "(").replace("）", ")")
        normalized = normalized.replace("—", "-").replace("–", "-").replace("－", "-")
        normalized = normalized.replace("％", "%")
        return normalized.strip()

    def _normalize_path(self, labels: list[str] | str | None) -> list[str]:
        if isinstance(labels, str):
            labels_list = [labels]
        else:
            labels_list = list(labels or [])
        out: list[str] = []
        for raw in labels_list:
            token = self.normalize_token(str(raw or ""))
            if token:
                out.append(token)
        return out

    def infer_column_role(self, labels: list[str] | str | None) -> str:
        """Infer a column role from one or more header labels."""
        normalized = self._normalize_path(labels)
        if not normalized:
            self.unknown_role_count += 1
            self._log_unknown(""
                              )
            return "unknown"
        joined = "/".join(normalized)

        for role, aliases in self._ROLE_ALIASES.items():
            for alias in aliases:
                # Use direct substring match and token-match against each label.
                if alias in joined:
                    return role

        # Value-like fallback: if there is any numeric unit marker in a single-level header,
        # keep it as value for compatibility.
        if re.search(r"(?:V|mV|μV|A|Ω|KΩ|kΩ|ppm|ms|Hz|V|VA|W)\b", joined):
            return "value"

        self.unknown_role_count += 1
        self._log_unknown(joined)
        return "unknown"

    def split_path_semantics(
        self,
        labels: list[str] | str | None,
    ) -> tuple[list[str], str, str]:
        """Split multidimensional header path into dimension labels and leaf value role.

        Returns:
            dimension_labels, leaf_label, leaf_role
        """
        normalized = self._normalize_path(labels)
        if not normalized:
            return [], "", "unknown"

        leaf_role = self.infer_column_role(normalized)

        if leaf_role in {"value", "default", "tolerance", "remark", "unknown"} and len(normalized) > 1:
            dimension_labels = normalized[:-1]
            leaf_label = normalized[-1]
            if leaf_role == "unknown":
                # For headers like "心房/值" if infer unknown, keep last segment as value candidate.
                leaf_role = "value"
            return dimension_labels, leaf_label, leaf_role

        if leaf_role in {"parameter", "model", "group"}:
            return normalized, "", leaf_role

        # Single-segment columns are usually dimension-like if they are not clearly value.
        if len(normalized) == 1:
            return normalized[:-0], normalized[0], leaf_role

        return normalized[:-1], normalized[-1], leaf_role

    def infer_column_roles(self, labels_per_column: list[list[str]] | list[str]) -> list[str]:
        """Infer roles for all columns and count unknowns."""
        roles: list[str] = []
        for labels in labels_per_column:
            roles.append(self.infer_column_role(labels))
        return roles

    def infer_value_leaf_label(self, label: str, role: str | None = None) -> str:
        """Normalize leaf label while keeping semantic preference for value columns."""
        normalized = self.normalize_token(label)
        if not normalized:
            return ""

        role = role or self.infer_column_role([normalized])
        if role == "unknown":
            if "检验结果" in normalized:
                return "检验结果"
            return normalized
        if role in {"default", "value", "tolerance", "remark", "model", "group", "parameter"}:
            return normalized
        return normalized

    def _log_unknown(self, token: str) -> None:
        if not self.logger:
            return
        self.logger.info("table_semantics unknown role for header token=%r", token)
