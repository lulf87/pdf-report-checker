"""
报告字段核对引擎

实现报告字段核对逻辑：
1. 首页与第三页三字段一致性核对
2. 样品描述表格与中文标签OCR字段比对
3. 照片说明覆盖性检查
4. 额外字段核对
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Any, Tuple, Set
import re


class Severity(Enum):
    """错误分级"""
    ERROR = "ERROR"    # 严格一致未通过、必需项缺失
    WARN = "WARN"      # OCR置信度低/需复核
    INFO = "INFO"      # 通过项、统计信息


@dataclass
class AuditResult:
    """单个核对结果"""
    severity: Severity
    message: str
    field_name: Optional[str] = None
    expected_value: Optional[str] = None
    actual_value: Optional[str] = None
    page_number: Optional[int] = None
    table_row: Optional[int] = None
    table_col: Optional[str] = None
    image_path: Optional[str] = None
    caption: Optional[str] = None
    ocr_text: Optional[str] = None


@dataclass
class ComponentRecord:
    """样品描述表格中的一行记录"""
    row_index: int
    component_name: str  # 部件名称/产品名称
    fields: Dict[str, str] = field(default_factory=dict)  # 其他字段

    def get_non_empty_fields(self) -> Dict[str, str]:
        """获取所有非空字段（用于联合键匹配）"""
        return {k: v for k, v in self.fields.items() if v and v.strip() and v != "/"}


@dataclass
class OCRResult:
    """OCR识别结果"""
    image_path: str
    caption: str
    raw_text: str
    structured_fields: Dict[str, str] = field(default_factory=dict)
    confidence: float = 1.0


@dataclass
class PhotoCaption:
    """照片说明"""
    caption: str
    image_path: str
    subject_name: str  # 主体名
    is_chinese_label: bool = False


class CaptionParser:
    """说明文字解析器"""

    # 编号前缀正则
    PREFIX_PATTERN = re.compile(r'^(?:№|No\.?|NO\.?|Number)\s*\d+\s*', re.IGNORECASE)

    # 方位词
    DIRECTION_WORDS = [
        '前侧', '后侧', '左侧', '右侧', '正面', '背面', '侧面',
        '俯视', '仰视', '顶部', '底部', '局部'
    ]

    # 类别词
    CATEGORY_WORDS = [
        '中文标签样张', '中文标签', '英文标签', '原文标签', '标签'
    ]

    @classmethod
    def extract_subject_name(cls, caption: str) -> str:
        """
        从说明文字中提取主体名

        规则：
        1) 去除前缀编号
        2) 去除尾部方位词
        3) 去除尾部类别词
        4) 剩余文本即主体名
        """
        text = caption.strip()

        # 1) 去除前缀编号
        text = cls.PREFIX_PATTERN.sub('', text)

        # 2) 去除尾部方位词和类别词（循环去除，处理"前侧 中文标签"这种情况）
        changed = True
        while changed:
            changed = False
            text = text.strip()

            # 先尝试去除类别词（按长度降序）
            for word in sorted(cls.CATEGORY_WORDS, key=len, reverse=True):
                if text.endswith(word):
                    text = text[:-len(word)].strip()
                    changed = True
                    break

            # 再尝试去除方位词
            if not changed:
                for word in cls.DIRECTION_WORDS:
                    if text.endswith(word):
                        text = text[:-len(word)].strip()
                        changed = True
                        break

        return text

    @classmethod
    def is_chinese_label(cls, caption: str) -> bool:
        """判断是否为中文标签"""
        return '中文标签' in caption or '中文标签样张' in caption

    @classmethod
    def is_label(cls, caption: str) -> bool:
        """判断是否为标签（包含'标签'两字）"""
        return '标签' in caption


class OCRFieldExtractor:
    """OCR字段提取器"""

    # 批号正则
    LOT_PATTERNS = [
        re.compile(r'批号[：:\s]*([^\s]+)'),
        re.compile(r'(?:LOT|Lot|BATCH|Batch)\s*(?:No\.?|#)?[：:\s]*([^\s]+)', re.IGNORECASE),
    ]

    # 序列号正则
    SN_PATTERNS = [
        re.compile(r'序列号[：:\s]*([^\s]+)'),
        re.compile(r'(?:SN|S/N|Serial)\s*(?:No\.?|#)?[：:\s]*([^\s]+)', re.IGNORECASE),
    ]

    # 生产日期正则
    MFG_PATTERNS = [
        re.compile(r'生产日期[：:\s]*([0-9]{4}[-./年][0-9]{1,2}[-./月][0-9]{1,2}日?)'),
        re.compile(r'(?:MFG|MFD|Manufacture(?:d)?\s*Date|Production\s*Date|Date)[：:\s]*([0-9]{4}[-./][0-9]{1,2}[-./][0-9]{1,2})', re.IGNORECASE),
    ]

    # 失效日期正则
    EXP_PATTERNS = [
        re.compile(r'(?:失效日期|有效期至)[：:\s]*([0-9]{4}[-./年][0-9]{1,2}[-./月][0-9]{1,2}日?)'),
        re.compile(r'(?:EXP|Expiry|Expiration)\s*(?:Date)?[：:\s]*([0-9]{4}[-./][0-9]{1,2}[-./][0-9]{1,2})', re.IGNORECASE),
    ]

    # 型号规格正则
    MODEL_PATTERNS = [
        re.compile(r'(?:型号规格|规格型号)[：:\s]*([^\n]+)'),
        re.compile(r'型号[：:\s]*([^\n]+)'),
        re.compile(r'规格[：:\s]*([^\n]+)'),
    ]

    @classmethod
    def extract_fields(cls, ocr_text: str) -> Dict[str, str]:
        """从OCR文本中提取结构化字段"""
        fields = {}

        # 提取批号
        for pattern in cls.LOT_PATTERNS:
            match = pattern.search(ocr_text)
            if match:
                fields['批号'] = match.group(1).strip()
                fields['产品编号/批号'] = match.group(1).strip()
                break

        # 提取序列号
        for pattern in cls.SN_PATTERNS:
            match = pattern.search(ocr_text)
            if match:
                fields['序列号'] = match.group(1).strip()
                break

        # 提取生产日期
        for pattern in cls.MFG_PATTERNS:
            match = pattern.search(ocr_text)
            if match:
                fields['生产日期'] = match.group(1).strip()
                break

        # 提取失效日期
        for pattern in cls.EXP_PATTERNS:
            match = pattern.search(ocr_text)
            if match:
                fields['失效日期'] = match.group(1).strip()
                break

        # 提取型号规格
        for pattern in cls.MODEL_PATTERNS:
            match = pattern.search(ocr_text)
            if match:
                fields['型号规格'] = match.group(1).strip()
                break

        return fields


class AuditEngine:
    """核对引擎主类"""

    # 三字段名称
    THREE_FIELDS = ['委 托 方', '样品名称', '型号规格']

    def __init__(self):
        self.results: List[AuditResult] = []

    def audit(
        self,
        # 首页数据
        page1_fields: Dict[str, str],
        # 第三页数据
        page3_fields: Dict[str, str],
        # 样品描述表格
        component_table: List[ComponentRecord],
        # 照片说明列表
        photo_captions: List[PhotoCaption],
        # 中文标签OCR结果
        label_ocr_results: List[OCRResult],
        # 表头列名映射（用于识别同义列）
        column_mapping: Optional[Dict[str, str]] = None
    ) -> List[AuditResult]:
        """
        执行完整核对流程

        Args:
            page1_fields: 首页三字段 {字段名: 值}
            page3_fields: 第三页三字段 {字段名: 值}
            component_table: 样品描述表格记录列表
            photo_captions: 照片说明列表
            label_ocr_results: 中文标签OCR结果列表
            column_mapping: 列名映射 {原始列名: 标准列名}

        Returns:
            核对结果列表
        """
        self.results = []

        # 1. 首页与第三页三字段一致性核对
        self._audit_page1_page3_consistency(page1_fields, page3_fields)

        # 2. 样品描述表格与中文标签OCR比对
        self._audit_table_vs_ocr(component_table, label_ocr_results, column_mapping)

        # 3. 照片说明覆盖性检查
        self._audit_photo_coverage(component_table, photo_captions)

        # 4. 额外字段核对（当首页值不是"见'样品描述'栏"时）
        self._audit_extra_fields(page1_fields, page3_fields, photo_captions, label_ocr_results)

        return self.results

    def _audit_page1_page3_consistency(
        self,
        page1_fields: Dict[str, str],
        page3_fields: Dict[str, str]
    ):
        """核对首页与第三页三字段一致性"""
        for field_name in self.THREE_FIELDS:
            page1_value = page1_fields.get(field_name, '')
            page3_value = page3_fields.get(field_name, '')

            # 严格一致比对（字符级，包括大小写、全半角、空格）
            if page1_value == page3_value:
                self.results.append(AuditResult(
                    severity=Severity.INFO,
                    message=f"首页与第三页'{field_name}'一致",
                    field_name=field_name,
                    expected_value=page1_value,
                    actual_value=page3_value,
                    page_number=3
                ))
            else:
                self.results.append(AuditResult(
                    severity=Severity.ERROR,
                    message=f"首页与第三页'{field_name}'不一致",
                    field_name=field_name,
                    expected_value=page1_value,
                    actual_value=page3_value,
                    page_number=3
                ))

    def _is_empty_or_slash(self, value: str) -> bool:
        """判断值是否为空白或/"""
        if not value:
            return True
        return value.strip() in ['', '/']

    def _strict_equal(self, val1: str, val2: str) -> bool:
        """严格一致比对（字符级）"""
        return val1 == val2

    def _audit_table_vs_ocr(
        self,
        component_table: List[ComponentRecord],
        label_ocr_results: List[OCRResult],
        column_mapping: Optional[Dict[str, str]] = None
    ):
        """核对样品描述表格与中文标签OCR"""
        # 按部件名称分组
        components_by_name: Dict[str, List[ComponentRecord]] = {}
        for record in component_table:
            name = record.component_name
            if name not in components_by_name:
                components_by_name[name] = []
            components_by_name[name].append(record)

        # 对每个部件进行核对
        for component_name, records in components_by_name.items():
            if len(records) == 1:
                # 单一部件
                self._audit_single_component(records[0], label_ocr_results, column_mapping)
            else:
                # 同名多行
                self._audit_multi_component(records, label_ocr_results, column_mapping)

    def _audit_single_component(
        self,
        record: ComponentRecord,
        label_ocr_results: List[OCRResult],
        column_mapping: Optional[Dict[str, str]] = None
    ):
        """核对单一部件"""
        component_name = record.component_name

        # 找到对应该部件的标签OCR
        matching_ocr = self._find_matching_ocr(component_name, label_ocr_results)

        if not matching_ocr:
            self.results.append(AuditResult(
                severity=Severity.ERROR,
                message=f"部件'{component_name}'未找到对应中文标签",
                field_name='部件名称',
                expected_value=component_name,
                page_number=4,
                table_row=record.row_index
            ))
            return

        # 逐字段比对
        self._compare_fields(record, matching_ocr, column_mapping)

    def _audit_multi_component(
        self,
        records: List[ComponentRecord],
        label_ocr_results: List[OCRResult],
        column_mapping: Optional[Dict[str, str]] = None
    ):
        """核对同名多行部件（使用非空字段联合键匹配）"""
        component_name = records[0].component_name

        # 获取该部件的所有标签OCR
        candidate_ocr = [
            ocr for ocr in label_ocr_results
            if CaptionParser.extract_subject_name(ocr.caption) == component_name
        ]

        if not candidate_ocr:
            self.results.append(AuditResult(
                severity=Severity.ERROR,
                message=f"同名多行部件'{component_name}'未找到任何中文标签",
                field_name='部件名称',
                expected_value=component_name,
                page_number=4
            ))
            return

        # 为每一行找到最佳匹配的标签
        matched_ocr_indices: Set[int] = set()

        for record in records:
            non_empty_fields = record.get_non_empty_fields()

            if not non_empty_fields:
                # 无非空字段，无法匹配
                self.results.append(AuditResult(
                    severity=Severity.ERROR,
                    message=f"部件'{component_name}'第{record.row_index}行无非空字段用于匹配",
                    field_name='部件名称',
                    page_number=4,
                    table_row=record.row_index
                ))
                continue

            # 找到最佳匹配
            best_match = None
            best_match_score = 0

            for idx, ocr in enumerate(candidate_ocr):
                if idx in matched_ocr_indices:
                    continue

                match_score = self._calculate_match_score(non_empty_fields, ocr, column_mapping)
                if match_score > best_match_score:
                    best_match_score = match_score
                    best_match = ocr

            if best_match and best_match_score > 0:
                matched_ocr_indices.add(candidate_ocr.index(best_match))
                self._compare_fields(record, best_match, column_mapping, is_multi=True)
            else:
                # 未找到匹配
                self.results.append(AuditResult(
                    severity=Severity.ERROR,
                    message=f"同名多行部件'{component_name}'第{record.row_index}行未找到匹配标签",
                    field_name='部件名称',
                    expected_value=str(non_empty_fields),
                    page_number=4,
                    table_row=record.row_index
                ))

    def _find_matching_ocr(
        self,
        component_name: str,
        label_ocr_results: List[OCRResult]
    ) -> Optional[OCRResult]:
        """找到对应部件名称的标签OCR"""
        for ocr in label_ocr_results:
            subject = CaptionParser.extract_subject_name(ocr.caption)
            if subject == component_name:
                return ocr
        return None

    def _calculate_match_score(
        self,
        non_empty_fields: Dict[str, str],
        ocr: OCRResult,
        column_mapping: Optional[Dict[str, str]] = None
    ) -> int:
        """
        计算匹配分数

        规则：该行每个非空字段都必须在OCR中找到且值完全一致
        返回匹配的字段数
        """
        score = 0
        ocr_fields = ocr.structured_fields

        for field_name, field_value in non_empty_fields.items():
            # 标准化字段名
            std_name = column_mapping.get(field_name, field_name) if column_mapping else field_name

            # 在OCR字段中查找
            matched = False
            for ocr_key, ocr_value in ocr_fields.items():
                ocr_std_name = column_mapping.get(ocr_key, ocr_key) if column_mapping else ocr_key
                if std_name == ocr_std_name or self._is_same_field(std_name, ocr_std_name):
                    if self._strict_equal(field_value, ocr_value):
                        matched = True
                        break

            if matched:
                score += 1
            else:
                # 有一个字段不匹配，整个匹配失败
                return 0

        return score

    def _is_same_field(self, name1: str, name2: str) -> bool:
        """判断两个字段名是否指同一字段（同义词判断）"""
        # 同义词映射
        synonyms = {
            '批号': ['批号', '产品编号', '产品编号/批号', '序列号批号'],
            '序列号': ['序列号', 'SN', 'S/N', 'Serial'],
            '生产日期': ['生产日期', 'MFG', 'MFD', 'Manufacture Date'],
            '失效日期': ['失效日期', '有效期至', 'EXP', 'Expiry'],
            '型号规格': ['型号规格', '规格型号', '型号', '规格'],
        }

        for std_name, variants in synonyms.items():
            if name1 in variants and name2 in variants:
                return True
        return False

    def _compare_fields(
        self,
        record: ComponentRecord,
        ocr: OCRResult,
        column_mapping: Optional[Dict[str, str]] = None,
        is_multi: bool = False
    ):
        """比对表格行与OCR的字段"""
        component_name = record.component_name
        table_fields = record.fields
        ocr_fields = ocr.structured_fields

        multi_info = "(同名多行)" if is_multi else ""

        for field_name, table_value in table_fields.items():
            # 标准化字段名
            std_name = column_mapping.get(field_name, field_name) if column_mapping else field_name

            # 在OCR字段中查找对应值
            ocr_value = None
            for ocr_key, ocr_val in ocr_fields.items():
                ocr_std_name = column_mapping.get(ocr_key, ocr_key) if column_mapping else ocr_key
                if std_name == ocr_std_name or self._is_same_field(std_name, ocr_std_name):
                    ocr_value = ocr_val
                    break

            # 应用/与空白等价规则
            if self._is_empty_or_slash(table_value):
                if ocr_value is None or self._is_empty_or_slash(ocr_value):
                    # 表格为/或空白，OCR为空 = 一致
                    self.results.append(AuditResult(
                        severity=Severity.INFO,
                        message=f"部件'{component_name}'{multi_info}'{field_name}'一致（均为空）",
                        field_name=field_name,
                        expected_value=table_value,
                        actual_value=ocr_value or '',
                        page_number=4,
                        table_row=record.row_index,
                        image_path=ocr.image_path,
                        caption=ocr.caption,
                        ocr_text=ocr.raw_text
                    ))
                else:
                    # 表格为/或空白，OCR有值 = 表格漏填
                    self.results.append(AuditResult(
                        severity=Severity.ERROR,
                        message=f"部件'{component_name}'{multi_info}'{field_name}'表格漏填",
                        field_name=field_name,
                        expected_value=ocr_value,
                        actual_value=table_value,
                        page_number=4,
                        table_row=record.row_index,
                        image_path=ocr.image_path,
                        caption=ocr.caption,
                        ocr_text=ocr.raw_text
                    ))
            else:
                # 表格有值，OCR必须完全一致
                if ocr_value is None:
                    self.results.append(AuditResult(
                        severity=Severity.ERROR,
                        message=f"部件'{component_name}'{multi_info}'{field_name}'OCR未识别到值",
                        field_name=field_name,
                        expected_value=table_value,
                        actual_value='',
                        page_number=4,
                        table_row=record.row_index,
                        image_path=ocr.image_path,
                        caption=ocr.caption,
                        ocr_text=ocr.raw_text
                    ))
                elif self._strict_equal(table_value, ocr_value):
                    self.results.append(AuditResult(
                        severity=Severity.INFO,
                        message=f"部件'{component_name}'{multi_info}'{field_name}'一致",
                        field_name=field_name,
                        expected_value=table_value,
                        actual_value=ocr_value,
                        page_number=4,
                        table_row=record.row_index,
                        image_path=ocr.image_path,
                        caption=ocr.caption,
                        ocr_text=ocr.raw_text
                    ))
                else:
                    self.results.append(AuditResult(
                        severity=Severity.ERROR,
                        message=f"部件'{component_name}'{multi_info}'{field_name}'不一致",
                        field_name=field_name,
                        expected_value=table_value,
                        actual_value=ocr_value,
                        page_number=4,
                        table_row=record.row_index,
                        image_path=ocr.image_path,
                        caption=ocr.caption,
                        ocr_text=ocr.raw_text
                    ))

        # 检查OCR置信度
        if ocr.confidence < 0.8:
            self.results.append(AuditResult(
                severity=Severity.WARN,
                message=f"部件'{component_name}'OCR置信度较低({ocr.confidence:.2f})，建议人工复核",
                field_name='OCR置信度',
                page_number=4,
                table_row=record.row_index,
                image_path=ocr.image_path,
                caption=ocr.caption,
                ocr_text=ocr.raw_text
            ))

    def _audit_photo_coverage(
        self,
        component_table: List[ComponentRecord],
        photo_captions: List[PhotoCaption]
    ):
        """核对照片说明覆盖性"""
        # 获取所有部件名称
        component_names = set()
        for record in component_table:
            component_names.add(record.component_name)

        # 获取照片说明中的主体名
        photo_subjects = set()
        label_subjects = set()

        for caption in photo_captions:
            if caption.is_chinese_label:
                label_subjects.add(caption.subject_name)
            else:
                photo_subjects.add(caption.subject_name)

        # 检查每个部件的覆盖性
        for component_name in component_names:
            # 检查照片说明覆盖
            if component_name not in photo_subjects:
                self.results.append(AuditResult(
                    severity=Severity.ERROR,
                    message=f"部件'{component_name}'缺少照片说明",
                    field_name='照片说明',
                    expected_value=component_name,
                    page_number=5
                ))
            else:
                self.results.append(AuditResult(
                    severity=Severity.INFO,
                    message=f"部件'{component_name}'有照片说明覆盖",
                    field_name='照片说明',
                    expected_value=component_name,
                    page_number=5
                ))

            # 检查中文标签覆盖
            if component_name not in label_subjects:
                self.results.append(AuditResult(
                    severity=Severity.ERROR,
                    message=f"部件'{component_name}'缺少中文标签",
                    field_name='中文标签',
                    expected_value=component_name,
                    page_number=5
                ))
            else:
                self.results.append(AuditResult(
                    severity=Severity.INFO,
                    message=f"部件'{component_name}'有中文标签覆盖",
                    field_name='中文标签',
                    expected_value=component_name,
                    page_number=5
                ))

    def _audit_extra_fields(
        self,
        page1_fields: Dict[str, str],
        page3_fields: Dict[str, str],
        photo_captions: List[PhotoCaption],
        label_ocr_results: List[OCRResult]
    ):
        """
        额外字段核对

        当首页值不是"见'样品描述'栏"时，需要额外核对：
        - 第三页：产品编号/批号、生产日期
        - 这些值必须在caption和中文标签OCR中出现
        """
        # 检查首页值
        sample_desc_ref = "见'样品描述'栏"
        need_extra_audit = False

        for field_name in self.THREE_FIELDS:
            value = page1_fields.get(field_name, '')
            if value != sample_desc_ref:
                need_extra_audit = True
                break

        if not need_extra_audit:
            return

        # 需要核对的额外字段
        extra_fields = {
            '产品编号/批号': page3_fields.get('产品编号/批号', ''),
            '批号': page3_fields.get('批号', ''),
            '生产日期': page3_fields.get('生产日期', '')
        }

        # 收集所有caption文本和OCR文本
        all_captions = ' '.join([c.caption for c in photo_captions])
        all_ocr_texts = ' '.join([ocr.raw_text for ocr in label_ocr_results])
        all_ocr_fields = {}
        for ocr in label_ocr_results:
            all_ocr_fields.update(ocr.structured_fields)

        for field_name, field_value in extra_fields.items():
            if not field_value or self._is_empty_or_slash(field_value):
                continue

            # 检查是否在caption中出现
            in_caption = field_value in all_captions

            # 检查是否在OCR中出现
            in_ocr = field_value in all_ocr_texts or field_value in all_ocr_fields.values()

            if in_caption and in_ocr:
                self.results.append(AuditResult(
                    severity=Severity.INFO,
                    message=f"额外字段'{field_name}'在caption和OCR中均有出现",
                    field_name=field_name,
                    expected_value=field_value,
                    actual_value='已找到'
                ))
            elif not in_caption:
                self.results.append(AuditResult(
                    severity=Severity.ERROR,
                    message=f"额外字段'{field_name}'未在照片说明中出现",
                    field_name=field_name,
                    expected_value=field_value,
                    actual_value='未找到'
                ))
            elif not in_ocr:
                self.results.append(AuditResult(
                    severity=Severity.ERROR,
                    message=f"额外字段'{field_name}'未在中文标签OCR中出现",
                    field_name=field_name,
                    expected_value=field_value,
                    actual_value='未找到'
                ))

    def get_summary(self) -> Dict[str, Any]:
        """获取核对结果汇总"""
        error_count = sum(1 for r in self.results if r.severity == Severity.ERROR)
        warn_count = sum(1 for r in self.results if r.severity == Severity.WARN)
        info_count = sum(1 for r in self.results if r.severity == Severity.INFO)

        return {
            'total': len(self.results),
            'error': error_count,
            'warn': warn_count,
            'info': info_count,
            'passed': error_count == 0
        }

    def get_errors(self) -> List[AuditResult]:
        """获取所有错误结果"""
        return [r for r in self.results if r.severity == Severity.ERROR]

    def get_warnings(self) -> List[AuditResult]:
        """获取所有警告结果"""
        return [r for r in self.results if r.severity == Severity.WARN]

    def get_infos(self) -> List[AuditResult]:
        """获取所有信息结果"""
        return [r for r in self.results if r.severity == Severity.INFO]


def create_photo_caption(caption: str, image_path: str) -> PhotoCaption:
    """工厂函数：创建PhotoCaption对象"""
    subject_name = CaptionParser.extract_subject_name(caption)
    is_chinese_label = CaptionParser.is_chinese_label(caption)
    return PhotoCaption(
        caption=caption,
        image_path=image_path,
        subject_name=subject_name,
        is_chinese_label=is_chinese_label
    )


def create_ocr_result(image_path: str, caption: str, raw_text: str, confidence: float = 1.0) -> OCRResult:
    """工厂函数：创建OCRResult对象"""
    structured_fields = OCRFieldExtractor.extract_fields(raw_text)
    return OCRResult(
        image_path=image_path,
        caption=caption,
        raw_text=raw_text,
        structured_fields=structured_fields,
        confidence=confidence
    )


def create_component_record(row_index: int, component_name: str, **fields) -> ComponentRecord:
    """工厂函数：创建ComponentRecord对象"""
    return ComponentRecord(
        row_index=row_index,
        component_name=component_name,
        fields=fields
    )
