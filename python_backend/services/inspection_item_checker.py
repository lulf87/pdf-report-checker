"""
检验项目表格检测与核对模块
支持检验项目表格的自动解析和单项结论逻辑核对
"""

import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

from models.schemas import (
    InspectionItemCheckResult, InspectionItemCheck, ClauseCheck,
    RequirementCheck, ErrorItem, TableData
)
from services.pdf_parser import PDFParser


class ConclusionStatus(str, Enum):
    """单项结论状态"""
    PASS = "符合"
    FAIL = "不符合"
    NA = "/"


class ConclusionErrorCode(str, Enum):
    """单项结论错误代码"""
    SHOULD_BE_NA = "CONCLUSION_MISMATCH_001"  # 应标为"/"但标为其他
    SHOULD_BE_PASS = "CONCLUSION_MISMATCH_002"  # 应标为"符合"但标为其他
    SHOULD_BE_FAIL = "CONCLUSION_MISMATCH_003"  # 应标为"不符合"但标为其他
    SHOULD_NOT_BE_FAIL = "CONCLUSION_MISMATCH_004"  # 不应标为"不符合"
    CONTINUITY_ERROR = "CONTINUITY_ERROR_001"  # 跨页数据不连续


class SerialNumberErrorCode(str, Enum):
    """序号连续性错误代码 (v2.2新增)"""
    NOT_CONTINUOUS = "SERIAL_NUMBER_ERROR_001"  # 序号不连续
    EMPTY = "SERIAL_NUMBER_ERROR_002"  # 序号为空


class ContinuationMarkErrorCode(str, Enum):
    """续表标记错误代码 (v2.2新增)"""
    MISSING = "CONTINUATION_MARK_ERROR_001"  # 缺少续表标记
    WRONG_POSITION = "CONTINUATION_MARK_ERROR_002"  # 续字位置错误


class NonEmptyFieldErrorCode(str, Enum):
    """非空字段错误代码 (v2.2新增)"""
    EMPTY_INSPECTION_RESULT = "EMPTY_FIELD_001"  # 检验结果为空
    EMPTY_CONCLUSION = "EMPTY_FIELD_002"  # 单项结论为空
    EMPTY_REMARK = "EMPTY_FIELD_003"  # 备注为空


@dataclass
class InspectionTableRow:
    """检验项目表格行数据"""
    item_number: str           # 序号（处理后的，去掉"续"字）
    item_name: str             # 检验项目
    clause_number: str         # 标准条款
    requirement_text: str      # 标准要求
    inspection_result: str     # 检验结果
    conclusion: str            # 单项结论
    remark: str                # 备注
    page_num: int = 0          # 所在页码 (v2.2新增)
    row_index: int = 0         # 行索引 (v2.2新增)
    is_first_row_in_page: bool = False  # 是否为本页第一行数据 (v2.2新增)
    original_item_number: str = ""  # 原始序号（包含"续"字标记）(v2.2新增)
    has_continuation_mark: bool = False  # 是否包含续表标记 (v2.2新增)


