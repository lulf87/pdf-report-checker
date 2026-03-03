"""
检验项目表格检测与解析模块的单元测试
"""

import pytest
from typing import List, Dict, Any

import sys
sys.path.insert(0, '/Users/lulingfeng/Documents/工作/开发/报告核对工具2026.2.9/python_backend')

from models.schemas import TableData
from services.inspection_item_checker import (
    InspectionItemChecker,
    InspectionTableRow,
    ConclusionStatus,
    NonEmptyFieldErrorCode,
    SerialNumberErrorCode,
    ContinuationMarkErrorCode
)


class TestInspectionTableDetection:
    """测试检验项目表格检测功能"""

    def test_detect_valid_inspection_table(self):
        """测试检测有效的检验项目表格"""
        checker = InspectionItemChecker()

        # 创建包含所有必需列的表格
        table_data = TableData(
            page_num=1,
            table_index=0,
            headers=['序号', '检验项目', '标准条款', '标准要求', '检验结果', '单项结论', '备注'],
            rows=[],
            row_count=0,
            col_count=7
        )

        assert checker._is_inspection_table(table_data) is True

    def test_detect_table_with_spaces_in_headers(self):
        """测试检测带空格的表头"""
        checker = InspectionItemChecker()

        table_data = TableData(
            page_num=1,
            table_index=0,
            headers=['序 号', '检验项目', '标准 条款', '标准要求', '检验结果', '单项结论', '备注'],
            rows=[],
            row_count=0,
            col_count=7
        )

        assert checker._is_inspection_table(table_data) is True

    def test_detect_invalid_table_missing_columns(self):
        """测试检测缺少列的表格"""
        checker = InspectionItemChecker()

        # 缺少"单项结论"列
        table_data = TableData(
            page_num=1,
            table_index=0,
            headers=['序号', '检验项目', '标准条款', '标准要求', '检验结果', '备注'],
            rows=[],
            row_count=0,
            col_count=6
        )

        assert checker._is_inspection_table(table_data) is False

    def test_detect_empty_table(self):
        """测试检测空表格"""
        checker = InspectionItemChecker()

        table_data = TableData(
            page_num=1,
            table_index=0,
            headers=[],
            rows=[],
            row_count=0,
            col_count=0
        )

        assert checker._is_inspection_table(table_data) is False

    def test_detect_none_table(self):
        """测试检测None"""
        checker = InspectionItemChecker()
        assert checker._is_inspection_table(None) is False


class TestColumnIndices:
    """测试列索引查找功能"""

    def test_find_all_column_indices(self):
        """测试查找所有列索引"""
        checker = InspectionItemChecker()

        headers = ['序号', '检验项目', '标准条款', '标准要求', '检验结果', '单项结论', '备注']
        indices = checker._get_column_indices(headers)

        assert indices['序号'] == 0
        assert indices['检验项目'] == 1
        assert indices['标准条款'] == 2
        assert indices['标准要求'] == 3
        assert indices['检验结果'] == 4
        assert indices['单项结论'] == 5
        assert indices['备注'] == 6

    def test_find_column_indices_with_partial_headers(self):
        """测试查找部分列索引"""
        checker = InspectionItemChecker()

        headers = ['序号', '检验项目', '标准条款']
        indices = checker._get_column_indices(headers)

        assert '序号' in indices
        assert '检验项目' in indices
        assert '标准条款' in indices
        assert '标准要求' not in indices


class TestContinuationDetection:
    """测试续表检测功能"""

    def test_detect_continuation_xu(self):
        """测试检测'续'标记"""
        checker = InspectionItemChecker()
        assert checker.is_continuation_table("检验报告 续") is True

    def test_detect_continuation_xubiao(self):
        """测试检测'续表'标记"""
        checker = InspectionItemChecker()
        assert checker.is_continuation_table("续表") is True
        assert checker.is_continuation_table("续表1") is True
        assert checker.is_continuation_table("续表 2") is True

    def test_detect_continuation_xushangbiao(self):
        """测试检测'续上表'标记"""
        checker = InspectionItemChecker()
        assert checker.is_continuation_table("续上表") is True

    def test_detect_not_continuation(self):
        """测试非续表"""
        checker = InspectionItemChecker()
        assert checker.is_continuation_table("检验报告") is False
        assert checker.is_continuation_table("") is False
        assert checker.is_continuation_table(None) is False


