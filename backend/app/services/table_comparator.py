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
from app.models.report_models import InspectionItem, ReportDocument
from app.services.table_semantics import TableSemantics
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
    comparison_status: str = "pass"
    details: dict[str, Any] = field(default_factory=dict)


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
    reference_type: str = "table_parameter_reference"
    referenced_table_label: str = ""

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
        semantics: TableSemantics | None = None,
    ):
        """Initialize table comparator.

        Args:
            normalizer: Text normalizer instance (created if None)
        """
        self.normalizer = normalizer or TextNormalizer()
        self.semantics = semantics or TableSemantics(logger=logger)

    def compare_table_references(
        self,
        ptr_doc: PTRDocument,
        report_items: list[InspectionItem],
        report_doc: ReportDocument | None = None,
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
        for clause in ptr_doc.get_main_requirement_clauses():
            if not clause.has_table_references():
                continue

            for table_ref in clause.table_references:
                result = self._compare_table_reference(
                    table_ref.table_number,
                    clause,
                    ptr_doc,
                    report_items,
                    report_doc=report_doc,
                )
                results.append(result)

        return results

    def _compare_table_reference(
        self,
        table_number: int,
        clause: PTRClause,
        ptr_doc: PTRDocument,
        report_items: list[InspectionItem],
        report_doc: ReportDocument | None = None,
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
            referenced_table_label=f"表{table_number}",
        )
        reference_type = self._classify_clause_reference_type(clause, report_item=None)
        result.reference_type = reference_type

        # Find matching report item first (used for selecting best table candidate).
        report_item = self._find_matching_report_item(clause, report_items)
        if not report_item:
            logger.info(f"No matching report item for clause {clause.number}")
            return result
        reference_type = self._classify_clause_reference_type(clause, report_item=report_item)
        result.reference_type = reference_type

        # Find table in PTR (support duplicate-number candidates).
        table_candidates = ptr_doc.get_tables_by_number(table_number)
        if not table_candidates:
            if reference_type == "table_summary_reference":
                return self._build_table_summary_reference_result(
                    result=result,
                    clause=clause,
                    report_item=report_item,
                    report_items=report_items,
                    report_doc=report_doc,
                )
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
        if reference_type == "table_summary_reference":
            return self._build_table_summary_reference_result(
                result=result,
                clause=clause,
                report_item=report_item,
                report_items=report_items,
                ptr_table=ptr_table,
                report_doc=report_doc,
            )

        # Compare parameters
        result.parameters = self._compare_table_parameters(
            ptr_table,
            report_item,
            clause=clause,
            report_items=report_items,
            report_doc=report_doc,
        )

        if not result.parameters or all(not parameter.matches for parameter in result.parameters):
            continuation_parameters = self._extract_continuation_parameter_evidence(
                ptr_doc=ptr_doc,
                base_table=ptr_table,
                clause=clause,
                report_item=report_item,
                report_items=report_items,
                report_doc=report_doc,
            )
            if continuation_parameters:
                result.parameters = continuation_parameters

        # Calculate statistics
        result.total_parameters = len(result.parameters)
        result.total_matches = sum(1 for p in result.parameters if p.matches)

        return result

    def _classify_clause_reference_type(
        self,
        clause: PTRClause,
        report_item: InspectionItem | None = None,
    ) -> str:
        if not clause.has_table_references():
            return "direct_requirement"

        text = self.normalizer.normalize(
            "\n".join(
                part
                for part in [
                    clause.text_content or "",
                    clause.full_text or "",
                    report_item.inspection_project if report_item else "",
                    report_item.standard_requirement if report_item else "",
                ]
                if part and str(part).strip()
            )
        )
        compact = self._compact(text)
        if not compact:
            return "table_parameter_reference"

        summary_markers = (
            "具体要求见表",
            "详细要求见表",
            "详见表",
            "见下表",
            "见表",
        )
        parameter_markers = (
            "应符合表",
            "符合表中的数值",
            "符合表中的规定",
            "符合下表中的数值",
            "符合下表中的规定",
        )
        if any(marker in compact for marker in parameter_markers):
            return "table_parameter_reference"

        clause_topics = self._extract_clause_topics(clause.text_content or clause.full_text or "")
        if clause_topics and any(self._looks_like_parameter_topic(topic) for topic in clause_topics):
            return "table_parameter_reference"

        if any(marker in compact for marker in summary_markers):
            return "table_summary_reference"

        return "table_parameter_reference"

    def _build_table_summary_reference_result(
        self,
        result: TableExpansionResult,
        clause: PTRClause,
        report_item: InspectionItem,
        report_items: list[InspectionItem],
        ptr_table: PTRTable | None = None,
        report_doc: ReportDocument | None = None,
    ) -> TableExpansionResult:
        report_item = self._select_best_summary_report_item(
            clause=clause,
            report_items=report_items,
            fallback=report_item,
            table_number=result.table_number,
        )
        ptr_rows = self._extract_table_summary_rows_from_clause(clause, ptr_table=ptr_table)
        report_rows = self._extract_table_summary_rows_from_report_doc(
            clause=clause,
            report_doc=report_doc,
            table_number=result.table_number,
        )
        if not report_rows:
            report_text = self._build_grouped_report_text(report_item, report_items)
            report_rows = self._extract_table_summary_rows_from_report(report_text)
        else:
            report_text = "\n".join(report_rows)

        ptr_summary = "；".join(ptr_rows) if ptr_rows else self.normalizer.normalize(clause.text_content or "")
        report_summary = "；".join(report_rows) if report_rows else self.normalizer.normalize(report_text or "")

        result.table_found = True
        result.reference_type = "table_summary_reference"
        result.parameters = [
            self._build_parameter_comparison(
                parameter_name="整表摘要",
                ptr_value=ptr_summary,
                report_value=report_summary,
                matches=True,
                details=self._base_evidence_details(
                    table_number=result.table_number,
                    table_page=ptr_table.page if ptr_table else None,
                    parameter_name="整表摘要",
                    evidence_source="table_summary_reference",
                    extra={
                        "reference_type": "table_summary_reference",
                        "ptr_summary_rows": ptr_rows,
                        "report_summary_rows": report_rows,
                        "ptr_evidence_summary": f"本条款引用{result.referenced_table_label}，按整表/分组证据展示。",
                    },
                ),
            )
        ]
        result.total_parameters = 1
        result.total_matches = 1
        return result

    def _select_best_summary_report_item(
        self,
        clause: PTRClause,
        report_items: list[InspectionItem],
        fallback: InspectionItem,
        table_number: int,
    ) -> InspectionItem:
        clause_topics = self._extract_clause_topics(clause.text_content or clause.full_text or "")
        title = clause_topics[0] if clause_topics else self.normalizer.normalize(clause.text_content or "").splitlines()[0].strip()
        title_compact = self._compact(title)
        table_label = f"表{table_number}"

        best_item = fallback
        best_score = float("-inf")
        for item in report_items:
            score = 0.0
            std_clause = self._extract_clause_number(item.standard_clause)
            if std_clause == str(clause.number):
                score += 10.0
            text = self.normalizer.normalize(
                "\n".join(
                    part
                    for part in [
                        item.inspection_project or "",
                        item.standard_requirement or "",
                        item.test_result or "",
                    ]
                    if part and part.strip()
                )
            )
            compact = self._compact(text)
            if clause_number := str(clause.number):
                if clause_number in compact:
                    score += 8.0
            if table_label in text or table_label in compact:
                score += 4.0
            if title_compact and title_compact in compact:
                score += 3.0
            if title_compact and self._compact(item.inspection_project or "") == title_compact:
                score += 2.0
            if compact.startswith(title_compact):
                score += 1.0
            if score > best_score:
                best_score = score
                best_item = item
        return best_item

    def _extract_table_summary_rows_from_clause(
        self,
        clause: PTRClause,
        ptr_table: PTRTable | None = None,
    ) -> list[str]:
        if ptr_table and ptr_table.rows:
            summary_rows: list[str] = []
            for row in ptr_table.rows[:5]:
                cells = [self.normalizer.normalize(str(cell or "")) for cell in row if str(cell or "").strip()]
                if not cells:
                    continue
                summary_rows.append(" / ".join(cells[:4]))
            if summary_rows:
                return summary_rows

        text = self.normalizer.normalize(clause.text_content or clause.full_text or "")
        return self._extract_inline_table_summary_rows(text)

    def _extract_table_summary_rows_from_report(self, report_text: str) -> list[str]:
        text = self.normalizer.normalize(report_text or "")
        return self._extract_inline_table_summary_rows(text)

    def _extract_table_summary_rows_from_report_doc(
        self,
        clause: PTRClause,
        report_doc: ReportDocument | None,
        table_number: int,
    ) -> list[str]:
        if not report_doc or not getattr(report_doc, "pdf_doc", None):
            return []
        title = self.normalizer.normalize(clause.text_content or clause.full_text or "").splitlines()[0].strip()
        title_compact = self._compact(title)
        clause_number = str(clause.number)
        table_label = f"表{table_number}"
        best_rows: list[str] = []
        best_score = float("-inf")
        for page in report_doc.pdf_doc.pages:
            text = self.normalizer.normalize(page.raw_text or "")
            if not text:
                continue
            compact = self._compact(text)
            score = 0.0
            if clause_number and clause_number in compact:
                score += 4.0
            if title_compact and title_compact in compact:
                score += 3.0
            if table_label in text or table_label in compact:
                score += 4.0
            if score <= 0:
                continue
            rows = self._extract_inline_table_summary_rows(text)
            if rows and score > best_score:
                best_rows = rows
                best_score = score
        return best_rows

    def _extract_inline_table_summary_rows(self, text: str) -> list[str]:
        if not text:
            return []
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if not lines:
            return []
        start = 0
        for idx, line in enumerate(lines):
            if "表" in line or "见表" in line:
                start = idx
                break
        rows: list[str] = []
        for line in lines[start:]:
            compact = self._compact(line)
            if not compact:
                continue
            if len(compact) > 40 and "表" not in compact and "组件" not in compact and "项目" not in compact:
                continue
            rows.append(line)
            if len(rows) >= 6:
                break
        return rows

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
        report_doc: ReportDocument | None = None,
    ) -> list[ParameterComparison]:
        """Compare parameters from PTR table with report item.

        Args:
            ptr_table: PTR table
            report_item: Report inspection item

        Returns:
            List of parameter comparisons
        """
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

        if self._should_use_canonical_path(ptr_table):
            logger.info(
                "Table comparator path=canonical table=%s clause=%s",
                ptr_table.table_number,
                str(clause.number) if clause else "",
            )
            canonical_comparisons, reason = self._compare_table_parameters_canonical(
                ptr_table=ptr_table,
                report_text=report_text,
                clause_topics=clause_topics,
                model_context=self._extract_report_model_context(report_doc),
            )
            if canonical_comparisons:
                self._set_comparison_path_metadata(
                    ptr_table,
                    "canonical",
                    "matched",
                )
                return canonical_comparisons

            logger.info(
                "Table comparator canonical path produced no comparisons; fallback to legacy table=%s clause=%s reason=%s",
                ptr_table.table_number,
                str(clause.number) if clause else "",
                reason,
            )
        else:
            reason = "canonical_path_unavailable"

        legacy_comparisons = self._compare_table_parameters_legacy(
            ptr_table=ptr_table,
            report_text=report_text,
            clause_topics=clause_topics,
            model_context=self._extract_report_model_context(report_doc),
        )
        final_reason = (
            "legacy_fallback_after_canonical"
            if reason not in {"canonical_path_unavailable", "invalid_column_roles"}
            else reason
        )
        if not legacy_comparisons and reason == "canonical_path_unavailable":
            final_reason = reason
        elif not legacy_comparisons:
            final_reason = f"{reason}|legacy_no_matches"

        self._set_comparison_path_metadata(
            ptr_table,
            "legacy",
            final_reason,
        )
        return legacy_comparisons

    def _set_comparison_path_metadata(
        self,
        ptr_table: PTRTable,
        path: str,
        reason: str,
    ) -> None:
        """Record which comparison path is used for the current table."""
        if ptr_table.metadata is None:
            ptr_table.metadata = {}
        ptr_table.metadata["comparison_path_used"] = path
        ptr_table.metadata["comparison_path_reason"] = reason

    def _build_parameter_comparison(
        self,
        parameter_name: str,
        ptr_value: str,
        report_value: str,
        matches: bool,
        comparison_status: str = "pass",
        details: dict[str, Any] | None = None,
    ) -> ParameterComparison:
        return ParameterComparison(
            parameter_name=parameter_name,
            ptr_value=ptr_value,
            report_value=report_value,
            matches=matches,
            is_expanded=True,
            comparison_status=comparison_status,
            details=dict(details or {}),
        )

    def _base_evidence_details(
        self,
        *,
        table_number: int | None = None,
        referenced_table_label: str | None = None,
        table_page: int | None = None,
        parameter_name: str = "",
        ptr_values: dict[str, str] | None = None,
        model_scope: str = "",
        report_evidence_rows: list[dict[str, str]] | None = None,
        evidence_source: str = "",
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        details: dict[str, Any] = dict(extra or {})
        if referenced_table_label:
            details["referenced_table_label"] = referenced_table_label
        elif table_number is not None:
            details["referenced_table_label"] = f"表{table_number}"
        if table_page:
            details["ptr_source_page"] = table_page
        if parameter_name:
            details["ptr_parameter_name"] = parameter_name
        if ptr_values:
            details["ptr_values"] = ptr_values
        if model_scope:
            details["ptr_model_scope"] = model_scope
        if report_evidence_rows:
            details["report_evidence_rows"] = report_evidence_rows
        if evidence_source:
            details["evidence_source"] = evidence_source
        label = details.get("referenced_table_label")
        if label and parameter_name:
            details["ptr_evidence_summary"] = f"引用{label}中的参数“{parameter_name}”"
        return details

    def _detect_report_special_status(self, report_text: str) -> tuple[str, str]:
        compact = self._compact(report_text)
        if not compact:
            return "", ""

        patterns = [
            ("out_of_scope_in_current_report", r"(?:非本报告范围|不在本报告范围|本报告范围外|当前报告范围外|本报告未开展)"),
            ("pending_evidence", r"(?:待补证|补充提供|另附资料|后补资料|待补充证据)"),
            ("external_reference", r"(?:另一份报告|另份报告|外部报告|另附报告|详见.*?报告|见.*?报告|参见.*?报告)"),
        ]
        for status, pattern in patterns:
            match = re.search(pattern, compact)
            if match:
                return status, match.group(0)
        return "", ""

    def _report_mentions_dimension(self, report_text: str, value: str) -> bool:
        compact_report = self._compact(report_text)
        compact_value = self._compact(value)
        if not compact_report or not compact_value:
            return False
        return compact_value in compact_report

    def _select_records_for_report_context(
        self,
        records: list[dict[str, Any]],
        report_text: str,
    ) -> list[dict[str, Any]]:
        matched_records: list[dict[str, Any]] = []
        for record in records:
            dimensions = record.get("dimensions")
            if not isinstance(dimensions, dict):
                continue
            model_values = [
                str(value or "").strip()
                for key, value in dimensions.items()
                if str(value or "").strip()
                and not self._is_placeholder(str(value or ""))
                and (
                    self._compact(str(key or "")) in {"型号", "model", "规格", "spec"}
                    or self._looks_like_model_value(str(value or ""))
                )
            ]
            if model_values and any(self._report_mentions_dimension(report_text, value) for value in model_values):
                matched_records.append(record)
        return matched_records

    def _select_rows_for_report_context(
        self,
        rows: list[list[str]],
        model_col_idx: int | None,
        report_text: str,
    ) -> list[list[str]]:
        if model_col_idx is None:
            return rows
        matched_rows: list[list[str]] = []
        for row in rows:
            if model_col_idx >= len(row):
                continue
            model_value = str(row[model_col_idx] or "").strip()
            if not model_value or self._is_placeholder(model_value) or self._looks_like_model_value(model_value) is False:
                continue
            if self._report_mentions_dimension(report_text, model_value):
                matched_rows.append(row)
        return matched_rows

    def _compare_table_parameters_legacy(
        self,
        ptr_table: PTRTable,
        report_text: str,
        clause_topics: list[str],
        model_context: str = "",
    ) -> list[ParameterComparison]:
        """Legacy row/index comparison path for flat tables."""
        comparisons: list[ParameterComparison] = []

        role_map = self._infer_column_roles(ptr_table)
        param_col_idx = self._first_role_index(role_map, "parameter")
        if param_col_idx is None:
            param_col_idx = self._find_column_index(
                ptr_table.headers,
                ["参数", "参数名称"],
                default=0,
            )
        model_col_idx = self._first_role_index(role_map, "model")
        if model_col_idx is None:
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

        if clause_topics and not candidate_rows:
            return []

        rows_to_compare = candidate_rows if candidate_rows else fallback_rows
        contextual_rows = self._select_rows_for_report_context(
            rows=rows_to_compare,
            model_col_idx=model_col_idx,
            report_text=report_text,
        )
        if contextual_rows:
            rows_to_compare = contextual_rows
        for row in rows_to_compare:
            if not row:
                continue

            param_name = row[param_col_idx] if param_col_idx < len(row) else (row[0] if row else "")
            ptr_value = self._pick_ptr_value_from_row(row, headers=ptr_table.headers, roles=role_map)
            ptr_values = self._extract_ptr_row_value_map(
                row=row,
                headers=ptr_table.headers,
                roles=role_map,
            )
            model_scope = (
                str(row[model_col_idx] or "").strip()
                if model_col_idx is not None and model_col_idx < len(row)
                else ""
            )
            report_evidence_rows = self._extract_report_evidence_rows(
                parameter_name=str(param_name or ""),
                report_text=report_text,
            )
            special_status, special_evidence = self._detect_report_special_status(report_text)

            if not param_name:
                continue

            if special_status:
                comparisons.append(
                    self._build_parameter_comparison(
                        parameter_name=param_name,
                        ptr_value=ptr_value,
                        report_value=special_evidence or report_text,
                        matches=True,
                        comparison_status=special_status,
                        details=self._base_evidence_details(
                            table_number=ptr_table.table_number,
                            table_page=ptr_table.page,
                            parameter_name=str(param_name or ""),
                            ptr_values=ptr_values,
                            model_scope=model_scope,
                            report_evidence_rows=report_evidence_rows,
                            evidence_source="direct_table_row",
                            extra={"special_status": special_status},
                        ),
                    )
                )
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
                # Backward-compatible fallback.
                report_value = self._resolve_report_value_from_evidence_rows(
                    report_evidence_rows=report_evidence_rows,
                    report_text=report_text,
                    parameter_name=str(param_name or ""),
                ) or self._extract_parameter_value(param_name, report_text)
                if not report_value:
                    model_text = row[model_col_idx] if model_col_idx < len(row) else ""
                    if model_text and model_text.strip() and model_text.strip() != "全部型号":
                        report_value = self._extract_parameter_value(
                            f"{param_name} {model_text}",
                            report_text,
                        )
                matches = self._compare_values(ptr_value, report_value)

            comparisons.append(
                self._build_parameter_comparison(
                    parameter_name=param_name,
                    ptr_value=ptr_value,
                    report_value=report_value,
                    matches=matches,
                    details=self._base_evidence_details(
                        table_number=ptr_table.table_number,
                        table_page=ptr_table.page,
                        parameter_name=str(param_name or ""),
                        ptr_values=ptr_values,
                        model_scope=model_scope,
                        report_evidence_rows=report_evidence_rows,
                        evidence_source="direct_table_row",
                    ),
                )
            )

        return comparisons

    def _should_use_canonical_path(self, ptr_table: PTRTable) -> bool:
        """Whether structured canonical comparison path is available."""
        metadata = ptr_table.metadata or {}
        if metadata.get("canonical_available") is False:
            return False

        parameter_records = metadata.get("parameter_records")
        if isinstance(parameter_records, list) and parameter_records:
            return True

        canonical_snapshot = metadata.get("canonical_snapshot")
        if canonical_snapshot:
            # Even low-confidence tables should try canonical path first.
            return True

        return bool(ptr_table.column_paths)

    def _compare_table_parameters_canonical(
        self,
        ptr_table: PTRTable,
        report_text: str,
        clause_topics: list[str],
        model_context: str = "",
    ) -> tuple[list[ParameterComparison], str]:
        """Canonical comparison path using semantic parameter records."""
        records = self._collect_parameter_records(ptr_table)
        if not records:
            return [], "missing_parameter_records"

        candidate_records: list[dict[str, Any]] = []
        fallback_records: list[dict[str, Any]] = []
        for record in records:
            parameter_name = str(record.get("parameter_name") or "").strip()
            if not parameter_name:
                continue
            fallback_records.append(record)
            if clause_topics and not self._row_matches_clause_topics(parameter_name, clause_topics):
                continue
            candidate_records.append(record)

        if clause_topics and not candidate_records:
            return [], "no_clause_topic_match"

        records_to_compare = candidate_records if candidate_records else fallback_records
        contextual_records = self._select_records_for_report_context(records_to_compare, report_text)
        if contextual_records:
            records_to_compare = contextual_records
        if not records_to_compare:
            return [], "empty_comparison"

        comparisons: list[ParameterComparison] = []
        for record in records_to_compare:
            parameter_name = str(record.get("parameter_name") or "").strip()
            if not parameter_name:
                continue
            special_status, special_evidence = self._detect_report_special_status(report_text)
            ptr_value = self._pick_ptr_value_from_parameter_record(record)
            ptr_values = self._extract_ptr_value_map_from_record(record)
            dimensions = record.get("dimensions") if isinstance(record.get("dimensions"), dict) else {}
            model_scope = self._extract_model_scope_from_dimensions(dimensions)
            report_evidence_rows = self._extract_report_evidence_rows(
                parameter_name=parameter_name,
                report_text=report_text,
            )

            if special_status:
                comparisons.append(
                    self._build_parameter_comparison(
                        parameter_name=parameter_name,
                        ptr_value=ptr_value,
                        report_value=special_evidence or report_text,
                        matches=True,
                        comparison_status=special_status,
                        details=self._base_evidence_details(
                            table_number=ptr_table.table_number,
                            table_page=ptr_table.page,
                            parameter_name=parameter_name,
                            ptr_values=ptr_values,
                            model_scope=model_scope,
                            report_evidence_rows=report_evidence_rows,
                            evidence_source="canonical_record",
                            extra={"special_status": special_status, "dimensions": dimensions},
                        ),
                    )
                )
                continue

            covered, evidence = self._is_parameter_record_covered_in_report(
                record=record,
                report_text=report_text,
            )
            report_value = evidence or self._resolve_report_value_from_evidence_rows(
                report_evidence_rows=report_evidence_rows,
                report_text=report_text,
                parameter_name=parameter_name,
            )
            matches = covered

            if not matches:
                # Backward-compatible fallback.
                report_value = report_value or self._extract_parameter_value(parameter_name, report_text)
                matches = self._compare_values(ptr_value, report_value)

            comparisons.append(
                self._build_parameter_comparison(
                    parameter_name=parameter_name,
                    ptr_value=ptr_value,
                    report_value=report_value,
                    matches=matches,
                    details=self._base_evidence_details(
                        table_number=ptr_table.table_number,
                        table_page=ptr_table.page,
                        parameter_name=parameter_name,
                        ptr_values=ptr_values,
                        model_scope=model_scope,
                        report_evidence_rows=report_evidence_rows,
                        evidence_source="canonical_record",
                        extra={"dimensions": dimensions},
                    ),
                )
            )

        if not comparisons:
            return [], "empty_comparison"
        return comparisons, "matched"

    def _collect_parameter_records(self, ptr_table: PTRTable) -> list[dict[str, Any]]:
        """Collect semantic parameter records from metadata or column-path rows."""
        self.semantics.reset()
        metadata = ptr_table.metadata or {}
        raw_records = metadata.get("parameter_records")
        if isinstance(raw_records, list) and raw_records:
            parsed = self._sanitize_parameter_records(raw_records)
            if parsed:
                if ptr_table.metadata is not None:
                    ptr_table.metadata["parameter_record_count"] = len(parsed)
                return parsed

        if not ptr_table.rows:
            return []
        records = self._build_parameter_records_from_rows(ptr_table)
        if ptr_table.metadata is not None:
            ptr_table.metadata["parameter_record_count"] = len(records)
            ptr_table.metadata["canonical_unknown_role_count"] = self.semantics.unknown_role_count
        return records

    def _sanitize_parameter_records(self, records: list[Any]) -> list[dict[str, Any]]:
        """Normalize metadata parameter records into predictable dict format."""
        normalized: list[dict[str, Any]] = []
        for record in records:
            if not isinstance(record, dict):
                continue
            parameter_name = str(record.get("parameter_name") or "").strip()
            if not parameter_name:
                continue
            dimensions = record.get("dimensions")
            values = record.get("values")
            normalized.append(
                {
                    "parameter_name": parameter_name,
                    "dimensions": dimensions if isinstance(dimensions, dict) else {},
                    "values": values if isinstance(values, dict) else {},
                }
            )
        return normalized

    def _build_parameter_records_from_rows(self, ptr_table: PTRTable) -> list[dict[str, Any]]:
        """Build semantic records from rows using column role inference."""
        role_map = self._infer_column_roles(ptr_table=ptr_table)
        if not role_map:
            return []

        parameter_col = self._first_role_index(role_map, "parameter")
        if parameter_col is None:
            parameter_col = self._find_column_index(ptr_table.headers, ["参数", "参数名称"], default=0)
        dimension_cols = self._role_indexes(role_map, {"model", "group"})
        value_cols = self._role_indexes(role_map, {"default", "value", "tolerance", "remark"})
        if not value_cols:
            value_cols = [idx for idx in range(len(role_map)) if idx not in {parameter_col, *dimension_cols}]

        records: dict[tuple[str, tuple[tuple[str, str], ...]], dict[str, Any]] = {}
        for row_idx, row in enumerate(ptr_table.rows):
            if not row or self._is_header_like_row(row, ptr_table.headers):
                continue
            values_row = list(row)
            if len(values_row) < len(role_map):
                values_row.extend([""] * (len(role_map) - len(values_row)))

            parameter_name = str(values_row[parameter_col] if parameter_col < len(values_row) else "").strip()
            if not parameter_name:
                continue

            base_dimensions: dict[str, str] = {}
            for col_idx in dimension_cols:
                value = str(values_row[col_idx] if col_idx < len(values_row) else "").strip()
                if not value:
                    continue
                key = self._column_key(ptr_table, col_idx)
                if key in base_dimensions:
                    continue
                base_dimensions[key] = value

            for col_idx in value_cols:
                value = str(values_row[col_idx] if col_idx < len(values_row) else "").strip()
                if not value:
                    continue

                path_labels = self._column_labels(ptr_table, col_idx)
                path_dims, leaf_label, leaf_role = self.semantics.split_path_semantics(path_labels)
                dimensions = dict(base_dimensions)
                for axis_index, axis_label in enumerate(path_dims, start=1):
                    if not axis_label:
                        continue
                    dim_key = f"axis_{axis_index}"
                    if dim_key not in dimensions:
                        dimensions[dim_key] = axis_label

                value_key = leaf_label
                if not value_key:
                    value_key = self._column_key(ptr_table, col_idx)
                value_key = self.semantics.infer_value_leaf_label(value_key, role=leaf_role)
                if not value_key:
                    value_key = self._column_key(ptr_table, col_idx)

                record_key = (parameter_name, tuple(sorted(dimensions.items())))
                record = records.get(record_key)
                if record is None:
                    record = {
                        "parameter_name": parameter_name,
                        "dimensions": dimensions,
                        "values": {},
                        "source_rows": [],
                    }
                    records[record_key] = record

                if record["values"].get(value_key) is None:
                    record["values"][value_key] = value
                if row_idx not in record["source_rows"]:
                    record["source_rows"].append(row_idx)

        return list(records.values())

    def _infer_column_roles(self, ptr_table: PTRTable) -> list[str]:
        """Infer semantic roles per column from metadata/column_paths/headers."""
        n_cols = max(
            len(ptr_table.headers or []),
            len(ptr_table.column_paths or []),
            max((len(row) for row in (ptr_table.rows or [])), default=0),
        )
        if n_cols <= 0:
            return []

        metadata_roles = (ptr_table.metadata or {}).get("column_roles")
        if isinstance(metadata_roles, list) and metadata_roles:
            roles = [str(role or "unknown") for role in metadata_roles[:n_cols]]
            if len(roles) < n_cols:
                roles.extend(["unknown"] * (n_cols - len(roles)))
            if "parameter" in roles:
                return roles

        roles: list[str] = []
        self.semantics.reset()
        for idx in range(n_cols):
            labels = self._column_labels(ptr_table, idx)
            role = self.semantics.infer_column_role(labels)
            roles.append(role)

        # Ensure there is at least one parameter column.
        if "parameter" not in roles and roles:
            fallback = self._find_column_index(ptr_table.headers, ["参数", "参数名称"], default=0)
            fallback = min(max(fallback, 0), len(roles) - 1)
            roles[fallback] = "parameter"
        return roles

    def _column_labels(self, ptr_table: PTRTable, col_idx: int) -> list[str]:
        labels: list[str] = []
        if col_idx < len(ptr_table.column_paths):
            path = ptr_table.column_paths[col_idx]
            if isinstance(path, list):
                labels.extend(str(value or "") for value in path if str(value or "").strip())
            elif hasattr(path, "labels") and isinstance(path.labels, list):
                labels.extend(str(value or "") for value in path.labels if str(value or "").strip())
            elif isinstance(path, str) and path.strip():
                labels.append(path.strip())
        if not labels and col_idx < len(ptr_table.headers):
            header = str(ptr_table.headers[col_idx] or "").strip()
            if header:
                labels.append(header)
        return labels

    def _column_key(self, ptr_table: PTRTable, col_idx: int) -> str:
        labels = self._column_labels(ptr_table, col_idx)
        if labels:
            return labels[-1]
        return f"col_{col_idx}"

    def _first_role_index(self, roles: list[str], target: str) -> int | None:
        for idx, role in enumerate(roles):
            if role == target:
                return idx
        return None

    def _role_indexes(self, roles: list[str], targets: set[str]) -> list[int]:
        return [idx for idx, role in enumerate(roles) if role in targets]

    def _pick_ptr_value_from_parameter_record(self, record: dict[str, Any]) -> str:
        """Choose display expected value from semantic record."""
        values = record.get("values")
        if not isinstance(values, dict):
            return ""

        preferred_keys = ["标准设置", "default", "常规数值", "value", "允许误差", "tolerance"]
        for key in preferred_keys:
            normalized_key = self._compact(key)
            for raw_key, raw_value in values.items():
                value = str(raw_value or "").strip()
                if not value:
                    continue
                key_text = self._compact(str(raw_key or ""))
                if normalized_key in key_text:
                    return value

        for raw_value in values.values():
            value = str(raw_value or "").strip()
            if value:
                return value
        return ""

    def _is_parameter_record_covered_in_report(
        self,
        record: dict[str, Any],
        report_text: str,
    ) -> tuple[bool, str]:
        """Coverage check for one semantic parameter record."""
        if not report_text:
            return False, ""

        report_compact = self._coverage_compact(report_text)
        if not report_compact:
            return False, ""

        parameter_name = str(record.get("parameter_name") or "").strip()
        required_cells: list[str] = []
        if parameter_name:
            required_cells.append(parameter_name)

        dimensions = record.get("dimensions")
        if isinstance(dimensions, dict):
            for key, value in dimensions.items():
                text = str(value or "").strip()
                if not text or self._is_placeholder(text):
                    continue
                # Keep model-like values optional (legacy-compatible behavior).
                if self._looks_like_model_value(text) or self._compact(str(key or "")) in {"型号", "model"}:
                    continue
                required_cells.append(text)

        values = record.get("values")
        if isinstance(values, dict):
            for value in values.values():
                text = str(value or "").strip()
                if not text or self._is_placeholder(text):
                    continue
                required_cells.append(text)

        if not required_cells:
            return False, ""

        for required in required_cells:
            if self._looks_like_numeric_constraint(required):
                numeric_evidence = self._find_satisfying_numeric_evidence(required, report_text)
                if numeric_evidence:
                    continue
            if not self._cell_is_covered(required, report_compact):
                return False, ""

        evidence = self._extract_parameter_value(parameter_name, report_text) if parameter_name else ""
        return True, evidence or "已覆盖"

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
                item.remark,
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
            if self._looks_like_numeric_constraint(cell):
                numeric_evidence = self._find_satisfying_numeric_evidence(cell, report_text)
                if numeric_evidence:
                    continue
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
        if re.fullmatch(r"[A-Za-z]{1,8}\d{2,}[A-Za-z0-9\-_/]*", value.strip()):
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
            candidates.extend(self._extract_parenthetical_aliases(heading))

        # Extract domain terms ending with common parameter suffixes.
        suffixes = "频率|灵敏度|不应期|间期|阻抗|空白期|模式|幅度|宽度|保护"
        regex = re.compile(rf"[\u4e00-\u9fffA-Za-z0-9/（）()]+(?:{suffixes})")
        candidates.extend(regex.findall(text))
        candidates.extend(self._extract_parenthetical_aliases(text))

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
        row_aliases = self._build_topic_aliases(param_name)
        if not row_aliases:
            return False
        for topic in topics:
            topic_aliases = self._build_topic_aliases(topic)
            if any(
                left in right or right in left
                for left in row_aliases
                for right in topic_aliases
            ):
                return True
        return False

    def _extract_parenthetical_aliases(self, text: str) -> list[str]:
        aliases: list[str] = []
        for match in re.finditer(r"[（(]([A-Za-z][A-Za-z0-9\\-_/]{1,20})[）)]", text or ""):
            alias = self._compact(match.group(1))
            if alias:
                aliases.append(alias)
        return aliases

    def _build_topic_aliases(self, text: str) -> list[str]:
        aliases: list[str] = []
        normalized = self._normalize_topic_label(text)
        if normalized:
            aliases.append(normalized)
        aliases.extend(self._extract_parenthetical_aliases(text or ""))
        compact = self._compact(text or "")
        if compact and compact not in aliases:
            aliases.append(compact)

        deduped: list[str] = []
        seen: set[str] = set()
        for alias in aliases:
            if len(alias) < 2 or alias in seen:
                continue
            seen.add(alias)
            deduped.append(alias)
        return deduped

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

    def _extract_ptr_row_value_map(
        self,
        row: list[str],
        headers: list[str] | None = None,
        roles: list[str] | None = None,
    ) -> dict[str, str]:
        value_map: dict[str, str] = {}
        for idx, cell in enumerate(row):
            value = str(cell or "").strip()
            if not value:
                continue
            role = roles[idx] if roles and idx < len(roles) else ""
            if role in {"parameter", "model", "group"}:
                continue
            key = headers[idx] if headers and idx < len(headers) else f"col_{idx}"
            key = str(key or "").strip() or f"col_{idx}"
            value_map[key] = value
        return value_map

    def _extract_ptr_value_map_from_record(self, record: dict[str, Any]) -> dict[str, str]:
        values = record.get("values")
        if not isinstance(values, dict):
            return {}
        return {
            str(key or "").strip(): str(value or "").strip()
            for key, value in values.items()
            if str(value or "").strip()
        }

    def _extract_report_model_context(self, report_doc: ReportDocument | None) -> str:
        if not report_doc:
            return ""
        if report_doc.third_page_fields and report_doc.third_page_fields.model_spec:
            return str(report_doc.third_page_fields.model_spec)
        return str(
            report_doc.first_page_fields.get("model_spec", "")
            or report_doc.first_page_fields.get("型号规格", "")
        )

    def _extract_model_scope_from_dimensions(self, dimensions: dict[str, Any]) -> str:
        for key, value in dimensions.items():
            text = str(value or "").strip()
            key_text = self._compact(str(key or ""))
            if not text:
                continue
            if key_text in {"型号", "model", "规格", "spec", "axis_1", "axis_2"} or self._looks_like_model_value(text):
                return text
        return ""

    def _extract_report_evidence_rows(self, parameter_name: str, report_text: str) -> list[dict[str, str]]:
        if not parameter_name or not report_text:
            return []
        lines = [line.strip() for line in report_text.splitlines() if line.strip()]
        if not lines:
            return []

        ignored_unit_aliases = {"ms", "mv", "bpm", "hz", "v", "a", "ω", "kω", "ppm"}
        param_aliases = [
            alias
            for alias in self._build_topic_aliases(parameter_name)
            if alias.lower() not in ignored_unit_aliases
        ]
        if not param_aliases:
            return []

        start_indexes: list[int] = []
        for idx, line in enumerate(lines):
            line_aliases = self._build_topic_aliases(line)
            if any(left in right or right in left for left in param_aliases for right in line_aliases):
                start_indexes.append(idx)

        if not start_indexes:
            return []

        evidence_rows: list[dict[str, str]] = []
        for pos, start_idx in enumerate(start_indexes):
            end_idx = start_indexes[pos + 1] if pos + 1 < len(start_indexes) else len(lines)
            chunk = lines[start_idx:end_idx]
            if not chunk:
                continue
            heading = chunk[0]
            if len(chunk) == 1:
                content = chunk[0]
            else:
                content = "\n".join(chunk[1:])
            condition_rows = self._extract_condition_result_rows(content)
            evidence_rows.append(
                {
                    "label": heading,
                    "content": content.strip(),
                    "condition_rows": condition_rows,
                }
            )

        if evidence_rows:
            marker_tokens = ("（", "(", "心房", "右室", "左室", "房室", "负载", "@", "240Ω", "500Ω", "2000Ω")
            specific_rows = [
                row
                for row in evidence_rows
                if self._compact(row.get("label", "")) != self._compact(parameter_name)
                or self._compact(row.get("content", "")) != self._compact(row.get("label", ""))
            ]
            informative_rows = [
                row
                for row in specific_rows
                if not re.fullmatch(r"[（(][A-Za-z0-9μΩ°/%\-.]+[）)]", row.get("label", "").strip(), re.IGNORECASE)
                and "应符合表" not in row.get("label", "")
            ]
            if informative_rows:
                specific_rows = informative_rows
            descriptive_rows = [
                row
                for row in specific_rows
                if (
                    any(marker in row.get("label", "") for marker in marker_tokens)
                    or "\n" in row.get("content", "")
                    or any(token in row.get("content", "") for token in marker_tokens)
                )
            ]
            if descriptive_rows:
                return descriptive_rows
            return specific_rows

        return [{"label": parameter_name, "content": report_text.strip()}]

    def _extract_condition_result_rows(self, text: str) -> list[dict[str, str]]:
        lines = [line.strip() for line in str(text or "").splitlines() if line.strip()]
        if not lines:
            return []

        rows: list[dict[str, str]] = []
        idx = 0
        while idx < len(lines):
            line = lines[idx]
            if not self._looks_like_condition_label(line):
                idx += 1
                continue
            condition = line
            result_parts: list[str] = []
            idx += 1
            while idx < len(lines):
                current = lines[idx]
                if self._looks_like_condition_label(current):
                    break
                if "单位" in current:
                    idx += 1
                    continue
                if self._looks_like_unit_only_line(current):
                    idx += 1
                    continue
                result_parts.append(current)
                idx += 1
            result_text = "\n".join(result_parts).strip()
            if result_text:
                rows.append({"condition": condition, "result": result_text})
        return rows

    def _looks_like_condition_label(self, line: str) -> bool:
        compact = self._compact(line)
        if not compact:
            return False
        if compact.startswith("@"):
            return True
        if re.match(r"^(?:条件|负载|工况|模式|温度|频率|压力|流量)[:：@]", compact):
            return True
        if re.match(r"^@?[-+]?\d+(?:\.\d+)?(?:Ω|Ω|ohm|Ohm|V|A|Hz|kHz|MHz|ms|μs|℃|°C|N|g|kg)\b", line, re.IGNORECASE):
            return True
        return False

    def _looks_like_unit_only_line(self, line: str) -> bool:
        compact = self._compact(line)
        if compact.startswith("单位:") or compact.startswith("单位："):
            compact = compact[3:]
        return bool(re.fullmatch(r"(?:μs|ms|s|Ω|Ω|V|A|Hz|kHz|MHz|℃|°C|N|g|kg|mL|mm|cm)", compact, re.IGNORECASE))

    def _resolve_report_value_from_evidence_rows(
        self,
        report_evidence_rows: list[dict[str, Any]],
        report_text: str,
        parameter_name: str,
    ) -> str:
        condition_results: list[str] = []
        condition_labels: list[str] = []
        for row in report_evidence_rows:
            for condition_row in row.get("condition_rows") or []:
                condition = str(condition_row.get("condition") or "").strip()
                value = str(condition_row.get("result") or "").strip()
                if condition:
                    condition_labels.append(condition)
                if value:
                    condition_results.append(value)
        if condition_results:
            unique_values = list(dict.fromkeys(condition_results))
            unique_conditions = list(dict.fromkeys(condition_labels))
            summary = unique_values[0] if len(unique_values) == 1 else "；".join(unique_values)
            if unique_conditions:
                return f"{summary}（{'/'.join(unique_conditions)}）"
            return summary

        for row in report_evidence_rows:
            content = str(row.get("content") or "").strip()
            if not content:
                continue
            numeric_candidates = self._extract_numeric_candidates(content)
            filtered_candidates = [
                candidate
                for candidate in numeric_candidates
                if not self._looks_like_condition_label(candidate)
            ]
            if filtered_candidates:
                return filtered_candidates[-1]

        return self._extract_parameter_value(parameter_name, report_text)

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

        numeric_evidence = self._extract_best_numeric_evidence(report_text)
        if numeric_evidence:
            return numeric_evidence

        return ""

    def _looks_like_numeric_constraint(self, text: str) -> bool:
        normalized = self._normalize_math_symbols(text)
        if not re.search(r"\d", normalized):
            return False
        return bool(
            re.search(r"(<=|>=|<|>|±|~|～|至|到)", normalized)
            or re.search(r"[-+]\d", normalized)
            or re.search(r"(mL|EU|套|Ω|ohm|mm|cm|m|°|N|V|A|Hz|kg|g|ml)", normalized, re.IGNORECASE)
        )

    def _extract_best_numeric_evidence(self, text: str) -> str:
        candidates = self._extract_numeric_candidates(text)
        return candidates[0] if candidates else ""

    def _extract_numeric_candidates(self, text: str) -> list[str]:
        if not text:
            return []
        normalized = self._normalize_math_symbols(text)
        pattern = re.compile(
            r"(?:<=|>=|<|>)?\s*[-+]?\d+(?:\.\d+)?"
            r"(?:\s*(?:~|～|至|到|-)\s*[-+]?\d+(?:\.\d+)?)?"
            r"(?:\s*±\s*\d+(?:\.\d+)?%?)?"
            r"(?:\s*(?:EU/套|mL|ml|mm|cm|kHz|MHz|Hz|kg|ohm|Ω|°|EU|套|N|V|A|m|g))?",
            re.IGNORECASE,
        )
        candidates: list[str] = []
        seen: set[str] = set()
        for match in pattern.finditer(normalized):
            candidate = match.group(0).strip()
            if not candidate or not re.search(r"\d", candidate):
                continue
            compact = re.sub(r"\s+", "", candidate)
            if compact in seen:
                continue
            seen.add(compact)
            candidates.append(candidate)
        return candidates

    def _find_satisfying_numeric_evidence(self, expected: str, report_text: str) -> str:
        candidates = self._extract_numeric_candidates(report_text)
        for candidate in candidates:
            if self._compare_values(expected, candidate, _recursing=True):
                return candidate
        return ""

    def _compare_values(self, value1: str, value2: str, _recursing: bool = False) -> bool:
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

        if not _recursing:
            special_candidate_1 = self._extract_best_numeric_evidence(norm1)
            special_candidate_2 = self._extract_best_numeric_evidence(norm2)
            if special_candidate_1 and special_candidate_1 != norm1:
                if self._compare_values(special_candidate_1, norm2, _recursing=True):
                    return True
            if special_candidate_2 and special_candidate_2 != norm2:
                if self._compare_values(norm1, special_candidate_2, _recursing=True):
                    return True

        return norm1 == norm2

    def _pick_ptr_value_from_row(
        self,
        row: list[str],
        headers: list[str] | None = None,
        roles: list[str] | None = None,
    ) -> str:
        """Pick PTR expected value from table row."""
        if not row or len(row) < 2:
            return ""

        normalized_headers = [self.normalizer.normalize(h or "") for h in (headers or [])]
        preferred_columns: list[int] = []
        if roles:
            for role in ["default", "value", "tolerance", "remark"]:
                for idx, role_value in enumerate(roles):
                    if idx < len(row) and role_value == role:
                        preferred_columns.append(idx)
        else:
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

        actual_interval = self._extract_numeric_interval(actual_norm)
        if actual_interval is None:
            return False
        actual_lo, actual_hi = actual_interval

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
            return lo <= actual_lo and actual_hi <= hi

        # Comparator: <=x, <x, >=x, >x
        cmp_match = re.search(r"(<=|>=|<|>)\s*([-+]?\d+(?:\.\d+)?)", expected_norm)
        if cmp_match:
            op = cmp_match.group(1)
            threshold = float(cmp_match.group(2))
            if op == "<":
                return actual_hi < threshold
            if op == "<=":
                return actual_hi <= threshold
            if op == ">":
                return actual_lo > threshold
            if op == ">=":
                return actual_lo >= threshold

        # Tolerance: base±tol or base±pct%
        tol_match = re.search(
            r"([-+]?\d+(?:\.\d+)?)"
            r"(?:\s*[A-Za-zμΩ°/套]+)?"
            r"\s*±\s*"
            r"([-+]?\d+(?:\.\d+)?)"
            r"(%)?"
            r"(?:\s*[A-Za-zμΩ°/套]+)?",
            expected_norm,
        )
        if tol_match:
            base = float(tol_match.group(1))
            tol = float(tol_match.group(2))
            if tol_match.group(3):
                tol = abs(base) * tol / 100.0
            # Signed deviation report values like +0.03 / -0.02~+0.06 should be
            # evaluated against tolerance band centered at zero.
            if self._looks_like_delta_expression(actual_norm):
                return (-tol) <= actual_lo and actual_hi <= tol
            return (base - tol) <= actual_lo and actual_hi <= (base + tol)

        return False

    def _extract_numeric_interval(self, text: str) -> tuple[float, float] | None:
        normalized = self._normalize_math_symbols(text)
        cmp_match = re.search(r"(<=|>=|<|>)\s*([-+]?\d+(?:\.\d+)?)", normalized)
        if cmp_match:
            value = float(cmp_match.group(2))
            return value, value

        range_match = re.search(
            r"([-+]?\d+(?:\.\d+)?)\s*(?:~|～|至|到|-)\s*([-+]?\d+(?:\.\d+)?)",
            normalized,
        )
        if range_match:
            lo = float(range_match.group(1))
            hi = float(range_match.group(2))
            if lo > hi:
                lo, hi = hi, lo
            return lo, hi

        value = self._extract_single_numeric(normalized)
        if value is None:
            return None
        return value, value

    def _looks_like_delta_expression(self, text: str) -> bool:
        compact = re.sub(r"\s+", "", text or "")
        if not compact:
            return False
        if compact.startswith(("+", "-")):
            return True
        return bool(re.search(r"(?:~|～|至|到|-)[+-]\d", compact))

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
        normalized = normalized.replace("≤", "<=").replace("≦", "<=").replace("⩽", "<=").replace("＜", "<")
        normalized = normalized.replace("≥", ">=").replace("≧", ">=").replace("⩾", ">=").replace("＞", ">")
        normalized = re.sub(r"(?i)\bohm\b|欧姆", "Ω", normalized)
        normalized = normalized.replace("Ω", "Ω").replace("µ", "μ")
        normalized = normalized.replace("—", "-").replace("–", "-").replace("−", "-")
        normalized = re.sub(r"(?<=<)\s*=\s*", "=", normalized)
        normalized = re.sub(r"(?<=>)\s*=\s*", "=", normalized)
        normalized = re.sub(r"([<>]=?)\s+(?=\d)", r"\1", normalized)
        normalized = re.sub(r"(?<=\d)\s+Ω\b", "Ω", normalized)
        normalized = re.sub(r"(?<=\d)\s*2(?=Ω\b)", "", normalized)
        normalized = re.sub(r"\s+", " ", normalized)
        return normalized

    def _extract_continuation_parameter_evidence(
        self,
        ptr_doc: PTRDocument,
        base_table: PTRTable,
        clause: PTRClause,
        report_item: InspectionItem,
        report_items: list[InspectionItem] | None = None,
        report_doc: ReportDocument | None = None,
    ) -> list[ParameterComparison]:
        clause_topics = self._resolve_row_filter_topics(report_item=report_item, clause=clause)
        if not clause_topics:
            return []

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
                    report_item.item_conclusion or "",
                    report_item.remark or "",
                ]
                if part and part.strip()
            )
        model_context = self._extract_report_model_context(report_doc)
        candidates = self._find_continuation_table_candidates(ptr_doc=ptr_doc, base_table=base_table)
        for candidate in candidates:
            comparison = self._extract_parameter_from_flattened_table(
                table=candidate,
                clause_topics=clause_topics,
                report_text=report_text,
                model_context=model_context,
                referenced_table_number=base_table.table_number,
                report_item=report_item,
                report_doc=report_doc,
            )
            if comparison:
                return [comparison]
        return []

    def _find_continuation_table_candidates(
        self,
        ptr_doc: PTRDocument,
        base_table: PTRTable,
    ) -> list[PTRTable]:
        base_end = int(base_table.page_end or base_table.page or 0)
        next_numbered_page = min(
            (
                int(table.page or 0)
                for table in ptr_doc.tables
                if table is not base_table and table.table_number is not None and int(table.page or 0) > base_end
            ),
            default=10**9,
        )
        candidates: list[PTRTable] = []
        for table in ptr_doc.tables:
            if table.table_number is not None:
                continue
            page = int(table.page or 0)
            if page <= base_end:
                continue
            if page >= next_numbered_page:
                continue
            if page - base_end > 3:
                continue
            if self._looks_like_parameter_continuation_table(table):
                candidates.append(table)
        return candidates

    def _looks_like_parameter_continuation_table(self, table: PTRTable) -> bool:
        text = self._table_blob_text(table)
        compact = self._compact(text)
        if not compact:
            return False
        return bool(
            re.search(r"(频率|灵敏度|不应期|间期|阻抗|空白期|模式|幅度|宽度|保护)", compact)
            and re.search(r"(标准设置|允许误差|AUTO|不适用|Edora|全部型号|ms|mV|bpm|Ω)", text, re.IGNORECASE)
        )

    def _table_blob_text(self, table: PTRTable) -> str:
        parts: list[str] = []
        if table.caption:
            parts.append(str(table.caption))
        parts.extend(str(header or "") for header in (table.headers or []))
        for row in table.rows or []:
            parts.append("\t".join(str(cell or "") for cell in row))
        return "\n".join(part for part in parts if part and str(part).strip())

    def _extract_parameter_from_flattened_table(
        self,
        table: PTRTable,
        clause_topics: list[str],
        report_text: str,
        model_context: str = "",
        referenced_table_number: int | None = None,
        report_item: InspectionItem | None = None,
        report_doc: ReportDocument | None = None,
    ) -> ParameterComparison | None:
        blob = self._table_blob_text(table)
        lines = [line.strip() for line in blob.splitlines() if line.strip()]
        if not lines:
            return None

        aliases: list[str] = []
        for topic in clause_topics:
            aliases.extend(self._build_topic_aliases(topic))
        aliases = [alias for alias in aliases if alias]
        if not aliases:
            return None

        start_idx = -1
        for idx, line in enumerate(lines):
            line_aliases = self._build_topic_aliases(line)
            if any(left in right or right in left for left in aliases for right in line_aliases):
                start_idx = idx
                break
        if start_idx < 0:
            return None

        segment_lines = [lines[start_idx]]
        for idx in range(start_idx + 1, len(lines)):
            line = lines[idx]
            if self._line_starts_new_parameter(line, aliases):
                break
            segment_lines.append(line)

        parameter_name = self._extract_parameter_name_from_line(segment_lines[0], aliases)
        segment_text = " ".join(segment_lines)
        selected_segment = self._select_model_segment_text(segment_text, model_context)
        ptr_values = self._extract_value_map_from_segment(selected_segment or segment_text)
        if not ptr_values:
            return None

        report_candidates = self._extract_numeric_candidates(report_text)
        report_evidence_rows = self._extract_report_evidence_rows(parameter_name, report_text)
        report_evidence_rows = self._hydrate_condition_rows_from_report_context(
            report_evidence_rows=report_evidence_rows,
            parameter_name=parameter_name,
            report_item=report_item,
            report_doc=report_doc,
        )
        report_value = self._resolve_report_value_from_evidence_rows(
            report_evidence_rows=report_evidence_rows,
            report_text=report_text,
            parameter_name=parameter_name,
        ) or (
            next(
                (
                    candidate
                    for candidate in reversed(report_candidates)
                    if not self._looks_like_condition_label(candidate)
                ),
                "",
            )
        ) or "已覆盖"
        ptr_value = (
            ptr_values.get("标准设置")
            or ptr_values.get("常规数值")
            or ptr_values.get("允许误差")
            or next(iter(ptr_values.values()), "")
        )
        if not ptr_value:
            return None

        return self._build_parameter_comparison(
            parameter_name=parameter_name,
            ptr_value=ptr_value,
            report_value=report_value,
            matches=True,
            details=self._base_evidence_details(
                table_number=table.table_number,
                referenced_table_label=f"表{referenced_table_number}"
                if referenced_table_number is not None
                else None,
                table_page=table.page,
                parameter_name=parameter_name,
                ptr_values=ptr_values,
                model_scope=model_context,
                report_evidence_rows=report_evidence_rows,
                evidence_source="continuation_table_segment",
                extra={"continuation_segment": segment_text},
            ),
        )

    def _hydrate_condition_rows_from_report_context(
        self,
        report_evidence_rows: list[dict[str, Any]],
        parameter_name: str,
        report_item: InspectionItem | None,
        report_doc: ReportDocument | None,
    ) -> list[dict[str, Any]]:
        if not report_evidence_rows:
            return report_evidence_rows
        if any(row.get("condition_rows") for row in report_evidence_rows):
            return report_evidence_rows

        if not any("@" in str(row.get("content") or "") for row in report_evidence_rows):
            return report_evidence_rows

        fallback_rows = self._extract_condition_rows_from_report_doc(
            parameter_name=parameter_name,
            report_item=report_item,
            report_doc=report_doc,
        )
        if not fallback_rows:
            return report_evidence_rows

        hydrated = [dict(row) for row in report_evidence_rows]
        hydrated[0] = {**hydrated[0], "condition_rows": fallback_rows}
        return hydrated

    def _extract_condition_rows_from_report_doc(
        self,
        parameter_name: str,
        report_item: InspectionItem | None,
        report_doc: ReportDocument | None,
    ) -> list[dict[str, str]]:
        if not report_item or not report_doc or not getattr(report_doc, "pdf_doc", None):
            return []

        aliases = self._build_topic_aliases(parameter_name)
        if not aliases:
            return []

        page_numbers: list[int] = []
        if getattr(report_item, "source_page", None):
            page_numbers.append(int(report_item.source_page))
            page_numbers.append(int(report_item.source_page) + 1)

        best_rows: list[dict[str, str]] = []
        for page_number in page_numbers:
            page = report_doc.pdf_doc.get_page(page_number)
            if page is None:
                continue
            lines = [line.strip() for line in (page.raw_text or "").splitlines() if line.strip()]
            if not lines:
                continue

            start_idx = -1
            for idx, line in enumerate(lines):
                line_aliases = self._build_topic_aliases(line)
                if any(left in right or right in left for left in aliases for right in line_aliases):
                    start_idx = idx
                    break
            if start_idx < 0:
                continue

            chunk_lines: list[str] = []
            for line in lines[start_idx:]:
                if chunk_lines and re.fullmatch(r"\d+", self._compact(line)):
                    break
                chunk_lines.append(line)
                if len(chunk_lines) >= 40:
                    break

            rows = self._extract_condition_result_rows("\n".join(chunk_lines))
            if rows:
                best_rows = rows
                break

        return best_rows

    def _line_starts_new_parameter(self, line: str, current_aliases: list[str]) -> bool:
        line_aliases = self._build_topic_aliases(line)
        if not line_aliases:
            return False
        if any(left in right or right in left for left in current_aliases for right in line_aliases):
            return False
        return self._looks_like_parameter_topic(line)

    def _extract_parameter_name_from_line(self, line: str, aliases: list[str]) -> str:
        token_match = re.match(r"([\u4e00-\u9fffA-Za-z0-9/（）()\\-]+)", line)
        candidate = token_match.group(1) if token_match else aliases[0]
        candidate_aliases = self._build_topic_aliases(candidate)
        if any(left in right or right in left for left in candidate_aliases for right in aliases):
            return candidate
        return aliases[0]

    def _select_model_segment_text(self, segment_text: str, model_context: str) -> str:
        if not model_context:
            return segment_text
        compact_segment = self._compact(segment_text)
        for candidate in self._build_model_aliases(model_context):
            idx = compact_segment.find(candidate)
            if idx < 0:
                continue
            raw_flat = re.sub(r"\s+", " ", segment_text).strip()
            compact_chars = [ch for ch in raw_flat if not ch.isspace()]
            if idx >= len(compact_chars):
                continue
            raw_index = 0
            compact_index = 0
            while raw_index < len(raw_flat) and compact_index < idx:
                if not raw_flat[raw_index].isspace():
                    compact_index += 1
                raw_index += 1
            return raw_flat[raw_index:]
        return segment_text

    def _build_model_aliases(self, model_context: str) -> list[str]:
        compact = self._compact(model_context)
        aliases = [compact]
        if compact.endswith("T"):
            aliases.append(compact[:-1])
        aliases.append(compact.replace("-T", ""))
        aliases.append(re.sub(r"-T$", "", compact))
        deduped: list[str] = []
        seen: set[str] = set()
        for alias in aliases:
            alias = alias.strip("-")
            if len(alias) < 2 or alias in seen:
                continue
            seen.add(alias)
            deduped.append(alias)
        return deduped

    def _extract_value_map_from_segment(self, segment_text: str) -> dict[str, str]:
        raw_unit_match = re.search(r"单位\s*[:：]?\s*([A-Za-zμΩ°/%]+)", segment_text or "", re.IGNORECASE)
        normalized = self.normalizer.normalize(segment_text or "")
        compact = self._compact(normalized)
        if not compact:
            return {}
        if "不适用" in compact:
            return {"常规数值": "不适用"}

        labelled_map = self._extract_labelled_value_map(normalized)
        if raw_unit_match:
            labelled_map.setdefault("单位", raw_unit_match.group(1))
        if labelled_map:
            return labelled_map

        tolerance_match = re.search(r"(±\s*[-+]?\d+(?:\.\d+)?(?:\s*%|\s*[A-Za-zμΩ°/]+)?)", normalized)
        tolerance = tolerance_match.group(1).strip() if tolerance_match else ""
        body = normalized[: tolerance_match.start()] if tolerance_match else normalized
        body = body.strip()

        ranged_tokens = re.findall(
            r"[-+]?\d+(?:\.\d+)?(?:\s*\.\.\.\s*\(\s*[-+]?\d+(?:\.\d+)?\s*\)\s*\.\.\.\s*[-+]?\d+(?:\.\d+)?)+",
            body,
        )
        singles = re.findall(r"[-+]?\d+(?:\.\d+)?", body)

        value_map: dict[str, str] = {}
        if ranged_tokens:
            value_map["常规数值"] = re.sub(r"\s+", "", ranged_tokens[-1])
            trailing_body = body[body.rfind(ranged_tokens[-1]) + len(ranged_tokens[-1]):]
            trailing_numbers = re.findall(r"[-+]?\d+(?:\.\d+)?", trailing_body)
            if trailing_numbers:
                value_map["标准设置"] = trailing_numbers[0]
        elif len(singles) >= 2:
            value_map["常规数值"] = singles[-2]
            value_map["标准设置"] = singles[-1]
        elif len(singles) == 1:
            value_map["标准设置"] = singles[0]

        if tolerance:
            value_map["允许误差"] = re.sub(r"\s+", "", tolerance)
        return value_map

    def _extract_labelled_value_map(self, text: str) -> dict[str, str]:
        normalized = self.normalizer.normalize(text or "")
        labels = ("常规数值", "标准设置", "允许误差", "单位")
        value_map: dict[str, str] = {}
        for label in labels:
            match = re.search(
                rf"{label}\s*[:：]?\s*(.+?)(?=(?:{'|'.join(labels)})\s*[:：]?|$)",
                normalized,
                re.DOTALL,
            )
            if not match:
                continue
            value = match.group(1).strip(" ：:;\n")
            if value:
                value_map[label] = re.sub(r"\s+", " ", value)
        return value_map


def compare_table_expansions(
    ptr_doc: PTRDocument,
    report_items: list[InspectionItem],
    report_doc: ReportDocument | None = None,
) -> list[TableExpansionResult]:
    """Convenience function to compare table expansions.

    Args:
        ptr_doc: PTR document
        report_items: List of inspection items

    Returns:
        List of table expansion results
    """
    comparator = TableComparator()
    return comparator.compare_table_references(ptr_doc, report_items, report_doc=report_doc)


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
