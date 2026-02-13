"""
第三页扩展字段核对模块测试

测试覆盖：
1. 扩展字段提取
2. 字段名映射
3. 生产日期格式检测
4. 值比对逻辑
5. 完整核对流程
"""

import pytest
from typing import Dict, List, Any

from services.third_page_checker import (
    ThirdPageChecker, ThirdPageField, ThirdPageErrorCode
)
from models.schemas import FieldComparison, ErrorItem, OCRResult


class TestThirdPageFieldExtraction:
    """测试扩展字段提取"""

    def test_extract_extended_fields_basic(self):
        """测试基本字段提取"""
        checker = ThirdPageChecker()

        third_page_fields = {
            '委 托 方': '某公司',
            '样品名称': '测试产品',
            '型号规格': 'ABC-123',
            '生产日期': '2026.01.15',
            '产品编号/批号': 'LOT20260101'
        }

        result = checker._extract_extended_fields(third_page_fields)

        assert '型号规格' in result
        assert '生产日期' in result
        assert '产品编号/批号' in result

        assert result['型号规格'].value == 'ABC-123'
        assert result['生产日期'].value == '2026.01.15'
        assert result['产品编号/批号'].value == 'LOT20260101'

    def test_extract_extended_fields_synonyms(self):
        """测试同义字段名提取"""
        checker = ThirdPageChecker()

        # 使用变体字段名
        third_page_fields = {
            '规格型号': 'XYZ-456',  # 变体
            'MFG': '2026/02/20',  # 英文缩写
            '批号': 'BATCH001'  # 简化名
        }

        result = checker._extract_extended_fields(third_page_fields)

        assert '型号规格' in result
        assert '生产日期' in result
        assert '产品编号/批号' in result


class TestSampleDescriptionReference:
    """测试'见样品描述栏'检测"""

    def test_is_sample_description_reference_variants(self):
        """测试各种变体"""
        checker = ThirdPageChecker()

        variants = [
            '见"样品描述"栏',
            '见「样品描述」栏',
            '见『样品描述』栏',
            '见样品描述栏',
        ]

        for variant in variants:
            assert checker._is_sample_description_reference(variant), f"Failed for: {variant}"

    def test_is_sample_description_reference_negative(self):
        """测试非参考值"""
        checker = ThirdPageChecker()

        non_references = [
            'ABC-123',
            '2026.01.15',
            '见实物',
            '/',
            ''
        ]

        for value in non_references:
            assert not checker._is_sample_description_reference(value), f"Failed for: {value}"


class TestAlphanumericCheck:
    """测试数字字母组合检测"""

    def test_contains_alphanumeric(self):
        """测试包含数字和字母的值"""
        checker = ThirdPageChecker()

        valid_values = [
            'ABC123',
            'LOT20260101',
            'Model-X123',
            'SN123456'
        ]

        for value in valid_values:
            assert checker._contains_alphanumeric(value), f"Failed for: {value}"

    def test_not_contains_alphanumeric(self):
        """测试不包含数字字母组合的值"""
        checker = ThirdPageChecker()

        invalid_values = [
            '2026.01.15',  # 只有数字
            '见实物',  # 只有中文
            '/',  # 特殊字符
            ''  # 空值
        ]

        for value in invalid_values:
            assert not checker._contains_alphanumeric(value), f"Failed for: {value}"


class TestDateFormatDetection:
    """测试生产日期格式检测"""

    def test_detect_date_format_patterns(self):
        """测试各种日期格式"""
        checker = ThirdPageChecker()

        test_cases = [
            ('2026.01.15', 'YYYY.MM.DD'),
            ('2026/01/15', 'YYYY/MM/DD'),
            ('2026-01-15', 'YYYY-MM-DD'),
            ('2026年01月15日', 'YYYY年MM月DD日'),
            ('2026.01', 'YYYY.MM'),
            ('2026/01', 'YYYY/MM'),
        ]

        for date_str, expected_format in test_cases:
            result = checker._detect_date_format(date_str)
            assert result is not None, f"Failed to detect format for: {date_str}"
            assert result['name'] == expected_format, f"Wrong format for: {date_str}"

    def test_detect_date_format_invalid(self):
        """测试无效日期格式"""
        checker = ThirdPageChecker()

        invalid_dates = [
            'ABC123',
            '见实物',
            '/',
            ''
        ]

        for date_str in invalid_dates:
            result = checker._detect_date_format(date_str)
            assert result is None, f"Should be None for: {date_str}"


