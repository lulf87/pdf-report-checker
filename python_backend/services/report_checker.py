"""
报告核对引擎
整合PDF解析、OCR识别和字段比对
"""

import re
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from models.schemas import (
    CheckResult, ComponentCheck, FieldComparison,
    ErrorItem, TableData, OCRResult
)
from services.pdf_parser import PDFParser
from services.ocr_service import OCRService
from services.inspection_item_checker import InspectionItemChecker
from services.page_number_checker import PageNumberChecker
from services.third_page_checker import third_page_checker
from utils.comparison_logger import ComparisonLogger
from config import is_llm_comparison_enabled, settings as app_settings


class ReportChecker:
    """报告核对器"""

    # 关键字段名
    KEY_FIELDS = ['委 托 方', '样品名称', '型号规格']

    # 样品描述表格同义列名映射
    COLUMN_SYNONYMS = {
        '部件名称': ['部件名称', '产品名称', '名称'],
        '规格型号': ['规格型号', '型号规格', '型号', '规格'],
        '序列号批号': ['序列号批号', '批号', '序列号', 'SN', 'LOT'],
        '生产日期': ['生产日期', 'MFG', 'MFD'],
        '失效日期': ['失效日期', '有效期至', 'EXP']
    }

    # Caption解析正则
    CAPTION_PATTERNS = {
        'prefix_number': r'^(?:№|No\.?|NO\.?|Number)\s*\d+\s*',
        'any_number_prefix': r'^(?:№|No\.?|NO\.?|Number)?\s*\d+\s*',  # 包括纯数字
        'position_words': r'(?:前侧|后侧|左侧|右侧|左面|右面|正面|背面|侧面|俯视|仰视|顶部|底部|局部)',
        'label_types': r'(?:中文标签样张|中文标签|英文标签|原文标签|标签)'
    }

    def __init__(self):
        self.pdf_parser = PDFParser()
        self.ocr_service = OCRService()
        self.inspection_checker = InspectionItemChecker()
        self.page_number_checker = PageNumberChecker()

    async def check(self, pdf_path: str, file_id: str, enable_detailed: bool = False) -> CheckResult:
        """
        执行完整的报告核对流程

        Args:
            pdf_path: PDF文件路径
            file_id: 文件ID
            enable_detailed: 是否启用详细比对信息
        """
        # 1. 解析PDF获取页面信息
        pages = self.pdf_parser.parse(pdf_path)

        # 2. 提取首页字段
        home_page_fields = self.pdf_parser.extract_home_page_fields(pdf_path)

        # 3. 定位第三页（检验报告首页）
        third_page_num = self._find_third_page(pages)
        third_page_fields = {}

        if third_page_num:
            third_page_fields = self._extract_third_page_fields(pdf_path, third_page_num)

        # 4. 比对首页和第三页
        home_third_comparison = self._compare_home_third(
            home_page_fields, third_page_fields
        )

        # 5. 提取样品描述表格（第四页起）
        sample_table = self._extract_sample_table(pdf_path, pages)

        # 6. 定位照片页
        photo_pages = self._find_photo_pages(pages)

        # 7. 解析照片页内容
        photo_analysis = self._analyze_photo_pages(pdf_path, photo_pages)

        # 8. 第三页扩展字段核对（新增 v2.2）
        third_page_extended_checks = self._check_third_page_extended_fields(
            pdf_path, third_page_num, third_page_fields, photo_analysis
        )

        # 9. 核对部件
        component_checks = self._check_components(
            sample_table, photo_analysis, enable_detailed=enable_detailed
        )

        # 10. 检验项目表格核对（新增 v2.1）
        inspection_item_check = self.inspection_checker.check_inspection_items(
            pdf_path, pages
        )

        # 11. 页码连续性校验（新增 v2.2）
        page_number_infos, page_number_errors = self.page_number_checker.check_page_numbers(
            pdf_path, pages
        )

        # 构建页码校验结果
        page_number_check = self._build_page_number_check_result(
            page_number_infos, page_number_errors
        )

        # 12. 收集错误和警告
        errors, warnings, info = self._collect_issues(
            home_third_comparison, component_checks, photo_analysis,
            inspection_item_check, page_number_errors, third_page_extended_checks
        )

        # 13. 保存结果
        result = CheckResult(
            success=True,
            file_id=file_id,
            filename=Path(pdf_path).name,
            check_time=datetime.now().isoformat(),
            total_pages=len(pages),
            home_page_fields=home_page_fields,
            third_page_fields=third_page_fields,
            home_third_comparison=home_third_comparison,
            sample_description_table=sample_table,
            component_checks=component_checks,
            photo_page_check=photo_analysis,
            inspection_item_check=inspection_item_check,
            third_page_extended_checks=third_page_extended_checks,
            page_number_check=page_number_check,
            errors=errors,
            warnings=warnings,
            info=info,
            total_components=len(component_checks),
            passed_components=sum(1 for c in component_checks if c.status == 'pass'),
            failed_components=sum(1 for c in component_checks if c.status == 'fail')
        )

        # 保存结果到临时文件
        self._save_result(file_id, result)

        return result

    def _find_third_page(self, pages: List[Any]) -> Optional[int]:
        """定位第三页（页眉包含"检验报告首页"）"""
        for page in pages:
            if page.page_header:
                cleaned = self.pdf_parser._clean_whitespace(page.page_header)
                if '检验报告首页' in cleaned or '检验报告首页' in cleaned:
                    return page.page_num
        return None

    def _extract_third_page_fields(self, pdf_path: str, page_num: int) -> Dict[str, str]:
        """提取第三页的三个关键字段"""
        import fitz

        doc = fitz.open(pdf_path)
        try:
            page = doc[page_num - 1]
            text = page.get_text()

            fields = {}
            for field_name in self.KEY_FIELDS:
                value = self.pdf_parser._extract_field_value(text, field_name)
                fields[field_name] = value

            return fields
        finally:
            doc.close()

    def _compare_home_third(self, home_fields: Dict[str, str],
                           third_fields: Dict[str, str]) -> List[FieldComparison]:
        """比对首页和第三页的字段"""
        comparisons = []

        for field_name in self.KEY_FIELDS:
            home_value = home_fields.get(field_name, '')
            third_value = third_fields.get(field_name, '')

            # 标准化比较
            is_match = self._values_equal(home_value, third_value)

            comparisons.append(FieldComparison(
                field_name=field_name,
                table_value=home_value,
                ocr_value=third_value,
                is_match=is_match,
                issue_type=None if is_match else 'mismatch'
            ))

        return comparisons

    def _values_equal(self, val1: str, val2: str) -> bool:
        """判断两个值是否相等（考虑/、空白、见实物的等价性）"""
        v1 = val1.strip() if val1 else ''
        v2 = val2.strip() if val2 else ''

        # / 和空白等价
        if v1 in ['', '/'] and v2 in ['', '/']:
            return True

        # /、空白、见实物 都视为等价（表示无固定值）
        empty_values = ['', '/', '见实物']
        if v1 in empty_values and v2 in empty_values:
            return True

        return v1 == v2

    def _extract_sample_table(self, pdf_path: str, pages: List[Any]) -> Optional[TableData]:
        """提取样品描述表格（支持跨页表格）"""
        import fitz

        # 从第四页开始查找
        doc = fitz.open(pdf_path)

        try:
            first_table = None
            all_rows = []
            found_sample_page = False
            last_item_number = 0  # 用于追踪最后一个序号

            for page_info in pages:
                if page_info.page_num < 4:
                    continue

                page = doc[page_info.page_num - 1]
                text = page.get_text()

                # 查找"样品描述"标记，开始提取
                if '样品描述' in text:
                    found_sample_page = True

                # 如果已经找到了样品描述页，继续处理后续可能包含表格延续的页
                if found_sample_page:
                    # 查找所有表格，找到包含部件数据的表格
                    tab = page.find_tables()
                    for table_idx in range(len(tab.tables)):
                        table_data = self.pdf_parser.extract_table_detailed(
                            pdf_path, page_info.page_num, table_idx
                        )

                        if not table_data:
                            continue

                        headers_str = ' '.join(str(h) for h in table_data.headers) if table_data.headers else ''

                        # 检查是否是部件表格
                        is_component_table = False
                        has_component_header = '部件名称' in headers_str

                        if first_table is None:
                            # 第一个表格必须有"部件名称"列头
                            if has_component_header:
                                is_component_table = True
                                first_table = table_data
                                all_rows.extend(table_data.rows)
                                # 更新最后一个序号
                                if table_data.rows:
                                    last_item = table_data.rows[-1][0].strip() if table_data.rows[-1] else '0'
                                    try:
                                        last_item_number = int(last_item)
                                    except ValueError:
                                        last_item_number = 0
                        else:
                            # 后续页面：检查是否是表格延续
                            # 1. 检查列数是否匹配
                            if table_data.col_count == first_table.col_count:
                                # 2. 检查是否有序号连续性
                                # 首先检查headers（第一行可能被当作header）
                                header_first_cell = table_data.headers[0].strip() if table_data.headers else ''
                                rows_to_add = []
                                found_continuation = False

                                # 检查headers中的序号
                                try:
                                    header_item_num = int(header_first_cell)
                                    if header_item_num == last_item_number + 1:
                                        # Headers包含延续的第一项
                                        rows_to_add = [table_data.headers] + table_data.rows
                                        found_continuation = True
                                except ValueError:
                                    pass

                                # 如果headers不是延续，检查第一行数据
                                if not found_continuation and table_data.rows and len(table_data.rows[0]) > 0:
                                    first_cell = table_data.rows[0][0].strip()
                                    try:
                                        first_item_num = int(first_cell)
                                        # 如果第一个序号紧接上一个表格的最后一个序号，认为是延续
                                        if first_item_num == last_item_number + 1:
                                            rows_to_add = table_data.rows
                                            found_continuation = True
                                        # 或者第一行包含"部件名称"（重复的header）
                                        elif has_component_header:
                                            # 跳过header行，添加其余行
                                            if len(table_data.rows) > 1:
                                                rows_to_add = table_data.rows[1:]
                                                found_continuation = True
                                    except ValueError:
                                        # 第一列不是数字，检查是否包含"部件名称"
                                        if has_component_header:
                                            if len(table_data.rows) > 1:
                                                rows_to_add = table_data.rows[1:]
                                                found_continuation = True

                                if found_continuation and rows_to_add:
                                    is_component_table = True
                                    all_rows.extend(rows_to_add)
                                    # 更新最后一个序号
                                    last_item = rows_to_add[-1][0].strip() if rows_to_add[-1] else '0'
                                    try:
                                        last_item_number = int(last_item)
                                    except ValueError:
                                        pass

            if first_table:
                # 创建合并后的表格数据
                merged_table = TableData(
                    page_num=first_table.page_num,
                    table_index=first_table.table_index,
                    headers=first_table.headers,
                    rows=all_rows,
                    row_count=len(all_rows),
                    col_count=first_table.col_count
                )
                return merged_table

            return None

        finally:
            doc.close()

    def _find_photo_pages(self, pages: List[Any]) -> List[int]:
        """定位所有照片页"""
        photo_pages = []

        for page in pages:
            if page.page_header:
                cleaned = self.pdf_parser._clean_whitespace(page.page_header)
                if '检验报告照片页' in cleaned:
                    photo_pages.append(page.page_num)

        return photo_pages

    def _analyze_photo_pages(self, pdf_path: str, photo_pages: List[int]) -> Dict[str, Any]:
        """分析照片页内容"""
        import fitz

        doc = fitz.open(pdf_path)

        photos = []
        labels = []

        try:
            for page_num in photo_pages:
                page = doc[page_num - 1]

                # 提取页面文本作为caption来源
                text = page.get_text()

                # 查找图片
                images = page.get_images(full=True)

                for img_idx, img in enumerate(images):
                    xref = img[0]
                    base_image = doc.extract_image(xref)

                    if base_image:
                        # 保存图片
                        img_path = f"temp/photo_{page_num}_{img_idx}.png"
                        Path(img_path).parent.mkdir(exist_ok=True)

                        with open(img_path, 'wb') as f:
                            f.write(base_image['image'])

                        # 分析caption（简化版：基于文本位置）
                        caption = self._extract_caption(text, img_idx)

                        # 判断是否为标签
                        is_label = self._is_chinese_label(caption)

                        # 提取主体名
                        subject_name = self._extract_subject_name(caption)

                        photo_info = {
                            'page_num': page_num,
                            'image_index': img_idx,
                            'image_path': img_path,
                            'caption': caption,
                            'is_label': is_label,
                            'subject_name': subject_name
                        }

                        photos.append(photo_info)

                        if is_label:
                            # 对标签进行OCR
                            try:
                                ocr_result = self.ocr_service.recognize_label(img_path)
                                photo_info['ocr_result'] = ocr_result.dict()
                                labels.append(photo_info)
                            except Exception as e:
                                photo_info['ocr_error'] = str(e)

        finally:
            doc.close()

        return {
            'total_photos': len(photos),
            'total_labels': len(labels),
            'photos': photos,
            'labels': labels
        }

    def _extract_caption(self, page_text: str, image_index: int) -> str:
        """从页面文本中提取图片的caption

        Args:
            page_text: 页面文本内容
            image_index: 图片在页面中的索引（0-based），用于匹配对应的caption编号

        Returns:
            匹配到的caption文本，如果没有找到则返回空字符串
        """
        lines = [l.strip() for l in page_text.split('\n') if l.strip()]

        # 收集所有带编号的caption
        numbered_lines = []
        for line in lines:
            # 匹配各种编号格式：№25, No.25, NO 25, Number 25, 纯数字25等
            match = re.search(r'^(?:№|No\.?|NO\.?|Number)?\s*(\d+)[:.\s]*', line, re.IGNORECASE)
            if match:
                line_number = int(match.group(1))
                numbered_lines.append((line_number, line))

        if not numbered_lines:
            return ''

        # 按编号排序
        numbered_lines.sort(key=lambda x: x[0])

        # 方法1: 尝试基于image_index直接匹配（假设编号连续）
        expected_number = image_index + 1
        for num, line in numbered_lines:
            if num == expected_number:
                print(f"[DEBUG] Caption匹配(连续编号): image_index={image_index} -> №{num}")
                return line

        # 方法2: 如果编号不连续（如从25开始），使用位置匹配
        if image_index < len(numbered_lines):
            matched_num, matched_line = numbered_lines[image_index]
            print(f"[DEBUG] Caption匹配(位置): image_index={image_index} -> №{matched_num}: {matched_line[:40]}...")
            return matched_line

        print(f"[DEBUG] Caption未匹配: image_index={image_index}, 找到{len(numbered_lines)}个编号caption")
        return ''

    def _is_chinese_label(self, caption: str) -> bool:
        """判断caption是否表示中文标签"""
        if not caption:
            return False

        # 清理空白字符，提高匹配鲁棒性
        caption_clean = re.sub(r'\s+', '', caption)

        # 支持多种中文标签变体
        chinese_label_patterns = [
            '中文标签',
            '中文标签样张',
            '中文標籤',
            '中文标签样本',
            '中文标签照片',
            '标签样张',
        ]

        return any(pattern in caption_clean for pattern in chinese_label_patterns)

    def _extract_subject_name(self, caption: str) -> str:
        """从caption中提取主体名"""
        if not caption:
            return ''

        name = caption

        # 1. 去除前缀编号
        name = re.sub(self.CAPTION_PATTERNS['prefix_number'], '', name)

        # 2. 去除尾部方位词
        name = re.sub(self.CAPTION_PATTERNS['position_words'], '', name)

        # 3. 去除尾部类别词
        name = re.sub(self.CAPTION_PATTERNS['label_types'], '', name)

        # 4. 清理所有空白字符（包括中间的空格、换行符等）
        name = re.sub(r'\s+', '', name)

        return name

    def _is_component_name_match(self, component_name: str, subject_name: str) -> bool:
        """判断部件名称是否与照片主体名匹配

        支持三种匹配方式：
        1. 精确匹配：部件名称完全等于主体名
        2. 部分匹配（组件→主体）：部件名称包含在主体名中（用于处理组合名称场景）
        3. 部分匹配（主体→组件）：主体名包含在部件名称中（用于处理名称缩写场景）

        例如：
        - component_name="心脏脉冲电场消融仪-主机" 匹配 subject_name="心脏脉冲电场消融仪-主机"
        - component_name="心脏脉冲电场消融仪-主机" 匹配 subject_name="心脏脉冲电场消融仪-主机及心脏脉冲电场消融仪-推车"
        - component_name="心脏脉冲电场消融仪-触摸屏连接线缆（30m）" 匹配 subject_name="触摸屏连接线缆（30m）"

        防误匹配：
        - "心脏脉冲电场消融仪-触摸屏" 不应匹配 "心脏脉冲电场消融仪-触摸屏连接线缆（30m）"
        """
        if not component_name or not subject_name:
            return False

        # 清理两个名称中的空白字符（包括换行符）
        component_clean = re.sub(r'\s+', '', component_name)
        subject_clean = re.sub(r'\s+', '', subject_name)

        # 精确匹配
        if component_clean == subject_clean:
            return True

        # 部分匹配：component_name 在 subject_name 中
        # 用于处理组合名称场景，如"主机"匹配"主机及推车"
        if component_clean in subject_clean:
            # 检查是否是完整的部件名（后面跟着连接词或分隔符）
            idx = subject_clean.find(component_clean)
            end_pos = idx + len(component_clean)

            # 如果在末尾，是合法匹配
            if end_pos == len(subject_clean):
                return True

            # 如果后面跟着连接词（及、和、与）或分隔符，是合法匹配
            next_char = subject_clean[end_pos]
            if next_char in '及和与-（([<《':
                return True

            # 如果后面跟着其他字符（字母/数字/中文），可能是误匹配
            return False

        # 部分匹配：subject_name 在 component_name 中
        # 用于处理名称缩写场景，但需要防止误匹配
        if subject_clean in component_clean:
            # 防误匹配检查：确保不是前缀匹配导致的错误
            # 例如："触摸屏"不应匹配"触摸屏电源适配器"
            idx = component_clean.find(subject_clean)
            end_pos = idx + len(subject_clean)

            # 如果subject_name在component_name末尾，是合法匹配
            if end_pos == len(component_clean):
                return True

            # 如果后面跟着分隔符（-、（、[等），是合法匹配
            next_char = component_clean[end_pos]
            if next_char in '-（([<《':
                return True

            # 如果后面跟着的是字母/数字/中文，说明是另一个词的开始，是误匹配
            # 例如："推车" + "线缆" -> "推车线缆套件"，这里的"线缆"是另一个词
            # 例如："触摸屏" + "电源" -> "触摸屏电源适配器"，这里的"电源"是另一个词
            return False

        return False

    def _check_components(self, sample_table: Optional[TableData],
                         photo_analysis: Dict[str, Any],
                         enable_detailed: bool = False) -> List[ComponentCheck]:
        """核对每个部件"""
        if not sample_table:
            return []

        component_checks = []

        # 从表格中提取部件列表
        components = self._extract_components_from_table(sample_table)

        # 获取照片和标签信息
        photos = photo_analysis.get('photos', [])
        labels = photo_analysis.get('labels', [])

        for component in components:
            component_name = component['name']

            # 初始化比对日志记录器
            logger = ComparisonLogger(component_name, enable_logging=enable_detailed)

            # 记录开始
            logger.start_step(
                "部件核对开始",
                "component_check",
                component_name=component_name,
                model=component.get('model', ''),
                serial_batch=component.get('serial_batch', '')
            )

            # 检查是否为"本次检测未使用"（清理换行符后检查）
            remark = component.get('remark', '')
            remark_clean = re.sub(r'\s+', '', remark)
            is_unused = '本次检测未使用' in remark_clean

            logger.start_step(
                "检查使用状态",
                "remark_check",
                remark=remark,
                is_unused=is_unused
            ).end_step(is_unused is not None, is_unused=is_unused)

            # 照片匹配 - 详细记录
            logger.start_step(
                "照片匹配",
                "photo_matching",
                available_photos=len(photos)
            )

            matched_photos = []
            for p in photos:
                is_match = self._is_component_name_match(component_name, p['subject_name'])
                if is_match and not p['is_label']:
                    matched_photos.append(p)

            has_photo = len(matched_photos) > 0
            logger.end_step(
                True,
                has_photo=has_photo,
                matched_count=len(matched_photos),
                matched_captions=[p['caption'] for p in matched_photos]
            )

            # 标签匹配 - 详细记录
            logger.start_step(
                "标签匹配",
                "label_matching",
                available_labels=len(labels)
            )

            matched_labels = []
            for l in labels:
                is_match = self._is_component_name_match(component_name, l['subject_name'])
                if is_match:
                    matched_labels.append(l)

            has_chinese_label = len(matched_labels) > 0
            logger.end_step(
                True,
                has_chinese_label=has_chinese_label,
                matched_count=len(matched_labels),
                matched_captions=[l['caption'] for l in matched_labels]
            )

            # 字段比对
            field_comparisons = []
            issues = []

            if is_unused:
                # 本次检测未使用的部件：只要有照片/标签就检查，没有也不报错
                if has_chinese_label:
                    # 进行OCR字段与表格字段比对
                    for idx, label_info in enumerate(matched_labels):
                        ocr_result_data = label_info.get('ocr_result', {})
                        ocr_result = OCRResult(**ocr_result_data) if ocr_result_data else None

                        if ocr_result:
                            logger.start_step(
                                f"OCR字段比对_{idx+1}",
                                "ocr_comparison",
                                label_caption=label_info.get('caption', ''),
                                label_page=label_info.get('page_num', 0)
                            )

                            comparisons = self._compare_component_fields(
                                component, ocr_result
                            )
                            field_comparisons.extend(comparisons)

                            comparison_results = []
                            for comp in comparisons:
                                comparison_results.append({
                                    "field": comp.field_name,
                                    "table": comp.table_value,
                                    "ocr": comp.ocr_value,
                                    "match": comp.is_match
                                })
                                if not comp.is_match:
                                    issues.append(
                                        f"{comp.field_name}: 表格'{comp.table_value}' vs OCR'{comp.ocr_value}'"
                                    )

                            logger.end_step(
                                True,
                                comparisons=comparison_results,
                                mismatch_count=sum(1 for c in comparisons if not c.is_match)
                            )

                # 未使用的部件，没有照片/标签是正常的
                if not has_photo and not has_chinese_label:
                    issues.append("本次检测未使用（无照片/标签）")
                elif not has_photo:
                    issues.append("缺少照片说明")
                elif not has_chinese_label:
                    issues.append("缺少中文标签")

                # 确定状态：未使用的部件最多是warning
                if field_comparisons and any(not c.is_match for c in field_comparisons):
                    status = 'warning'
                else:
                    status = 'pass' if has_photo or has_chinese_label else 'pass'
            else:
                # 正常使用的部件：必须有照片和标签
                if has_chinese_label:
                    # 进行OCR字段与表格字段比对
                    for idx, label_info in enumerate(matched_labels):
                        ocr_result_data = label_info.get('ocr_result', {})
                        ocr_result = OCRResult(**ocr_result_data) if ocr_result_data else None

                        if ocr_result:
                            logger.start_step(
                                f"OCR字段比对_{idx+1}",
                                "ocr_comparison",
                                label_caption=label_info.get('caption', ''),
                                label_page=label_info.get('page_num', 0)
                            )

                            comparisons = self._compare_component_fields(
                                component, ocr_result
                            )
                            field_comparisons.extend(comparisons)

                            comparison_results = []
                            for comp in comparisons:
                                comparison_results.append({
                                    "field": comp.field_name,
                                    "table": comp.table_value,
                                    "ocr": comp.ocr_value,
                                    "match": comp.is_match
                                })
                                if not comp.is_match:
                                    issues.append(
                                        f"{comp.field_name}: 表格'{comp.table_value}' vs OCR'{comp.ocr_value}'"
                                    )

                            logger.end_step(
                                True,
                                comparisons=comparison_results,
                                mismatch_count=sum(1 for c in comparisons if not c.is_match)
                            )
                else:
                    issues.append("缺少中文标签")

                if not has_photo:
                    issues.append("缺少照片说明")

                # 确定状态
                if issues:
                    status = 'fail' if not has_chinese_label or not has_photo else 'warning'
                else:
                    status = 'pass'

            # 结束部件核对
            logger.start_step(
                "部件核对完成",
                "component_check_complete",
                status=status,
                issue_count=len(issues)
            ).end_step(status != 'fail')

            # 构建结果
            check_result = ComponentCheck(
                component_name=component_name,
                has_photo=has_photo,
                has_chinese_label=has_chinese_label,
                field_comparisons=field_comparisons,
                issues=issues,
                status=status
            )

            # 如果启用详细模式，添加详细信息到extra字段
            if enable_detailed:
                check_result.comparison_details = logger.get_details()
                check_result.matched_photos = matched_photos
                check_result.matched_labels = matched_labels
                check_result.match_reason = "匹配成功" if (has_photo or has_chinese_label) else "未找到匹配"
                if is_unused:
                    check_result.match_reason = "本次检测未使用"

            component_checks.append(check_result)

        return component_checks

    def _extract_components_from_table(self, table: TableData) -> List[Dict[str, str]]:
        """从样品描述表格中提取部件列表"""
        components = []

        # 调试信息
        print(f"[DEBUG] 表格表头: {table.headers}")
        print(f"[DEBUG] 表格行数: {len(table.rows)}")

        # 找到各列索引
        name_col_idx = None
        model_col_idx = None
        serial_batch_col_idx = None
        prod_date_col_idx = None
        exp_date_col_idx = None

        for idx, header in enumerate(table.headers):
            header_clean = header.strip() if header else ''
            header_clean_no_space = re.sub(r'\s+', '', header_clean)

            # 部件名称列
            if name_col_idx is None:
                for synonym in self.COLUMN_SYNONYMS.get('部件名称', []):
                    if synonym in header_clean or header_clean in synonym:
                        name_col_idx = idx
                        print(f"[DEBUG] 找到部件名称列: idx={idx}, header='{header}'")
                        break

            # 规格型号列（映射到model）
            if model_col_idx is None:
                for synonym in self.COLUMN_SYNONYMS.get('规格型号', []):
                    if synonym in header_clean_no_space or header_clean_no_space in synonym:
                        model_col_idx = idx
                        print(f"[DEBUG] 找到规格型号列: idx={idx}, header='{header}'")
                        break

            # 序列号/批号列
            if serial_batch_col_idx is None:
                for synonym in self.COLUMN_SYNONYMS.get('序列号批号', []):
                    if synonym in header_clean_no_space or header_clean_no_space in synonym:
                        serial_batch_col_idx = idx
                        print(f"[DEBUG] 找到序列号/批号列: idx={idx}, header='{header}'")
                        break

            # 生产日期列
            if prod_date_col_idx is None:
                for synonym in self.COLUMN_SYNONYMS.get('生产日期', []):
                    if synonym in header_clean_no_space or header_clean_no_space in synonym:
                        prod_date_col_idx = idx
                        print(f"[DEBUG] 找到生产日期列: idx={idx}, header='{header}'")
                        break

            # 失效日期列
            if exp_date_col_idx is None:
                for synonym in self.COLUMN_SYNONYMS.get('失效日期', []):
                    if synonym in header_clean_no_space or header_clean_no_space in synonym:
                        exp_date_col_idx = idx
                        print(f"[DEBUG] 找到失效日期列: idx={idx}, header='{header}'")
                        break

        # 备注列（单独处理，不加入COLUMN_SYNONYMS）
        remark_col_idx = None
        for idx, header in enumerate(table.headers):
            header_clean = header.strip() if header else ''
            if '备注' in header_clean:
                remark_col_idx = idx
                print(f"[DEBUG] 找到备注列: idx={idx}, header='{header}'")
                break

        # 如果没找到部件名称列，可能是文本格式表格
        if name_col_idx is None and table.rows:
            print(f"[DEBUG] 未找到标准表格结构，尝试解析文本格式")
            return self._extract_components_from_text_format(table)

        if name_col_idx is None:
            print(f"[DEBUG] 无法识别表格结构，返回空列表")
            return components

        # 提取每行数据，使用标准化字段名
        for row_idx, row in enumerate(table.rows):
            if len(row) > name_col_idx:
                component_name = row[name_col_idx].strip() if row[name_col_idx] else ''
                # 清理部件名称中的换行符和多余空白
                component_name = re.sub(r'\s+', '', component_name)
                # 过滤掉空行和非数据行
                if component_name and not self._is_header_or_metadata_row(component_name):
                    # 使用标准化字段名存储数据
                    component = {'name': component_name}

                    # 型号规格 -> model
                    if model_col_idx is not None and model_col_idx < len(row):
                        model_value = row[model_col_idx].strip() if row[model_col_idx] else ''
                        model_value = re.sub(r'\s+', '', model_value)  # 清理换行符
                        component['model'] = model_value

                    # 序列号/批号 -> 同时作为serial_number和batch_number
                    if serial_batch_col_idx is not None and serial_batch_col_idx < len(row):
                        serial_batch_value = row[serial_batch_col_idx].strip() if row[serial_batch_col_idx] else ''
                        serial_batch_value = re.sub(r'\s+', '', serial_batch_value)
                        # 联合列：值可能是序列号或批号，同时存储在两个字段中
                        component['serial_number'] = serial_batch_value
                        component['batch_number'] = serial_batch_value
                        # 保留原始字段用于显示
                        component['serial_batch'] = serial_batch_value

                    # 生产日期 -> production_date
                    if prod_date_col_idx is not None and prod_date_col_idx < len(row):
                        prod_date_value = row[prod_date_col_idx].strip() if row[prod_date_col_idx] else ''
                        prod_date_value = re.sub(r'\s+', '', prod_date_value)
                        component['production_date'] = prod_date_value

                    # 失效日期 -> expiration_date
                    if exp_date_col_idx is not None and exp_date_col_idx < len(row):
                        exp_date_value = row[exp_date_col_idx].strip() if row[exp_date_col_idx] else ''
                        exp_date_value = re.sub(r'\s+', '', exp_date_value)
                        component['expiration_date'] = exp_date_value

                    # 备注
                    if remark_col_idx is not None and remark_col_idx < len(row):
                        remark_value = row[remark_col_idx].strip() if row[remark_col_idx] else ''
                        component['remark'] = remark_value

                    components.append(component)
                    print(f"[DEBUG] 提取部件 #{len(components)}: {component_name}, model={component.get('model', '')}, serial_batch={component.get('serial_batch', '')}, remark={component.get('remark', '')[:20]}")

        print(f"[DEBUG] 共提取 {len(components)} 个部件")
        return components

    def _is_header_or_metadata_row(self, text: str) -> bool:
        """判断是否为表头行或元数据行（非数据行）"""
        header_keywords = ['序号', '部件名称', '产品名称', '规格型号', '型号规格',
                          '序列号', '批号', '生产日期', '失效日期', '备注',
                          '被检样品主要部件包括']
        text_clean = text.strip()
        # 如果是纯数字（序号列），也认为是非数据行
        if text_clean.isdigit():
            return True
        for keyword in header_keywords:
            if keyword in text_clean:
                return True
        return False

    def _extract_components_from_text_format(self, table: TableData) -> List[Dict[str, str]]:
        """从文本格式的表格内容中提取部件（当PyMuPDF无法正确识别表格结构时）

        处理PDF表格被提取为单列文本的情况，如：
        被检样品主要部件包括：
        序
        号
        部件名称
        规格型号
        ...
        1
        心脏脉冲电场消融仪-主
        机
        PFA-GEN-01
        ...
        """
        components = []

        if not table.rows:
            return components

        # 获取所有文本内容（可能在第一行的第一列）
        text_content = ''
        for row in table.rows:
            for cell in row:
                if cell:
                    text_content += cell + '\n'

        print(f"[DEBUG] 文本格式内容长度: {len(text_content)}")

        # 解析文本内容（保留原始换行结构）
        lines = [l.rstrip() for l in text_content.split('\n') if l.strip()]

        # 找到第一个数据行（序号"1"）
        start_idx = -1
        for i, line in enumerate(lines):
            if line.strip() == '1':
                start_idx = i
                break

        if start_idx < 0:
            print(f"[DEBUG] 未找到数据开始位置")
            return components

        print(f"[DEBUG] 数据开始位置: {start_idx}")

        # 按列顺序解析数据
        i = start_idx
        while i < len(lines):
            line = lines[i].strip()

            # 检查是否是纯数字序号（新部件开始）
            if line.isdigit():
                seq_num = line
                print(f"[DEBUG] 找到序号: {seq_num}")

                # 收集部件名称（可能跨多行）
                i += 1
                component_name_parts = []
                while i < len(lines):
                    current = lines[i].strip()

                    # 检查是否是规格型号（通常以大写字母/数字开头，较短）
                    if re.match(r'^[A-Z0-9]', current) and len(current) < 30 and not current.startswith('心脏'):
                        break

                    # 检查是否是纯数字（序列号）
                    if current.isdigit() and len(current) > 5:
                        break

                    # 检查是否是日期格式
                    if re.match(r'^20\d{2}[-/]', current):
                        break

                    # 检查是否是备注标记
                    if current in ['/', '本次检测未使用']:
                        break

                    # 检查是否是下一个序号
                    if current.isdigit() and int(current) == int(seq_num) + 1:
                        i -= 1  # 回退，让外层循环处理
                        break

                    component_name_parts.append(current)
                    i += 1

                component_name = ' '.join(component_name_parts)
                # 清理部件名称中的换行符和多余空白
                component_name = re.sub(r'\s+', '', component_name)
                print(f"[DEBUG] 部件名称: {component_name}")

                # 当前行应该是规格型号
                model_spec = ''
                if i < len(lines):
                    model_spec = lines[i].strip()
                    print(f"[DEBUG] 规格型号: {model_spec}")
                    i += 1

                # 序列号/批号
                serial_batch = ''
                if i < len(lines):
                    serial_batch = lines[i].strip()
                    print(f"[DEBUG] 序列号/批号: {serial_batch}")
                    i += 1

                # 生产日期
                prod_date = ''
                if i < len(lines):
                    prod_date = lines[i].strip()
                    print(f"[DEBUG] 生产日期: {prod_date}")
                    i += 1

                # 备注
                remark = ''
                if i < len(lines):
                    remark_line = lines[i].strip()
                    if remark_line in ['/', '本次检测未使用']:
                        remark = remark_line
                        i += 1
                    elif '本次检测未' in remark_line:
                        # 备注可能跨行
                        remark_parts = [remark_line]
                        i += 1
                        while i < len(lines):
                            next_line = lines[i].strip()
                            if next_line.isdigit():  # 下一个序号
                                i -= 1
                                break
                            if re.match(r'^[A-Z0-9]', next_line) and len(next_line) < 30:
                                i -= 1
                                break
                            remark_parts.append(next_line)
                            i += 1
                        remark = ' '.join(remark_parts)
                    print(f"[DEBUG] 备注: {remark}")

                # 保存部件（使用标准化字段名）
                if component_name:
                    component = {
                        'name': component_name,
                        'model': model_spec,  # 标准化字段名
                        'serial_number': serial_batch,  # 联合列
                        'batch_number': serial_batch,   # 联合列
                        'production_date': prod_date,
                    }
                    # 保留原始字段用于显示
                    if remark:
                        component['remark'] = remark
                    if serial_batch:
                        component['serial_batch'] = serial_batch
                    components.append(component)
                    print(f"[DEBUG] 添加部件 #{len(components)}: {component_name[:40]}...")
            else:
                i += 1

        print(f"[DEBUG] 文本格式共提取 {len(components)} 个部件")
        return components

    def _compare_component_fields(self, component: Dict[str, str],
                                  ocr_result: OCRResult) -> List[FieldComparison]:
        """比对部件表格字段与OCR结果

        component字典使用标准化字段名（由_extract_components_from_table设置）：
        - 'model': 型号规格
        - 'serial_number': 序列号/批号（联合列）
        - 'batch_number': 序列号/批号（联合列）
        - 'production_date': 生产日期
        - 'expiration_date': 失效日期
        """
        comparisons = []

        # 字段映射配置：(component中的键, OCR字段键列表, 字段显示名)
        field_configs = [
            ('model', ['model'], '型号规格'),  # 标准化字段名
            ('production_date', ['production_date'], '生产日期'),
            ('expiration_date', ['expiration_date'], '失效日期'),
        ]

        # 处理序列号/批号联合列
        # 表格中是一个联合值（存储在serial_number和batch_number中），OCR中可能是序列号或批号
        serial_batch_table_value = component.get('serial_number', '')  # 使用标准化字段名
        serial_batch_ocr_value = None
        serial_batch_matched_key = None

        # 检查OCR结果中的序列号或批号
        for ocr_key in ['serial_number', 'batch_number']:
            if ocr_key in ocr_result.structured_data:
                ocr_value = ocr_result.structured_data[ocr_key].get('value', '')
                if ocr_value:
                    serial_batch_ocr_value = ocr_value
                    serial_batch_matched_key = ocr_key
                    break

        # 比对序列号/批号联合列（表格值与OCR识别的序列号或批号任一匹配即可）
        is_match = self._values_equal(serial_batch_table_value, serial_batch_ocr_value or '')
        comparisons.append(FieldComparison(
            field_name='序列号/批号',
            table_value=serial_batch_table_value,
            ocr_value=serial_batch_ocr_value or '',
            is_match=is_match,
            issue_type=None if is_match else 'mismatch'
        ))

        # 处理其他字段（使用标准化字段名从component获取）
        for comp_key, ocr_keys, display_name in field_configs:
            table_value = component.get(comp_key, '')

            # 在OCR结果中查找对应字段
            ocr_value = None
            for ocr_key in ocr_keys:
                if ocr_key in ocr_result.structured_data:
                    ocr_value = ocr_result.structured_data[ocr_key].get('value', '')
                    break

            # 比对
            is_match = self._values_equal(table_value, ocr_value or '')

            print(f"[DEBUG] 字段比对 '{display_name}': comp_key={comp_key}, table='{table_value}', ocr='{ocr_value}', match={is_match}")

            comparisons.append(FieldComparison(
                field_name=display_name,
                table_value=table_value,
                ocr_value=ocr_value or '',
                is_match=is_match,
                issue_type=None if is_match else 'mismatch'
            ))

        return comparisons

    def _check_third_page_extended_fields(
        self,
        pdf_path: str,
        third_page_num: Optional[int],
        third_page_fields: Dict[str, str],
        photo_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        核对第三页扩展字段（v2.2新增）

        核对型号规格、生产日期、产品编号/批号三个字段与中文标签的一致性
        """
        if not third_page_num:
            return {'comparisons': [], 'errors': []}

        # 提取样品名称（从第三页字段或首页字段）
        sample_name = third_page_fields.get('样品名称', '')

        # 获取照片页标签
        labels = photo_analysis.get('labels', [])

        # 调用第三页核对器
        comparisons, errors = third_page_checker.check_third_page_fields(
            third_page_fields, sample_name, labels
        )

        return {
            'comparisons': comparisons,
            'errors': errors
        }

    def _collect_issues(self, home_third_comparison: List[FieldComparison],
                       component_checks: List[ComponentCheck],
                       photo_analysis: Dict[str, Any],
                       inspection_item_check: Optional[Any] = None,
                       page_number_errors: Optional[List[ErrorItem]] = None,
                       third_page_extended_checks: Optional[Dict[str, Any]] = None) -> Tuple[List[ErrorItem], List[ErrorItem], List[ErrorItem]]:
        """收集所有问题"""
        errors = []
        warnings = []
        info = []

        # 首页与第三页比对问题
        for comp in home_third_comparison:
            if not comp.is_match:
                errors.append(ErrorItem(
                    level="ERROR",
                    message=f"首页与第三页'{comp.field_name}'不一致",
                    page_num=1,
                    location="首页/第三页",
                    details={
                        'home_value': comp.table_value,
                        'third_value': comp.ocr_value
                    }
                ))

        # 第三页扩展字段核对问题（v2.2新增）
        if third_page_extended_checks:
            # 添加扩展字段比对信息到info
            if third_page_extended_checks.get('comparisons'):
                for comp in third_page_extended_checks['comparisons']:
                    if comp.is_match:
                        info.append(ErrorItem(
                            level="INFO",
                            message=f"第三页扩展字段'{comp.field_name}'核对通过",
                            page_num=comp.page_num,
                            location=f"第三页表格/{comp.field_name}",
                            details={
                                'table_value': comp.table_value,
                                'label_value': comp.ocr_value
                            }
                        ))

            # 添加扩展字段错误
            if third_page_extended_checks.get('errors'):
                for error in third_page_extended_checks['errors']:
                    errors.append(error)

        # 部件问题
        for check in component_checks:
            if check.status == 'fail':
                for issue in check.issues:
                    errors.append(ErrorItem(
                        level="ERROR",
                        message=f"部件'{check.component_name}': {issue}",
                        location=f"样品描述表/{check.component_name}",
                        details={'component': check.component_name}
                    ))
            elif check.status == 'warning':
                for issue in check.issues:
                    warnings.append(ErrorItem(
                        level="WARN",
                        message=f"部件'{check.component_name}': {issue}",
                        location=f"样品描述表/{check.component_name}",
                        details={'component': check.component_name}
                    ))

        # 照片页统计
        info.append(ErrorItem(
            level="INFO",
            message=f"照片页统计: {photo_analysis.get('total_photos', 0)}张照片, {photo_analysis.get('total_labels', 0)}个标签",
            details=photo_analysis
        ))

        # 检验项目核对结果（新增 v2.1）
        if inspection_item_check and inspection_item_check.has_table:
            # 添加检验项目统计
            info.append(ErrorItem(
                level="INFO",
                message=f"检验项目表格: {inspection_item_check.total_items}个项目, "
                       f"{inspection_item_check.total_clauses}个条款, "
                       f"{inspection_item_check.correct_conclusions}个正确结论, "
                       f"{inspection_item_check.incorrect_conclusions}个错误结论",
                details={
                    'total_items': inspection_item_check.total_items,
                    'total_clauses': inspection_item_check.total_clauses,
                    'correct_conclusions': inspection_item_check.correct_conclusions,
                    'incorrect_conclusions': inspection_item_check.incorrect_conclusions,
                    'cross_page_continuations': inspection_item_check.cross_page_continuations
                }
            ))

            # 添加检验项目错误
            if inspection_item_check.errors:
                for error in inspection_item_check.errors:
                    errors.append(error)

        # 页码连续性错误（新增 v2.2）
        if page_number_errors:
            for error in page_number_errors:
                errors.append(error)

        return errors, warnings, info

    def _build_page_number_check_result(
        self,
        page_number_infos: List[Any],
        page_number_errors: List[ErrorItem]
    ) -> Optional[Dict[str, Any]]:
        """
        构建页码校验结果

        Args:
            page_number_infos: 页码信息列表
            page_number_errors: 页码错误列表

        Returns:
            页码校验结果字典，如果没有页码信息则返回None
        """
        if not page_number_infos:
            return None

        # 构建页码列表
        page_numbers = []
        for info in page_number_infos:
            # 查找该页的错误
            page_errors = [
                error for error in page_number_errors
                if error.page_num == info.page_num
            ]

            page_numbers.append({
                'page_num': info.page_num,
                'total_pages': info.total_pages,
                'current_page': info.current_page,
                'raw_text': info.raw_text,
                'errors': [
                    {
                        'type': error.details.get('error_code', 'UNKNOWN').replace('PAGE_NUMBER_ERROR_', ''),
                        'message': error.message
                    }
                    for error in page_errors
                ] if page_errors else []
            })

        # 构建连续性错误列表（去重，不包含具体页码错误）
        continuity_errors = []
        for error in page_number_errors:
            error_code = error.details.get('error_code', '')
            if error_code == 'PAGE_NUMBER_ERROR_001':
                error_type = 'skip' if '跳号' in error.message else 'duplicate'
            elif error_code == 'PAGE_NUMBER_ERROR_002':
                error_type = 'last_page_mismatch'
            elif error_code == 'PAGE_NUMBER_ERROR_003':
                error_type = 'mismatch_total'
            else:
                error_type = 'unknown'

            continuity_errors.append({
                'type': error_type,
                'message': error.message,
                'page_num': error.page_num
            })

        # 构建总页数信息
        total_pages_info = None
        if page_number_infos:
            first_info = page_number_infos[0]
            actual_count = len(page_number_infos)
            total_pages_info = {
                'declared_total': first_info.total_pages,
                'actual_count': actual_count,
                'is_match': first_info.total_pages == actual_count
            }

        return {
            'page_numbers': page_numbers,
            'continuity_errors': continuity_errors,
            'total_pages_info': total_pages_info
        }

    def _save_result(self, file_id: str, result: CheckResult):
        """保存核对结果"""
        result_path = Path(f"temp/{file_id}_result.json")
        result_path.parent.mkdir(exist_ok=True)

        with open(result_path, 'w', encoding='utf-8') as f:
            json.dump(result.dict(), f, ensure_ascii=False, indent=2)
