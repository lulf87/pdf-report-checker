"""
Clause Text Comparison Engine.

Compares PTR clauses with report inspection items using strict matching
and diff algorithms to locate differences.
"""

import logging
import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from enum import Enum
from typing import Literal

from app.models.ptr_models import PTRClause, PTRDocument
from app.models.report_models import InspectionItem, ReportDocument
from app.services.text_normalizer import TextNormalizer

logger = logging.getLogger(__name__)


class ComparisonResult(Enum):
    """Result of clause comparison."""

    MATCH = "match"  # Exact match after normalization
    DIFFER = "differ"  # Text differs
    MISSING = "missing"  # Clause not found in report
    EXCLUDED = "excluded"  # Clause excluded from comparison


@dataclass
class DiffFragment:
    """A fragment of text difference.

    Attributes:
        text: The text fragment
        type: Type of difference ('added', 'removed', 'same')
        position: Position in original text
    """

    text: str
    type: Literal["added", "removed", "same"]
    position: int = 0


@dataclass
class ComparisonDetail:
    """Detailed comparison result for a single clause.

    Attributes:
        ptr_clause: The PTR clause
        report_item: The matching report item (if found)
        result: Comparison result
        differences: List of text differences
        normalized_ptr: Normalized PTR text
        normalized_report: Normalized report text
        similarity: Similarity score (0-1)
    """

    ptr_clause: PTRClause | None = None
    report_item: InspectionItem | None = None
    result: ComparisonResult = ComparisonResult.MATCH
    differences: list[DiffFragment] = field(default_factory=list)
    normalized_ptr: str = ""
    normalized_report: str = ""
    report_text_for_display: str = ""
    similarity: float = 0.0
    match_reason: str = ""

    @property
    def has_differences(self) -> bool:
        """Check if there are any differences."""
        return len(self.differences) > 0

    @property
    def is_match(self) -> bool:
        """Check if clauses match."""
        return self.result == ComparisonResult.MATCH