class TestFieldNameMapping:
    """测试字段名映射"""

    def test_model_spec_mapping(self):
        """测试型号规格映射"""
        checker = ThirdPageChecker()

        structured_data = {
            'model': {'value': 'ABC-123', 'confidence': 0.95},
            'spec': {'value': '规格值', 'confidence': 0.90}
        }

        result = checker._extract_label_field_value('型号规格', structured_data)
        assert result == 'ABC-123'

    def test_production_date_mapping(self):
        """测试生产日期映射"""
        checker = ThirdPageChecker()

        structured_data = {
            'MFG': {'value': '2026.01.15', 'confidence': 0.95},
            'production_date': {'value': '2026/02/20', 'confidence': 0.90}
        }

        result = checker._extract_label_field_value('生产日期', structured_data)
        assert result in ['2026.01.15', '2026/02/20']

    def test_batch_number_mapping(self):
        """测试批号映射"""
        checker = ThirdPageChecker()

        structured_data = {
            'LOT': {'value': 'LOT20260101', 'confidence': 0.95},
            'serial_number': {'value': 'SN123456', 'confidence': 0.90}
        }

        result = checker._extract_label_field_value('产品编号/批号', structured_data)
        assert result in ['LOT20260101', 'SN123456']


class TestValueComparison:
    """测试值比对逻辑"""

    def test_compare_values_exact_match(self):
        """测试精确匹配"""
        checker = ThirdPageChecker()

        assert checker._compare_values('ABC-123', 'ABC-123', '型号规格')
        assert checker._compare_values('2026.01.15', '2026.01.15', '生产日期')

    def test_compare_values_with_whitespace(self):
        """测试带空格的匹配"""
        checker = ThirdPageChecker()

        assert checker._compare_values('ABC-123', ' ABC-123 ', '型号规格')
        assert checker._compare_values('ABC 123', 'ABC123', '型号规格')

    def test_compare_values_batch_partial_match(self):
        """测试批号部分匹配"""
        checker = ThirdPageChecker()

        # 批号支持部分匹配
        assert checker._compare_values('LOT001', 'LOT001-Extra', '产品编号/批号')
        assert checker._compare_values('LOT001-Extra', 'LOT001', '产品编号/批号')

    def test_compare_values_no_match(self):
        """测试不匹配"""
        checker = ThirdPageChecker()

        assert not checker._compare_values('ABC-123', 'XYZ-456', '型号规格')
        assert not checker._compare_values('2026.01.15', '2026/01/15', '生产日期')


class TestConsistencyCheck:
    """测试一致性检查"""

    def test_all_reference_consistency(self):
        """测试所有字段都是'见样品描述栏'的情况"""
        checker = ThirdPageChecker()

        extended_fields = {
            '型号规格': ThirdPageField('型号规格', '见"样品描述"栏', 3),
            '生产日期': ThirdPageField('生产日期', '见"样品描述"栏', 3),
            '产品编号/批号': ThirdPageField('产品编号/批号', '见"样品描述"栏', 3)
        }

        result = checker._check_consistency(extended_fields)

        assert len(result['comparisons']) == 3
        assert all(comp.is_match for comp in result['comparisons'])
        assert result['error'] is None

    def test_inconsistent_reference(self):
        """测试不一致的参考值"""
        checker = ThirdPageChecker()

        extended_fields = {
            '型号规格': ThirdPageField('型号规格', '见"样品描述"栏', 3),
            '生产日期': ThirdPageField('生产日期', '2026.01.15', 3),  # 不一致
            '产品编号/批号': ThirdPageField('产品编号/批号', '见"样品描述"栏', 3)
        }

        result = checker._check_consistency(extended_fields)

        assert len(result['comparisons']) == 3
        assert not all(comp.is_match for comp in result['comparisons'])
        assert result['error'] is not None
        assert result['error'].level == 'ERROR'