class TestConclusionCalculation:
    """测试单项结论计算功能"""

    def test_conclusion_fail_priority(self):
        """测试'不符合'优先级最高"""
        checker = InspectionItemChecker()

        # 包含"不符合要求"应该返回"不符合"
        from services.inspection_item_checker import InspectionTableRow
        rows = [
            InspectionTableRow(
                item_number='1', item_name='测试项目', clause_number='5.1',
                requirement_text='要求1', inspection_result='符合要求',
                conclusion='', remark=''
            ),
            InspectionTableRow(
                item_number='1', item_name='测试项目', clause_number='5.1',
                requirement_text='要求2', inspection_result='不符合要求',
                conclusion='', remark=''
            )
        ]

        from services.inspection_item_checker import RequirementCheck
        requirements = [
            RequirementCheck(requirement_text=r.requirement_text,
                           inspection_result=r.inspection_result,
                           remark=r.remark)
            for r in rows
        ]

        result = checker._calculate_expected_conclusion(requirements)
        assert result == ConclusionStatus.FAIL

    def test_conclusion_na_when_all_dash(self):
        """测试全部为'——'时返回'/'"""
        checker = InspectionItemChecker()

        from services.inspection_item_checker import RequirementCheck
        requirements = [
            RequirementCheck(requirement_text='要求1', inspection_result='——', remark=''),
            RequirementCheck(requirement_text='要求2', inspection_result='——', remark='')
        ]

        result = checker._calculate_expected_conclusion(requirements)
        assert result == ConclusionStatus.NA

    def test_conclusion_na_when_all_empty(self):
        """测试全部为空时返回'/'"""
        checker = InspectionItemChecker()

        from services.inspection_item_checker import RequirementCheck
        requirements = [
            RequirementCheck(requirement_text='要求1', inspection_result='', remark=''),
            RequirementCheck(requirement_text='要求2', inspection_result='', remark='')
        ]

        result = checker._calculate_expected_conclusion(requirements)
        assert result == ConclusionStatus.NA

    def test_conclusion_na_when_dash(self):
        """测试检验结果为'——'时返回'/'（但'/'和'符合'都视为正确）"""
        checker = InspectionItemChecker()

        from services.inspection_item_checker import RequirementCheck
        # 检验结果为"——"（不适用）
        requirements = [
            RequirementCheck(requirement_text='要求1', inspection_result='——', remark='/')
        ]

        result = checker._calculate_expected_conclusion(requirements)
        # 期望值为"/"，但实际标记为"符合"也视为正确
        assert result == ConclusionStatus.NA  # 返回"/"作为期望值

    def test_is_conclusion_valid_with_na_and_pass(self):
        """测试当期望为'/'时，'符合'也视为正确（误报修复）"""
        checker = InspectionItemChecker()

        # 实际为"/"，期望为"/" -> 正确
        assert checker._is_conclusion_valid('/', '/') is True

        # 实际为"符合"，期望为"/" -> 也视为正确（误报修复）
        assert checker._is_conclusion_valid('符合', '/') is True

        # 实际为"/"，期望为"符合" -> 不正确
        assert checker._is_conclusion_valid('/', '符合') is False

        # 实际为"符合"，期望为"符合" -> 正确
        assert checker._is_conclusion_valid('符合', '符合') is True

    def test_conclusion_pass_when_mixed(self):
        """测试混合情况返回'符合'"""
        checker = InspectionItemChecker()

        from services.inspection_item_checker import RequirementCheck
        requirements = [
            RequirementCheck(requirement_text='要求1', inspection_result='符合要求', remark=''),
            RequirementCheck(requirement_text='要求2', inspection_result='——', remark='')
        ]

        result = checker._calculate_expected_conclusion(requirements)
        assert result == ConclusionStatus.PASS

    def test_conclusion_pass_with_number(self):
        """测试数字结果返回'符合'"""
        checker = InspectionItemChecker()

        from services.inspection_item_checker import RequirementCheck
        requirements = [
            RequirementCheck(requirement_text='要求1', inspection_result='100', remark=''),
            RequirementCheck(requirement_text='要求2', inspection_result='——', remark='')
        ]

        result = checker._calculate_expected_conclusion(requirements)
        assert result == ConclusionStatus.PASS

    def test_conclusion_pass_with_text(self):
        """测试文本结果返回'符合'"""
        checker = InspectionItemChecker()

        from services.inspection_item_checker import RequirementCheck
        requirements = [
            RequirementCheck(requirement_text='要求1', inspection_result='测试文本', remark=''),
            RequirementCheck(requirement_text='要求2', inspection_result='——', remark='')
        ]

        result = checker._calculate_expected_conclusion(requirements)
        assert result == ConclusionStatus.PASS

    def test_conclusion_empty_requirements(self):
        """测试空要求列表返回'/'"""
        checker = InspectionItemChecker()

        result = checker._calculate_expected_conclusion([])
        assert result == ConclusionStatus.NA


class TestTableParsing:
    """测试表格解析功能"""

    def test_parse_simple_table(self):
        """测试解析简单表格"""
        checker = InspectionItemChecker()

        table_data = TableData(
            page_num=1,
            table_index=0,
            headers=['序号', '检验项目', '标准条款', '标准要求', '检验结果', '单项结论', '备注'],
            rows=[
                ['1', '外观检查', '5.1', '外观完好', '符合要求', '符合', ''],
                ['2', '尺寸检查', '5.2', '尺寸达标', '符合要求', '符合', '']
            ],
            row_count=2,
            col_count=7
        )

        items = checker.parse_inspection_table(table_data)

        assert len(items) == 2
        assert items[0].item_number == '1'
        assert items[0].item_name == '外观检查'
        assert len(items[0].clauses) == 1

    def test_parse_multi_clause_item(self):
        """测试解析多条款项目"""
        checker = InspectionItemChecker()

        table_data = TableData(
            page_num=1,
            table_index=0,
            headers=['序号', '检验项目', '标准条款', '标准要求', '检验结果', '单项结论', '备注'],
            rows=[
                ['1', '性能测试', '5.1.1', '性能A达标', '符合要求', '符合', ''],
                ['', '', '5.1.2', '性能B达标', '符合要求', '符合', '']
            ],
            row_count=2,
            col_count=7
        )

        items = checker.parse_inspection_table(table_data)

        assert len(items) == 1
        assert len(items[0].clauses) == 2
        assert items[0].clauses[0].clause_number == '5.1.1'
        assert items[0].clauses[1].clause_number == '5.1.2'

    def test_parse_continuation_row(self):
        """测试解析续行（序号为空）"""
        checker = InspectionItemChecker()

        table_data = TableData(
            page_num=1,
            table_index=0,
            headers=['序号', '检验项目', '标准条款', '标准要求', '检验结果', '单项结论', '备注'],
            rows=[
                ['1', '综合测试', '5.1', '要求1', '符合要求', '符合', ''],
                ['', '', '', '要求2', '符合要求', '符合', ''],
                ['2', '单独测试', '5.2', '要求3', '符合要求', '符合', '']
            ],
            row_count=3,
            col_count=7
        )

        items = checker.parse_inspection_table(table_data)

        assert len(items) == 2
        assert items[0].item_number == '1'
        assert len(items[0].clauses[0].requirements) == 2


