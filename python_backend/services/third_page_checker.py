"""
第三页表格扩展字段核对模块
实现 REPORT_CHECKER_SPEC.md V2.2 中 3.3 节的扩展字段核对规则

功能：
1. 扩展字段核对（型号规格、生产日期、产品编号/批号）
2. 字段名映射（表格字段名与标签字段名的映射）
3. 生产日期格式一致性校验
"""

import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from models.schemas import FieldComparison, ErrorItem, OCRResult


class ThirdPageErrorCode(str, Enum):
    """第三页字段核对错误代码"""
    FIELD_MISMATCH = "THIRD_PAGE_FIELD_ERROR_001"  # 第三页字段与标签不一致
    DATE_FORMAT_MISMATCH = "DATE_FORMAT_ERROR_001"  # 生产日期格式不一致


@dataclass
class ThirdPageField:
    """第三页扩展字段"""
    name: str           # 字段名（表格中的名称）
    value: str          # 字段值
    page_num: int       # 所在页码


@dataclass
class LabelFieldMapping:
    """标签字段映射"""
    table_field: str           # 表格字段名
    label_field_synonyms: List[str]  # 标签上可能的字段名


class ThirdPageChecker:
    """第三页表格扩展字段核对器"""

    # 扩展字段列表（需要核对的字段）
    EXTENDED_FIELDS = ['型号规格', '生产日期', '产品编号/批号']

    # 字段名映射：表格字段名 -> 标签可能的字段名列表
    FIELD_NAME_MAPPING = {
        '型号规格': ['型号', '规格', '规格型号'],
        '生产日期': ['MFG', 'MFD', '生产日期'],
        '产品编号/批号': ['批号', 'LOT', '序列号', 'SN']
    }

    # 生产日期格式正则表达式
    DATE_FORMAT_PATTERNS = [
        (r'\d{4}\.\d{1,2}\.\d{1,2}', 'YYYY.MM.DD'),
        (r'\d{4}/\d{1,2}/\d{1,2}', 'YYYY/MM/DD'),
        (r'\d{4}-\d{1,2}-\d{1,2}', 'YYYY-MM-DD'),
        (r'\d{4}年\d{1,2}月\d{1,2}日', 'YYYY年MM月DD日'),
        (r'\d{4}\.\d{1,2}', 'YYYY.MM'),
        (r'\d{4}/\d{1,2}', 'YYYY/MM'),
        (r'\d{4}-\d{1,2}', 'YYYY-MM'),
        (r'\d{4}年\d{1,2}月', 'YYYY年MM月'),
    ]

    # 特殊值标记
    SAMPLE_DESCRIPTION_REFERENCE = '见"样品描述"栏'

    def __init__(self):
        pass

    def check_third_page_fields(
        self,
        third_page_fields: Dict[str, str],
        sample_name: str,
        photo_labels: List[Dict[str, Any]]
    ) -> Tuple[List[FieldComparison], List[ErrorItem]]:
        """
        核对第三页扩展字段

        Args:
            third_page_fields: 第三页字段字典 {字段名: 字段值}
            sample_name: 样品名称（用于匹配标签）
            photo_labels: 照片页标签列表

        Returns:
            (字段比对结果列表, 错误列表)
        """
        comparisons = []
        errors = []

        # 提取扩展字段
        extended_values = self._extract_extended_fields(third_page_fields)

        # 检查是否所有字段都是"见样品描述栏"
        all_reference = all(
            self._is_sample_description_reference(field.value)
            for field in extended_values.values()
        )

        if all_reference:
            # 所有字段都是"见样品描述栏"，只需验证一致性
            consistency_check = self._check_consistency(extended_values)
            comparisons.extend(consistency_check['comparisons'])
            if consistency_check['error']:
                errors.append(consistency_check['error'])
            return comparisons, errors

        # 找到样品名称对应的中文标签
        matched_labels = self._find_labels_by_sample_name(sample_name, photo_labels)

        if not matched_labels:
            # 未找到对应标签，记录警告但不报错（可能在样品描述表格中核对）
            return comparisons, errors

        # 核对每个扩展字段
        for field_name, field in extended_values.items():
            # 跳过"见样品描述栏"的字段
            if self._is_sample_description_reference(field.value):
                continue

            # 检查是否包含数字和字母组合
            if not self._contains_alphanumeric(field.value):
                continue

            # 核对字段与标签
            field_comparison, field_errors = self._check_field_against_labels(
                field, matched_labels
            )

            comparisons.append(field_comparison)
            errors.extend(field_errors)

        return comparisons, errors

    def _extract_extended_fields(self, third_page_fields: Dict[str, str]) -> Dict[str, ThirdPageField]:
        """
        从第三页字段中提取扩展字段

        处理字段名可能的变化：
        - 型号规格 / 规格型号
        - 生产日期 / MFG / MFD
        - 产品编号/批号 / 批号 / 序列号 / LOT / SN
        """
        extended = {}

        for field_name, value in third_page_fields.items():
            field_name_clean = field_name.strip()

            # 型号规格匹配
            if any(syn in field_name_clean for syn in ['型号规格', '规格型号', '型号', '规格']):
                if '型号规格' not in extended:
                    extended['型号规格'] = ThirdPageField(
                        name='型号规格',
                        value=value.strip() if value else '',
                        page_num=3
                    )

            # 生产日期匹配
            elif any(syn in field_name_clean for syn in ['生产日期', 'MFG', 'MFD']):
                if '生产日期' not in extended:
                    extended['生产日期'] = ThirdPageField(
                        name='生产日期',
                        value=value.strip() if value else '',
                        page_num=3
                    )

            # 产品编号/批号匹配
            elif any(syn in field_name_clean for syn in ['产品编号', '批号', '序列号', 'LOT', 'SN']):
                if '产品编号/批号' not in extended:
                    extended['产品编号/批号'] = ThirdPageField(
                        name='产品编号/批号',
                        value=value.strip() if value else '',
                        page_num=3
                    )

        return extended

    def _is_sample_description_reference(self, value: str) -> bool:
        """检查值是否为'见样品描述栏'的变体"""
        if not value:
            return False

        value_clean = value.strip().replace('"', '').replace('"', '').replace('"', '')
        value_clean = value_clean.replace('「', '').replace('』', '').replace('『', '').replace('」', '')

        reference_patterns = [
            '见样品描述栏',
            '见"样品描述"栏',
            '见『样品描述』栏',
            '见「样品描述」栏',
        ]

        return value_clean in reference_patterns or '见' in value_clean and '样品描述' in value_clean and '栏' in value_clean

    def _contains_alphanumeric(self, value: str) -> bool:
        """检查值是否包含数字和字母组合"""
        if not value:
            return False

        has_digit = bool(re.search(r'\d', value))
        has_alpha = bool(re.search(r'[a-zA-Z]', value))

        return has_digit and has_alpha

    def _check_consistency(self, extended_fields: Dict[str, ThirdPageField]) -> Dict[str, Any]:
        """
        检查所有字段值是否一致（都是'见样品描述栏'）

        返回: {
            'comparisons': [FieldComparison, ...],
            'error': ErrorItem or None
        }
        """
        comparisons = []
        values = [field.value for field in extended_fields.values()]

        # 所有值应该相同
        all_same = len(set(values)) == 1 if values else True

        for field_name, field in extended_fields.items():
            comparison = FieldComparison(
                field_name=field_name,
                table_value=field.value,
                ocr_value=field.value,  # 自比
                is_match=all_same,
                issue_type=None if all_same else 'inconsistent_reference',
                page_num=field.page_num
            )
            comparisons.append(comparison)

        error = None
        if not all_same:
            error = ErrorItem(
                level="ERROR",
                message=f"第三页扩展字段值不一致：所有字段都应为'{self.SAMPLE_DESCRIPTION_REFERENCE}'",
                page_num=3,
                location="第三页表格",
                details={
                    'error_code': ThirdPageErrorCode.FIELD_MISMATCH,
                    'fields': {name: field.value for name, field in extended_fields.items()}
                }
            )

        return {'comparisons': comparisons, 'error': error}

    def _find_labels_by_sample_name(
        self,
        sample_name: str,
        photo_labels: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        根据样品名称找到对应的中文标签

        匹配逻辑：
        1. 样品名称与标签的subject_name完全匹配
        2. 样品名称包含在标签的subject_name中
        3. 标签的subject_name包含在样品名称中
        """
        if not sample_name:
            return []

        matched = []
        sample_clean = self._clean_name(sample_name)

        for label in photo_labels:
            subject_name = label.get('subject_name', '')
            if not subject_name:
                continue

            subject_clean = self._clean_name(subject_name)

            # 完全匹配
            if sample_clean == subject_clean:
                matched.append(label)
                continue

            # 样品名称包含在标签主体名中
            if sample_clean in subject_clean:
                matched.append(label)
                continue

            # 标签主体名包含在样品名称中
            if subject_clean in sample_clean:
                matched.append(label)
                continue

        return matched

    def _clean_name(self, name: str) -> str:
        """清理名称中的空白字符"""
        return re.sub(r'\s+', '', name.strip())

    def _check_field_against_labels(
        self,
        field: ThirdPageField,
        labels: List[Dict[str, Any]]
    ) -> Tuple[FieldComparison, List[ErrorItem]]:
        """
        核对单个字段与标签OCR结果

        Args:
            field: 表格字段
            labels: 匹配的标签列表

        Returns:
            (字段比对结果, 错误列表)
        """
        errors = []

        # 从标签OCR中提取对应字段
        label_values = []
        date_formats = []  # 用于生产日期格式检查

        for label in labels:
            ocr_result = label.get('ocr_result', {})
            if not ocr_result:
                continue

            # 提取结构化数据
            structured_data = ocr_result.get('structured_data', {})

            # 根据字段名映射找到对应的OCR字段值
            label_value = self._extract_label_field_value(
                field.name, structured_data
            )

            if label_value:
                label_values.append({
                    'value': label_value,
                    'label_caption': label.get('caption', ''),
                    'label_page': label.get('page_num', 0)
                })

                # 如果是生产日期，记录格式
                if field.name == '生产日期':
                    date_format = self._detect_date_format(label_value)
                    if date_format:
                        date_formats.append(date_format)

        # 确定最终标签值（如果有多个标签，取出现次数最多的值）
        final_label_value = ''
        if label_values:
            value_counts = {}
            for lv in label_values:
                v = lv['value']
                value_counts[v] = value_counts.get(v, 0) + 1
            final_label_value = max(value_counts.items(), key=lambda x: x[1])[0]

        # 比对值
        is_match = self._compare_values(field.value, final_label_value, field.name)

        # 如果是生产日期，检查格式一致性
        if field.name == '生产日期' and field.value and final_label_value:
            table_date_format = self._detect_date_format(field.value)
            label_date_format = date_formats[0] if date_formats else None

            if table_date_format and label_date_format:
                if table_date_format['pattern'] != label_date_format['pattern']:
                    is_match = False
                    errors.append(ErrorItem(
                        level="ERROR",
                        message=f"生产日期格式不一致：表格为'{table_date_format['name']}'，标签为'{label_date_format['name']}'",
                        page_num=field.page_num,
                        location=f"第三页表格/{field.name}",
                        details={
                            'error_code': ThirdPageErrorCode.DATE_FORMAT_MISMATCH,
                            'field_name': field.name,
                            'table_value': field.value,
                            'table_format': table_date_format,
                            'label_value': final_label_value,
                            'label_format': label_date_format
                        }
                    ))

        # 如果不匹配且没有格式错误，添加字段不匹配错误
        if not is_match and not any(
            e.details.get('error_code') == ThirdPageErrorCode.DATE_FORMAT_MISMATCH
            for e in errors
        ):
            errors.append(ErrorItem(
                level="ERROR",
                message=f"第三页字段'{field.name}'与标签不一致：表格'{field.value}' vs 标签'{final_label_value}'",
                page_num=field.page_num,
                location=f"第三页表格/{field.name}",
                details={
                    'error_code': ThirdPageErrorCode.FIELD_MISMATCH,
                    'field_name': field.name,
                    'table_value': field.value,
                    'label_value': final_label_value,
                    'matched_labels': [
                        {
                            'caption': lv['label_caption'],
                            'page': lv['label_page'],
                            'value': lv['value']
                        }
                        for lv in label_values
                    ]
                }
            ))

        comparison = FieldComparison(
            field_name=field.name,
            table_value=field.value,
            ocr_value=final_label_value,
            is_match=is_match,
            issue_type=None if is_match else 'mismatch',
            page_num=field.page_num
        )

        return comparison, errors

    def _extract_label_field_value(
        self,
        table_field_name: str,
        structured_data: Dict[str, Any]
    ) -> str:
        """
        从OCR结构化数据中提取对应字段值

        根据字段名映射找到对应的OCR字段
        """
        # 获取该表格字段可能对应的OCR字段名
        label_synonyms = self.FIELD_NAME_MAPPING.get(table_field_name, [table_field_name])

        # 在OCR结构化数据中查找
        for ocr_key, ocr_value in structured_data.items():
            ocr_key_clean = ocr_key.strip().lower()

            # 检查OCR字段名是否匹配任何同义词
            for synonym in label_synonyms:
                synonym_clean = synonym.strip().lower()

                # 直接匹配
                if ocr_key_clean == synonym_clean:
                    if isinstance(ocr_value, dict):
                        return ocr_value.get('value', '')
                    return str(ocr_value)

                # 包含匹配（如"生产日期"匹配"MFG Date"）
                if synonym_clean in ocr_key_clean or ocr_key_clean in synonym_clean:
                    if isinstance(ocr_value, dict):
                        return ocr_value.get('value', '')
                    return str(ocr_value)

            # 特殊处理：产品编号/批号可能对应serial_number或batch_number
            if table_field_name == '产品编号/批号':
                if ocr_key_clean in ['serial_number', 'batch_number', '批号', 'lot', 'sn', '序列号']:
                    if isinstance(ocr_value, dict):
                        return ocr_value.get('value', '')
                    return str(ocr_value)

            # 特殊处理：型号规格
            if table_field_name == '型号规格':
                if ocr_key_clean in ['model', 'spec', '规格', '型号']:
                    if isinstance(ocr_value, dict):
                        return ocr_value.get('value', '')
                    return str(ocr_value)

            # 特殊处理：生产日期
            if table_field_name == '生产日期':
                if ocr_key_clean in ['production_date', 'mfg', 'mfd', '生产日期']:
                    if isinstance(ocr_value, dict):
                        return ocr_value.get('value', '')
                    return str(ocr_value)

        return ''

    def _detect_date_format(self, date_str: str) -> Optional[Dict[str, str]]:
        """
        检测日期字符串的格式

        返回: {
            'pattern': 正则模式,
            'name': 格式名称
        }
        """
        if not date_str:
            return None

        date_str = date_str.strip()

        for pattern, name in self.DATE_FORMAT_PATTERNS:
            if re.match(pattern, date_str):
                return {'pattern': pattern, 'name': name}

        return None

    def _compare_values(self, table_value: str, label_value: str, field_name: str) -> bool:
        """
        比较表格值和标签值

        规则：
        1. 严格一致比对
        2. 清理空白字符后比较
        3. 对于产品编号/批号，支持部分匹配（表格值包含在标签值中或反之）
        """
        if not table_value and not label_value:
            return True

        table_clean = self._clean_name(table_value)
        label_clean = self._clean_name(label_value)

        if not table_clean and not label_clean:
            return True

        # 完全匹配
        if table_clean == label_clean:
            return True

        # 产品编号/批号支持部分匹配（因为标签可能包含额外信息）
        if field_name == '产品编号/批号':
            if table_clean in label_clean or label_clean in table_clean:
                return True

        return False

    def extract_third_page_extended_fields(
        self,
        pdf_path: str,
        page_num: int
    ) -> Dict[str, str]:
        """
        从PDF第三页提取扩展字段

        用于在核对流程中提取第三页的型号规格、生产日期、产品编号/批号字段
        """
        import fitz

        doc = fitz.open(pdf_path)
        try:
            page = doc[page_num - 1]
            text = page.get_text()

            fields = {}

            # 查找扩展字段
            field_patterns = {
                '型号规格': [
                    r'型号规格[：:\s]*([^\n]+)',
                    r'规格型号[：:\s]*([^\n]+)',
                ],
                '生产日期': [
                    r'生产日期[：:\s]*([^\n]+)',
                    r'MFG[：:\s]*([^\n]+)',
                    r'MFD[：:\s]*([^\n]+)',
                ],
                '产品编号/批号': [
                    r'产品编号[/／]批号[：:\s]*([^\n]+)',
                    r'批号[：:\s]*([^\n]+)',
                    r'产品编号[：:\s]*([^\n]+)',
                ]
            }

            for field_name, patterns in field_patterns.items():
                for pattern in patterns:
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        value = match.group(1).strip()
                        # 清理值
                        value = value.replace('"', '').replace('"', '').replace('"', '')
                        fields[field_name] = value
                        break

            return fields

        finally:
            doc.close()


# 全局实例
third_page_checker = ThirdPageChecker()