class TestLabelMatching:
    """测试标签匹配"""

    def test_find_labels_by_sample_name_exact(self):
        """测试精确匹配"""
        checker = ThirdPageChecker()

        photo_labels = [
            {'subject_name': '测试产品', 'caption': '1: 测试产品 中文标签'},
            {'subject_name': '其他产品', 'caption': '2: 其他产品 中文标签'}
        ]

        result = checker._find_labels_by_sample_name('测试产品', photo_labels)

        assert len(result) == 1
        assert result[0]['subject_name'] == '测试产品'

    def test_find_labels_by_sample_name_containment(self):
        """测试包含匹配"""
        checker = ThirdPageChecker()

        photo_labels = [
            {'subject_name': '心脏脉冲电场消融仪-主机', 'caption': '1: 心脏脉冲电场消融仪-主机 中文标签'},
            {'subject_name': '心脏脉冲电场消融仪-推车', 'caption': '2: 心脏脉冲电场消融仪-推车 中文标签'}
        ]

        # 样品名称包含在标签主体名中
        result = checker._find_labels_by_sample_name('心脏脉冲电场消融仪', photo_labels)

        assert len(result) == 2


class TestDateFormatConsistency:
    """测试生产日期格式一致性"""

    def test_date_format_mismatch(self):
        """测试日期格式不匹配"""
        checker = ThirdPageChecker()

        # 表格值
        table_value = '2026.01.15'
        # 标签值（不同格式）
        label_value = '2026/01/15'

        table_format = checker._detect_date_format(table_value)
        label_format = checker._detect_date_format(label_value)

        assert table_format is not None
        assert label_format is not None
        assert table_format['pattern'] != label_format['pattern']

    def test_date_format_match(self):
        """测试日期格式匹配"""
        checker = ThirdPageChecker()

        table_value = '2026-01-15'
        label_value = '2026-01-15'

        table_format = checker._detect_date_format(table_value)
        label_format = checker._detect_date_format(label_value)

        assert table_format is not None
        assert label_format is not None
        assert table_format['pattern'] == label_format['pattern']


class TestFullCheckFlow:
    """测试完整核对流程"""

    def test_check_all_reference(self):
        """测试所有字段都是参考值的情况"""
        checker = ThirdPageChecker()

        third_page_fields = {
            '样品名称': '测试产品',
            '型号规格': '见"样品描述"栏',
            '生产日期': '见"样品描述"栏',
            '产品编号/批号': '见"样品描述"栏'
        }

        photo_labels = []

        comparisons, errors = checker.check_third_page_fields(
            third_page_fields, '测试产品', photo_labels
        )

        # 应该有一致性比对结果
        assert len(comparisons) == 3
        assert all(comp.is_match for comp in comparisons)
        assert len(errors) == 0

    def test_check_with_label_matching(self):
        """测试有标签匹配的情况"""
        checker = ThirdPageChecker()

        third_page_fields = {
            '样品名称': '测试产品',
            '型号规格': 'ABC-123',
            '生产日期': '2026.01.15',
            '产品编号/批号': 'LOT001'
        }

        photo_labels = [
            {
                'subject_name': '测试产品',
                'caption': '1: 测试产品 中文标签',
                'page_num': 5,
                'ocr_result': {
                    'structured_data': {
                        'model': {'value': 'ABC-123'},
                        'production_date': {'value': '2026.01.15'},
                        'LOT': {'value': 'LOT001'}
                    }
                }
            }
        ]

        comparisons, errors = checker.check_third_page_fields(
            third_page_fields, '测试产品', photo_labels
        )

        # 应该有比对结果
        assert len(comparisons) > 0
        # 应该没有错误（值匹配）
        assert len(errors) == 0

    def test_check_with_mismatch(self):
        """测试不匹配的情况"""
        checker = ThirdPageChecker()

        third_page_fields = {
            '样品名称': '测试产品',
            '型号规格': 'ABC-123',  # 表格值
            '生产日期': '2026.01.15'  # 表格值
        }

        photo_labels = [
            {
                'subject_name': '测试产品',
                'caption': '1: 测试产品 中文标签',
                'page_num': 5,
                'ocr_result': {
                    'structured_data': {
                        'model': {'value': 'XYZ-456'},  # 标签值不同
                        'production_date': {'value': '2026/01/15'}  # 格式不同
                    }
                }
            }
        ]

        comparisons, errors = checker.check_third_page_fields(
            third_page_fields, '测试产品', photo_labels
        )

        # 应该有错误（值不匹配或格式不匹配）
        assert len(errors) > 0
        # 检查错误代码
        error_codes = [e.details.get('error_code') for e in errors]
        assert ThirdPageErrorCode.FIELD_MISMATCH in error_codes or ThirdPageErrorCode.DATE_FORMAT_MISMATCH in error_codes


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
