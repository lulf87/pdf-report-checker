"""
Table Expansion Comparator.

Handles "见表X" references by expanding table content and comparing
parameter names and values.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Any

from app.models.ptr_models import PTRClause, PTRDocument, PTRTable
from app.models.report_models import InspectionItem
from app.services.text_normalizer import TextNormalizer

logger = logging.getLogger(__name__)


@dataclass
class ParameterComparison:
    """Result of comparing a single parameter.

    Attributes:
        parameter_name: Name of the parameter
        ptr_value: Value from PTR table
        report_value: Value from report
        matches: Whether values match
        is_expanded: Whether this was from a "见表X" expansion
    """

    parameter_name: str
    ptr_value: str
    report_value: str
    matches: bool
    is_expanded: bool = False


@dataclass
class TableExpansionResult:
    """Result of table expansion and comparison.

    Attributes:
        table_number: Table number that was expanded
        table_found: Whether the table was found in PTR
        clause_number: PTR clause number that references this table
        parameters: List of parameter comparisons
        total_matches: Number of matching parameters
        total_parameters: Total number of parameters
    """

    table_number: int
    table_found: bool
    parameters: list[ParameterComparison] = field(default_factory=list)
    total_matches: int = 0
    total_parameters: int = 0
    clause_number: str = ""

    @property
    def all_match(self) -> bool:
        """Check if all parameters match."""
        return self.total_matches == self.total_parameters and self.total_parameters > 0

    @property
    def match_rate(self) -> float:
        """Calculate match rate."""
        if self.total_parameters == 0:
            return 0.0
        return self.total_matches / self.total_parameters


class TableComparator:
    """Compares table-referenced content between PTR and report."""

    def __init__(
        self,
        normalizer: TextNormalizer | None = None,
    ):
        """Initialize table comparator.

        Args:
            normalizer: Text normalizer instance (created if None)
        """
        self.normalizer = normalizer or TextNormalizer()

    def compare_table_references(
        self,
        ptr_doc: PTRDocument,
        report_items: list[InspectionItem],
    ) -> list[TableExpansionResult]:
        """Compare all table-referenced clauses.

        Args:
            ptr_doc: PTR document
            report_items: List of inspection items from report

        Returns:
            List of table expansion results
        """
        results: list[TableExpansionResult] = []

        # Find clauses with table references
        for clause in ptr_doc.clauses:
            if not clause.has_table_references():
                continue

            for table_ref in clause.table_references:
                result = self._compare_table_reference(
                    table_ref.table_number,
                    clause,
                    ptr_doc,
                    report_items,
                )
                results.append(result)

        return results

    def _compare_table_reference(
        self,
        table_number: int,
        clause: PTRClause,
        ptr_doc: PTRDocument,
        report_items: list[InspectionItem],
    ) -> TableExpansionResult:
        """Compare a single table reference.

        Args:
            table_number: Table number to expand
            clause: Clause containing the reference
            ptr_doc: PTR document
            report_items: Report items to compare against

        Returns:
            TableExpansionResult
        """
        result = TableExpansionResult(
            table_number=table_number,
            table_found=False,
            clause_number=str(clause.number),
        )

        # Find matching report item first (used for selecting best table candidate).
        report_item = self._find_matching_report_item(clause, report_items)
        if not report_item:
            logger.info(f"No matching report item for clause {clause.number}")
            return result

        # Find table in PTR (support duplicate-number candidates).
        table_candidates = ptr_doc.get_tables_by_number(table_number)
        if not table_candidates:
            logger.warning(f"Table {table_number} not found in PTR document")
            return result
        scoped_candidates = self._scope_table_candidates_for_clause(
            ptr_doc=ptr_doc,
            clause=clause,
            candidates=table_candidates,
            report_item=report_item,
        )
        if scoped_candidates:
            table_candidates = scoped_candidates

        ptr_table = self._select_best_ptr_table(
            candidates=table_candidates,
            clause=clause,
            report_item=report_item,
        )
        if not ptr_table:
            logger.warning(
                f"Table {table_number} candidates exist but no suitable table selected"
            )
            return result

        result.table_found = True

        # Compare parameters
        result.parameters = self._compare_table_parameters(
            ptr_table,
            report_item,
            clause=clause,
            report_items=report_items,
        )

        # Calculate statistics
        result.total_parameters = len(result.parameters)
        result.total_matches = sum(1 for p in result.parameters if p.matches)

        return result

    def _select_best_ptr_table(
        self,
        candidates: list[PTRTable],
        clause: PTRClause,
        report_item: InspectionItem,
    ) -> PTRTable | None:
        """Select the most plausible table when table numbers are duplicated."""
        if not candidates:
            return None
        if len(candidates) == 1:
            return candidates[0]

        clause_text = self.normalizer.normalize(clause.text_content or "")
        report_text = self.normalizer.normalize(
            "\n".join(
                part
                for part in [
                    report_item.standard_requirement or "",
                    report_item.test_result or "",
                    report_item.inspection_project or "",
                ]
                if part and part.strip()
            )
        )

        best_score = float("-inf")
        best_table: PTRTable | None = None
        for table in candidates:
            score = self._score_table_candidate(table, clause_text, report_text)
            if score > best_score:
                best_score = score
                best_table = table

        if best_table and len(candidates) > 1:
            logger.info(
                "Selected table candidate for 表%s: page=%s score=%.2f",
                best_table.table_number,
                best_table.page,
                best_score,
            )
        return best_table

    def _scope_table_candidates_for_clause(
        self,
        ptr_doc: PTRDocument,
        clause: PTRClause,
        candidates: list[PTRTable],
        report_item: InspectionItem,
    ) -> list[PTRTable]:
        """Scope duplicate-number table candidates with chapter-2-first strategy.

        Rule:
        1) For Chapter-2 clauses, first search same-number tables inside Chapter 2 page range.
        2) If any in-range table name/topic matches clause text, use only those in-range matches.
        3) If in-range tables exist but none name-matches, fallback to all candidates.
        """
        if not candidates:
            return []
        if not clause.number.parts or clause.number.parts[0] != 2:
            return candidates

        start_page = int(ptr_doc.chapter2_start or 0)
        end_page = int(ptr_doc.chapter2_end or 0)
        if start_page <= 0 or end_page <= 0 or end_page < start_page:
            return candidates

        chapter2_candidates = [
            table
            for table in candidates
            if self._table_in_page_range(table, start_page, end_page)
        ]
        if not chapter2_candidates:
            return candidates

        name_matched = [
            table
            for table in chapter2_candidates
            if self._table_name_matches_clause(table, clause, report_item)
        ]
        if name_matched:
            logger.info(
                "Table scoping for clause %s: using %s chapter-2 name-matched candidates (total=%s)",
                clause.number,
                len(name_matched),
                len(candidates),
            )
            return name_matched

        logger.info(
            "Table scoping for clause %s: no chapter-2 name match, fallback to all candidates (chapter2=%s total=%s)",
            clause.number,
            len(chapter2_candidates),
            len(candidates),
        )
        return candidates

    def _table_in_page_range(self, table: PTRTable, start_page: int, end_page: int) -> bool:
        """Whether table overlaps with target page range."""
        table_start = int(table.page or 0)
        table_end = int(table.page_end or table.page or 0)
        if table_start <= 0:
            return False
        if table_end < table_start:
            table_end = table_start
        return not (table_end < start_page or table_start > end_page)

    def _table_name_matches_clause(
        self,
        table: PTRTable,
        clause: PTRClause,
        report_item: InspectionItem,
    ) -> bool:
        """Whether table content/caption appears relevant to the clause topic name."""
        clause_topics = self._extract_clause_topics(clause.text_content or "")
        if not clause_topics:
            # For generic table-reference sentence, keep parameter tables as valid name matches.
            return self._is_parameter_table(table)

        table_text = self._compact(
            " ".join(
                [
                    table.caption or "",
                    " ".join(table.headers or []),
                    " ".join((row[0] if row else "") for row in table.rows[:80]),
                ]
            )
        )
        report_text = self._compact(
            " ".join(
                part
                for part in [
                    report_item.inspection_project or "",
                    report_item.standard_requirement or "",
                ]
                if part and part.strip()
            )
        )

        for topic in clause_topics:
            if not topic:
                continue
            if topic in table_text:
                return True
            if report_text and topic in report_text:
                # Topic aligns with report; allow parameter table fallback.
                if self._is_parameter_table(table):
                    return True
        return False

    def _score_table_candidate(
        self,
        table: PTRTable,
        clause_text: str,
        report_text: str,
    ) -> float:
        """Score a table candidate for clause-specific matching."""
        headers_compact = self._compact(" ".join(table.headers or []))
        row_count = len(table.rows or [])
        col_count = max(
            len(table.headers or []),
            max((len(r) for r in (table.rows or [])), default=0),
        )

        score = 0.0
        score += float(row_count) * 0.12
        score += float(col_count) * 0.4

        if self._is_parameter_table(table):
            score += 12.0
        if "符合表1中的数值" in clause_text and self._is_parameter_table(table):
            score += 8.0

        if len(table.headers) <= 2 and len(headers_compact) > 40:
            # Penalize narrative/requirement tables with long sentence-like headers.
            score -= 10.0

        # Overlap between report text and table row labels.
        row_label_text = self._compact(" ".join((row[0] if row else "") for row in table.rows[:60]))
        if row_label_text and report_text:
            overlap = self._token_overlap_ratio(row_label_text, self._compact(report_text))
            score += overlap * 10.0

        # Prefer table with richer parameter rows over title-only fragments.
        non_empty_rows = sum(1 for row in table.rows if any(str(cell or "").strip() for cell in row))
        score += float(non_empty_rows) * 0.08
        return score

    def _is_parameter_table(self, table: PTRTable) -> bool:
        headers = self._compact(" ".join(table.headers or []))
        return (
            "参数" in headers
            and ("型号" in headers or "标准设置" in headers or "允许误差" in headers or "常规数值" in headers)
        )

    def _compact(self, text: str) -> str:
        return re.sub(r"\s+", "", self.normalizer.normalize(text or ""))

    def _token_overlap_ratio(self, text_a: str, text_b: str) -> float:
        if not text_a or not text_b:
            return 0.0
        tokens = [token for token in re.findall(r"[\u4e00-\u9fffA-Za-z0-9]+", text_a) if len(token) >= 2]
        if not tokens:
            return 0.0
        matched = sum(1 for token in tokens if token in text_b)
        return matched / len(tokens)

    def _find_matching_report_item(
        self,
        clause: PTRClause,
        report_items: list[InspectionItem],
    ) -> InspectionItem | None:
        """Find the report item matching a clause.

        Args:
            clause: PTR clause
            report_items: List of inspection items

        Returns:
            Matching item or None
        """
        clause_num_str = str(clause.number)

        # Prefer report standard clause column.
        for item in report_items:
            std_clause = self._extract_clause_number(item.standard_clause)
            if std_clause and std_clause == clause_num_str:
                return item

        # Try exact match on sequence number
        for item in report_items:
            if item.sequence_number == clause_num_str:
                return item

        # Try partial match
        for item in report_items:
            if item.sequence_number.startswith(clause_num_str):
                return item

        # Try text match
        clause_text = self.normalizer.normalize(clause.text_content)
        for item in report_items:
            item_text = self.normalizer.normalize(item.inspection_project)
            if clause_text in item_text or item_text in clause_text:
                return item

        return None

    def _extract_clause_number(self, text: str) -> str:
        """Extract normalized clause number from report standard clause text."""
        if not text:
            return ""
        import re

        match = re.search(r"(\d+(?:\.\d+)+)", text)
        return match.group(1) if match else ""

    def _compare_table_parameters(
        self,
        ptr_table: PTRTable,
        report_item: InspectionItem,
        clause: PTRClause | None = None,
        report_items: list[InspectionItem] | None = None,
    ) -> list[ParameterComparison]:
        """Compare parameters from PTR table with report item.

        Args:
            ptr_table: PTR table
            report_item: Report inspection item

        Returns:
            List of parameter comparisons
        """
        comparisons: list[ParameterComparison] = []

        # Merge grouped continuation rows with same sequence block.
        report_text = self._build_grouped_report_text(
            report_item=report_item,
            report_items=report_items or [],
        )
        if not report_text:
            report_text = "\n".join(
                part
                for part in [
                    report_item.standard_requirement or "",
                    report_item.test_result or "",
                    report_item.inspection_project or "",
                ]
                if part and part.strip()
            )

        # Prefer report-row topic (inspection_project) to avoid OCR noise from PTR clause body.
        clause_topics = self._resolve_row_filter_topics(report_item=report_item, clause=clause)

        # Compare each row in PTR table
        param_col_idx = self._find_column_index(
            ptr_table.headers,
            ["参数", "参数名称"],
            default=0,
        )
        model_col_idx = self._find_column_index(
            ptr_table.headers,
            ["型号"],
            default=1 if len(ptr_table.headers) > 1 else 0,
        )
        candidate_rows: list[list[str]] = []
        fallback_rows: list[list[str]] = []
        for row in ptr_table.rows:
            if not row or self._is_header_like_row(row, ptr_table.headers):
                continue
            fallback_rows.append(row)
            param_name = row[param_col_idx] if param_col_idx < len(row) else (row[0] if row else "")
            if clause_topics and not self._row_matches_clause_topics(param_name, clause_topics):
                continue
            candidate_rows.append(row)

        rows_to_compare = candidate_rows if candidate_rows else fallback_rows
        for row in rows_to_compare:
            if not row:
                continue

            # First column is typically parameter name
            param_name = row[param_col_idx] if param_col_idx < len(row) else (row[0] if row else "")
            ptr_value = self._pick_ptr_value_from_row(row, ptr_table.headers)

            if not param_name:
                continue

            # Coverage-style comparison: report can contain extra content,
            # but should include all core content for corresponding PTR row.
            covered, evidence = self._is_ptr_row_covered_in_report(
                row=row,
                headers=ptr_table.headers,
                report_text=report_text,
                param_col_idx=param_col_idx,
                model_col_idx=model_col_idx,
            )

            report_value = evidence
            matches = covered
            if not matches:
                # Fallback to legacy single-value extraction for backward compatibility.
                report_value = self._extract_parameter_value(param_name, report_text)
                if not report_value:
                    model_text = row[model_col_idx] if model_col_idx < len(row) else ""
                    if model_text and model_text.strip() and model_text.strip() != "全部型号":
                        report_value = self._extract_parameter_value(
                            f"{param_name} {model_text}",
                            report_text,
                        )
                matches = self._compare_values(ptr_value, report_value)

            comparison = ParameterComparison(
                parameter_name=param_name,
                ptr_value=ptr_value,
                report_value=report_value,
                matches=matches,
                is_expanded=True,
            )
            comparisons.append(comparison)

        return comparisons

    def _resolve_row_filter_topics(
        self,
        report_item: InspectionItem,
        clause: PTRClause | None,
    ) -> list[str]:
        """Resolve parameter topics for row filtering.

        Priority:
        1) Report inspection project/requirement heading (usually cleaner and clause-specific).
        2) PTR clause text fallback.
        """
        report_topics = self._extract_report_item_topics(report_item)
        if report_topics:
            return report_topics
        return self._extract_clause_topics(clause.text_content if clause else "")

    def _extract_report_item_topics(self, report_item: InspectionItem) -> list[str]:
        """Extract clause topic from report row fields with minimal noise."""
        candidates: list[str] = []

        project = str(report_item.inspection_project or "").strip()
        if project:
            normalized = self._normalize_topic_label(project)
            if normalized and len(normalized) >= 2:
                candidates.append(normalized)
            candidates.extend(self._extract_clause_topics(project))

        requirement = str(report_item.standard_requirement or "").strip()
        if requirement:
            first_line = requirement.splitlines()[0].strip()
            first_segment = re.split(r"[。；;]", first_line, maxsplit=1)[0].strip()
            if first_segment:
                candidates.extend(self._extract_clause_topics(first_segment))

        topics: list[str] = []
        seen: set[str] = set()
        for topic in candidates:
            normalized = self._normalize_topic_label(topic)
            if len(normalized) < 2:
                continue
            if normalized in seen:
                continue
            seen.add(normalized)
            topics.append(normalized)
        return topics

    def _build_grouped_report_text(
        self,
        report_item: InspectionItem,
        report_items: list[InspectionItem],
    ) -> str:
        """Build merged text for one logical sequence group in report table."""
        if not report_items:
            return ""
        try:
            start_idx = next(i for i, item in enumerate(report_items) if item is report_item)
        except StopIteration:
            start_idx = -1
        if start_idx < 0:
            return ""

        base_seq = self._extract_sequence_index(report_item.sequence_number)
        parts: list[str] = []
        seen: set[str] = set()

        for idx in range(start_idx, len(report_items)):
            item = report_items[idx]
            if idx > start_idx:
                seq = self._extract_sequence_index(item.sequence_number)
                if base_seq and seq and seq != base_seq:
                    break
                if not base_seq and seq:
                    break

            for raw in [
                item.standard_requirement,
                item.test_result,
                item.inspection_project,
                item.sequence_number if self._looks_like_shifted_text(item.sequence_number) else "",
            ]:
                text = str(raw or "").strip()
                if not text:
                    continue
                key = self._compact(text)
                if key in seen:
                    continue
                seen.add(key)
                parts.append(text)

        return "\n".join(parts).strip()

    def _extract_sequence_index(self, sequence: str | None) -> str:
        """Extract numeric row index from sequence column like '39' or '续39'."""
        text = re.sub(r"\s+", "", str(sequence or "")).replace("续", "")
        match = re.fullmatch(r"(\d+)", text)
        return match.group(1) if match else ""

    def _looks_like_shifted_text(self, value: str | None) -> bool:
        """Whether sequence column likely contains shifted requirement text."""
        text = str(value or "").strip()
        if not text:
            return False
        if self._extract_sequence_index(text):
            return False
        compact = re.sub(r"\s+", "", text)
        if re.fullmatch(r"\d+(?:\.\d+)+", compact):
            return False
        if len(text) >= 8 and ("\n" in text or "。" in text or "：" in text or "；" in text):
            return True
        if re.search(r"\d+(?:\.\d+)+", text) and len(text) > 10:
            return True
        return False

    def _is_ptr_row_covered_in_report(
        self,
        row: list[str],
        headers: list[str],
        report_text: str,
        param_col_idx: int,
        model_col_idx: int,
    ) -> tuple[bool, str]:
        """Whether report text covers all core cells from one PTR parameter row."""
        if not report_text:
            return False, ""

        report_compact = self._coverage_compact(report_text)
        if not report_compact:
            return False, ""

        required_cells: list[str] = []
        for idx, raw_cell in enumerate(row):
            cell = str(raw_cell or "").strip()
            if not cell or self._is_placeholder(cell):
                continue
            # Model column is metadata in most parameter rows; don't enforce strict presence.
            if idx == model_col_idx:
                continue
            header = headers[idx] if idx < len(headers) else ""
            header_compact = self._compact(header)
            if "型号" in header_compact:
                continue
            if self._looks_like_model_value(cell):
                continue
            required_cells.append(cell)

        if not required_cells:
            return False, ""

        for cell in required_cells:
            if not self._cell_is_covered(cell, report_compact):
                return False, ""

        param_name = row[param_col_idx] if param_col_idx < len(row) else (row[0] if row else "")
        evidence = self._extract_parameter_value(str(param_name or ""), report_text)
        return True, evidence or "已覆盖"

    def _cell_is_covered(self, cell_text: str, report_compact: str) -> bool:
        """Check if one PTR cell content is present in report text (allows formatting variance)."""
        cell_compact = self._coverage_compact(cell_text)
        if not cell_compact:
            return True
        if cell_compact in report_compact:
            return True

        tokens = re.findall(r"[\u4e00-\u9fff]+|[A-Za-z]{2,}", cell_compact)
        for token in tokens:
            if token not in report_compact:
                return False

        numbers = self._extract_all_numbers(cell_compact)
        if numbers and not self._numbers_in_order(numbers, report_compact):
            return False

        # When there is at least some semantic token overlap and numbers align, treat as covered.
        return bool(tokens or numbers)

    def _numbers_in_order(self, numbers: list[str], text: str) -> bool:
        """Check whether numbers appear in order inside text."""
        if not numbers:
            return True
        cursor = 0
        for num in numbers:
            idx = text.find(num, cursor)
            if idx < 0:
                return False
            cursor = idx + len(num)
        return True

    def _coverage_compact(self, text: str) -> str:
        """Compact text for coverage comparison while normalizing common OCR symbol variants."""
        compact = self._compact(text or "")
        if not compact:
            return ""
        compact = compact.replace("µ", "μ")
        compact = re.sub(r"(?i)(\d)u(?=s\b)", r"\1μ", compact)
        compact = re.sub(r"(?i)u(?=g/)", "μ", compact)
        compact = compact.replace("﹣", "-").replace("－", "-").replace("–", "-").replace("—", "-")
        compact = compact.replace("％", "%")
        return compact

    def _looks_like_model_value(self, value: str) -> bool:
        compact = self._compact(value)
        if not compact:
            return False
        if "全部型号" in compact:
            return True
        if "Edora" in value:
            return True
        if re.search(r"(SR|DR)(?:-T)?", value, re.IGNORECASE):
            return True
        return False

    def _extract_clause_topics(self, clause_text: str) -> list[str]:
        """Extract likely parameter topics from clause text."""
        text = self.normalizer.normalize(clause_text or "")
        if not text:
            return []

        candidates: list[str] = []
        # Priority: heading before colon.
        heading = re.split(r"[:：]", text, maxsplit=1)[0].strip()
        if heading and self._looks_like_parameter_topic(heading):
            candidates.append(heading)

        # Extract domain terms ending with common parameter suffixes.
        suffixes = "频率|灵敏度|不应期|间期|阻抗|空白期|模式|幅度|宽度|保护"
        regex = re.compile(rf"[\u4e00-\u9fffA-Za-z0-9/（）()]+(?:{suffixes})")
        candidates.extend(regex.findall(text))

        normalized_terms: list[str] = []
        seen: set[str] = set()
        for raw in candidates:
            normalized = self._normalize_topic_label(raw)
            if len(normalized) < 2:
                continue
            if normalized in seen:
                continue
            seen.add(normalized)
            normalized_terms.append(normalized)
        return normalized_terms

    def _looks_like_parameter_topic(self, text: str) -> bool:
        compact = self._normalize_topic_label(text)
        if not compact:
            return False
        keywords = ["频率", "灵敏度", "不应期", "间期", "阻抗", "空白期", "模式", "幅度", "宽度", "保护"]
        if any(keyword in compact for keyword in keywords):
            return True
        # Unit-bearing labels such as "脉冲宽度(ms)".
        if re.search(r"[（(].*(ms|mV|bpm|Hz|V|A|Ω|KΩ|ppm).*[）)]", text, re.IGNORECASE):
            return True
        return False

    def _normalize_topic_label(self, text: str) -> str:
        normalized = self._compact(text)
        # Remove bracketed unit fragments and footnote markers.
        normalized = re.sub(r"[（(][^）)]*[）)]", "", normalized)
        normalized = re.sub(r"[①②③④⑤⑥⑦⑧⑨⑩0-9]+$", "", normalized)
        normalized = normalized.replace("/", "")
        return normalized

    def _row_matches_clause_topics(self, param_name: str, topics: list[str]) -> bool:
        param_norm = self._normalize_topic_label(param_name)
        if not param_norm:
            return False
        for topic in topics:
            if topic in param_norm or param_norm in topic:
                return True
        return False

    def _find_column_index(
        self,
        headers: list[str],
        keywords: list[str],
        default: int = 0,
    ) -> int:
        for idx, header in enumerate(headers or []):
            merged = self.normalizer.normalize(header or "")
            if any(keyword in merged for keyword in keywords):
                return idx
        return default

    def _is_header_like_row(self, row: list[str], headers: list[str]) -> bool:
        if not row:
            return False
        row_norm = [self._compact(cell) for cell in row]
        header_norm = [self._compact(cell) for cell in headers or []]
        if header_norm and row_norm[: len(header_norm)] == header_norm[: len(row_norm)]:
            return True
        merged = "".join(row_norm)
        return all(keyword in merged for keyword in ["参数", "型号"]) and ("标准设置" in merged or "允许误差" in merged)

    def _extract_parameter_value(
        self,
        param_name: str,
        report_text: str,
    ) -> str:
        """Extract parameter value from report text.

        Args:
            param_name: Name of parameter to find
            report_text: Report test result text

        Returns:
            Extracted value or empty string
        """
        if not param_name or not report_text:
            return ""

        # Normalize for comparison
        norm_name = self.normalizer.normalize(param_name)
        norm_text = self.normalizer.normalize(report_text)
        compact_name = re.sub(r"\s+", "", norm_name)
        compact_text = re.sub(r"\s+", "", norm_text)

        # Try line-oriented matching first (better for OCR line breaks).
        lines = [line.strip() for line in report_text.splitlines() if line.strip()]
        for idx, line in enumerate(lines):
            normalized_line = self.normalizer.normalize(line)
            compact_line = re.sub(r"\s+", "", normalized_line)
            if compact_name and compact_name not in compact_line:
                continue

            # Pattern: 参数[:：=]值
            same_line = re.search(
                re.escape(norm_name) + r"\s*[:：=]\s*([^\n，,。；;]+)",
                normalized_line,
            )
            if same_line:
                return same_line.group(1).strip()

            # Pattern: 参数 值（同一行）
            same_line = re.search(
                re.escape(norm_name) + r"\s+([^\n，,。；;]+)",
                normalized_line,
            )
            if same_line:
                return same_line.group(1).strip()

            # Pattern: 参数在当前行，值在下一行
            if idx + 1 < len(lines):
                next_line = self.normalizer.normalize(lines[idx + 1]).strip()
                if next_line:
                    return next_line

        # Fallback: compact-text regex, tolerant to OCR spacing.
        compact_pattern = re.escape(compact_name) + r"(?:[:：=]|)([^，,。；;]{1,40})"
        compact_match = re.search(compact_pattern, compact_text)
        if compact_match:
            candidate = compact_match.group(1).strip()
            candidate = re.sub(r"^[=:：\-\s]+", "", candidate).strip()
            if candidate:
                return candidate

        # Last-resort: if parameter name appears, return nearby numeric expression.
        idx = compact_text.find(compact_name)
        if idx >= 0:
            window = compact_text[idx: idx + len(compact_name) + 60]
            numeric = self._extract_primary_numeric_token(window)
            if numeric:
                return numeric

        return ""

    def _compare_values(self, value1: str, value2: str) -> bool:
        """Compare two parameter values.

        Args:
            value1: First value
            value2: Second value

        Returns:
            True if values match
        """
        if not value1 and not value2:
            return True

        # Treat placeholders as empty equivalents.
        if self._is_placeholder(value1) and self._is_placeholder(value2):
            return True

        norm1 = self.normalizer.normalize(value1)
        norm2 = self.normalizer.normalize(value2)

        if self._is_placeholder(norm1) and self._is_placeholder(norm2):
            return True

        # Fast path: normalized exact match
        if norm1 == norm2:
            return True

        compact1 = re.sub(r"\s+", "", norm1)
        compact2 = re.sub(r"\s+", "", norm2)
        if compact1 == compact2:
            return True

        # Semantic numeric comparison
        if self._evaluate_numeric_constraint(expected=norm1, actual=norm2):
            return True

        if self._evaluate_numeric_constraint(expected=norm2, actual=norm1):
            return True

        # If both contain the same ordered numeric tokens, consider equal.
        nums1 = self._extract_all_numbers(norm1)
        nums2 = self._extract_all_numbers(norm2)
        if nums1 and nums2 and nums1 == nums2:
            return True

        # Unit-only differences that survive normalizer should not fail.
        unitless1 = re.sub(r"[A-Za-zμΩ/%]+", "", compact1)
        unitless2 = re.sub(r"[A-Za-zμΩ/%]+", "", compact2)
        if unitless1 and unitless1 == unitless2:
            return True

        return norm1 == norm2

    def _pick_ptr_value_from_row(self, row: list[str], headers: list[str] | None = None) -> str:
        """Pick PTR expected value from table row."""
        if not row or len(row) < 2:
            return ""

        normalized_headers = [self.normalizer.normalize(h or "") for h in (headers or [])]
        preferred_columns: list[int] = []
        for keywords in [["标准设置"], ["常规数值"], ["允许误差"]]:
            for idx, header in enumerate(normalized_headers):
                if any(keyword in header for keyword in keywords):
                    preferred_columns.append(idx)
                    break

        seen: set[int] = set()
        ordered_candidates: list[int] = []
        for idx in preferred_columns + list(range(1, len(row))):
            if idx not in seen and idx < len(row):
                seen.add(idx)
                ordered_candidates.append(idx)

        for idx in ordered_candidates:
            cell = row[idx]
            value = (cell or "").strip()
            if not value:
                continue
            # Avoid model-name column as comparison value.
            if idx == 1 and re.search(r"(Edora|SR|DR|全部型号)", value, re.IGNORECASE):
                continue
            if value:
                return value
        return ""

    def _is_placeholder(self, value: str) -> bool:
        """Whether value is placeholder/empty equivalent."""
        compact = re.sub(r"\s+", "", value or "")
        return compact in {"", "/", "／", "-", "—", "——", "N/A", "NA"}

    def _extract_all_numbers(self, text: str) -> list[str]:
        """Extract normalized numeric tokens from text."""
        if not text:
            return []
        return re.findall(r"[-+]?\d+(?:\.\d+)?", text)

    def _extract_primary_numeric_token(self, text: str) -> str:
        """Extract a likely primary numeric constraint/value token."""
        if not text:
            return ""
        token_pattern = re.compile(
            r"(?:<=|>=|<|>|≤|≥)?\s*[-+]?\d+(?:\.\d+)?(?:\s*±\s*[-+]?\d+(?:\.\d+)?%?)?"
        )
        match = token_pattern.search(text)
        return match.group(0).strip() if match else ""

    def _evaluate_numeric_constraint(self, expected: str, actual: str) -> bool:
        """Evaluate numeric constraint expressions.

        Supported expected patterns:
        - <=2.0, <2.0, >=, >
        - 20~350 / 20-350 / 20至350
        - 100±5 / 100±20%
        """
        expected_norm = self._normalize_math_symbols(expected)
        actual_norm = self._normalize_math_symbols(actual)

        actual_value = self._extract_single_numeric(actual_norm)
        if actual_value is None:
            return False

        # Range: a~b / a-b / a至b
        range_match = re.search(
            r"([-+]?\d+(?:\.\d+)?)\s*(?:~|～|至|到|-)\s*([-+]?\d+(?:\.\d+)?)",
            expected_norm,
        )
        if range_match:
            lo = float(range_match.group(1))
            hi = float(range_match.group(2))
            if lo > hi:
                lo, hi = hi, lo
            return lo <= actual_value <= hi

        # Comparator: <=x, <x, >=x, >x
        cmp_match = re.search(r"(<=|>=|<|>)\s*([-+]?\d+(?:\.\d+)?)", expected_norm)
        if cmp_match:
            op = cmp_match.group(1)
            threshold = float(cmp_match.group(2))
            if op == "<":
                return actual_value < threshold
            if op == "<=":
                return actual_value <= threshold
            if op == ">":
                return actual_value > threshold
            if op == ">=":
                return actual_value >= threshold

        # Tolerance: base±tol or base±pct%
        tol_match = re.search(
            r"([-+]?\d+(?:\.\d+)?)\s*±\s*([-+]?\d+(?:\.\d+)?)(%)?",
            expected_norm,
        )
        if tol_match:
            base = float(tol_match.group(1))
            tol = float(tol_match.group(2))
            if tol_match.group(3):
                tol = abs(base) * tol / 100.0
            return (base - tol) <= actual_value <= (base + tol)

        return False

    def _extract_single_numeric(self, text: str) -> float | None:
        """Extract first numeric value as float."""
        if not text:
            return None
        match = re.search(r"[-+]?\d+(?:\.\d+)?", text)
        if not match:
            return None
        try:
            return float(match.group(0))
        except ValueError:
            return None

    def _normalize_math_symbols(self, text: str) -> str:
        """Normalize math symbols for constraint parsing."""
        normalized = (text or "").strip()
        normalized = normalized.replace("≤", "<=").replace("≦", "<=").replace("＜", "<")
        normalized = normalized.replace("≥", ">=").replace("≧", ">=").replace("＞", ">")
        normalized = normalized.replace("—", "-").replace("–", "-").replace("−", "-")
        normalized = re.sub(r"\s+", " ", normalized)
        return normalized


def compare_table_expansions(
    ptr_doc: PTRDocument,
    report_items: list[InspectionItem],
) -> list[TableExpansionResult]:
    """Convenience function to compare table expansions.

    Args:
        ptr_doc: PTR document
        report_items: List of inspection items

    Returns:
        List of table expansion results
    """
    comparator = TableComparator()
    return comparator.compare_table_references(ptr_doc, report_items)


def get_table_expansion_summary(
    results: list[TableExpansionResult],
) -> dict[str, Any]:
    """Get summary of table expansion comparisons.

    Args:
        results: List of table expansion results

    Returns:
        Summary dictionary
    """
    total_tables = len(results)
    found_tables = sum(1 for r in results if r.table_found)
    total_params = sum(r.total_parameters for r in results)
    total_matches = sum(r.total_matches for r in results)

    return {
        "total_tables": total_tables,
        "found_tables": found_tables,
        "total_parameters": total_params,
        "total_matches": total_matches,
        "match_rate": total_matches / total_params if total_params > 0 else 0.0,
    }