class TestConclusionChecking:
    """测试单项结论核对功能"""

    def test_correct_conclusion(self):
        """测试正确结论"""
        checker = InspectionItemChecker()

        from services.inspection_item_checker import InspectionItemCheck, ClauseCheck, RequirementCheck

        items = [
            InspectionItemCheck(
                item_number='1',
                item_name='测试项目',
                clauses=[
                    ClauseCheck(
                        clause_number='5.1',
                        requirements=[
                            RequirementCheck(requirement_text='要求1', inspection_result='符合要求', remark='')
                        ],
                        conclusion='符合',
                        expected_conclusion='',
                        is_conclusion_correct=False
                    )
                ],
                issues=[],
                status='pass'
            )
        ]

        correct, incorrect, errors = checker.check_conclusions(items)

        assert correct == 1
        assert incorrect == 0
        assert len(errors) == 0
        assert items[0].clauses[0].is_conclusion_correct is True

    def test_incorrect_conclusion(self):
        """测试错误结论"""
        checker = InspectionItemChecker()

        from services.inspection_item_checker import InspectionItemCheck, ClauseCheck, RequirementCheck

        items = [
            InspectionItemCheck(
                item_number='1',
                item_name='测试项目',
                clauses=[
                    ClauseCheck(
                        clause_number='5.1',
                        requirements=[
                            RequirementCheck(requirement_text='要求1', inspection_result='——', remark='')
                        ],
                        conclusion='符合',
                        expected_conclusion='',
                        is_conclusion_correct=False
                    )
                ],
                issues=[],
                status='pass'
            )
        ]

        correct, incorrect, errors = checker.check_conclusions(items)

        assert correct == 0
        assert incorrect == 1
        assert len(errors) == 1
        assert items[0].clauses[0].is_conclusion_correct is False
        assert items[0].clauses[0].expected_conclusion == '/'

    def test_error_code_generation(self):
        """测试错误代码生成"""
        checker = InspectionItemChecker()

        # 应标为"/"但标为其他
        code = checker._get_error_code('/', '符合')
        assert code == 'CONCLUSION_MISMATCH_001'

        # 应标为"符合"但标为其他
        code = checker._get_error_code('符合', '/')
        assert code == 'CONCLUSION_MISMATCH_002'

        # 应标为"不符合"但标为其他
        code = checker._get_error_code('不符合', '符合')
        assert code == 'CONCLUSION_MISMATCH_003'


class TestTableMerging:
    """测试表格合并功能"""

    def test_merge_single_table(self):
        """测试单表格不合并"""
        checker = InspectionItemChecker()

        table_data = TableData(
            page_num=1,
            table_index=0,
            headers=['序号', '检验项目', '标准条款', '标准要求', '检验结果', '单项结论', '备注'],
            rows=[['1', '测试', '5.1', '要求', '符合', '符合', '']],
            row_count=1,
            col_count=7
        )

        tables = [(1, 0, table_data)]
        pages = []

        merged = checker.merge_continuation_tables(tables, pages)

        assert len(merged) == 1
        assert merged[0][0] == 1

    def test_merge_continuation_tables(self):
        """测试合并续表"""
        checker = InspectionItemChecker()

        table1 = TableData(
            page_num=1,
            table_index=0,
            headers=['序号', '检验项目', '标准条款', '标准要求', '检验结果', '单项结论', '备注'],
            rows=[['1', '测试1', '5.1', '要求1', '符合', '符合', '']],
            row_count=1,
            col_count=7
        )

        table2 = TableData(
            page_num=2,
            table_index=0,
            headers=['序号', '检验项目', '标准条款', '标准要求', '检验结果', '单项结论', '备注'],
            rows=[['2', '测试2', '5.2', '要求2', '符合', '符合', '']],
            row_count=1,
            col_count=7
        )

        tables = [(1, 0, table1), (2, 0, table2)]

        # 模拟PageInfo
        class MockPageInfo:
            def __init__(self, page_num, text_content):
                self.page_num = page_num
                self.text_content = text_content

        pages = [
            MockPageInfo(1, "检验报告"),
            MockPageInfo(2, "续表")  # 第二页有续表标记
        ]

        merged = checker.merge_continuation_tables(tables, pages)

        assert len(merged) == 1
        assert merged[0][1].row_count == 2


class TestEdgeCases:
    """测试边界情况"""

    def test_empty_table_data(self):
        """测试空表格数据"""
        checker = InspectionItemChecker()

        table_data = TableData(
            page_num=1,
            table_index=0,
            headers=['序号', '检验项目', '标准条款', '标准要求', '检验结果', '单项结论', '备注'],
            rows=[],
            row_count=0,
            col_count=7
        )

        items = checker.parse_inspection_table(table_data)
        assert len(items) == 0

    def test_table_with_empty_rows(self):
        """测试包含空行的表格"""
        checker = InspectionItemChecker()

        table_data = TableData(
            page_num=1,
            table_index=0,
            headers=['序号', '检验项目', '标准条款', '标准要求', '检验结果', '单项结论', '备注'],
            rows=[
                ['1', '测试', '5.1', '要求', '符合', '符合', ''],
                ['', '', '', '', '', '', ''],
                ['2', '测试2', '5.2', '要求2', '符合', '符合', '']
            ],
            row_count=3,
            col_count=7
        )

        items = checker.parse_inspection_table(table_data)
        assert len(items) == 2

    def test_extract_number_sorting(self):
        """测试数字提取排序"""
        checker = InspectionItemChecker()

        assert checker._extract_number('1') == 1
        assert checker._extract_number('10') == 10
        assert checker._extract_number('A5') == 5
        assert checker._extract_number('12A') == 12
        assert checker._extract_number('ABC') == 0
        assert checker._extract_number('') == 0


