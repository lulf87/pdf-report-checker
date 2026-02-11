"""
OCR识别服务
基于PaddleOCR实现中文标签识别
"""

import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import cv2
import numpy as np
from PIL import Image

from models.schemas import OCRResult, OCRTextBlock

# 延迟导入PaddleOCR，避免启动时加载
_paddle_ocr = None


def get_paddle_ocr():
    """获取PaddleOCR实例（延迟加载）"""
    global _paddle_ocr
    if _paddle_ocr is None:
        from paddleocr import PaddleOCR
        _paddle_ocr = PaddleOCR(
            use_angle_cls=True,
            lang='ch',
            show_log=False,
            use_gpu=False
        )
    return _paddle_ocr


class OCRService:
    """OCR识别服务"""

    # OCR字段提取正则表达式
    FIELD_PATTERNS = {
        'batch_number': {
            'patterns': [
                r'批号[：:\s]*([^\s]+)',
                r'(?:LOT|Lot|BATCH|Batch)\s*(?:No\.?|#)?[：:\s]*([^\s]+)',
            ],
            'name': '批号'
        },
        'serial_number': {
            'patterns': [
                r'序列号[：:\s]*([^\s]+)',
                r'(?:SN|S/N|Serial)\s*(?:No\.?|#)?[：:\s]*([^\s]+)',
            ],
            'name': '序列号'
        },
        'production_date': {
            'patterns': [
                r'生产日期[：:\s]*([0-9]{4}[-./年][0-9]{1,2}[-./月][0-9]{1,2}日?)',
                r'(?:MFG|MFD|Manufacture(?:d)?\s*Date|Production\s*Date|Date)[：:\s]*([0-9]{4}[-./][0-9]{1,2}[-./][0-9]{1,2})',
            ],
            'name': '生产日期'
        },
        'expiration_date': {
            'patterns': [
                r'(?:失效日期|有效期至)[：:\s]*([0-9]{4}[-./年][0-9]{1,2}[-./月][0-9]{1,2}日?)',
                r'(?:EXP|Expiry|Expiration)\s*(?:Date)?[：:\s]*([0-9]{4}[-./][0-9]{1,2}[-./][0-9]{1,2})',
            ],
            'name': '失效日期'
        },
        'model': {
            'patterns': [
                r'(?:型号|规格型号|型号规格)[：:\s]*([^\n]+?)(?=\n|$|规格|批号|日期)',
            ],
            'name': '型号规格'
        },
        'product_name': {
            'patterns': [
                r'(?:产品名称|名称)[：:\s]*([^\n]+?)(?=\n|$|型号|规格)',
            ],
            'name': '产品名称'
        }
    }

    def __init__(self):
        self.ocr = None

    def _ensure_ocr(self):
        """确保OCR引擎已初始化"""
        if self.ocr is None:
            self.ocr = get_paddle_ocr()

    def recognize_page(self, pdf_path: str, page_num: int) -> OCRResult:
        """
        对PDF页面进行OCR识别
        """
        import fitz

        self._ensure_ocr()

        # 将PDF页面转为图片
        doc = fitz.open(pdf_path)
        page = doc[page_num - 1]

        # 高DPI渲染以获得更好的OCR效果
        zoom = 300 / 72
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)

        # 转换为OpenCV格式
        img_data = np.frombuffer(pix.tobytes("png"), np.uint8)
        img = cv2.imdecode(img_data, cv2.IMREAD_COLOR)

        doc.close()

        # OCR识别
        return self._recognize_image_array(img, page_num=page_num)

    def recognize_image(self, image_path: str) -> OCRResult:
        """
        对图片文件进行OCR识别
        """
        self._ensure_ocr()

        # 读取图片
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"无法读取图片: {image_path}")

        return self._recognize_image_array(img, image_path=image_path)

    def _recognize_image_array(self, img: np.ndarray, page_num: Optional[int] = None,
                               image_path: Optional[str] = None) -> OCRResult:
        """
        对图片数组进行OCR识别
        """
        # 图片预处理
        processed_img = self._preprocess_image(img)

        # OCR识别
        result = self.ocr.ocr(processed_img, cls=True)

        # 解析结果
        text_blocks = []
        full_text_lines = []

        if result and result[0]:
            for line in result[0]:
                if line:
                    bbox = line[0]  # 边界框
                    text = line[1][0]  # 文本
                    confidence = line[1][1]  # 置信度

                    # 转换bbox格式
                    flat_bbox = [
                        bbox[0][0], bbox[0][1],
                        bbox[2][0], bbox[2][1]
                    ]

                    text_blocks.append(OCRTextBlock(
                        text=text,
                        confidence=confidence,
                        bbox=flat_bbox
                    ))

                    full_text_lines.append(text)

        full_text = '\n'.join(full_text_lines)

        # 提取结构化字段
        structured_data = self._extract_fields(full_text)

        return OCRResult(
            page_num=page_num,
            image_path=image_path,
            text_blocks=text_blocks,
            full_text=full_text,
            structured_data=structured_data
        )

    def _preprocess_image(self, img: np.ndarray) -> np.ndarray:
        """
        图片预处理以提高OCR准确率
        """
        # 调整大小（如果太小）
        height, width = img.shape[:2]
        min_dimension = 800

        if min(height, width) < min_dimension:
            scale = min_dimension / min(height, width)
            new_width = int(width * scale)
            new_height = int(height * scale)
            img = cv2.resize(img, (new_width, new_height), interpolation=cv2.INTER_CUBIC)

        # 轻度降噪
        img = cv2.fastNlMeansDenoisingColored(img, None, 10, 10, 7, 21)

        return img

    def _extract_fields(self, text: str) -> Dict[str, Any]:
        """
        从OCR文本中提取结构化字段
        """
        structured = {}

        for field_key, field_config in self.FIELD_PATTERNS.items():
            for pattern in field_config['patterns']:
                matches = re.findall(pattern, text)
                if matches:
                    # 取第一个匹配
                    value = matches[0]
                    if isinstance(value, tuple):
                        value = value[0] if value[0] else value[1] if len(value) > 1 else ''

                    structured[field_key] = {
                        'value': value.strip(),
                        'name': field_config['name']
                    }
                    break

        return structured

    def recognize_label(self, image_path: str, expected_fields: List[str] = None) -> OCRResult:
        """
        专门用于识别中文标签
        可以指定期望的字段列表进行针对性提取
        """
        result = self.recognize_image(image_path)

        # 如果指定了期望字段，进行额外处理
        if expected_fields:
            enhanced_data = {}
            for field in expected_fields:
                if field in result.structured_data:
                    enhanced_data[field] = result.structured_data[field]
                else:
                    # 尝试从全文搜索
                    enhanced_data[field] = self._search_field_in_text(result.full_text, field)

            result.structured_data = enhanced_data

        return result

    def _search_field_in_text(self, text: str, field_name: str) -> Optional[Dict[str, str]]:
        """
        在文本中搜索特定字段
        """
        # 构建灵活的搜索模式
        patterns = [
            rf'{field_name}[：:\s]*([^\n]+?)(?=\n|$)',
            rf'{field_name.replace(" ", "")}[：:\s]*([^\n]+?)(?=\n|$)',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text)
            if matches:
                return {
                    'value': matches[0].strip(),
                    'name': field_name
                }

        return None

    def compare_with_table(self, ocr_result: OCRResult, table_row: Dict[str, str]) -> List[Dict[str, Any]]:
        """
        比较OCR结果与表格行数据
        返回差异列表
        """
        differences = []

        for table_field, table_value in table_row.items():
            # 标准化表格值
            normalized_table_value = self._normalize_value(table_value)

            # 查找OCR中对应的字段
            ocr_field_value = None
            for ocr_field_key, ocr_field_data in ocr_result.structured_data.items():
                if self._field_names_match(table_field, ocr_field_data.get('name', '')):
                    ocr_field_value = ocr_field_data.get('value', '')
                    break

            if ocr_field_value is None:
                # 字段缺失
                if normalized_table_value and normalized_table_value != '/':
                    differences.append({
                        'field': table_field,
                        'table_value': table_value,
                        'ocr_value': None,
                        'status': 'missing_in_ocr'
                    })
            else:
                # 比较值
                normalized_ocr_value = self._normalize_value(ocr_field_value)

                if normalized_table_value != normalized_ocr_value:
                    differences.append({
                        'field': table_field,
                        'table_value': table_value,
                        'ocr_value': ocr_field_value,
                        'status': 'mismatch'
                    })

        return differences

    def _normalize_value(self, value: str) -> str:
        """
        标准化字段值用于比较
        """
        if value is None:
            return ''

        value = str(value).strip()

        # 空值和'/'视为等价
        if value == '' or value == '/':
            return ''

        # 统一全角/半角字符
        value = value.replace('／', '/')

        return value

    def _field_names_match(self, name1: str, name2: str) -> bool:
        """
        判断两个字段名是否匹配（处理同义词）
        """
        # 清理并标准化
        n1 = name1.replace(' ', '').replace('　', '').lower()
        n2 = name2.replace(' ', '').replace('　', '').lower()

        # 直接匹配
        if n1 == n2:
            return True

        # 同义词映射
        synonyms = {
            '批号': ['批号', 'lot', 'batch', 'batchno', 'lotno'],
            '序列号': ['序列号', 'sn', 's/n', 'serial', 'serialno'],
            '生产日期': ['生产日期', 'mfg', 'mfd', 'manufacturedate', 'productiondate'],
            '失效日期': ['失效日期', '有效期至', 'exp', 'expiry', 'expirationdate'],
            '型号规格': ['型号规格', '规格型号', '型号', '规格', 'model', 'specification'],
            '产品名称': ['产品名称', '名称', 'productname', 'name'],
        }

        # 检查是否属于同一组同义词
        for group in synonyms.values():
            if n1 in group and n2 in group:
                return True

        return False