class InspectionItemChecker:
    """检验项目核对器"""

    # 检验项目表格表头关键词
    TABLE_HEADERS = ['序号', '检验项目', '标准条款', '标准要求', '检验结果', '单项结论', '备注']

    # 续表标记
    CONTINUATION_MARKERS = ['续', '续表', '续上表', '续前表']

    def __init__(self):
        self.pdf_parser = PDFParser()

    def check_inspection_items(self, pdf_path: str, pages: List[Any]) -> InspectionItemCheckResult:
        """
        检测并核对检验项目表格

        Args:
            pdf_path: PDF文件路径
            pages: 页面信息列表

        Returns:
            InspectionItemCheckResult: 检验项目核对结果
        """
        # 1. 检测检验项目表格
        tables = self._detect_inspection_tables(pdf_path, pages)

        if not tables:
            return InspectionItemCheckResult(
                has_table=False,
                total_items=0,
                total_clauses=0,
                correct_conclusions=0,
                incorrect_conclusions=0,
                item_checks=[],
                cross_page_continuations=0,
                errors=[]
            )

        # 2. 解析表格数据
        all_rows = self._parse_inspection_tables(tables, pdf_path)

        # 3. 【v2.2新增】非空字段校验（在单项结论核对之前）
        empty_field_errors = self._check_non_empty_fields(all_rows)

        # 4. 【v2.2新增】序号连续性校验（包含续表标记校验）
        serial_number_errors = self._check_serial_number_continuity(all_rows)

        # 5. 组织数据结构并核对单项结论
        item_checks = self._check_items(all_rows)

        # 6. 统计结果
        total_clauses = sum(len(item.clauses) for item in item_checks)
        correct_conclusions = sum(
            1 for item in item_checks
            for clause in item.clauses
            if clause.is_conclusion_correct
        )
        incorrect_conclusions = total_clauses - correct_conclusions

        # 7. 收集错误（包含非空字段错误和序号连续性错误）
        errors = empty_field_errors + serial_number_errors + self._collect_inspection_errors(item_checks)

        return InspectionItemCheckResult(
            has_table=True,
            total_items=len(item_checks),
            total_clauses=total_clauses,
            correct_conclusions=correct_conclusions,
            incorrect_conclusions=incorrect_conclusions,
            item_checks=item_checks,
            cross_page_continuations=len(tables) - 1,  # 续表数量 = 表格数 - 1
            errors=errors
        )

    def _detect_inspection_tables(self, pdf_path: str, pages: List[Any]) -> List[Tuple[int, int]]:
        """
        检测检验项目表格的位置

        Returns:
            List[Tuple[int, int]]: [(页码, 表格索引), ...]
        """
        import fitz

        tables = []
        doc = fitz.open(pdf_path)

        try:
            for page_info in pages:
                page_num = page_info.page_num
                page = doc[page_num - 1]

                # 查找表格
                tab = page.find_tables()
                for table_idx in range(len(tab.tables)):
                    # 提取表格文本检查表头
                    table_data = self.pdf_parser.extract_table_detailed(
                        pdf_path, page_num, table_idx
                    )

                    if table_data and self._is_inspection_table(table_data):
                        tables.append((page_num, table_idx))

            return tables

        finally:
            doc.close()

    def _is_inspection_table(self, table_data: TableData) -> bool:
        """判断是否为检验项目表格"""
        if table_data is None:
            return False
        if not table_data.headers:
            return False

        headers_str = ' '.join(str(h) for h in table_data.headers)
        headers_clean = re.sub(r'\s+', '', headers_str)

        # 检查是否包含所有必需的表头
        required_headers = ['序号', '检验项目', '标准条款', '标准要求', '检验结果', '单项结论']
        for header in required_headers:
            if header not in headers_clean:
                return False

        return True

    def _parse_inspection_tables(self, tables: List[Tuple[int, int]], pdf_path: str) -> List[InspectionTableRow]:
        """
        解析检验项目表格数据，处理跨页续表

        Returns:
            List[InspectionTableRow]: 解析后的表格行数据
        """
        all_rows = []
        last_item_number = ""
        last_item_name = ""
        last_clause_number = ""
        row_index = 0

        for page_num, table_idx in tables:
            table_data = self.pdf_parser.extract_table_detailed(pdf_path, page_num, table_idx)

            if not table_data:
                continue

            # 获取列索引
            col_indices = self._get_column_indices(table_data.headers)

            header_col_count = len(table_data.headers)
            is_first_data_row = True  # 标记是否为本页第一行数据行

            for row in table_data.rows:
                if len(row) < 2:
                    continue

                # 使用智能列映射处理变长行
                mapped = self._map_row_columns(row, col_indices, header_col_count)
                original_item_number = mapped['item_number']  # 保存原始序号
                item_number = mapped['item_number']
                item_name = mapped['item_name']
                clause_number = mapped['clause_number']
                requirement_text = mapped['requirement_text']
                inspection_result = mapped['inspection_result']
                conclusion = mapped['conclusion']
                remark = mapped['remark']

                # 过滤表头行
                if item_number in ['序号', ''] and not item_name:
                    continue

                # 处理跨页续行：检测"续"字标记（如"续30"、"续 30"等）
                has_continuation_mark = False
                if item_number and '续' in item_number:
                    # 提取真实序号（去掉"续"字后的数字）
                    real_number = self._extract_number_from_continuation(item_number)
                    if real_number:
                        item_number = real_number
                        has_continuation_mark = True

                # 处理续表：序号为空或者是续行时继承上一行
                is_continuation = False
                if (not original_item_number or has_continuation_mark) and last_item_number:
                    if not original_item_number or item_number == last_item_number:
                        # 如果是续行且序号匹配，使用上一行的项目名称
                        item_number = last_item_number
                        item_name = last_item_name if not item_name else item_name
                        is_continuation = True

                # 处理同一检验项目多行：标准条款为空时继承上一行
                if not clause_number and last_clause_number:
                    clause_number = last_clause_number

                # 更新最后记录的值
                if item_number and item_number != last_item_number:
                    last_item_number = item_number
                    last_item_name = item_name
                if clause_number:
                    last_clause_number = clause_number

                all_rows.append(InspectionTableRow(
                    item_number=item_number or last_item_number,
                    item_name=item_name or last_item_name,
                    clause_number=clause_number or last_clause_number,
                    requirement_text=requirement_text,
                    inspection_result=inspection_result,
                    conclusion=conclusion,
                    remark=remark,
                    page_num=page_num,
                    row_index=row_index,
                    is_first_row_in_page=is_first_data_row,
                    original_item_number=original_item_number,
                    has_continuation_mark=has_continuation_mark
                ))

                is_first_data_row = False
                row_index += 1

        return all_rows

    def _get_column_indices(self, headers: List[str]) -> Dict[str, int]:
        """获取各列的索引"""
        indices = {}

        for idx, header in enumerate(headers):
            header_clean = re.sub(r'\s+', '', header.strip())

            if '序号' in header_clean:
                indices['序号'] = idx
            elif '检验项目' in header_clean:
                indices['检验项目'] = idx
            elif '标准条款' in header_clean:
                indices['标准条款'] = idx
            elif '标准要求' in header_clean:
                indices['标准要求'] = idx
            elif '检验结果' in header_clean:
                indices['检验结果'] = idx
            elif '单项结论' in header_clean:
                indices['单项结论'] = idx
            elif '备注' in header_clean:
                indices['备注'] = idx

        return indices

    def _map_row_columns(self, row: list, col_indices: Dict[str, int], header_col_count: int = 7) -> Dict[str, str]:
        """
        将变长行映射到标准列字典。
        
        PyMuPDF 在提取合并单元格表格时，不同行可能返回不同列数：
        - 7列：标准完整行 [序号, 检验项目, 标准条款, 标准要求, 检验结果, 单项结论, 备注]
        - 2列：续行（合并单元格子行）[标准要求, 检验结果]
        - 3列：续行（带分类名）[分类名, 标准要求, 检验结果]
        - 4列：续行（带两级分类）[分类1, 分类2, 标准要求, 检验结果]
        - 6列：缺少某一列的行
        - 8列：多了一个分类名列
        
        Returns:
            dict: 包含 item_number, item_name, clause_number, requirement_text,
                  inspection_result, conclusion, remark
        """
        result = {
            'item_number': '',
            'item_name': '',
            'clause_number': '',
            'requirement_text': '',
            'inspection_result': '',
            'conclusion': '',
            'remark': ''
        }
        
        num_cols = len(row)
        
        if num_cols >= header_col_count:
            # 列数 >= 表头列数 (7列或8列+)
            if num_cols == header_col_count:
                # 标准7列行，直接按列索引映射
                result['item_number'] = row[col_indices.get('序号', 0)].strip() if col_indices.get('序号', 0) < num_cols and row[col_indices.get('序号', 0)] else ''
                result['item_name'] = row[col_indices.get('检验项目', 1)].strip() if col_indices.get('检验项目', 1) < num_cols and row[col_indices.get('检验项目', 1)] else ''
                result['clause_number'] = row[col_indices.get('标准条款', 2)].strip() if col_indices.get('标准条款', 2) < num_cols and row[col_indices.get('标准条款', 2)] else ''
                result['requirement_text'] = row[col_indices.get('标准要求', 3)].strip() if col_indices.get('标准要求', 3) < num_cols and row[col_indices.get('标准要求', 3)] else ''
                result['inspection_result'] = row[col_indices.get('检验结果', 4)].strip() if col_indices.get('检验结果', 4) < num_cols and row[col_indices.get('检验结果', 4)] else ''
                result['conclusion'] = row[col_indices.get('单项结论', 5)].strip() if col_indices.get('单项结论', 5) < num_cols and row[col_indices.get('单项结论', 5)] else ''
                result['remark'] = row[col_indices.get('备注', 6)].strip() if col_indices.get('备注', 6) < num_cols and row[col_indices.get('备注', 6)] else ''
            else:
                # 列数 > 表头列数 (如8列)，多出的列通常是分类名
                # 前3列保持不变（序号、检验项目、标准条款）
                result['item_number'] = row[0].strip() if row[0] else ''
                result['item_name'] = row[1].strip() if row[1] else ''
                result['clause_number'] = row[2].strip() if row[2] else ''
                # 多出的列在中间，合并到标准要求
                extra_cols = num_cols - header_col_count
                req_start = col_indices.get('标准要求', 3)
                # 将 col[3] 到 col[3+extra_cols] 合并为标准要求
                req_parts = []
                for i in range(req_start, req_start + 1 + extra_cols):
                    if i < num_cols and row[i] and row[i].strip():
                        req_parts.append(row[i].strip())
                result['requirement_text'] = ' '.join(req_parts)
                # 后面的列偏移 extra_cols
                result_idx = col_indices.get('检验结果', 4) + extra_cols
                conclusion_idx = col_indices.get('单项结论', 5) + extra_cols
                remark_idx = col_indices.get('备注', 6) + extra_cols
                result['inspection_result'] = row[result_idx].strip() if result_idx < num_cols and row[result_idx] else ''
                result['conclusion'] = row[conclusion_idx].strip() if conclusion_idx < num_cols and row[conclusion_idx] else ''
                result['remark'] = row[remark_idx].strip() if remark_idx < num_cols and row[remark_idx] else ''
        elif num_cols <= 4:
            # 2-4列：续行（合并单元格中的子行）
            # 只包含标准要求和检验结果，其余字段继承上一行
            # 最后一列是检验结果，前面的列合并为标准要求
            req_parts = []
            for i in range(num_cols - 1):
                if row[i] and row[i].strip():
                    req_parts.append(row[i].strip())
            result['requirement_text'] = ' '.join(req_parts)
            result['inspection_result'] = row[num_cols - 1].strip() if row[num_cols - 1] else ''
        elif num_cols == 5:
            # 5列行：可能缺少序号+检验项目列，或其他组合
            # 分析：通常是 [标准条款, 标准要求子分类, 标准要求, 检验结果, 单项结论]
            # 或者 [分类1, 分类2, 标准要求, 检验结果, 备注]
            result['requirement_text'] = ' '.join(row[i].strip() for i in range(num_cols - 2) if row[i] and row[i].strip())
            result['inspection_result'] = row[num_cols - 2].strip() if row[num_cols - 2] else ''
            result['conclusion'] = row[num_cols - 1].strip() if row[num_cols - 1] else ''
        elif num_cols == 6:
            # 6列行：通常缺少一列（最可能缺少备注或序号）
            # 策略：检查第一列是否像序号
            first_cell = row[0].strip() if row[0] else ''
            if re.match(r'^\d+$', first_cell) or '续' in first_cell:
                # 有序号，缺少一列。判断缺少的是"检验结果"还是"备注"
                result['item_number'] = first_cell
                result['item_name'] = row[1].strip() if row[1] else ''
                result['clause_number'] = row[2].strip() if row[2] else ''
                result['requirement_text'] = row[3].strip() if row[3] else ''
                
                # 启发式判断col[4]是"检验结果"还是"单项结论"
                # 单项结论只会是 "符合"、"不符合"、"/" 
                # 检验结果通常是 "符合要求"、"不符合要求"、"——"、数字等
                col4_val = row[4].strip() if row[4] else ''
                conclusion_values = {'符合', '不符合', '/', ''}
                if col4_val in conclusion_values:
                    # col[4]是单项结论，说明缺少的是"检验结果"列
                    result['inspection_result'] = ''
                    result['conclusion'] = col4_val
                    result['remark'] = row[5].strip() if row[5] else ''
                else:
                    # col[4]是检验结果，缺少的是"备注"列
                    result['inspection_result'] = col4_val
                    result['conclusion'] = row[5].strip() if row[5] else ''
            else:
                # 无序号，可能是 [检验项目, 标准条款, 标准要求, 检验结果, 单项结论, 备注]
                result['item_name'] = row[0].strip() if row[0] else ''
                result['clause_number'] = row[1].strip() if row[1] else ''
                result['requirement_text'] = row[2].strip() if row[2] else ''
                result['inspection_result'] = row[3].strip() if row[3] else ''
                result['conclusion'] = row[4].strip() if row[4] else ''
                result['remark'] = row[5].strip() if row[5] else ''
        
        return result

    def _check_items(self, rows: List[InspectionTableRow]) -> List[InspectionItemCheck]:
        """
        核对检验项目，按序号分组并检查单项结论

        Args:
            rows: 表格行数据

        Returns:
            List[InspectionItemCheck]: 各检验项目核对结果
        """
        # 按序号分组
        items_dict: Dict[str, Dict] = {}

        for row in rows:
            item_num = row.item_number

            if item_num not in items_dict:
                items_dict[item_num] = {
                    'name': row.item_name,
                    'clauses': {}
                }

            # 按标准条款分组
            clause_num = row.clause_number
            if clause_num not in items_dict[item_num]['clauses']:
                items_dict[item_num]['clauses'][clause_num] = {
                    'requirements': [],
                    'conclusion': row.conclusion
                }
            else:
                # 保留第一行的单项结论（通常是主要结论行）
                # 不覆盖已有的结论，因为第一行通常是父行，包含正确的单项结论
                pass

            items_dict[item_num]['clauses'][clause_num]['requirements'].append(
                RequirementCheck(
                    requirement_text=row.requirement_text,
                    inspection_result=row.inspection_result,
                    remark=row.remark
                )
            )

        # 构建核对结果
        item_checks = []

        for item_num in sorted(items_dict.keys(), key=lambda x: self._extract_number(x)):
            item_data = items_dict[item_num]
            clauses = []
            item_issues = []

            for clause_num in sorted(item_data['clauses'].keys()):
                clause_data = item_data['clauses'][clause_num]
                requirements = clause_data['requirements']
                actual_conclusion = clause_data['conclusion']

                # 计算期望的单项结论
                expected_conclusion = self._calculate_expected_conclusion(requirements)

                # 核对结论（考虑特殊情况：当期望为"/"时，"符合"也视为正确）
                is_correct = self._is_conclusion_valid(actual_conclusion, expected_conclusion)

                if not is_correct:
                    item_issues.append(
                        f"序号 {item_num} 标准条款 {clause_num}: "
                        f"单项结论应为 '{expected_conclusion}'，实际为 '{actual_conclusion}'"
                    )

                clauses.append(ClauseCheck(
                    clause_number=clause_num,
                    requirements=requirements,
                    conclusion=actual_conclusion,
                    expected_conclusion=expected_conclusion,
                    is_conclusion_correct=is_correct
                ))

            # 确定项目状态
            if any(not c.is_conclusion_correct for c in clauses):
                status = 'fail'
            elif item_issues:
                status = 'warning'
            else:
                status = 'pass'

            item_checks.append(InspectionItemCheck(
                item_number=item_num,
                item_name=item_data['name'],
                clauses=clauses,
                issues=item_issues,
                status=status
            ))

        return item_checks

    def _calculate_expected_conclusion(self, requirements: List[RequirementCheck]) -> str:
        """
        根据检验结果计算期望的单项结论

        判定优先级：
        1. 任意检验结果为"不符合要求" -> "不符合"
        2. 所有检验结果都为"——"、"/"或空白 -> "/" 或 "符合"（两者都接受）
        3. 其他情况（包含"符合要求"、任意文本或数字）-> "符合"

        注意：
        - 根据规格说明2.2节，"/"与空白等价
        - 当检验结果为"——"时，单项结论可以是"/"或"符合"，两者都视为正确
          （实际文档中可能标记为"符合"表示该项已通过其他方式验证）
        """
        results = [r.inspection_result for r in requirements]

        # 优先级1: 判断是否包含 "不符合要求"
        # 注意：需要处理 None 值，避免 TypeError
        if any(r and '不符合' in r for r in results):
            return '不符合'

        # 优先级2: 判断是否全为 "/"、"——" 或空白（"/"、"——"视为不适用）
        # "—"、"-" 被视为非法值，不在此处理
        na_values = {'/', '——', '', None}
        all_results_na = all(
            r in na_values or r is None or (isinstance(r, str) and not r.strip())
            for r in results
        )

        if all_results_na:
            # 当所有检验结果都为"——"、"/"或空白时，
            # 单项结论可以是"/"或"符合"，两者都接受
            # 返回"/"作为期望值，但在核对时会接受"符合"作为有效值
            return '/'

        # 优先级3: 其他情况
        return '符合'

    def _is_conclusion_valid(self, actual: str, expected: str) -> bool:
        """
        判断实际结论是否有效

        规则：
        1. 如果实际值等于期望值，有效
        2. 如果期望值为"/"，实际值为"符合"也视为有效（误报修复）
           因为当检验结果为"——"时，单项结论可以是"/"或"符合"
        3. 其他情况无效
        """
        if actual == expected:
            return True

        # 当期望为"/"时，"符合"也视为正确
        if expected == '/' and actual == '符合':
            return True

        return False

    def _collect_inspection_errors(self, item_checks: List[InspectionItemCheck]) -> List[ErrorItem]:
        """收集检验项目核对错误"""
        errors = []

        for item in item_checks:
            for clause in item.clauses:
                if not clause.is_conclusion_correct:
                    error_code = self._get_error_code(
                        clause.expected_conclusion,
                        clause.conclusion
                    )

                    errors.append(ErrorItem(
                        level="ERROR",
                        message=f"序号 {item.item_number} 标准条款 {clause.clause_number}: "
                               f"单项结论错误（期望: {clause.expected_conclusion}, 实际: {clause.conclusion}）",
                        location=f"检验项目表格/{item.item_name}",
                        details={
                            'error_code': error_code,
                            'item_number': item.item_number,
                            'item_name': item.item_name,
                            'clause_number': clause.clause_number,
                            'expected': clause.expected_conclusion,
                            'actual': clause.conclusion
                        }
                    ))

        return errors

    def _get_error_code(self, expected: str, actual: str) -> str:
        """获取错误代码"""
        if expected == '/' and actual != '/':
            return 'CONCLUSION_MISMATCH_001'  # 应标为"/"但标为其他
        elif expected == '符合' and actual != '符合':
            # 需要进一步判断实际值
            if actual == '不符合':
                return 'CONCLUSION_MISMATCH_004'  # 不应标为"不符合"
            else:
                return 'CONCLUSION_MISMATCH_002'  # 应标为"符合"但标为其他
        elif expected == '不符合' and actual != '不符合':
            return 'CONCLUSION_MISMATCH_003'  # 应标为"不符合"但标为其他
        elif expected != '不符合' and actual == '不符合':
            return 'CONCLUSION_MISMATCH_004'  # 不应标为"不符合"
        return 'CONCLUSION_MISMATCH_UNKNOWN'

    def _extract_number(self, s: str) -> int:
        """从字符串中提取数字用于排序"""
        match = re.search(r'\d+', s)
        return int(match.group()) if match else 0

    def _extract_number_from_continuation(self, s: str) -> str:
        """
        从续行标记中提取真实序号
        例如："续30" -> "30", "续 30" -> "30", "续-30" -> "30"
        """
        if not s:
            return ""
        # 移除"续"字及其后面的非数字字符，提取数字
        match = re.search(r'续\s*[\-\s]*(\d+)', s)
        if match:
            return match.group(1)
        # 备选：直接提取所有数字
        match = re.search(r'\d+', s)
        return match.group() if match else ""

    # ============== 公共API方法 ==============

    def detect_inspection_table(self, table_data: TableData) -> bool:
        """
        检测表格是否为检验项目表格

        检查表头是否包含全部7个标准列名
        """
        return self._is_inspection_table(table_data)

    def is_continuation_table(self, page_text: str) -> bool:
        """
        检测是否为续表

        检查页眉或表格上方是否包含续表标记
        """
        if not page_text:
            return False

        text_clean = re.sub(r'\s+', '', page_text)

        for marker in self.CONTINUATION_MARKERS:
            # 匹配"续表 X"或"续表"等格式
            pattern = marker + r'\d*'
            if re.search(pattern, text_clean):
                return True

        return False

    def parse_inspection_table(self, table_data: TableData) -> List[InspectionItemCheck]:
        """
        解析检验项目表格

        处理跨行数据，构建检验项目结构
        """
        if not table_data or not table_data.rows:
            return []

        # 获取列索引
        col_indices = self._get_column_indices(table_data.headers)

        if not col_indices:
            return []

        all_rows = []
        last_item_number = ""
        last_item_name = ""
        last_clause_number = ""

        header_col_count = len(table_data.headers)

        for row in table_data.rows:
            if len(row) < 2:
                continue

            # 使用智能列映射处理变长行
            mapped = self._map_row_columns(row, col_indices, header_col_count)
            item_number = mapped['item_number']
            item_name = mapped['item_name']
            clause_number = mapped['clause_number']
            requirement_text = mapped['requirement_text']
            inspection_result = mapped['inspection_result']
            conclusion = mapped['conclusion']
            remark = mapped['remark']

            # 处理跨页续行：检测"续"字标记（如"续30"、"续 30"等）
            is_continuation = False
            if item_number and '续' in item_number:
                # 提取真实序号（去掉"续"字后的数字）
                real_number = self._extract_number_from_continuation(item_number)
                if real_number:
                    item_number = real_number
                    is_continuation = True

            # 处理续行：序号为空或者是续行时继承上一行
            if (not item_number or is_continuation) and last_item_number:
                if not item_number or item_number == last_item_number:
                    # 如果是续行且序号匹配，使用上一行的项目名称
                    item_number = last_item_number
                    item_name = last_item_name if not item_name else item_name

            # 处理同一检验项目多行：标准条款为空时继承上一行
            if not clause_number and last_clause_number:
                clause_number = last_clause_number

            # 更新最后记录的值
            if item_number:
                last_item_number = item_number
                last_item_name = item_name
            if clause_number:
                last_clause_number = clause_number

            # 过滤表头行
            if item_number in ['序号', ''] and not item_name:
                continue

            all_rows.append(InspectionTableRow(
                item_number=item_number or last_item_number,
                item_name=item_name or last_item_name,
                clause_number=clause_number or last_clause_number,
                requirement_text=requirement_text,
                inspection_result=inspection_result,
                conclusion=conclusion,
                remark=remark
            ))

        return self._check_items(all_rows)

    def check_conclusions(self, items: List[InspectionItemCheck]) -> Tuple[int, int, List[ErrorItem]]:
        """
        核对所有单项结论

        Returns:
            (正确数量, 错误数量, 错误列表)
        """
        correct_count = 0
        incorrect_count = 0
        errors = []

        for item in items:
            for clause in item.clauses:
                expected = self._calculate_expected_conclusion(clause.requirements)
                clause.expected_conclusion = expected

                # 标准化实际结论
                actual = clause.conclusion.strip() if clause.conclusion else ''

                # 结论正确性检查
                if actual == expected:
                    clause.is_conclusion_correct = True
                    correct_count += 1
                else:
                    clause.is_conclusion_correct = False
                    incorrect_count += 1

                    # 确定错误类型
                    error_code = self._get_error_code(expected, actual)

                    # 构建错误信息
                    error_msg = (f"序号 {item.item_number} ({item.item_name}) - "
                               f"标准条款 {clause.clause_number}: "
                               f"单项结论应为'{expected}'，实际为'{actual}'")

                    errors.append(ErrorItem(
                        level="ERROR",
                        message=error_msg,
                        location=f"检验项目表格/序号{item.item_number}/条款{clause.clause_number}",
                        details={
                            'error_code': error_code,
                            'item_number': item.item_number,
                            'item_name': item.item_name,
                            'clause_number': clause.clause_number,
                            'expected_conclusion': expected,
                            'actual_conclusion': actual,
                            'requirements': [
                                {
                                    'text': r.requirement_text,
                                    'result': r.inspection_result
                                }
                                for r in clause.requirements
                            ]
                        }
                    ))

                    # 添加到项目问题列表
                    item.issues.append(f"条款{clause.clause_number}: 单项结论应为'{expected}'，实际为'{actual}'")

            # 更新项目状态
            if any(not c.is_conclusion_correct for c in item.clauses):
                item.status = 'fail'
            elif item.issues:
                item.status = 'warning'
            else:
                item.status = 'pass'

        return correct_count, incorrect_count, errors

    def merge_continuation_tables(self, tables: List[Tuple[int, int, TableData]],
                                   pages: List[Any]) -> List[Tuple[int, TableData]]:
        """
        合并跨页续表

        Args:
            tables: List of (page_num, table_index, table_data)
            pages: List of PageInfo

        Returns:
            List of (start_page_num, merged_table_data)
        """
        if not tables:
            return []

        # 按页码排序
        sorted_tables = sorted(tables, key=lambda x: x[0])

        merged = []
        current_group = [sorted_tables[0]]

        for i in range(1, len(sorted_tables)):
            prev_page_num = sorted_tables[i - 1][0]
            curr_page_num = sorted_tables[i][0]

            # 检查是否连续页
            if curr_page_num == prev_page_num + 1:
                # 检查当前页是否有续表标记
                page_info = next((p for p in pages if p.page_num == curr_page_num), None)
                if page_info and page_info.text_content:
                    if self.is_continuation_table(page_info.text_content):
                        current_group.append(sorted_tables[i])
                        continue

            # 不连续或不是续表，结束当前组
            merged_table = self._merge_table_group(current_group)
            merged.append((current_group[0][0], merged_table))
            current_group = [sorted_tables[i]]

        # 处理最后一组
        if current_group:
            merged_table = self._merge_table_group(current_group)
            merged.append((current_group[0][0], merged_table))

        return merged

    def _merge_table_group(self, table_group: List[Tuple[int, int, TableData]]) -> TableData:
        """合并一组续表"""
        if not table_group:
            return None

        if len(table_group) == 1:
            return table_group[0][2]

        first_table = table_group[0][2]
        all_rows = list(first_table.rows)

        for _, _, table_data in table_group[1:]:
            # 续表可能无表头，第一行可能是数据
            rows = table_data.rows

            if not rows:
                continue

            # 检查第一行是否是表头重复
            first_row = rows[0]
            is_header = any(col in ' '.join(first_row) for col in self.TABLE_HEADERS[:3])

            if is_header and len(rows) > 1:
                rows = rows[1:]

            all_rows.extend(rows)

        return TableData(
            page_num=first_table.page_num,
            table_index=first_table.table_index,
            headers=first_table.headers,
            rows=all_rows,
            row_count=len(all_rows),
            col_count=first_table.col_count
        )

    def _is_field_filled(self, value: Optional[str], allow_na: bool = True) -> bool:
        """
        判断字段是否已填写（非空）

        区分"真正的空值"和"不适用标记":
        - 真正的空值: None, "", "  " → 返回 False（应该报错）
        - 不适用标记: "/", "——", "—", "-" → 返回 True（合法值，不报错）
        - 有效内容: "符合要求", "0.01"等 → 返回 True

        Args:
            value: 字段值
            allow_na: 是否允许"/"、"——"等表示"不适用"的值为有效值

        Returns:
            bool: True表示字段已填写（或有合法的不适用标记），False表示为空
        """
        if value is None:
            return False

        if not isinstance(value, str):
            return False

        stripped = value.strip()
        if not stripped:
            # 空字符串或只有空白字符
            return False

        if allow_na:
            # "/"、"——" 表示"不适用"，是合法的有效值
            # 其他非空内容（如"符合要求"、"0.01"）也是合法的
            # "—"、"-" 被视为非法值
            if stripped in {'—', '-'}:
                return False
            # "/"、"——" 或任何其他非空内容都视为有效
            return True

        # allow_na=False时，所有非空内容都视为有效
        return True

    def _check_non_empty_fields(self, rows: List[InspectionTableRow]) -> List[ErrorItem]:
        """
        非空字段校验 (v2.2新增)

        对检验项目表格中的以下三列进行非空检查：
        - 检验结果：必填，不得为空
        - 单项结论：必填，不得为空
        - 备注：必填，不得为空

        合并单元格处理：
        - 检测到合并单元格时，以合并区域的首行值作为该区域的值进行校验
        - 合并单元格内的每一行继承该值，逐行进行非空判断
        - 若合并区域首行为空，则整个合并区域都视为空值，逐行报错

        Args:
            rows: 表格行数据列表

        Returns:
            List[ErrorItem]: 非空字段错误列表
        """
        errors = []

        # 预计算：检测哪些key（序号+标准条款）跨了多页
        key_page_count = {}  # key -> set of page_nums
        for row in rows:
            key = f"{row.item_number}_{row.clause_number}"
            if key not in key_page_count:
                key_page_count[key] = set()
            key_page_count[key].add(row.page_num)

        last_item_clause_key = None  # 用于检测是否处于同一合并区域

        for idx, row in enumerate(rows):
            # 构建当前行的唯一标识（序号+标准条款）
            current_key = f"{row.item_number}_{row.clause_number}"

            # 检测是否为key的第一行
            is_first_row_of_key = (current_key != last_item_clause_key)
            if is_first_row_of_key:
                last_item_clause_key = current_key

            # 每一行的检验结果独立检查（不继承）
            # 只有真正的空值（None/""）才报错，"——"和"/"是合法的
            effective_result = row.inspection_result.strip() if row.inspection_result else None
            effective_conclusion = row.conclusion.strip() if row.conclusion else None
            effective_remark = row.remark.strip() if row.remark else None

            # 检测是否为"标题行"（多级表格中的父行，本身无检验结果，子行才有）
            # 特征：
            # 1. 当前行是key的第一行（不是后续行）
            # 2. 当前行检验结果为空
            # 3. 后面有相同key的行有检验结果
            is_title_row = False

            if is_first_row_of_key and (not row.inspection_result or not row.inspection_result.strip()):
                # 检查后面的行是否有相同的序号+标准条款且有检验结果
                for next_row in rows[idx + 1:]:
                    next_key = f"{next_row.item_number}_{next_row.clause_number}"
                    if next_key == current_key and next_row.inspection_result and next_row.inspection_result.strip():
                        is_title_row = True
                        break
                    elif next_key != current_key:
                        # 不同序号，停止搜索
                        break

            # 如果是标题行，跳过非空校验（因为它本身没有检验结果，子行才有）
            if is_title_row:
                continue

            # 校验检验结果
            # 注意："/"、"——"、"—"、"-" 表示不适用，是合法值，不应视为空
            # 真正的空值（None/""）会报错
            if not self._is_field_filled(effective_result):
                errors.append(ErrorItem(
                    level="ERROR",
                    message=f"序号 {row.item_number} 标准条款 {row.clause_number}: 检验结果为空",
                    location=f"检验项目表格/{row.item_name}/检验结果",
                    details={
                        'error_code': NonEmptyFieldErrorCode.EMPTY_INSPECTION_RESULT,
                        'item_number': row.item_number,
                        'item_name': row.item_name,
                        'clause_number': row.clause_number,
                        'field_name': '检验结果',
                        'row_index': idx
                    }
                ))

            # 校验单项结论
            # 注意："/" 表示不适用，是合法值，不应视为空
            if not self._is_field_filled(effective_conclusion, allow_na=True):
                errors.append(ErrorItem(
                    level="ERROR",
                    message=f"序号 {row.item_number} 标准条款 {row.clause_number}: 单项结论为空",
                    location=f"检验项目表格/{row.item_name}/单项结论",
                    details={
                        'error_code': NonEmptyFieldErrorCode.EMPTY_CONCLUSION,
                        'item_number': row.item_number,
                        'item_name': row.item_name,
                        'clause_number': row.clause_number,
                        'field_name': '单项结论',
                        'row_index': idx
                    }
                ))

            # 校验备注
            # 注意："/"、"——"、"—" 表示不适用，是合法值，不应视为空
            if not self._is_field_filled(effective_remark, allow_na=True):
                errors.append(ErrorItem(
                    level="ERROR",
                    message=f"序号 {row.item_number} 标准条款 {row.clause_number}: 备注为空",
                    location=f"检验项目表格/{row.item_name}/备注",
                    details={
                        'error_code': NonEmptyFieldErrorCode.EMPTY_REMARK,
                        'item_number': row.item_number,
                        'item_name': row.item_name,
                        'clause_number': row.clause_number,
                        'field_name': '备注',
                        'row_index': idx
                    }
                ))

        return errors

    def _check_serial_number_continuity(self, rows: List[InspectionTableRow]) -> List[ErrorItem]:
        """
        序号连续性校验 (v2.2新增)

        校验规则：
        1. 序号连续性：从检验项目表格开始，序号必须连续（1,2,3...），无跳号
        2. 跨页续表标记：同一序号跨页时，新页第一行的序号前必须加"续"字
        3. 续字位置校验："续"字只能出现在本页第一行的序号中，其他位置出现均为错误
        4. 序号非空：序号列不得出现空白

        Args:
            rows: 表格行数据列表

        Returns:
            List[ErrorItem]: 序号连续性错误列表
        """
        errors = []
        if not rows:
            return errors

        # 提取所有唯一的序号（按出现顺序）
        seen_numbers = []
        last_page_num = 0
        last_item_number = ""
        page_first_item_numbers = {}  # 记录每页的第一个序号

        for idx, row in enumerate(rows):
            # 记录每页的第一个序号
            if row.page_num not in page_first_item_numbers:
                page_first_item_numbers[row.page_num] = {
                    'item_number': row.item_number,
                    'row_index': idx,
                    'is_first_row_in_page': row.is_first_row_in_page
                }

            # 检查序号是否为空（原始序号，不是继承后的）
            # 注意：这里需要检查原始输入，所以需要在解析时记录原始序号
            # 由于继承逻辑，我们假设如果row.item_number为空字符串，则原始为空
            if not row.item_number or row.item_number.strip() == '':
                errors.append(ErrorItem(
                    level="ERROR",
                    message=f"第 {idx + 1} 行: 序号为空",
                    location=f"检验项目表格/第{row.page_num}页/行{idx + 1}",
                    details={
                        'error_code': SerialNumberErrorCode.EMPTY,
                        'row_index': idx,
                        'page_num': row.page_num,
                        'item_name': row.item_name
                    }
                ))
                continue

            # 提取数字序号用于连续性检查
            current_num = self._extract_number(row.item_number)

            # 检查是否为新序号
            if row.item_number not in seen_numbers:
                seen_numbers.append(row.item_number)

                # 检查序号连续性（只检查数字序号）
                if current_num > 0 and len(seen_numbers) > 1:
                    # 获取上一个序号
                    prev_num = self._extract_number(seen_numbers[-2])
                    if prev_num > 0 and current_num != prev_num + 1:
                        # 序号不连续
                        errors.append(ErrorItem(
                            level="ERROR",
                            message=f"序号不连续：从 {seen_numbers[-2]} 跳到 {row.item_number}（缺少 {prev_num + 1}）",
                            location=f"检验项目表格/第{row.page_num}页",
                            details={
                                'error_code': SerialNumberErrorCode.NOT_CONTINUOUS,
                                'expected': prev_num + 1,
                                'actual': current_num,
                                'previous_item': seen_numbers[-2],
                                'current_item': row.item_number,
                                'page_num': row.page_num
                            }
                        ))

            # 检查跨页续表标记和续字位置
            if row.page_num != last_page_num and last_page_num > 0:
                # 页面切换了，检查是否需要续表标记
                if row.item_number == last_item_number:
                    # 同一序号跨页，需要"续"字标记
                    if row.is_first_row_in_page:
                        # 本页第一行，检查是否有续表标记
                        if not row.has_continuation_mark:
                            errors.append(ErrorItem(
                                level="ERROR",
                                message=f"跨页续表缺少标记：序号 {row.item_number} 跨页到第 {row.page_num} 页，第一行应标记为\"续{row.item_number}\"或\"续\"",
                                location=f"检验项目表格/第{row.page_num}页/第一行",
                                details={
                                    'error_code': ContinuationMarkErrorCode.MISSING,
                                    'item_number': row.item_number,
                                    'page_num': row.page_num,
                                    'expected_mark': f"续{row.item_number}",
                                    'actual_mark': row.original_item_number
                                }
                            ))

            # 检查续字位置是否正确（"续"字只能出现在本页第一行）
            if row.has_continuation_mark and not row.is_first_row_in_page:
                errors.append(ErrorItem(
                    level="ERROR",
                    message=f"续字位置错误：序号 \"{row.original_item_number}\" 出现在非第一行，\"续\"字只能出现在本页第一行",
                    location=f"检验项目表格/第{row.page_num}页/行{idx + 1}",
                    details={
                        'error_code': ContinuationMarkErrorCode.WRONG_POSITION,
                        'item_number': row.item_number,
                        'original_mark': row.original_item_number,
                        'page_num': row.page_num,
                        'row_index': idx,
                        'is_first_row': row.is_first_row_in_page
                    }
                ))

            last_page_num = row.page_num
            last_item_number = row.item_number

        return errors