class TestNonEmptyFieldValidation:
    """测试非空字段校验功能 (v2.2新增)"""

    def test_all_fields_filled(self):
        """测试所有字段都有值的情况"""
        checker = InspectionItemChecker()

        rows = [
            InspectionTableRow(
                item_number='1',
                item_name='测试项目',
                clause_number='5.1',
                requirement_text='要求1',
                inspection_result='符合要求',
                conclusion='符合',
                remark='无'
            )
        ]

        errors = checker._check_non_empty_fields(rows)
        assert len(errors) == 0

    def test_empty_inspection_result(self):
        """测试检验结果为空的情况"""
        checker = InspectionItemChecker()

        rows = [
            InspectionTableRow(
                item_number='1',
                item_name='测试项目',
                clause_number='5.1',
                requirement_text='要求1',
                inspection_result='',  # 空
                conclusion='符合',
                remark='无'
            )
        ]

        errors = checker._check_non_empty_fields(rows)
        assert len(errors) == 1
        assert errors[0].details['error_code'] == NonEmptyFieldErrorCode.EMPTY_INSPECTION_RESULT

    def test_empty_conclusion(self):
        """测试单项结论为空的情况"""
        checker = InspectionItemChecker()

        rows = [
            InspectionTableRow(
                item_number='1',
                item_name='测试项目',
                clause_number='5.1',
                requirement_text='要求1',
                inspection_result='符合要求',
                conclusion='',  # 空
                remark='无'
            )
        ]

        errors = checker._check_non_empty_fields(rows)
        assert len(errors) == 1
        assert errors[0].details['error_code'] == NonEmptyFieldErrorCode.EMPTY_CONCLUSION

    def test_empty_remark(self):
        """测试备注为空的情况"""
        checker = InspectionItemChecker()

        rows = [
            InspectionTableRow(
                item_number='1',
                item_name='测试项目',
                clause_number='5.1',
                requirement_text='要求1',
                inspection_result='符合要求',
                conclusion='符合',
                remark=''  # 空
            )
        ]

        errors = checker._check_non_empty_fields(rows)
        assert len(errors) == 1
        assert errors[0].details['error_code'] == NonEmptyFieldErrorCode.EMPTY_REMARK

    def test_all_fields_empty(self):
        """测试所有字段都为空的情况"""
        checker = InspectionItemChecker()

        rows = [
            InspectionTableRow(
                item_number='1',
                item_name='测试项目',
                clause_number='5.1',
                requirement_text='要求1',
                inspection_result='',  # 空
                conclusion='',  # 空
                remark=''  # 空
            )
        ]

        errors = checker._check_non_empty_fields(rows)
        assert len(errors) == 3
        error_codes = [e.details['error_code'] for e in errors]
        assert NonEmptyFieldErrorCode.EMPTY_INSPECTION_RESULT in error_codes
        assert NonEmptyFieldErrorCode.EMPTY_CONCLUSION in error_codes
        assert NonEmptyFieldErrorCode.EMPTY_REMARK in error_codes

    def test_na_values_not_empty(self):
        """测试"/"、"——"表示"不适用"的值不应被视为空，但"-"、"—"应被视为空"""
        checker = InspectionItemChecker()

        # "/" 和 "——" 是合法的"不适用"标记
        legal_values = ['/', '——']
        for val in legal_values:
            rows = [
                InspectionTableRow(
                    item_number='59',
                    item_name='测试项目',
                    clause_number='8.7',
                    requirement_text='要求1',
                    inspection_result=val,
                    conclusion='/',
                    remark='/'
                )
            ]
            errors = checker._check_non_empty_fields(rows)
            assert len(errors) == 0, f"'{val}' 不应被视为空值，但报错了"

        # "-"、"—" 应被视为非法值（空值）
        illegal_values = ['-', '—']
        for val in illegal_values:
            rows = [
                InspectionTableRow(
                    item_number='59',
                    item_name='测试项目',
                    clause_number='8.7',
                    requirement_text='要求1',
                    inspection_result=val,
                    conclusion='/',
                    remark='/'
                )
            ]
            errors = checker._check_non_empty_fields(rows)
            assert len(errors) > 0, f"'{val}' 应被视为空值，但没有报错"
            assert NonEmptyFieldErrorCode.EMPTY_INSPECTION_RESULT in [e.details['error_code'] for e in errors]

    def test_cross_page_continuation_scenarios(self):
        """测试跨页续表的四种情况（用户定义的规则）"""
        checker = InspectionItemChecker()

        # 情况1: 前一页非空内容，后一页"——"
        # 预期：不报错（都有值，只是类型不同）
        rows_case1 = [
            InspectionTableRow(
                item_number='113', item_name='测试项目', clause_number='201.7.8.1',
                requirement_text='要求1', inspection_result='符合要求',  # 非空内容
                conclusion='符合', remark='无', page_num=80
            ),
            InspectionTableRow(
                item_number='113', item_name='测试项目', clause_number='201.7.8.1',
                requirement_text='要求2', inspection_result='——',  # 不适用标记
                conclusion='/', remark='——', page_num=81  # 跨页
            ),
        ]
        errors = checker._check_non_empty_fields(rows_case1)
        assert len(errors) == 0, f"情况1应该不报错，但报错了: {[e.message for e in errors]}"

        # 情况2: 前一页"——"，后一页非空内容
        # 预期：不报错
        rows_case2 = [
            InspectionTableRow(
                item_number='113', item_name='测试项目', clause_number='201.7.8.1',
                requirement_text='要求1', inspection_result='——',
                conclusion='/', remark='——', page_num=80
            ),
            InspectionTableRow(
                item_number='113', item_name='测试项目', clause_number='201.7.8.1',
                requirement_text='要求2', inspection_result='0.05',  # 非空内容
                conclusion='符合', remark='正常', page_num=81  # 跨页
            ),
        ]
        errors = checker._check_non_empty_fields(rows_case2)
        assert len(errors) == 0, f"情况2应该不报错，但报错了: {[e.message for e in errors]}"

        # 情况3: 前一页和后一页都是"——"
        # 预期：不报错（"——"是合法的不适用标记）
        rows_case3 = [
            InspectionTableRow(
                item_number='113', item_name='测试项目', clause_number='201.7.8.1',
                requirement_text='要求1', inspection_result='——',
                conclusion='/', remark='——', page_num=80
            ),
            InspectionTableRow(
                item_number='113', item_name='测试项目', clause_number='201.7.8.1',
                requirement_text='要求2', inspection_result='——',
                conclusion='/', remark='——', page_num=81  # 跨页
            ),
        ]
        errors = checker._check_non_empty_fields(rows_case3)
        assert len(errors) == 0, f"情况3应该不报错，但报错了: {[e.message for e in errors]}"

        # 情况4: 前一页或后一页有任何一个是真正的空值（不是"——"）
        # 预期：报错
        rows_case4 = [
            InspectionTableRow(
                item_number='113', item_name='测试项目', clause_number='201.7.8.1',
                requirement_text='要求1', inspection_result='——',
                conclusion='/', remark='——', page_num=80
            ),
            InspectionTableRow(
                item_number='113', item_name='测试项目', clause_number='201.7.8.1',
                requirement_text='要求2', inspection_result='',  # 真正的空值！
                conclusion='', remark='', page_num=81  # 跨页
            ),
        ]
        errors = checker._check_non_empty_fields(rows_case4)
        assert len(errors) > 0, "情况4应该报错（有真正的空值），但没有报错"
        # 应该报检验结果为空
        error_codes = [e.details['error_code'] for e in errors]
        assert NonEmptyFieldErrorCode.EMPTY_INSPECTION_RESULT in error_codes

    def test_cross_multiple_pages_same_item(self):
        """测试同一序号跨多页（如5-6页都是同一序号）所有行都独立检查"""
        checker = InspectionItemChecker()

        # 序号59跨第5页和第6页，每页有多行
        rows = [
            # 第5页第1行
            InspectionTableRow(
                item_number='59', item_name='测试项目', clause_number='8.7',
                requirement_text='要求1', inspection_result='——',
                conclusion='/', remark='——', page_num=5
            ),
            # 第5页第2行（同页，但跨页key所有行都独立）
            InspectionTableRow(
                item_number='59', item_name='测试项目', clause_number='8.7',
                requirement_text='要求2', inspection_result='',  # 真正的空值！
                conclusion='/', remark='——', page_num=5
            ),
            # 第6页第1行（跨页）
            InspectionTableRow(
                item_number='59', item_name='测试项目', clause_number='8.7',
                requirement_text='要求3', inspection_result='——',
                conclusion='/', remark='——', page_num=6
            ),
            # 第6页第2行（跨页）
            InspectionTableRow(
                item_number='59', item_name='测试项目', clause_number='8.7',
                requirement_text='要求4', inspection_result='0.01',
                conclusion='符合', remark='正常', page_num=6
            ),
        ]

        errors = checker._check_non_empty_fields(rows)
        # 应该只报第5页第2行的错误（真正的空值）
        assert len(errors) == 1, f"应该只报1个错误（第5页第2行空值），但报了{len(errors)}个: {[e.message for e in errors]}"
        assert errors[0].details['row_index'] == 1  # 第2行（索引1）
        assert NonEmptyFieldErrorCode.EMPTY_INSPECTION_RESULT in errors[0].details['error_code']

    def test_multi_level_table_title_row(self):
        """测试多级表格标题行（父行无检验结果，子行有）不应报错"""
        checker = InspectionItemChecker()

        # 模拟序号59的情况：标题行 + 多个子行
        rows = [
            # 标题行（父行）：无检验结果
            InspectionTableRow(
                item_number='59',
                item_name='漏电流和患者辅助电流的测量（潮湿预处理前）',
                clause_number='8.7',
                requirement_text='漏电流和患者辅助电流的测量（潮湿预处理前） 单位：mA',
                inspection_result='',  # 空，因为标题行本身无检验结果
                conclusion='',
                remark=''
            ),
            # 子行1：有检验结果
            InspectionTableRow(
                item_number='59',
                item_name='漏电流和患者辅助电流的测量（潮湿预处理前）',
                clause_number='8.7',
                requirement_text='无频率加权漏电流',
                inspection_result='——',
                conclusion='/',
                remark='——'
            ),
            # 子行2：有检验结果
            InspectionTableRow(
                item_number='59',
                item_name='漏电流和患者辅助电流的测量（潮湿预处理前）',
                clause_number='8.7',
                requirement_text='对地漏电流（正常状态）',
                inspection_result='——',
                conclusion='/',
                remark='——'
            ),
            # 子行3：有检验结果
            InspectionTableRow(
                item_number='59',
                item_name='漏电流和患者辅助电流的测量（潮湿预处理前）',
                clause_number='8.7',
                requirement_text='对地漏电流（单一故障状态）',
                inspection_result='——',
                conclusion='/',
                remark='——'
            ),
        ]

        errors = checker._check_non_empty_fields(rows)
        # 标题行不应报错，只有子行会被检查
        # 所有子行的检验结果都是"——"（合法值），所以不应报错
        assert len(errors) == 0, f"标题行不应报错，但报错了: {[e.message for e in errors]}"

    def test_merged_cell_inheritance(self):
        """测试合并单元格场景：每行独立检查，不继承值"""
        checker = InspectionItemChecker()

        rows = [
            # 首行有值
            InspectionTableRow(
                item_number='1',
                item_name='测试项目',
                clause_number='5.1',
                requirement_text='要求1',
                inspection_result='符合要求',
                conclusion='符合',
                remark='正常'
            ),
            # 续行（合并单元格），但检验结果是"——"（合法值）
            InspectionTableRow(
                item_number='1',
                item_name='测试项目',
                clause_number='5.1',
                requirement_text='要求2',
                inspection_result='——',  # 合法的不适用标记
                conclusion='/',
                remark='——'
            )
        ]

        errors = checker._check_non_empty_fields(rows)
        # 每行都有值（第一行有实际值，第二行有"——"），不应该报错
        assert len(errors) == 0

    def test_merged_cell_empty_value(self):
        """测试合并单元格场景：续行是真正空值的情况（应报错）"""
        checker = InspectionItemChecker()

        rows = [
            # 首行有值
            InspectionTableRow(
                item_number='1',
                item_name='测试项目',
                clause_number='5.1',
                requirement_text='要求1',
                inspection_result='符合要求',
                conclusion='符合',
                remark='正常'
            ),
            # 续行为真正的空值（不是"——"）
            InspectionTableRow(
                item_number='1',
                item_name='测试项目',
                clause_number='5.1',
                requirement_text='要求2',
                inspection_result='',  # 真正的空值
                conclusion='',  # 真正的空值
                remark=''  # 真正的空值
            )
        ]

        errors = checker._check_non_empty_fields(rows)
        # 续行是真正的空值，应该报错（不继承首行的值）
        assert len(errors) == 3  # 续行的3个字段都为空

    def test_merged_cell_first_row_empty(self):
        """测试合并单元格首行为空的情况（每行独立检查）"""
        checker = InspectionItemChecker()

        rows = [
            # 首行为空
            InspectionTableRow(
                item_number='1',
                item_name='测试项目',
                clause_number='5.1',
                requirement_text='要求1',
                inspection_result='',  # 首行为空
                conclusion='',  # 首行为空
                remark=''  # 首行为空
            ),
            # 续行也为空
            InspectionTableRow(
                item_number='1',
                item_name='测试项目',
                clause_number='5.1',
                requirement_text='要求2',
                inspection_result='',  # 空
                conclusion='',  # 空
                remark=''  # 空
            )
        ]

        errors = checker._check_non_empty_fields(rows)
        # 每行独立检查，所有空字段都报错
        assert len(errors) == 6  # 2行 x 3个字段

    def test_extreme_cross_page_scenario(self):
        """
        测试极端跨页场景：
        序号1在第一页有10行，第1行="符合要求"，其余9行="——"
        第3-4页续1各="——"
        结论：单项结论应为"符合"（因为有一个非NA值）
        """
        checker = InspectionItemChecker()

        rows = [
            # 第1页 - 第1行：有实际值
            InspectionTableRow(
                item_number='1', item_name='测试项目', clause_number='5.1',
                requirement_text='要求1', inspection_result='符合要求',
                conclusion='符合', remark='正常', page_num=1
            ),
            # 第1页 - 第2-10行：都是"——"
            InspectionTableRow(
                item_number='1', item_name='测试项目', clause_number='5.1',
                requirement_text='要求2', inspection_result='——',
                conclusion='/', remark='——', page_num=1
            ),
            InspectionTableRow(
                item_number='1', item_name='测试项目', clause_number='5.1',
                requirement_text='要求3', inspection_result='——',
                conclusion='/', remark='——', page_num=1
            ),
            # ... 省略中间行
            InspectionTableRow(
                item_number='1', item_name='测试项目', clause_number='5.1',
                requirement_text='要求10', inspection_result='——',
                conclusion='/', remark='——', page_num=1
            ),
            # 第3页续1
            InspectionTableRow(
                item_number='1', item_name='测试项目', clause_number='5.1',
                requirement_text='要求11', inspection_result='——',
                conclusion='/', remark='——', page_num=3
            ),
            # 第4页续1
            InspectionTableRow(
                item_number='1', item_name='测试项目', clause_number='5.1',
                requirement_text='要求12', inspection_result='——',
                conclusion='/', remark='——', page_num=4
            ),
        ]

        # 非空字段校验：每行都有值（"符合要求"或"——"），不应报错
        errors = checker._check_non_empty_fields(rows)
        assert len(errors) == 0, f"所有行都有值，不应报错: {[e.message for e in errors]}"

        # 单项结论计算：基于所有行汇总
        item_checks = checker._check_items(rows)
        assert len(item_checks) == 1
        assert len(item_checks[0].clauses) == 1

        # 期望结论："符合"（因为有一个非NA值"符合要求"）
        expected = item_checks[0].clauses[0].expected_conclusion
        assert expected == '符合', f"期望结论应为'符合'，实际为'{expected}'"

    def test_multiple_items_with_different_clauses(self):
        """测试多个项目不同条款的情况"""
        checker = InspectionItemChecker()

        rows = [
            # 项目1 条款5.1 - 完整
            InspectionTableRow(
                item_number='1',
                item_name='项目1',
                clause_number='5.1',
                requirement_text='要求1',
                inspection_result='符合要求',
                conclusion='符合',
                remark='无'
            ),
            # 项目1 条款5.2 - 检验结果为空
            InspectionTableRow(
                item_number='1',
                item_name='项目1',
                clause_number='5.2',
                requirement_text='要求2',
                inspection_result='',  # 空
                conclusion='符合',
                remark='无'
            ),
            # 项目2 条款5.1 - 完整
            InspectionTableRow(
                item_number='2',
                item_name='项目2',
                clause_number='5.1',
                requirement_text='要求3',
                inspection_result='符合要求',
                conclusion='符合',
                remark='无'
            )
        ]

        errors = checker._check_non_empty_fields(rows)
        assert len(errors) == 1
        assert errors[0].details['item_number'] == '1'
        assert errors[0].details['clause_number'] == '5.2'

    def test_error_message_format(self):
        """测试错误消息格式"""
        checker = InspectionItemChecker()

        rows = [
            InspectionTableRow(
                item_number='5',
                item_name='外观检查',
                clause_number='5.1.1',
                requirement_text='表面应光洁',
                inspection_result='',  # 空
                conclusion='符合',
                remark='无'
            )
        ]

        errors = checker._check_non_empty_fields(rows)
        assert len(errors) == 1
        assert '序号 5' in errors[0].message
        assert '标准条款 5.1.1' in errors[0].message
        assert '检验结果为空' in errors[0].message
        assert errors[0].level == 'ERROR'
        assert '外观检查' in errors[0].location