class ClauseComparator:
    """Compares PTR clauses with report inspection items."""

    def __init__(
        self,
        normalizer: TextNormalizer | None = None,
        strict_mode: bool = True,
    ):
        """Initialize comparator.

        Args:
            normalizer: Text normalizer instance (created if None)
            strict_mode: If True, require exact match (after normalization)
        """
        self.normalizer = normalizer or TextNormalizer()
        self.strict_mode = strict_mode
        self.soft_match_similarity_threshold = 0.82

    def compare_documents(
        self,
        ptr_doc: PTRDocument,
        report_doc: ReportDocument,
    ) -> list[ComparisonDetail]:
        """Compare all PTR clauses with report items.

        Args:
            ptr_doc: PTR document
            report_doc: Report document

        Returns:
            List of comparison details
        """
        results: list[ComparisonDetail] = []

        # Get excluded sequences from report
        excluded_numbers = report_doc.get_excluded_sequences() if report_doc.third_page_fields else []
        inspection_scope = self._parse_inspection_scope_from_third_page(report_doc)

        # Compare each PTR clause
        for ptr_clause in ptr_doc.clauses:
            # Chapter heading "2" is section title, not a standalone requirement.
            if str(ptr_clause.number) == "2":
                continue
            if inspection_scope and not self._is_clause_in_scope(
                str(ptr_clause.number),
                inspection_scope,
            ):
                detail = ComparisonDetail(ptr_clause=ptr_clause)
                detail.result = ComparisonResult.EXCLUDED
                detail.match_reason = "out_of_scope_third_page"
                results.append(detail)
                continue
            detail = self._compare_clause(ptr_clause, report_doc, excluded_numbers)
            results.append(detail)

        # Parent promotion is a lenient strategy and must not be applied in
        # strict mode (PRD requires clause-level strict matching).
        if not self.strict_mode:
            self._promote_parent_clause_matches(results)

        # Log summary
        matches = sum(1 for r in results if r.is_match)
        total = len(results)
        logger.info(f"Comparison complete: {matches}/{total} clauses match")

        return results

    def _compare_clause(
        self,
        ptr_clause: PTRClause,
        report_doc: ReportDocument,
        excluded_numbers: list[str],
    ) -> ComparisonDetail:
        """Compare a single PTR clause with report items.

        Args:
            ptr_clause: PTR clause to compare
            report_doc: Report document
            excluded_numbers: List of excluded sequence numbers

        Returns:
            ComparisonDetail with comparison result
        """
        detail = ComparisonDetail(ptr_clause=ptr_clause)

        # Check if this clause is excluded
        clause_num_str = str(ptr_clause.number)
        if clause_num_str in excluded_numbers:
            detail.result = ComparisonResult.EXCLUDED
            detail.match_reason = "excluded_by_standard_content"
            return detail

        # Find matching report item
        report_item = self._find_matching_item(ptr_clause, report_doc)
        if not report_item:
            detail.result = ComparisonResult.MISSING
            return detail

        detail.report_item = report_item

        # Normalize texts for comparison
        ptr_text = ptr_clause.text_content
        clause_num_str = str(ptr_clause.number)
        report_text = self._build_report_text_for_clause(
            report_doc=report_doc,
            report_item=report_item,
            clause_number=clause_num_str,
        )
        if not report_text:
            report_text = report_item.standard_requirement

        # Some report rows keep the short heading in "检验项目" while
        # "标准要求" only stores the body text.
        project_text = self.normalizer.normalize(report_item.inspection_project or "")
        ptr_norm_preview = self.normalizer.normalize(ptr_text)
        report_norm_preview = self.normalizer.normalize(report_text)
        if (
            project_text
            and ptr_norm_preview.startswith(project_text)
            and not report_norm_preview.startswith(project_text)
        ):
            report_text = f"{project_text} {report_text}".strip()
        detail.report_text_for_display = report_text

        detail.normalized_ptr = self.normalizer.normalize(ptr_text)
        detail.normalized_report = self.normalizer.normalize(report_text)
        ptr_compact = re.sub(r"\s+", "", detail.normalized_ptr)
        report_compact = re.sub(r"\s+", "", detail.normalized_report)
        detail.similarity = self._compute_similarity(
            detail.normalized_ptr,
            detail.normalized_report,
        )

        # Perform comparison
        if detail.normalized_ptr == detail.normalized_report or ptr_compact == report_compact:
            detail.result = ComparisonResult.MATCH
            detail.similarity = 1.0
            detail.match_reason = "exact_normalized_match"
        elif self._is_short_heading_match(
            ptr_clause.text_content,
            report_item,
            strict=self.strict_mode,
        ):
            detail.result = ComparisonResult.MATCH
            detail.similarity = max(detail.similarity, 0.95)
            detail.match_reason = "short_heading_equivalent"
        elif self._is_table_reference_clause_equivalent(
            ptr_clause.text_content,
            report_text,
        ):
            detail.result = ComparisonResult.MATCH
            detail.similarity = max(detail.similarity, 0.9)
            detail.match_reason = "table_reference_equivalent"
        elif self._is_table_parameter_clause_equivalent(
            ptr_clause.text_content,
            report_text,
        ):
            detail.result = ComparisonResult.MATCH
            detail.similarity = max(detail.similarity, 0.9)
            detail.match_reason = "table_parameter_equivalent"
        elif not self.strict_mode and detail.similarity >= self.soft_match_similarity_threshold:
            detail.result = ComparisonResult.MATCH
            detail.match_reason = "lenient_similarity_match"
        else:
            detail.result = ComparisonResult.DIFFER
            detail.match_reason = "text_mismatch"
            detail.differences = self._compute_diff(
                detail.normalized_ptr,
                detail.normalized_report,
            )

        return detail

    def _extract_clause_specific_text(
        self,
        requirement_text: str,
        clause_number: str,
    ) -> str:
        """Extract clause-specific segment from merged report requirement text."""
        if not requirement_text or not clause_number:
            return requirement_text or ""

        text = requirement_text
        # Locate target clause marker in mixed OCR/table text.
        marker_re = re.compile(
            rf"{re.escape(clause_number)}(?:[\.．、]|\s)*",
            re.IGNORECASE,
        )
        marker = marker_re.search(text)
        if not marker:
            return text

        segment = text[marker.end():].strip()
        if not segment:
            return text

        # Trim at next clause marker if present.
        next_clause_re = re.compile(r"\n\s*\d+(?:\.\d+)+(?:[\.．、]|\s)+")
        next_marker = next_clause_re.search(segment)
        if next_marker:
            segment = segment[: next_marker.start()].strip()

        return segment or text

    def _build_report_text_for_clause(
        self,
        report_doc: ReportDocument,
        report_item: InspectionItem,
        clause_number: str,
    ) -> str:
        """Build clause-specific report text with continuation rows merged."""
        if not report_doc.inspection_table:
            return report_item.standard_requirement or ""

        items = report_doc.inspection_table.items
        try:
            start_idx = next(idx for idx, item in enumerate(items) if item is report_item)
        except StopIteration:
            start_idx = -1

        merged_parts: list[str] = []
        base_sequence = self._extract_sequence_index(report_item.sequence_number)

        if start_idx >= 0:
            for idx in range(start_idx, len(items)):
                row = items[idx]

                # For grouped rows, stop at the next numeric sequence block.
                if idx > start_idx:
                    seq_idx = self._extract_sequence_index(row.sequence_number)
                    if base_sequence and seq_idx and seq_idx != base_sequence:
                        break
                    if not base_sequence and seq_idx:
                        break

                row_text = self._compose_row_requirement_text(row)
                if row_text:
                    merged_parts.append(row_text)
        else:
            row_text = self._compose_row_requirement_text(report_item)
            if row_text:
                merged_parts.append(row_text)

        merged_text = "\n".join(merged_parts).strip()
        extracted = self._extract_clause_specific_text(merged_text, clause_number).strip()

        project_text = self.normalizer.normalize(report_item.inspection_project or "")
        if project_text and project_text not in extracted and not self.strict_mode:
            if extracted:
                extracted = f"{project_text} {extracted}"
            else:
                extracted = project_text

        return extracted

    def _extract_sequence_index(self, sequence: str | None) -> str:
        """Extract numeric index from sequence cells like '157' or '续\\n157'."""
        if not sequence:
            return ""
        normalized = re.sub(r"\s+", "", sequence)
        match = re.fullmatch(r"续?(\d+)", normalized)
        return match.group(1) if match else ""

    def _looks_like_shifted_requirement_text(self, sequence: str | None) -> bool:
        """Whether sequence column likely contains shifted requirement text."""
        if not sequence:
            return False
        text = (sequence or "").strip()
        if not text:
            return False
        if self._extract_sequence_index(text):
            return False
        # Plain clause-like identifiers (e.g. "2.1") are not shifted text.
        if re.fullmatch(r"\d+(?:\.\d+)+", re.sub(r"\s+", "", text)):
            return False
        if re.search(r"\d+(?:\.\d+)+", text):
            return True
        if len(text) >= 8 and (("\n" in text) or ("。" in text) or ("；" in text)):
            return True
        return False

    def _compose_row_requirement_text(self, item: InspectionItem) -> str:
        """Compose requirement-like text from potentially shifted columns."""
        parts: list[str] = []
        requirement = (item.standard_requirement or "").strip()
        if requirement:
            parts.append(requirement)
        sequence = (item.sequence_number or "").strip()
        if self._looks_like_shifted_requirement_text(sequence):
            parts.append(sequence)
        return "\n".join(parts).strip()

    def _is_short_heading_match(
        self,
        ptr_text: str,
        report_item: InspectionItem,
        strict: bool = False,
    ) -> bool:
        """Short heading clauses can match report inspection project headings."""
        ptr_norm = self.normalizer.normalize(ptr_text or "")
        ptr_compact = re.sub(r"\s+", "", ptr_norm)
        if not ptr_compact or len(ptr_compact) > 10:
            return False

        project_norm = self.normalizer.normalize(report_item.inspection_project or "")
        project_compact = re.sub(r"\s+", "", project_norm)
        if not project_compact:
            return False
        if strict:
            return ptr_compact == project_compact
        return ptr_compact in project_compact

    def _is_table_reference_clause_equivalent(
        self,
        ptr_text: str,
        report_text: str,
    ) -> bool:
        """Treat table-reference clauses as equivalent when heading+table ref align."""
        ptr_norm = self.normalizer.normalize(ptr_text or "")
        report_norm = self.normalizer.normalize(report_text or "")
        if "见表" not in ptr_norm or "见表" not in report_norm:
            return False

        def _first_heading(text: str) -> str:
            cleaned = re.sub(r"^\d+(?:\.\d+)+(?:[\.．、]|\s)*", "", text).strip()
            match = re.match(r"([\u4e00-\u9fff]{1,12})", cleaned)
            return match.group(1) if match else ""

        ptr_head = _first_heading(ptr_norm)
        report_head = _first_heading(report_norm)
        if not ptr_head or not report_head:
            return False
        return ptr_head in report_head or report_head in ptr_head

    def _is_table_parameter_clause_equivalent(
        self,
        ptr_text: str,
        report_text: str,
    ) -> bool:
        """Treat parameter rows as equivalent when core '表X数值符合' statement matches.

        Many reports append detailed parameter matrices after the base sentence
        (e.g. “XXX应符合表1中的数值”), which should not force a strict mismatch.
        """
        ptr_norm = self.normalizer.normalize(ptr_text or "")
        report_norm = self.normalizer.normalize(report_text or "")
        ptr_compact = re.sub(r"\s+", "", ptr_norm)
        report_compact = re.sub(r"\s+", "", report_norm)
        key_phrase = "应符合表1中的数值"
        if key_phrase not in ptr_compact or key_phrase not in report_compact:
            return False

        phrase_re = re.compile(r"应符合表\s*1\s*中的数值")

        def _topic_prefix(text: str) -> str:
            cleaned = re.sub(r"^\d+(?:\.\d+)+(?:[\.．、]|\s)*", "", text).strip()
            parts = phrase_re.split(cleaned, maxsplit=1)
            prefix = parts[0] if parts else cleaned
            if "：" in prefix or ":" in prefix:
                # Prefer rhs when text is in form "参数名: 具体项目应符合表1..."
                colon_split = re.split(r"[：:]", prefix, maxsplit=1)
                if len(colon_split) == 2 and colon_split[1].strip():
                    prefix = colon_split[1]
                else:
                    prefix = colon_split[0]
            prefix = re.sub(r"[^\u4e00-\u9fffA-Za-z0-9()（）/]+", "", prefix)
            return prefix

        ptr_topic = _topic_prefix(ptr_norm)
        report_topic = _topic_prefix(report_norm)
        if not ptr_topic or not report_topic:
            return False
        return ptr_topic in report_topic or report_topic in ptr_topic

    def _parse_inspection_scope_from_third_page(
        self,
        report_doc: ReportDocument,
    ) -> list[tuple[tuple[int, ...], tuple[int, ...]]]:
        """Parse clause scope from third-page inspection items.

        Example source values:
        - "2.1.2～2.1.9"
        - "2.10（除 ...）"
        """
        third = report_doc.third_page_fields
        if not third or not third.inspection_items:
            return []

        scope: list[tuple[tuple[int, ...], tuple[int, ...]]] = []
        range_re = re.compile(r"(\d+(?:\.\d+)+)\s*[~～\-至到]+\s*(\d+(?:\.\d+)+)")
        number_re = re.compile(r"\d+(?:\.\d+)+")

        for raw_item in third.inspection_items:
            text = (raw_item or "").strip()
            if not text:
                continue
            for m in range_re.finditer(text):
                start = self._parse_clause_number(m.group(1))
                end = self._parse_clause_number(m.group(2))
                if start and end:
                    if start > end:
                        start, end = end, start
                    scope.append((start, end))
            # Also capture standalone clause numbers (single item scope).
            # Keep after range parsing to include isolated items like "2.10（除...）".
            for token in number_re.findall(text):
                num = self._parse_clause_number(token)
                if num:
                    scope.append((num, num))

        # Deduplicate while preserving stable order.
        seen: set[tuple[tuple[int, ...], tuple[int, ...]]] = set()
        deduped: list[tuple[tuple[int, ...], tuple[int, ...]]] = []
        for item in scope:
            if item in seen:
                continue
            seen.add(item)
            deduped.append(item)
        return deduped

    def _parse_clause_number(self, value: str) -> tuple[int, ...]:
        """Parse dotted clause number into integer tuple."""
        parts = []
        for token in (value or "").split("."):
            token = token.strip()
            if not token:
                continue
            if not token.isdigit():
                return tuple()
            parts.append(int(token))
        return tuple(parts)

    def _is_clause_in_scope(
        self,
        clause_number: str,
        scope: list[tuple[tuple[int, ...], tuple[int, ...]]],
    ) -> bool:
        """Check whether clause number falls into parsed third-page scope."""
        clause = self._parse_clause_number(clause_number)
        if not clause:
            return True

        for start, end in scope:
            if not start or not end:
                continue
            # Treat single-point scope as "this clause and descendants".
            if start == end:
                if clause[:len(start)] == start:
                    return True
                continue

            # Compare at the range depth and include descendants.
            depth = min(len(start), len(end), len(clause))
            clause_prefix = clause[:depth]
            start_prefix = start[:depth]
            end_prefix = end[:depth]
            if start_prefix <= clause_prefix <= end_prefix:
                # Ensure shared parent segments for hierarchical ranges.
                parent_depth = max(0, depth - 1)
                if parent_depth == 0 or (
                    clause[:parent_depth] == start[:parent_depth] == end[:parent_depth]
                ):
                    return True

        return False

    def _find_matching_item(
        self,
        ptr_clause: PTRClause,
        report_doc: ReportDocument,
    ) -> InspectionItem | None:
        """Find the report item that matches a PTR clause.

        Args:
            ptr_clause: PTR clause
            report_doc: Report document

        Returns:
            Matching InspectionItem or None
        """
        if not report_doc.inspection_table:
            return None

        # Try to match by clause number
        clause_num_str = str(ptr_clause.number)

        # Prefer matching against report "标准条款" column.
        for item in report_doc.inspection_table.items:
            clause_in_report = self._extract_clause_number(item.standard_clause)
            if clause_in_report and clause_in_report == clause_num_str:
                return item

        # Try exact match on sequence number only when sequence looks like
        # a clause identifier (e.g. 2.1.1), not row index (e.g. 157).
        for item in report_doc.inspection_table.items:
            seq_value = self._normalize_sequence_for_matching(item.sequence_number)
            if self._is_clause_like_number(seq_value) and seq_value == clause_num_str:
                return item

        # Try hierarchical partial match for clause-like sequence values only.
        for item in report_doc.inspection_table.items:
            seq_value = self._normalize_sequence_for_matching(item.sequence_number)
            if not self._is_clause_like_number(seq_value):
                continue
            if seq_value.startswith(clause_num_str) or clause_num_str.startswith(seq_value):
                return item

        # Clause marker may be embedded inside a parent row's requirement text.
        # Skip chapter-level generic marker search (e.g. "2"), too ambiguous.
        if "." in clause_num_str:
            clause_marker = re.compile(
                rf"(?<![\d.]){re.escape(clause_num_str)}(?:[\.．、]|\s|$)",
                re.IGNORECASE,
            )
            for item in report_doc.inspection_table.items:
                requirement = self._compose_row_requirement_text(item)
                if requirement and clause_marker.search(requirement):
                    return item

        # Match by parent standard-clause prefix (e.g. report has 2.1, PTR has 2.1.1.2).
        best_prefix_item: InspectionItem | None = None
        best_prefix_len = -1
        for item in report_doc.inspection_table.items:
            clause_in_report = self._extract_clause_number(item.standard_clause)
            if not clause_in_report:
                continue
            if clause_num_str.startswith(clause_in_report + "."):
                if len(clause_in_report) > best_prefix_len:
                    best_prefix_len = len(clause_in_report)
                    best_prefix_item = item
        if best_prefix_item is not None:
            return best_prefix_item

        # Try matching by requirement text similarity/containment.
        ptr_text = self.normalizer.normalize(ptr_clause.text_content)
        best_item: InspectionItem | None = None
        best_score = 0.0
        has_parseable_clause_column = any(
            bool(self._extract_clause_number(item.standard_clause))
            for item in report_doc.inspection_table.items
        )
        similarity_candidates = (
            [
                item
                for item in report_doc.inspection_table.items
                if not self._extract_clause_number(item.standard_clause)
            ]
            if has_parseable_clause_column
            else report_doc.inspection_table.items
        )

        for item in similarity_candidates:
            candidate_text = self.normalizer.normalize(
                self._compose_row_requirement_text(item) or item.inspection_project
            )
            if not candidate_text:
                continue

            if ptr_text == candidate_text:
                return item

            similarity = self._compute_similarity(ptr_text, candidate_text)
            score = similarity
            if ptr_text in candidate_text or candidate_text in ptr_text:
                score += 0.2
            if score > best_score:
                best_score = score
                best_item = item

        if best_item and best_score >= 0.55:
            return best_item

        return None

    def _promote_parent_clause_matches(
        self,
        details: list[ComparisonDetail],
    ) -> None:
        """Promote parent heading to MATCH when all descendant clauses match."""
        detail_map = {
            str(detail.ptr_clause.number): detail
            for detail in details
            if detail.ptr_clause is not None
        }
        keys = sorted(detail_map.keys(), key=lambda x: x.count("."), reverse=True)

        for number in keys:
            detail = detail_map[number]
            if detail.result == ComparisonResult.MATCH:
                continue
            descendants = [
                child_detail
                for child_num, child_detail in detail_map.items()
                if child_num.startswith(number + ".")
            ]
            if descendants and all(d.result == ComparisonResult.MATCH for d in descendants):
                detail.result = ComparisonResult.MATCH
                detail.similarity = max((d.similarity for d in descendants), default=1.0)
                detail.differences = []

    def _extract_clause_number(self, text: str) -> str:
        """Extract normalized clause number from report standard-clause text."""
        if not text:
            return ""
        match = re.search(r"(\d+(?:\.\d+)+)", text)
        if match:
            return match.group(1)
        return ""

    def _normalize_sequence_for_matching(self, sequence: str) -> str:
        """Normalize sequence text for clause-number matching."""
        return re.sub(r"\s+", "", (sequence or "").replace("续", "").strip())

    def _is_clause_like_number(self, value: str) -> bool:
        """Whether value is a hierarchical clause number (contains dots)."""
        return bool(re.fullmatch(r"\d+(?:\.\d+)+", value or ""))

    def _compute_diff(
        self,
        text1: str,
        text2: str,
    ) -> list[DiffFragment]:
        """Compute text differences using SequenceMatcher.

        Args:
            text1: First text
            text2: Second text

        Returns:
            List of DiffFragment objects
        """
        differences: list[DiffFragment] = []

        matcher = SequenceMatcher(None, text1, text2, autojunk=False)

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "equal":
                differences.append(
                    DiffFragment(
                        text=text1[i1:i2],
                        type="same",
                        position=i1,
                    )
                )
            elif tag == "delete":
                differences.append(
                    DiffFragment(
                        text=text1[i1:i2],
                        type="removed",
                        position=i1,
                    )
                )
            elif tag == "insert":
                differences.append(
                    DiffFragment(
                        text=text2[j1:j2],
                        type="added",
                        position=i1,
                    )
                )
            elif tag == "replace":
                # Removed
                differences.append(
                    DiffFragment(
                        text=text1[i1:i2],
                        type="removed",
                        position=i1,
                    )
                )
                # Added
                differences.append(
                    DiffFragment(
                        text=text2[j1:j2],
                        type="added",
                        position=i1,
                    )
                )

        return differences

    def _compute_similarity(self, text1: str, text2: str) -> float:
        """Compute similarity score between two texts.

        Args:
            text1: First text
            text2: Second text

        Returns:
            Similarity score (0-1)
        """
        if not text1 and not text2:
            return 1.0
        if not text1 or not text2:
            return 0.0

        matcher = SequenceMatcher(None, text1, text2, autojunk=False)
        return matcher.ratio()


def compare_ptr_and_report(
    ptr_doc: PTRDocument,
    report_doc: ReportDocument,
) -> list[ComparisonDetail]:
    """Convenience function to compare PTR and report documents.

    Args:
        ptr_doc: PTR document
        report_doc: Report document

    Returns:
        List of comparison details
    """
    comparator = ClauseComparator()
    return comparator.compare_documents(ptr_doc, report_doc)


def compare_texts(text1: str, text2: str) -> tuple[bool, float, list[DiffFragment]]:
    """Compare two texts and return match status.

    Args:
        text1: First text
        text2: Second text

    Returns:
        Tuple of (is_match, similarity, differences)
    """
    normalizer = TextNormalizer()
    comparator = ClauseComparator(normalizer=normalizer)

    norm1 = normalizer.normalize(text1)
    norm2 = normalizer.normalize(text2)

    is_match = norm1 == norm2
    similarity = comparator._compute_similarity(norm1, norm2)

    if not is_match:
        differences = comparator._compute_diff(norm1, norm2)
    else:
        differences = []

    return is_match, similarity, differences
