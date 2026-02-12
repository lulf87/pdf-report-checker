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


@dataclass
class InspectionTableRow:
    """检验项目表格行数据"""
    item_number: str           # 序号
    item_name: str             # 检验项目
    clause_number: str         # 标准条款
    requirement_text: str      # 标准要求
    inspection_result: str     # 检验结果
    conclusion: str            # 单项结论
    remark: str                # 备注


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

        # 3. 组织数据结构并核对单项结论
        item_checks = self._check_items(all_rows)

        # 4. 统计结果
        total_clauses = sum(len(item.clauses) for item in item_checks)
        correct_conclusions = sum(
            1 for item in item_checks
            for clause in item.clauses
            if clause.is_conclusion_correct
        )
        incorrect_conclusions = total_clauses - correct_conclusions

        # 5. 收集错误
        errors = self._collect_inspection_errors(item_checks)

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

        for page_num, table_idx in tables:
            table_data = self.pdf_parser.extract_table_detailed(pdf_path, page_num, table_idx)

            if not table_data:
                continue

            # 获取列索引
            col_indices = self._get_column_indices(table_data.headers)

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

                # 处理续表：序号为空或者是续行时继承上一行
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
                # 更新结论：使用最后一行的结论（处理同一标准条款跨多行的情况）
                if row.conclusion:
                    items_dict[item_num]['clauses'][clause_num]['conclusion'] = row.conclusion

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

                # 核对结论
                is_correct = actual_conclusion == expected_conclusion

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
        2. 所有检验结果都为"——"、"/"或空白 -> "/"
        3. 其他情况（包含"符合要求"、任意文本或数字）-> "符合"
        
        注意：根据规格说明2.2节，"/"与空白等价
        """
        results = [r.inspection_result for r in requirements]

        # 优先级1: 判断是否包含 "不符合要求"
        if any('不符合' in r for r in results):
            return '不符合'

        # 优先级2: 判断是否全为 "——"、"/" 或空白（均视为不适用）
        na_values = {'——', '—', '/', '', None}
        if all(r in na_values or r is None for r in results):
            return '/'

        # 优先级3: 其他情况
        return '符合'

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
