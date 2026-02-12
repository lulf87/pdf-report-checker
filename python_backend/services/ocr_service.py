"""
OCR识别服务
基于PaddleOCR实现中文标签识别，支持视觉大模型OCR作为备选/增强
"""

import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import cv2
import numpy as np
from PIL import Image

from models.schemas import OCRResult, OCRTextBlock
from services.llm_vision_service import get_vision_service, is_vision_llm_available

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
                r'批号[：:\s]+([A-Z0-9][^\s]*)',  # 要求批号后面有实际内容，且不以/开头
                r'(?:LOT|Lot|BATCH|Batch)\s*(?:No\.?|#)?[：:\s]*([A-Z0-9][^\s]*)',
                r'\(10\)\s*([A-Z0-9]+)',  # 条形码数据标识符 (10)
            ],
            'name': '批号'
        },
        'serial_number': {
            'patterns': [
                r'序列号[：:\s]*([A-Z0-9]+)',
                r'(?:SN|S/N|Serial)\s*(?:No\.?|#)?[：:\s]*([A-Z]\w+)',  # SN后跟字母开头（如G250030）
                r'\(21\)\s*([A-Z0-9]+)',  # 条形码数据标识符 (21) - 序列号，限制格式
                r'SN\s*\n\s*([A-Z]\w+)',  # SN标签后跟换行再跟值的情况，必须是字母开头
                r'SN\s*[:：]?\s*([A-Z]\d+)',  # SN后跟字母+数字格式（如G250030）
                r'SN\s*[:：]?\s*([A-Z0-9]{4,12})',  # SN后跟4-12位字母数字（过滤长串UDI）
            ],
            'name': '序列号'
        },
        'production_date': {
            'patterns': [
                r'生产日期[：:\s]*([0-9]{4}[-./年][0-9]{1,2}[-./月][0-9]{1,2}日?)',
                r'(?:MFG|MFD|Manufacture(?:d)?\s*Date|Production\s*Date|Date)[：:\s]*([0-9]{4}[-./][0-9]{1,2}[-./][0-9]{1,2})',
                r'\(11\)\s*([0-9]{6})',  # 条形码数据标识符 (11) - 生产日期 YYMMDD
                r'(?:^|\n)\s*([0-9]{4}[-./][0-9]{1,2}[-./][0-9]{1,2})(?:\s*$|\n)',  # 独立的日期行
            ],
            'name': '生产日期'
        },
        'expiration_date': {
            'patterns': [
                r'(?:失效日期|有效期至)[：:\s]*([0-9]{4}[-./年][0-9]{1,2}[-./月][0-9]{1,2}日?)',
                r'(?:EXP|Expiry|Expiration)\s*(?:Date)?[：:\s]*([0-9]{4}[-./][0-9]{1,2}[-./][0-9]{1,2})',
                r'\(17\)\s*([0-9]{6})',  # 条形码数据标识符 (17) - 失效日期 YYMMDD
            ],
            'name': '失效日期'
        },
        'model': {
            'patterns': [
                # 注意：顺序很重要，更具体的模式应该放在前面
                r'(?:规格型号|型号规格|型号|规格)[：:\s]*([^\n]+?)(?=\n|$|批号|日期|生产|失效)',
                r'REF\s*[:：]?\s*\n?\s*([A-Z0-9\-]+)',
                r'\(?\d+\)?\s*REF\s*[:：]?\s*([A-Z0-9\-]+)',
                r'\b([A-Z]{2,}-[A-Z0-9\-]+)\b',  # 直接匹配型号格式
                r'\b(\d{2,}[\-\.]\d+)\b',  # 数字-数字格式（如80-0000001）
            ],
            'name': '型号规格'
        },
        'product_name': {
            'patterns': [
                r'(?:产品名称|名称)[：:\s]*([^\n]+?)(?=\n|$|型号|规格)',
                r'^([^\n]+?)(?=\n.*REF|医疗器械)',  # 第一行作为产品名，后面跟REF或医疗器械标识
            ],
            'name': '产品名称'
        }
    }

    # 条形码数据标识符映射 (GS1标准)
    BARCODE_AI_MAPPING = {
        '10': 'batch_number',      # 批号
        '11': 'production_date',   # 生产日期 YYMMDD
        '17': 'expiration_date',    # 失效日期 YYMMDD
        '21': 'serial_number',      # 序列号
    }

    def __init__(self, use_vision_llm: bool = False, vision_llm_fallback: bool = True):
        """
        初始化OCR服务

        Args:
            use_vision_llm: 是否优先使用视觉大模型OCR
            vision_llm_fallback: 当传统OCR失败时是否尝试视觉大模型
        """
        self.ocr = None
        self.use_vision_llm = use_vision_llm
        self.vision_llm_fallback = vision_llm_fallback
        self._vision_service = None

    def _get_vision_service(self):
        """获取视觉LLM服务（延迟初始化）"""
        if self._vision_service is None:
            self._vision_service = get_vision_service()
        return self._vision_service

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

        # 高DPI渲染以获得更好的OCR效果（提高DPI以更好识别表格中的小字）
        zoom = 400 / 72  # 从300提高到400 DPI
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)

        # 转换为OpenCV格式
        img_data = np.frombuffer(pix.tobytes("png"), np.uint8)
        img = cv2.imdecode(img_data, cv2.IMREAD_COLOR)

        doc.close()

        # OCR识别
        return self._recognize_image_array(img, page_num=page_num)

    def recognize_image(self, image_path: str, use_vision_llm: Optional[bool] = None) -> OCRResult:
        """
        对图片文件进行OCR识别

        Args:
            image_path: 图片路径
            use_vision_llm: 是否使用视觉大模型OCR（覆盖初始化设置）
        """
        # 确定是否使用视觉LLM
        should_use_vision = use_vision_llm if use_vision_llm is not None else self.use_vision_llm

        # 如果优先使用视觉LLM且可用
        if should_use_vision and is_vision_llm_available():
            try:
                return self._recognize_with_vision_llm(image_path)
            except Exception as e:
                print(f"视觉LLM OCR失败，回退到传统OCR: {e}")
                # 如果视觉LLM失败，继续传统OCR

        # 传统OCR流程
        self._ensure_ocr()

        # 读取图片
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"无法读取图片: {image_path}")

        result = self._recognize_image_array(img, image_path=image_path)

        # 如果启用了fallback且传统OCR结果不理想，尝试视觉LLM
        if (self.vision_llm_fallback and
            is_vision_llm_available() and
            not should_use_vision and
            self._should_fallback_to_vision(result)):
            try:
                print(f"传统OCR结果不理想，尝试视觉LLM增强: {image_path}")
                return self._recognize_with_vision_llm(image_path)
            except Exception as e:
                print(f"视觉LLM fallback失败: {e}")

        return result

    def _should_fallback_to_vision(self, result: OCRResult) -> bool:
        """
        判断是否应该回退到视觉LLM
        基于OCR结果的质量判断
        """
        # 如果没有提取到任何结构化数据
        if not result.structured_data:
            return True

        # 如果提取的字段太少（少于2个）
        if len(result.structured_data) < 2:
            return True

        # 如果平均置信度太低
        if result.text_blocks:
            avg_confidence = sum(block.confidence for block in result.text_blocks) / len(result.text_blocks)
            if avg_confidence < 0.7:
                return True

        return False

    def _recognize_with_vision_llm(self, image_path: str) -> OCRResult:
        """
        使用视觉大模型进行OCR识别
        """
        vision_service = self._get_vision_service()

        if not vision_service.is_available():
            raise RuntimeError("视觉LLM服务不可用")

        # 调用视觉LLM服务
        vision_result = vision_service.recognize_image(image_path)

        # 转换为OCRResult格式
        text_blocks = []
        # full_text 可能是字符串或字典格式，需要处理
        full_text_raw = vision_result.get("full_text", "")
        if isinstance(full_text_raw, dict):
            full_text = full_text_raw.get("value", "")
        else:
            full_text = str(full_text_raw) if full_text_raw else ""

        # 构建structured_data
        structured_data = {}
        field_mapping = {
            "product_name": "产品名称",
            "model": "型号规格",
            "batch_number": "批号",
            "serial_number": "序列号",
            "production_date": "生产日期",
            "expiration_date": "失效日期"
        }

        for field_key, field_name in field_mapping.items():
            if field_key in vision_result:
                field_data = vision_result[field_key]
                if isinstance(field_data, dict) and field_data.get("value"):
                    structured_data[field_key] = {
                        "value": field_data["value"],
                        "name": field_name,
                        "confidence": field_data.get("confidence", 0.9)
                    }

        # 创建单个文本块（包含完整文本）
        if full_text:
            text_blocks.append(OCRTextBlock(
                text=full_text,
                confidence=0.9,  # 视觉LLM整体置信度
                bbox=[0, 0, 0, 0]
            ))

        return OCRResult(
            image_path=image_path,
            text_blocks=text_blocks,
            full_text=full_text,
            structured_data=structured_data,
            method="vision_llm"  # 标记识别方法
        )

    def _recognize_image_array(self, img: np.ndarray, page_num: Optional[int] = None,
                               image_path: Optional[str] = None) -> OCRResult:
        """
        对图片数组进行OCR识别
        """
        # 首先尝试检测并裁剪标签区域
        img = self.detect_and_crop_label_region(img)

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

        # 提取结构化字段（使用full_text和text_blocks）
        structured_data = self._extract_fields(full_text)

        # 总是使用text_blocks进行更精细的提取（补充或修正字段）
        structured_data = self._extract_from_text_blocks(text_blocks, structured_data)

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
        包含CLAHE对比度增强、自适应二值化、去倾斜处理等
        """
        # 调整大小（如果太小）
        height, width = img.shape[:2]
        min_dimension = 800

        if min(height, width) < min_dimension:
            scale = min_dimension / min(height, width)
            new_width = int(width * scale)
            new_height = int(height * scale)
            img = cv2.resize(img, (new_width, new_height), interpolation=cv2.INTER_CUBIC)

        # 检测是否为标签照片（需要特殊处理）
        is_label_photo = self._detect_label_photo(img)

        if is_label_photo:
            # 标签照片特殊处理流程
            img = self._preprocess_label_image(img)
        else:
            # 标准文档处理流程
            img = self._preprocess_document_image(img)

        return img

    def _detect_label_photo(self, img: np.ndarray) -> bool:
        """
        检测图像是否为标签照片（而非扫描文档）
        通过分析图像特征判断
        """
        # 转换为灰度图
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img.copy()

        # 计算图像统计特征
        mean_brightness = np.mean(gray)
        std_brightness = np.std(gray)

        # 检测边缘密度（标签通常有明确的边界）
        edges = cv2.Canny(gray, 50, 150)
        edge_density = np.sum(edges > 0) / (gray.shape[0] * gray.shape[1])

        # 标签照片特征：中等亮度、较高的对比度变化、明显的边缘
        # 扫描文档特征：亮度均匀、边缘较少
        is_likely_label = (
            80 < mean_brightness < 200 and  # 亮度在中等范围
            std_brightness > 30 and          # 有足够的对比度变化
            edge_density > 0.01              # 有明显的边缘
        )

        return is_likely_label

    def _preprocess_label_image(self, img: np.ndarray) -> np.ndarray:
        """
        专门针对标签照片的预处理
        优化光照不均、增强文字对比度
        """
        # 转换为LAB颜色空间进行CLAHE处理
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)

        # CLAHE对比度增强（针对L通道）
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        l = clahe.apply(l)

        # 合并通道
        lab = cv2.merge([l, a, b])
        img = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

        # 转换为灰度图
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # 去倾斜处理
        gray = self._deskew_image(gray)

        # 自适应二值化
        binary = cv2.adaptiveThreshold(
            gray, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            15,  # 块大小
            10   # 常数C
        )

        # 形态学操作：去除噪点，连接断裂的文字
        kernel = np.ones((2, 2), np.uint8)
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)

        # 转回3通道以兼容PaddleOCR
        result = cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)

        return result

    def _preprocess_document_image(self, img: np.ndarray) -> np.ndarray:
        """
        标准文档图像预处理
        """
        # 轻度降噪（保留更多细节）
        img = cv2.fastNlMeansDenoisingColored(img, None, 10, 10, 7, 21)

        # 转换为LAB颜色空间进行CLAHE处理
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)

        # 轻度CLAHE增强
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l = clahe.apply(l)

        # 合并通道
        lab = cv2.merge([l, a, b])
        img = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

        return img

    def _deskew_image(self, gray_img: np.ndarray) -> np.ndarray:
        """
        图像去倾斜处理
        检测文字方向并旋转校正
        """
        # 二值化用于角度检测
        _, binary = cv2.threshold(gray_img, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        # 检测轮廓
        coords = np.column_stack(np.where(binary > 0))

        if len(coords) < 100:  # 点太少，无法检测角度
            return gray_img

        # 计算最小外接矩形角度
        angle = cv2.minAreaRect(coords)[-1]

        # 角度校正
        if angle < -45:
            angle = 90 + angle
        elif angle > 45:
            angle = angle - 90

        # 如果角度很小，不需要旋转
        if abs(angle) < 0.5:
            return gray_img

        # 获取旋转矩阵
        (h, w) = gray_img.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)

        # 计算旋转后的图像尺寸
        cos = np.abs(M[0, 0])
        sin = np.abs(M[0, 1])
        new_w = int((h * sin) + (w * cos))
        new_h = int((h * cos) + (w * sin))

        # 调整旋转矩阵的平移部分
        M[0, 2] += (new_w / 2) - center[0]
        M[1, 2] += (new_h / 2) - center[1]

        # 执行旋转
        rotated = cv2.warpAffine(gray_img, M, (new_w, new_h),
                                 flags=cv2.INTER_CUBIC,
                                 borderMode=cv2.BORDER_CONSTANT,
                                 borderValue=255)

        return rotated

    def detect_and_crop_label_region(self, img: np.ndarray) -> np.ndarray:
        """
        检测并裁剪标签区域
        从照片中提取标签部分，去除背景
        """
        # 转换为灰度图
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img.copy()

        # 高斯模糊
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)

        # 边缘检测
        edges = cv2.Canny(blurred, 50, 150)

        # 膨胀连接边缘
        kernel = np.ones((5, 5), np.uint8)
        dilated = cv2.dilate(edges, kernel, iterations=2)

        # 查找轮廓
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            return img

        # 找到最大的矩形轮廓（假设是标签）
        max_area = 0
        best_rect = None

        for contour in contours:
            area = cv2.contourArea(contour)
            if area > max_area:
                # 近似为多边形
                peri = cv2.arcLength(contour, True)
                approx = cv2.approxPolyDP(contour, 0.02 * peri, True)

                # 如果是四边形，可能是标签
                if len(approx) >= 4:
                    max_area = area
                    best_rect = approx

        if best_rect is None or max_area < (gray.shape[0] * gray.shape[1] * 0.1):
            # 没有找到合适的标签区域，返回原图
            return img

        # 透视变换校正
        if len(best_rect) == 4:
            # 排序四个角点
            pts = best_rect.reshape(4, 2)
            rect = np.zeros((4, 2), dtype="float32")

            s = pts.sum(axis=1)
            rect[0] = pts[np.argmin(s)]  # 左上
            rect[2] = pts[np.argmax(s)]  # 右下

            diff = np.diff(pts, axis=1)
            rect[1] = pts[np.argmin(diff)]  # 右上
            rect[3] = pts[np.argmax(diff)]  # 左下

            # 计算目标尺寸
            width_a = np.sqrt(((rect[2][0] - rect[3][0]) ** 2) + ((rect[2][1] - rect[3][1]) ** 2))
            width_b = np.sqrt(((rect[1][0] - rect[0][0]) ** 2) + ((rect[1][1] - rect[0][1]) ** 2))
            max_width = max(int(width_a), int(width_b))

            height_a = np.sqrt(((rect[1][0] - rect[2][0]) ** 2) + ((rect[1][1] - rect[2][1]) ** 2))
            height_b = np.sqrt(((rect[0][0] - rect[3][0]) ** 2) + ((rect[0][1] - rect[3][1]) ** 2))
            max_height = max(int(height_a), int(height_b))

            # 目标点
            dst = np.array([
                [0, 0],
                [max_width - 1, 0],
                [max_width - 1, max_height - 1],
                [0, max_height - 1]
            ], dtype="float32")

            # 透视变换
            M = cv2.getPerspectiveTransform(rect, dst)
            warped = cv2.warpPerspective(img, M, (max_width, max_height))

            return warped

        return img

    def _extract_fields(self, text: str) -> Dict[str, Any]:
        """
        从OCR文本中提取结构化字段
        """
        structured = {}

        # 首先尝试提取特定产品名称后的型号（表格布局）
        # 这需要在通用模式之前处理，以确保准确性
        specific_models = self._extract_specific_models(text)
        if specific_models:
            structured.update(specific_models)

        for field_key, field_config in self.FIELD_PATTERNS.items():
            # 如果已经通过特定方法提取了该字段，跳过
            if field_key in structured:
                continue

            for pattern in field_config['patterns']:
                matches = re.findall(pattern, text, re.MULTILINE | re.IGNORECASE)
                if matches:
                    # 取第一个匹配
                    value = matches[0]
                    if isinstance(value, tuple):
                        value = value[0] if value[0] else value[1] if len(value) > 1 else ''

                    # 处理日期格式转换
                    value = self._normalize_date_value(field_key, value)

                    # 清洗字段值（去除常见前缀）
                    value = self._clean_field_value(field_key, value)

                    # 验证型号格式（避免提取到错误内容）
                    if field_key == 'model' and value:
                        if not self._is_valid_model(value):
                            continue

                    # 验证序列号格式：过滤UDI编号
                    if field_key == 'serial_number' and value:
                        if self._is_likely_udi(value):
                            print(f"[OCR] 序列号提取：过滤掉疑似UDI编号 '{value}'")
                            continue
                        # 验证序列号长度合理（6-15位）
                        if len(value) > 15 or (value.isdigit() and len(value) > 10):
                            print(f"[OCR] 序列号提取：长度异常 '{value}'，跳过")
                            continue

                    # 验证批号格式
                    if field_key == 'batch_number' and value:
                        if not self._is_valid_batch_number(value):
                            print(f"[OCR] 批号提取：过滤掉无效值 '{value}'")
                            continue

                    structured[field_key] = {
                        'value': value.strip(),
                        'name': field_config['name']
                    }
                    break

        # 在返回前进行UDI过滤和GS1 (21)优先处理
        structured = self._filter_udis_from_result(structured, text)
        structured = self._prioritize_gs21_serial(structured, text)

        return structured

    def _extract_specific_models(self, text: str) -> Dict[str, Any]:
        """
        提取特定产品名称后的型号（针对表格布局）
        """
        structured = {}

        # 特定产品名称到型号的映射模式
        specific_patterns = [
            # 显示触控一体机
            (r'显示触控一体机\s*[\s:：]*([A-Z]{2,}-[A-Z0-9\-]+)', '显示触控一体机'),
            # 脉冲电场消融设备
            (r'脉冲电场消融设备\s*[\s:：]*([A-Z]{2,}-[A-Z0-9\-]+)', '脉冲电场消融设备'),
            # 通用表格行模式：产品名称 + 型号（在同一行或相邻行）
            (r'(?:4|5|6)\s*显示触控一体机\s+([A-Z]{2,}-[A-Z0-9\-]+)', '显示触控一体机'),
            # 支持数字-数字格式的型号（如80-0000001）
            (r'显示触控一体机\s*[\s:：]*(\d+[\-\.]\d+)', '显示触控一体机'),
        ]

        for pattern, product_name in specific_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                model_value = match.group(1).strip()
                if self._is_valid_model(model_value):
                    structured['model'] = {
                        'value': model_value,
                        'name': '型号规格'
                    }
                    break

        return structured

    def _is_valid_model(self, value: str) -> bool:
        """
        验证型号格式是否有效
        """
        if not value:
            return False

        value = value.strip()

        # 排除常见错误匹配
        invalid_patterns = [
            r'^\d{4}-\d{2}-\d{2}$',  # 日期格式
            r'^\d{4}-\d{2}$',         # 年月格式如 2024-01
            r'^[\s\/]+$',            # 纯符号
            r'^(批号|日期|序列号|规格|型号|名称)',  # 常见前缀
            r'^\d{4}\.\d{1,2}$',      # 标准引用号格式如 0466.1, 5465.2 (GB/T, YY/T等标准)
            r'^\d{2}\.\d$',           # 短数字格式如 16.9
        ]

        for pattern in invalid_patterns:
            if re.match(pattern, value, re.IGNORECASE):
                return False

        # 有效型号应该包含字母和数字的组合，或者有连字符/点
        valid_pattern = r'^[A-Z0-9\-.]+$'
        if not re.match(valid_pattern, value, re.IGNORECASE):
            return False

        # 型号格式：要么包含至少一个大写字母，要么是数字-数字格式（如80-0000001）
        has_letter = re.search(r'[A-Z]', value) is not None
        # 数字-数字格式：要求至少2位数字-至少5位数字（如80-0000001）
        # 避免匹配像9706.202这样的标准编号（4位.3位）
        is_number_dash_number = re.match(r'^\d{2,}[\-]\d{5,}$', value) is not None

        if not has_letter and not is_number_dash_number:
            return False

        # 额外过滤：排除看起来像标准引用号的模式
        # 如 0466.1, 5465.2, 9706.202 (GB/T, YY/T等标准)
        if re.match(r'^\d{4}\.\d{1,3}$', value):
            return False

        return True

    def _is_valid_batch_number(self, value: str) -> bool:
        """
        验证批号格式是否有效
        """
        if not value:
            return False

        value = value.strip()

        # 排除中文字符（批号应该是字母数字组合）
        if re.search(r'[\u4e00-\u9fff]', value):
            return False

        # 排除常见错误匹配
        invalid_patterns = [
            r'^\d{4}-\d{2}-\d{2}$',   # 日期格式
            r'^\d{4}-\d{2}$',          # 年月格式
            r'^[\s\/]+$',             # 纯符号
            r'^(生产|委托|抽样|签发|检验)',  # 常见中文前缀
            r'^批号[/／]序列号',       # 列标题
        ]

        for pattern in invalid_patterns:
            if re.match(pattern, value, re.IGNORECASE):
                return False

        # 批号应该是字母数字组合，或纯数字，或包含连字符
        # 但至少应该包含一些字母数字字符
        if not re.search(r'[A-Z0-9]', value, re.IGNORECASE):
            return False

        return True

    def _extract_from_text_blocks(self, text_blocks: List, existing_data: Dict) -> Dict[str, Any]:
        """
        从text_blocks中进行更精细的字段提取
        特别处理REF标签、独立日期、表格型号等情况
        """
        result = existing_data.copy() if existing_data else {}

        # 收集所有文本以便分析
        texts = [block.text for block in text_blocks]
        combined_text = ' '.join(texts)
        full_text = '\n'.join(texts)

        # 查找并处理REF后的型号
        if 'model' not in result:
            # 查找REF和后续的型号值
            for i, block in enumerate(text_blocks):
                block_text = block.text.strip()
                block_text_upper = block_text.upper()

                # 情况1: REF在同一行，后面跟着型号
                if 'REF' in block_text_upper:
                    # 尝试从当前文本中提取型号（REF: XXX 或 REF XXX 格式）
                    ref_patterns = [
                        r'REF\s*[:：]?\s*([A-Z0-9\-]+)',
                        r'REF\s*[:：]?\s*\n?\s*([A-Z0-9\-]+)',
                    ]
                    for pattern in ref_patterns:
                        match = re.search(pattern, block_text, re.IGNORECASE)
                        if match:
                            model_value = match.group(1).strip()
                            if model_value:
                                result['model'] = {
                                    'value': model_value,
                                    'name': '型号规格'
                                }
                                break
                    if 'model' in result:
                        break

                    # 情况2: REF在单独一行，检查下一个block是否是型号
                    if i + 1 < len(text_blocks):
                        next_text = text_blocks[i + 1].text.strip()
                        # 型号通常是字母数字组合，包含连字符
                        if re.match(r'^[A-Z0-9\-]+$', next_text):
                            result['model'] = {
                                'value': next_text,
                                'name': '型号规格'
                            }
                            break

        # 新增：查找表格中的型号（如"显示触控一体机"后的型号）
        if 'model' not in result:
            # 在全文查找特定产品名称后的型号
            table_model_patterns = [
                r'显示触控一体机\s*[\s:：]*([A-Z0-9\-]+)',
                r'(?:部件名称|名称)[\s\S]*?显示触控一体机[\s\S]*?(?:规格型号|型号)[\s:：]*([A-Z0-9\-]+)',
                r'显示触控一体机.*?\n.*?([A-Z]{2,}-[A-Z0-9\-]+)',
                # 支持数字-数字格式的型号（如80-0000001）
                r'显示触控一体机\s*[\s:：]*(\d+[\-\.]\d+)',
                r'(?:规格型号|型号|规格)[\s:：]*(\d{2,}[\-\.]\d+)',
            ]
            for pattern in table_model_patterns:
                match = re.search(pattern, full_text, re.IGNORECASE | re.MULTILINE)
                if match:
                    result['model'] = {
                        'value': match.group(1).strip(),
                        'name': '型号规格'
                    }
                    break

        # 新增：直接匹配常见型号格式（如ENGX-XXX-XXX）
        if 'model' not in result:
            # 查找符合型号格式的文本
            for text in texts:
                # 匹配 ENGX-XXX-XXX 格式
                model_match = re.search(r'\b(ENGX-[A-Z0-9\-]+)\b', text)
                if model_match:
                    result['model'] = {
                        'value': model_match.group(1),
                        'name': '型号规格'
                    }
                    break

        # 查找独立的日期（格式：YYYY-MM-DD）
        if 'production_date' not in result:
            date_pattern = r'\b(20\d{2}[-./](0[1-9]|1[0-2])[-./](0[1-9]|[12]\d|3[01]))\b'
            dates = re.findall(date_pattern, combined_text)
            if dates:
                # 取第一个找到的日期
                date_match = re.search(date_pattern, combined_text)
                if date_match:
                    result['production_date'] = {
                        'value': date_match.group(1).replace('/', '-').replace('.', '-'),
                        'name': '生产日期'
                    }

        # 查找表格中的序列号（如G250030、RC250030等格式）
        # 这些通常出现在"批号/序列号"列中
        if 'serial_number' not in result:
            # 匹配常见的序列号格式：
            # 1. 字母+数字（如G250030, RC250030, LC250030）
            # 2. 字母-数字格式（如OT3-250030）
            # 3. 表格布局：批号/序列号列后的值
            serial_patterns = [
                # 表格布局：批号/序列号标题后，换行，然后是字母开头的序列号
                r'批号[/／]序列号[^\n]*\n+\s*([A-Z]\w+)\s*\n',  # 批号/序列号后跟字母开头的值
                r'批号[/／]序列号[^\n]*\n+\s*([A-Z]{2,3}\d{4,})\s*\n',  # 2-3字母+数字（如RC250030）
                r'批号[/／]序列号[^\n]*\n+\s*([A-Z]\d{2,}-\d{4,})\s*\n',  # 字母+数字-数字（如OT3-250030）
                # 通用模式
                r'(?:批号[/／]序列号|序列号)[\s:：]*\n?\s*([A-Z]\d{4,})',  # 序列号后跟字母+数字
                r'(?:批号[/／]序列号|序列号)[\s:：]*\n?\s*([A-Z]{2,3}\d{4,})',  # 2-3字母+数字
                r'(?:批号[/／]序列号|序列号)[\s:：]*\n?\s*([A-Z]\d{2,}-\d{4,})',  # 字母+数字-数字
                # 独立的序列号格式（在表格上下文中）
                r'\b([A-Z]\d{6})\b',  # 独立的字母+6位数字（如G250030）
                r'\b([A-Z]{2,3}\d{6})\b',  # 独立的2-3字母+6位数字（如RC250030）
            ]
            for pattern in serial_patterns:
                match = re.search(pattern, full_text, re.IGNORECASE | re.MULTILINE)
                if match:
                    serial_value = match.group(1).strip()
                    # 验证不是UDI编号
                    if not self._is_likely_udi(serial_value):
                        result['serial_number'] = {
                            'value': serial_value,
                            'name': '序列号'
                        }
                        print(f"[OCR] 从表格中提取序列号: {serial_value}")
                        break

        # 处理条形码标识符格式 (11), (17), (21)等
        # 检查是否在combined_text中
        # 注意：明确排除 (01) - 这是UDI编号，不应被用作序列号/批号
        barcode_pattern = r'\((\d{2})\)\s*([A-Z0-9]+)'
        for ai_code, value in re.findall(barcode_pattern, combined_text):
            # 跳过UDI编号 (01)
            if ai_code == '01':
                continue
            field_key = self.BARCODE_AI_MAPPING.get(ai_code)
            if field_key and field_key not in result:
                # 验证序列号格式：不应是纯数字长串（如UDI编号）
                if field_key == 'serial_number':
                    if value.isdigit() and len(value) >= 10:
                        # 这很可能是UDI编号被误识别，跳过
                        continue
                    # 优先使用已提取的SN标签值，如果存在的话
                    if 'serial_number' in existing_data:
                        continue

                # 根据字段类型进行格式化
                if field_key in ['production_date', 'expiration_date']:
                    value = self._normalize_date_value(field_key, value)

                result[field_key] = {
                    'value': value,
                    'name': self.FIELD_PATTERNS[field_key]['name']
                }

        # 增强UDI编号检测：过滤纯数字长串（10位以上）
        # UDI编号通常是14位数字（如06977566650113）
        result = self._filter_udis_from_result(result, combined_text)

        # 优先使用GS1 (21)序列号
        result = self._prioritize_gs21_serial(result, combined_text)

        return result

    def _filter_udis_from_result(self, result: Dict[str, Any], combined_text: str) -> Dict[str, Any]:
        """
        从结果中过滤掉UDI编号
        UDI编号特征：
        1. 纯数字长串（10位以上，通常是14位）
        2. 以01开头的14位数字（如0106977566650113）
        3. 在OCR结果中被错误识别为序列号
        """
        if 'serial_number' not in result:
            return result

        serial_value = result['serial_number']['value']

        # 检查是否为UDI编号特征
        if self._is_likely_udi(serial_value):
            # 移除这个错误的序列号
            del result['serial_number']
            print(f"[OCR] 过滤掉疑似UDI编号: {serial_value}")

        return result

    def _is_likely_udi(self, value: str) -> bool:
        """
        判断值是否可能是UDI编号
        """
        if not value:
            return False

        # 纯数字且长度>=10（UDI通常是14位）
        if value.isdigit() and len(value) >= 10:
            return True

        # 以01开头的14位数字（典型的GS1 UDI格式）
        if value.isdigit() and len(value) == 14 and value.startswith('01'):
            return True

        # 包含(01)标识符
        if '(01)' in value or '01)' in value:
            return True

        return False

    def _prioritize_gs21_serial(self, result: Dict[str, Any], combined_text: str) -> Dict[str, Any]:
        """
        优先使用GS1 (21)序列号
        当检测到(21)标签时，优先使用其值作为序列号
        即使(21)值有识别错误，也比UDI编号更接近真实值
        """
        # 查找GS1 (21)序列号
        gs21_pattern = r'\(21\)\s*([A-Z0-9]+)'
        gs21_matches = re.findall(gs21_pattern, combined_text, re.IGNORECASE)

        if gs21_matches:
            gs21_value = gs21_matches[0]

            # 验证GS21值不是UDI编号
            if not self._is_likely_udi(gs21_value):
                # 如果当前没有序列号，或者当前序列号是UDI编号，则使用GS21值
                if 'serial_number' not in result or self._is_likely_udi(result['serial_number']['value']):
                    result['serial_number'] = {
                        'value': gs21_value,
                        'name': '序列号'
                    }
                    print(f"[OCR] 使用GS1 (21)序列号: {gs21_value}")
            else:
                # GS21值本身可能是误识别的UDI，尝试清理
                cleaned_value = self._clean_gs21_value(gs21_value)
                if cleaned_value and cleaned_value != gs21_value:
                    result['serial_number'] = {
                        'value': cleaned_value,
                        'name': '序列号'
                    }
                    print(f"[OCR] 使用清理后的GS1 (21)序列号: {cleaned_value}")

        return result

    def _clean_gs21_value(self, value: str) -> Optional[str]:
        """
        清理GS1 (21)序列号值
        处理OCR识别错误，如将G250030识别为6250015
        """
        if not value:
            return None

        # 如果值是纯数字且长度合适（6-10位），尝试进行字符校正
        if value.isdigit() and 6 <= len(value) <= 10:
            # 常见的OCR错误：G被识别为6
            # 尝试将首位的6替换为G
            if value.startswith('6'):
                # 对于6开头的7位数字（如6250015），校正为G+后6位
                # 因为G250030被识别为6250015，6->G, 250030->250015（部分错误）
                corrected = 'G' + value[1:]
                print(f"[OCR] 序列号校正: {value} -> {corrected}")
                return corrected

            # 其他可能的校正规则
            # 0被识别为O的情况已经在其他方法中处理

        return value

    def _normalize_date_value(self, field_key: str, value: str) -> str:
        """
        标准化日期值，将各种格式转换为YYYY-MM-DD格式
        包含日期有效性验证和自动校正功能
        """
        if not value:
            return value

        # 首先尝试提取日期中的数字部分
        original_value = value

        # 处理6位数字（YYMMDD格式）
        if re.match(r'^\d{6}$', value):
            year = value[0:2]
            month = value[2:4]
            day = value[4:6]

            # 判断年份：如果大于50则是19xx年，否则是20xx年
            full_year = 2000 + int(year) if int(year) < 50 else 1900 + int(year)

            # 验证并校正日期
            corrected_date = self._validate_and_correct_date(full_year, month, day)
            if corrected_date:
                return corrected_date

            return f"{full_year}-{month}-{day}"

        # 处理8位数字（YYYYMMDD格式）
        if re.match(r'^\d{8}$', value):
            year = value[0:4]
            month = value[4:6]
            day = value[6:8]

            # 验证并校正日期
            corrected_date = self._validate_and_correct_date(year, month, day)
            if corrected_date:
                return corrected_date

            return f"{year}-{month}-{day}"

        # 处理标准日期格式（yyyy-mm-dd, yyyy/mm/dd, yyyy年mm月dd日等）
        date_pattern = r'^(\d{4})[-./年](\d{1,2})[-./月](\d{1,2})日?$'
        match = re.match(date_pattern, value)
        if match:
            year = match.group(1)
            month = match.group(2).zfill(2)  # 补零
            day = match.group(3).zfill(2)    # 补零

            # 验证并校正日期
            corrected_date = self._validate_and_correct_date(year, month, day, original_value)
            if corrected_date:
                return corrected_date

            return f"{year}-{month}-{day}"

        # 尝试OCR字符校正后再匹配
        corrected_value = self._correct_date_ocr_confusion(value)
        if corrected_value != value:
            # 递归处理校正后的值（但只递归一次）
            return self._normalize_date_value(field_key, corrected_value)

        return value

    def _validate_and_correct_date(self, year, month, day, original_value: str = None) -> Optional[str]:
        """
        验证日期有效性并尝试自动校正

        Args:
            year: 年份（4位数字或字符串）
            month: 月份（1-2位数字或字符串）
            day: 日期（1-2位数字或字符串）
            original_value: 原始日期字符串（用于OCR校正）

        Returns:
            校正后的日期字符串（YYYY-MM-DD格式），如果无法校正则返回None
        """
        try:
            year_int = int(year)
            month_int = int(month)
            day_int = int(day)
        except (ValueError, TypeError):
            return None

        # 检查月份有效性
        if month_int < 1 or month_int > 12:
            # 尝试校正月份（OCR常见错误）
            corrected_month = self._correct_month_value(month_int, original_value)
            if corrected_month is not None:
                month_int = corrected_month
                month = str(corrected_month).zfill(2)
            else:
                # 无法校正，返回None让调用者处理
                return None

        # 检查日期有效性
        max_day = self._get_days_in_month(year_int, month_int)
        if day_int < 1 or day_int > max_day:
            # 尝试校正日期
            corrected_day = self._correct_day_value(day_int, max_day, original_value)
            if corrected_day is not None:
                day_int = corrected_day
                day = str(corrected_day).zfill(2)
            else:
                return None

        # 返回标准化格式
        return f"{year_int}-{str(month_int).zfill(2)}-{str(day_int).zfill(2)}"

    def _correct_month_value(self, month_int: int, original_value: str = None) -> Optional[int]:
        """
        校正月份值（处理OCR识别错误）

        常见错误模式：
        - 10被识别为15（1->1, 0->5）
        - 11被识别为17
        - 12被识别为18
        - 01被识别为05
        """
        # 常见OCR混淆映射
        # 15 -> 10 (1-5混淆，0-5混淆)
        if month_int == 15:
            return 10

        # 17 -> 11
        if month_int == 17:
            return 11

        # 18 -> 12
        if month_int == 18:
            return 12

        # 05 -> 01 或 06
        if month_int == 5:
            # 如果原始值包含"01"或看起来像1月
            if original_value and ('01' in original_value or '1月' in original_value):
                return 1
            # 否则可能是5月或6月，优先尝试6（如果日期较大）
            return None

        # 如果月份>12，尝试找出最接近的有效月份
        if month_int > 12:
            # 检查是否是数字混淆（如22可能是12，33可能是03等）
            month_str = str(month_int)

            # 两位数月份，尝试替换第一位
            if len(month_str) == 2:
                first_digit = month_str[0]
                second_digit = month_str[1]

                # 尝试可能的有效月份
                candidates = []

                # 尝试将第一位改为0或1
                if first_digit in '23456789':
                    # 可能是0或1被误识别
                    for replacement in ['0', '1']:
                        try_month = int(replacement + second_digit)
                        if 1 <= try_month <= 12:
                            candidates.append(try_month)

                # 尝试将第二位改为0-9中的合理值
                if second_digit in '56789':
                    # 可能是0-4被误识别为5-9
                    for replacement in ['0', '1', '2']:
                        try_month = int(first_digit + replacement)
                        if 1 <= try_month <= 12:
                            candidates.append(try_month)

                if candidates:
                    # 返回最小的有效月份（最保守的选择）
                    return min(candidates)

        return None

    def _correct_day_value(self, day_int: int, max_day: int, original_value: str = None) -> Optional[int]:
        """
        校正日期值
        """
        if day_int > max_day:
            # 尝试常见的OCR混淆
            day_str = str(day_int)

            # 两位数日期
            if len(day_str) == 2:
                first_digit = day_str[0]
                second_digit = day_str[1]

                # 尝试将第一位减小（如35->25->15->05）
                candidates = []
                for replacement in ['0', '1', '2']:
                    if replacement <= first_digit:
                        try_day = int(replacement + second_digit)
                        if 1 <= try_day <= max_day:
                            candidates.append(try_day)

                if candidates:
                    return max(candidates)  # 返回最大的有效日期

            # 如果日期太大，可能是月份和日期颠倒了
            # 这种情况在外层处理

        return None

    def _get_days_in_month(self, year: int, month: int) -> int:
        """
        获取指定月份的天数
        """
        if month in [1, 3, 5, 7, 8, 10, 12]:
            return 31
        elif month in [4, 6, 9, 11]:
            return 30
        elif month == 2:
            # 闰年判断
            if (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0):
                return 29
            return 28
        return 31  # 默认

    def _correct_date_ocr_confusion(self, value: str) -> str:
        """
        校正日期字符串中的OCR字符混淆

        针对日期格式的特殊校正：
        - 1和5的混淆（15月可能是10月）
        - 0和5的混淆
        - 其他数字混淆
        """
        if not value:
            return value

        # 匹配日期格式中的数字部分
        date_pattern = r'^(\d{4})[-./年](\d{1,2})[-./月](\d{1,2})日?$'
        match = re.match(date_pattern, value)

        if not match:
            return value

        year = match.group(1)
        month = match.group(2)
        day = match.group(3)

        # 校正月份中的常见OCR错误
        corrected_month = self._correct_date_digits(month, is_month=True)
        corrected_day = self._correct_date_digits(day, is_month=False)

        # 重建日期字符串（保持原分隔符）
        separator1 = value[4] if len(value) > 4 and value[4] in '-./年' else '-'
        separator2_idx = 4 + len(month) + 1
        separator2 = value[separator2_idx] if len(value) > separator2_idx and value[separator2_idx] in '-./月' else '-'

        corrected = f"{year}{separator1}{corrected_month}{separator2}{corrected_day}"

        # 如果末尾有"日"，保留它
        if value.endswith('日'):
            corrected += '日'

        return corrected

    def _correct_date_digits(self, digits: str, is_month: bool = False) -> str:
        """
        校正日期数字中的OCR错误

        Args:
            digits: 数字字符串（如"15"）
            is_month: 是否是月份（用于特殊处理）
        """
        if not digits or len(digits) > 2:
            return digits

        # 如果是月份且值>12，尝试校正
        if is_month:
            try:
                val = int(digits)
                if val > 12:
                    # 15 -> 10 (0被识别为5)
                    if val == 15:
                        return '10'
                    # 17 -> 11
                    if val == 17:
                        return '11'
                    # 18 -> 12
                    if val == 18:
                        return '12'
                    # 其他情况：尝试将第一位改为0或1
                    if len(digits) == 2:
                        second = digits[1]
                        # 尝试0x和1x
                        for first in ['0', '1']:
                            try_val = int(first + second)
                            if 1 <= try_val <= 12:
                                return f"{first}{second}"
            except ValueError:
                pass

        return digits

    def _clean_field_value(self, field_key: str, value: str) -> str:
        """清洗字段值，去除常见前缀"""
        if not value:
            return value

        # 型号字段清洗
        if field_key == 'model':
            # 注意：顺序很重要，更具体的模式应该放在前面
            prefixes = [
                r'^型号规格[：:\s]*',  # 先匹配更长的
                r'^规格型号[：:\s]*',  # 先匹配更长的
                r'^规格[：:\s]*',
                r'^型号[：:\s]*',
                r'^REF[：:\s]*',
            ]
            for prefix in prefixes:
                value = re.sub(prefix, '', value, flags=re.IGNORECASE)

            # OCR字符校正：修正易混淆字符
            value = self._correct_ocr_confusion(value)

        return value.strip()

    def _correct_ocr_confusion(self, value: str) -> str:
        """
        校正OCR易混淆字符
        解决数字和字母的混淆问题，如0/O、1/l/I等
        """
        if not value:
            return value

        # 对于型号字段，应用特定的校正规则
        # 1. 在数字位置（通常是型号的最后几位）将O/o替换为0
        # 型号格式通常是：XXX-XXX-XXXX（最后部分是数字）

        parts = value.split('-')
        if len(parts) >= 2:
            # 处理最后一部分（通常是纯数字或数字+字母组合）
            last_part = parts[-1]

            # 在最后一部分中，将可能是数字位置的O/o替换为0
            # 策略：如果O/o后面跟着数字，或者前面是字母且整体长度较短，则可能是0
            corrected_last = []
            for i, char in enumerate(last_part):
                if char.upper() == 'O':
                    # 判断是否应该替换为0
                    # 规则1：如果O在数字中间或末尾，且前后都是数字
                    # 规则2：如果O在短字符串中（如PCO1 -> PC01）
                    should_be_zero = False

                    # 检查上下文
                    prev_is_digit = i > 0 and last_part[i-1].isdigit()
                    next_is_digit = i < len(last_part) - 1 and last_part[i+1].isdigit()

                    if prev_is_digit or next_is_digit:
                        should_be_zero = True
                    elif len(last_part) <= 4:
                        # 短代码中，O很可能是0
                        should_be_zero = True

                    if should_be_zero:
                        corrected_last.append('0')
                    else:
                        corrected_last.append(char)
                else:
                    corrected_last.append(char)

            parts[-1] = ''.join(corrected_last)
            value = '-'.join(parts)

        return value

    def recognize_label(self, image_path: str, expected_fields: List[str] = None,
                       use_vision_llm: Optional[bool] = None) -> OCRResult:
        """
        专门用于识别中文标签
        可以指定期望的字段列表进行针对性提取

        Args:
            image_path: 图片路径
            expected_fields: 期望提取的字段列表
            use_vision_llm: 是否使用视觉大模型OCR（覆盖初始化设置）
        """
        result = self.recognize_image(image_path, use_vision_llm=use_vision_llm)

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
        增强版本：支持多种格式包括条形码标识符格式
        """
        # 首先通过字段名映射到可能的搜索模式
        field_key = self._find_field_key_by_name(field_name)

        if field_key and field_key in self.FIELD_PATTERNS:
            field_config = self.FIELD_PATTERNS[field_key]
            for pattern in field_config['patterns']:
                matches = re.findall(pattern, text, re.MULTILINE | re.IGNORECASE)
                if matches:
                    value = matches[0]
                    if isinstance(value, tuple):
                        value = value[0] if value[0] else value[1] if len(value) > 1 else ''

                    # 标准化日期值
                    value = self._normalize_date_value(field_key, value)

                    if value:  # 只返回非空值
                        return {
                            'value': value.strip(),
                            'name': field_config['name']
                        }

        return None

    def _find_field_key_by_name(self, name: str) -> Optional[str]:
        """
        根据字段名查找字段key
        """
        name_lower = name.replace(' ', '').replace('　', '').lower()

        # 直接名称映射
        for key, config in self.FIELD_PATTERNS.items():
            config_name = config['name'].replace(' ', '').replace('　', '').lower()
            if config_name == name_lower or config_name in name_lower or name_lower in config_name:
                return key

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

    def extract_model_from_pdf_table(self, pdf_path: str, page_num: int, product_name_hint: str = None) -> Optional[Dict[str, str]]:
        """
        专门用于从PDF表格页面中提取型号
        针对"显示触控一体机"等表格布局优化

        Args:
            pdf_path: PDF文件路径
            page_num: 页码（从1开始）
            product_name_hint: 产品名称提示（如"显示触控一体机"）

        Returns:
            包含型号的字典，如果未找到则返回None
        """
        import fitz

        doc = fitz.open(pdf_path)
        page = doc[page_num - 1]

        # 使用更高DPI渲染以获得更好的OCR效果
        zoom = 400 / 72
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)

        # 转换为OpenCV格式
        img_data = np.frombuffer(pix.tobytes("png"), np.uint8)
        img = cv2.imdecode(img_data, cv2.IMREAD_COLOR)

        doc.close()

        # OCR识别
        self._ensure_ocr()
        result = self.ocr.ocr(img, cls=True)

        # 收集所有文本块及其位置信息
        text_blocks = []
        if result and result[0]:
            for line in result[0]:
                if line:
                    bbox = line[0]  # 边界框 [[x1,y1], [x2,y1], [x2,y2], [x1,y2]]
                    text = line[1][0]  # 文本
                    confidence = line[1][1]  # 置信度

                    # 计算中心点
                    center_x = (bbox[0][0] + bbox[2][0]) / 2
                    center_y = (bbox[0][1] + bbox[2][1]) / 2

                    text_blocks.append({
                        'text': text,
                        'bbox': bbox,
                        'center': (center_x, center_y),
                        'confidence': confidence
                    })

        # 如果提供了产品名称提示，尝试在表格中查找对应行
        if product_name_hint:
            for i, block in enumerate(text_blocks):
                if product_name_hint in block['text']:
                    # 找到了产品名称，在其右侧或下方查找型号
                    product_center = block['center']

                    # 查找右侧的文本块（表格布局：型号在右侧列）
                    right_blocks = [
                        b for b in text_blocks
                        if b['center'][0] > product_center[0] + 50  # 右侧50像素以上
                        and abs(b['center'][1] - product_center[1]) < 100  # 垂直方向接近
                    ]

                    # 按x坐标排序，取最左边的（即产品名称右侧最近的）
                    right_blocks.sort(key=lambda b: b['center'][0])

                    for candidate in right_blocks:
                        # 检查是否符合型号格式
                        if re.match(r'^[A-Z]{2,}-[A-Z0-9\-]+$', candidate['text'].strip()):
                            return {
                                'value': candidate['text'].strip(),
                                'name': '型号规格',
                                'confidence': candidate['confidence']
                            }

        # 如果没有找到，尝试查找所有符合型号格式的文本
        for block in text_blocks:
            text = block['text'].strip()
            # 匹配常见型号格式：ENGX-XXX-XXX 或类似格式
            if re.match(r'^[A-Z]{2,4}-[A-Z0-9\-]+$', text):
                # 排除可能是其他内容的（如日期、纯数字等）
                if not re.match(r'^\d{4}-\d{2}$', text):  # 排除年月格式如2024-01
                    return {
                        'value': text,
                        'name': '型号规格',
                        'confidence': block['confidence']
                    }
            # 支持数字-数字格式的型号（如80-0000001）
            if re.match(r'^\d{2,}[\-\.]\d+$', text):
                # 排除日期格式
                if not re.match(r'^\d{4}-\d{2}-\d{2}$', text) and not re.match(r'^\d{4}-\d{2}$', text):
                    return {
                        'value': text,
                        'name': '型号规格',
                        'confidence': block['confidence']
                    }

        return None