class TestSerialNumberContinuity:
    """测试序号连续性校验功能 (v2.2新增)"""

    def test_continuous_serial_numbers(self):
        """测试连续的序号（正常情况）"""
        checker = InspectionItemChecker()

        rows = [
            InspectionTableRow(
                item_number='1', item_name='项目1', clause_number='5.1',
                requirement_text='要求1', inspection_result='符合', conclusion='符合', remark='无',
                page_num=1, row_index=0, is_first_row_in_page=True,
                original_item_number='1', has_continuation_mark=False
            ),
            InspectionTableRow(
                item_number='2', item_name='项目2', clause_number='5.2',
                requirement_text='要求2', inspection_result='符合', conclusion='符合', remark='无',
                page_num=1, row_index=1, is_first_row_in_page=False,
                original_item_number='2', has_continuation_mark=False
            ),
            InspectionTableRow(
                item_number='3', item_name='项目3', clause_number='5.3',
                requirement_text='要求3', inspection_result='符合', conclusion='符合', remark='无',
                page_num=1, row_index=2, is_first_row_in_page=False,
                original_item_number='3', has_continuation_mark=False
            )
        ]

        errors = checker._check_serial_number_continuity(rows)
        assert len(errors) == 0

    def test_discontinuous_serial_numbers(self):
        """测试不连续的序号（跳号）"""
        checker = InspectionItemChecker()

        rows = [
            InspectionTableRow(
                item_number='1', item_name='项目1', clause_number='5.1',
                requirement_text='要求1', inspection_result='符合', conclusion='符合', remark='无',
                page_num=1, row_index=0, is_first_row_in_page=True,
                original_item_number='1', has_continuation_mark=False
            ),
            InspectionTableRow(
                item_number='3', item_name='项目3', clause_number='5.3',
                requirement_text='要求3', inspection_result='符合', conclusion='符合', remark='无',
                page_num=1, row_index=1, is_first_row_in_page=False,
                original_item_number='3', has_continuation_mark=False
            )
        ]

        errors = checker._check_serial_number_continuity(rows)
        assert len(errors) == 1
        assert errors[0].details['error_code'] == SerialNumberErrorCode.NOT_CONTINUOUS
        assert errors[0].details['expected'] == 2
        assert errors[0].details['actual'] == 3

    def test_empty_serial_number(self):
        """测试序号为空的情况"""
        checker = InspectionItemChecker()

        rows = [
            InspectionTableRow(
                item_number='1', item_name='项目1', clause_number='5.1',
                requirement_text='要求1', inspection_result='符合', conclusion='符合', remark='无',
                page_num=1, row_index=0, is_first_row_in_page=True,
                original_item_number='1', has_continuation_mark=False
            ),
            InspectionTableRow(
                item_number='', item_name='项目2', clause_number='5.2',
                requirement_text='要求2', inspection_result='符合', conclusion='符合', remark='无',
                page_num=1, row_index=1, is_first_row_in_page=False,
                original_item_number='', has_continuation_mark=False
            )
        ]

        errors = checker._check_serial_number_continuity(rows)
        # 应该报告序号为空错误
        empty_errors = [e for e in errors if e.details['error_code'] == SerialNumberErrorCode.EMPTY]
        assert len(empty_errors) == 1

    def test_continuation_mark_correct_position(self):
        """测试续表标记在正确位置（第一行）"""
        checker = InspectionItemChecker()

        rows = [
            # 第1页最后一行
            InspectionTableRow(
                item_number='5', item_name='项目5', clause_number='5.1',
                requirement_text='要求1', inspection_result='符合', conclusion='符合', remark='无',
                page_num=1, row_index=0, is_first_row_in_page=False,
                original_item_number='5', has_continuation_mark=False
            ),
            # 第2页第一行，同一序号跨页，有续表标记
            InspectionTableRow(
                item_number='5', item_name='项目5', clause_number='5.2',
                requirement_text='要求2', inspection_result='符合', conclusion='符合', remark='无',
                page_num=2, row_index=1, is_first_row_in_page=True,
                original_item_number='续5', has_continuation_mark=True
            )
        ]

        errors = checker._check_serial_number_continuity(rows)
        # 有续表标记，不应该报错
        continuation_errors = [e for e in errors if 'CONTINUATION' in str(e.details.get('error_code', ''))]
        assert len(continuation_errors) == 0

    def test_missing_continuation_mark(self):
        """测试缺少续表标记的情况"""
        checker = InspectionItemChecker()

        rows = [
            # 第1页最后一行
            InspectionTableRow(
                item_number='5', item_name='项目5', clause_number='5.1',
                requirement_text='要求1', inspection_result='符合', conclusion='符合', remark='无',
                page_num=1, row_index=0, is_first_row_in_page=False,
                original_item_number='5', has_continuation_mark=False
            ),
            # 第2页第一行，同一序号跨页，但没有续表标记
            InspectionTableRow(
                item_number='5', item_name='项目5', clause_number='5.2',
                requirement_text='要求2', inspection_result='符合', conclusion='符合', remark='无',
                page_num=2, row_index=1, is_first_row_in_page=True,
                original_item_number='5', has_continuation_mark=False
            )
        ]

        errors = checker._check_serial_number_continuity(rows)
        # 应该报告缺少续表标记错误
        missing_mark_errors = [e for e in errors if e.details.get('error_code') == ContinuationMarkErrorCode.MISSING]
        assert len(missing_mark_errors) == 1
        assert '续5' in missing_mark_errors[0].details['expected_mark']

    def test_continuation_mark_wrong_position(self):
        """测试续表标记位置错误（不在第一行）"""
        checker = InspectionItemChecker()

        rows = [
            # 第1页
            InspectionTableRow(
                item_number='5', item_name='项目5', clause_number='5.1',
                requirement_text='要求1', inspection_result='符合', conclusion='符合', remark='无',
                page_num=1, row_index=0, is_first_row_in_page=True,
                original_item_number='5', has_continuation_mark=False
            ),
            # 第2页第一行，序号6（新序号）
            InspectionTableRow(
                item_number='6', item_name='项目6', clause_number='5.2',
                requirement_text='要求2', inspection_result='符合', conclusion='符合', remark='无',
                page_num=2, row_index=1, is_first_row_in_page=True,
                original_item_number='6', has_continuation_mark=False
            ),
            # 第2页第二行，有续表标记但不在第一行
            InspectionTableRow(
                item_number='5', item_name='项目5', clause_number='5.3',
                requirement_text='要求3', inspection_result='符合', conclusion='符合', remark='无',
                page_num=2, row_index=2, is_first_row_in_page=False,
                original_item_number='续5', has_continuation_mark=True
            )
        ]

        errors = checker._check_serial_number_continuity(rows)
        # 应该报告续字位置错误
        position_errors = [e for e in errors if e.details.get('error_code') == ContinuationMarkErrorCode.WRONG_POSITION]
        assert len(position_errors) == 1
        assert position_errors[0].details['is_first_row'] is False

    def test_multiple_pages_with_continuation(self):
        """测试多页跨页续表场景"""
        checker = InspectionItemChecker()

        rows = [
            # 第1页
            InspectionTableRow(
                item_number='1', item_name='项目1', clause_number='5.1',
                requirement_text='要求1', inspection_result='符合', conclusion='符合', remark='无',
                page_num=1, row_index=0, is_first_row_in_page=True,
                original_item_number='1', has_continuation_mark=False
            ),
            # 第2页，续项目1
            InspectionTableRow(
                item_number='1', item_name='项目1', clause_number='5.2',
                requirement_text='要求2', inspection_result='符合', conclusion='符合', remark='无',
                page_num=2, row_index=1, is_first_row_in_page=True,
                original_item_number='续1', has_continuation_mark=True
            ),
            # 第3页，续项目1
            InspectionTableRow(
                item_number='1', item_name='项目1', clause_number='5.3',
                requirement_text='要求3', inspection_result='符合', conclusion='符合', remark='无',
                page_num=3, row_index=2, is_first_row_in_page=True,
                original_item_number='续1', has_continuation_mark=True
            ),
            # 第3页，新项目2
            InspectionTableRow(
                item_number='2', item_name='项目2', clause_number='6.1',
                requirement_text='要求4', inspection_result='符合', conclusion='符合', remark='无',
                page_num=3, row_index=3, is_first_row_in_page=False,
                original_item_number='2', has_continuation_mark=False
            )
        ]

        errors = checker._check_serial_number_continuity(rows)
        # 所有续表标记都在正确位置，不应该有错误
        assert len(errors) == 0

    def test_continuation_with_empty_original_number(self):
        """测试原始序号为空的续表情况"""
        checker = InspectionItemChecker()

        rows = [
            # 第1页
            InspectionTableRow(
                item_number='5', item_name='项目5', clause_number='5.1',
                requirement_text='要求1', inspection_result='符合', conclusion='符合', remark='无',
                page_num=1, row_index=0, is_first_row_in_page=True,
                original_item_number='5', has_continuation_mark=False
            ),
            # 第2页，续项目5，原始序号为"续"（无数字）
            InspectionTableRow(
                item_number='5', item_name='项目5', clause_number='5.2',
                requirement_text='要求2', inspection_result='符合', conclusion='符合', remark='无',
                page_num=2, row_index=1, is_first_row_in_page=True,
                original_item_number='续', has_continuation_mark=True
            )
        ]

        errors = checker._check_serial_number_continuity(rows)
        # 有续表标记，不应该报错
        continuation_errors = [e for e in errors if 'CONTINUATION' in str(e.details.get('error_code', ''))]
        assert len(continuation_errors) == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
