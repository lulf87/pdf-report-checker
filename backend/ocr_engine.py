"""
OCR识别模块 - 中文标签图片OCR识别与字段提取

功能：
1. 对中文标签图片进行OCR识别（支持PaddleOCR和Tesseract）
2. 提取关键字段：批号、序列号、生产日期、失效日期、型号规格
3. 解析说明文字（caption），提取主体名
4. 结构化输出OCR结果
"""

import re
import json
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field, asdict
from enum import Enum
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class OCREngineType(Enum):
    """OCR引擎类型"""
    PADDLE = "paddle"
    TESSERACT = "tesseract"


@dataclass
class OCRResult:
    """OCR识别结果数据结构"""
    # 提取的字段
    batch_number: Optional[str] = None  # 批号
    serial_number: Optional[str] = None  # 序列号
    manufacture_date: Optional[str] = None  # 生产日期
    expiry_date: Optional[str] = None  # 失效日期
    model_spec: Optional[str] = None  # 型号规格

    # 原始OCR文本
    raw_text: str = ""

    # OCR引擎信息
    engine: str = ""
    confidence: Optional[float] = None

    # 解析元数据
    parsed_fields: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "批号": self.batch_number,
            "序列号": self.serial_number,
            "生产日期": self.manufacture_date,
            "失效日期": self.expiry_date,
            "型号规格": self.model_spec,
            "raw_text": self.raw_text,
            "engine": self.engine,
            "confidence": self.confidence,
            "parsed_fields": self.parsed_fields
        }

    def to_json(self, indent: int = 2) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)


@dataclass
class CaptionParseResult:
    """说明文字解析结果"""
    original: str = ""  # 原始caption
    subject_name: str = ""  # 主体名
    prefix_number: Optional[str] = None  # 前缀编号
    orientation: Optional[str] = None  # 方位词
    category: Optional[str] = None  # 类别词
    is_chinese_label: bool = False  # 是否为中文标签

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "original": self.original,
            "subject_name": self.subject_name,
            "prefix_number": self.prefix_number,
            "orientation": self.orientation,
            "category": self.category,
            "is_chinese_label": self.is_chinese_label
        }


class CaptionParser:
    """说明文字（caption）解析器"""

    # 前缀编号正则
    PREFIX_PATTERN = re.compile(
        r'^(?:№|No\.?|NO\.?|Number)\s*\d+\s*',
        re.IGNORECASE
    )

    # 方位词列表
    ORIENTATIONS = [
        '前侧', '后侧', '左侧', '右侧',
        '正面', '背面', '侧面',
        '俯视', '仰视',
        '顶部', '底部',
        '局部'
    ]

    # 类别词列表（按优先级排序，先匹配长的）
    CATEGORIES = [
        '中文标签样张',
        '中文标签',
        '英文标签',
        '原文标签',
        '标签'
    ]

    @classmethod
    def parse(cls, caption: str) -> CaptionParseResult:
        """
        解析说明文字，提取主体名

        规则：
        1. 去除前缀编号：^(?:№|No\\.?|NO\\.?|Number)\\s*\\d+\\s*
        2. 去除尾部方位词
        3. 去除尾部类别词
        4. 剩余文本即主体名
        """
        result = CaptionParseResult(original=caption)

        if not caption:
            return result

        text = caption.strip()

        # 步骤1: 去除前缀编号
        match = cls.PREFIX_PATTERN.match(text)
        if match:
            result.prefix_number = match.group(0).strip()
            text = text[match.end():].strip()

        # 检查是否为中文标签
        for cat in cls.CATEGORIES:
            if cat in text:
                if cat in ['中文标签', '中文标签样张']:
                    result.is_chinese_label = True
                result.category = cat
                break

        # 步骤2: 去除尾部方位词
        for orient in cls.ORIENTATIONS:
            if text.endswith(orient):
                result.orientation = orient
                text = text[:-len(orient)].strip()
                break

        # 步骤3: 去除尾部类别词（再次检查，因为可能在方位词之前）
        for cat in cls.CATEGORIES:
            if text.endswith(cat):
                result.category = cat
                if cat in ['中文标签', '中文标签样张']:
                    result.is_chinese_label = True
                text = text[:-len(cat)].strip()
                break

        # 步骤4: 剩余文本即主体名
        result.subject_name = text.strip()

        return result


class FieldExtractor:
    """字段提取器 - 从OCR文本中提取关键字段"""

    # 批号正则
    BATCH_PATTERNS = [
        # 中文批号
        re.compile(r'批号[：:\s]*([^\s]+)', re.IGNORECASE),
        # 英文批号
        re.compile(r'(?:LOT|Lot|BATCH|Batch)\s*(?:No\.?|#)?[：:\s]*([^\s]+)', re.IGNORECASE),
    ]

    # 序列号正则
    SERIAL_PATTERNS = [
        # 中文序列号
        re.compile(r'序列号[：:\s]*([^\s]+)', re.IGNORECASE),
        # 英文序列号
        re.compile(r'(?:SN|S/N|Serial)\s*(?:No\.?|#)?[：:\s]*([^\s]+)', re.IGNORECASE),
    ]

    # 生产日期正则
    MFG_PATTERNS = [
        # 中文生产日期
        re.compile(r'生产日期[：:\s]*([0-9]{4}[-./年][0-9]{1,2}[-./月][0-9]{1,2}日?)', re.IGNORECASE),
        # 英文生产日期
        re.compile(r'(?:MFG|MFD|Manufactured?\s*Date|Production\s*Date|Date)[：:\s]*([0-9]{4}[-./][0-9]{1,2}[-./][0-9]{1,2})', re.IGNORECASE),
        # 数字日期格式
        re.compile(r'(?:MFG|MFD)[：:\s]*([0-9]{4}[-./][0-9]{1,2}[-./][0-9]{1,2})', re.IGNORECASE),
    ]

    # 失效日期正则
    EXP_PATTERNS = [
        # 中文失效日期/有效期至
        re.compile(r'(?:失效日期|有效期至)[：:\s]*([0-9]{4}[-./年][0-9]{1,2}[-./月][0-9]{1,2}日?)', re.IGNORECASE),
        # 英文失效日期
        re.compile(r'(?:EXP|Expiry|Expiration)\s*(?:Date)?[：:\s]*([0-9]{4}[-./][0-9]{1,2}[-./][0-9]{1,2})', re.IGNORECASE),
    ]

    # 型号规格正则
    MODEL_PATTERNS = [
        # 型号规格/规格型号
        re.compile(r'(?:型号规格|规格型号)[：:\s]*([^\n]+?)(?=\s|$)', re.IGNORECASE),
        # 仅型号
        re.compile(r'型号[：:\s]*([^\n]+?)(?=\s|$)', re.IGNORECASE),
        # 仅规格
        re.compile(r'规格[：:\s]*([^\n]+?)(?=\s|$)', re.IGNORECASE),
        # Model
        re.compile(r'Model[：:\s]*([^\n]+?)(?=\s|$)', re.IGNORECASE),
    ]

    @classmethod
    def extract_field(cls, text: str, patterns: List[re.Pattern]) -> Optional[str]:
        """使用多个正则模式提取字段值"""
        for pattern in patterns:
            match = pattern.search(text)
            if match:
                value = match.group(1).strip()
                # 清理值
                value = value.replace('\n', ' ').replace('\r', '')
                return value if value else None
        return None

    @classmethod
    def extract_all(cls, text: str) -> Dict[str, Optional[str]]:
        """从文本中提取所有字段"""
        return {
            'batch_number': cls.extract_field(text, cls.BATCH_PATTERNS),
            'serial_number': cls.extract_field(text, cls.SERIAL_PATTERNS),
            'manufacture_date': cls.extract_field(text, cls.MFG_PATTERNS),
            'expiry_date': cls.extract_field(text, cls.EXP_PATTERNS),
            'model_spec': cls.extract_field(text, cls.MODEL_PATTERNS),
        }


class OCREngine:
    """OCR引擎基类"""

    def __init__(self, engine_type: OCREngineType):
        self.engine_type = engine_type
        self._engine = None

    def recognize(self, image_path: str) -> OCRResult:
        """识别图片中的文字"""
        raise NotImplementedError

    def recognize_batch(self, image_paths: List[str]) -> List[OCRResult]:
        """批量识别图片"""
        return [self.recognize(path) for path in image_paths]


class PaddleOCREngine(OCREngine):
    """PaddleOCR引擎实现（推荐用于中文识别）"""

    def __init__(self, use_gpu: bool = False, lang: str = 'ch'):
        super().__init__(OCREngineType.PADDLE)
        self.use_gpu = use_gpu
        self.lang = lang
        self._paddleocr = None

    def _init_engine(self):
        """延迟初始化PaddleOCR引擎"""
        if self._paddleocr is None:
            try:
                from paddleocr import PaddleOCR
                self._paddleocr = PaddleOCR(
                    use_angle_cls=True,
                    lang=self.lang,
                    use_gpu=self.use_gpu,
                    show_log=False
                )
                logger.info("PaddleOCR引擎初始化成功")
            except ImportError:
                logger.error("PaddleOCR未安装，请运行: pip install paddleocr")
                raise
        return self._paddleocr

    def recognize(self, image_path: str) -> OCRResult:
        """使用PaddleOCR识别图片"""
        engine = self._init_engine()

        try:
            result = engine.ocr(image_path, cls=True)

            # 提取文本和置信度
            texts = []
            confidences = []

            if result and result[0]:
                for line in result[0]:
                    if line:
                        text = line[1][0]  # 文本内容
                        conf = line[1][1]  # 置信度
                        texts.append(text)
                        confidences.append(conf)

            raw_text = '\n'.join(texts)
            avg_confidence = sum(confidences) / len(confidences) if confidences else None

            # 提取字段
            fields = FieldExtractor.extract_all(raw_text)

            return OCRResult(
                batch_number=fields.get('batch_number'),
                serial_number=fields.get('serial_number'),
                manufacture_date=fields.get('manufacture_date'),
                expiry_date=fields.get('expiry_date'),
                model_spec=fields.get('model_spec'),
                raw_text=raw_text,
                engine="paddleocr",
                confidence=avg_confidence,
                parsed_fields={
                    "text_lines": texts,
                    "confidences": confidences
                }
            )

        except Exception as e:
            logger.error(f"PaddleOCR识别失败: {e}")
            return OCRResult(
                raw_text="",
                engine="paddleocr",
                parsed_fields={"error": str(e)}
            )


class TesseractOCREngine(OCREngine):
    """Tesseract OCR引擎实现"""

    def __init__(self, lang: str = 'chi_sim+eng'):
        super().__init__(OCREngineType.TESSERACT)
        self.lang = lang

    def _init_engine(self):
        """检查Tesseract安装"""
        try:
            import pytesseract
            return pytesseract
        except ImportError:
            logger.error("pytesseract未安装，请运行: pip install pytesseract")
            raise

    def recognize(self, image_path: str) -> OCRResult:
        """使用Tesseract识别图片"""
        try:
            from PIL import Image
            pytesseract = self._init_engine()

            # 打开图片
            image = Image.open(image_path)

            # OCR识别
            raw_text = pytesseract.image_to_string(image, lang=self.lang)

            # 获取置信度信息
            try:
                data = pytesseract.image_to_data(image, lang=self.lang, output_type=pytesseract.Output.DICT)
                confidences = [conf for conf in data['conf'] if conf > 0]
                avg_confidence = sum(confidences) / len(confidences) if confidences else None
            except Exception:
                avg_confidence = None

            # 提取字段
            fields = FieldExtractor.extract_all(raw_text)

            return OCRResult(
                batch_number=fields.get('batch_number'),
                serial_number=fields.get('serial_number'),
                manufacture_date=fields.get('manufacture_date'),
                expiry_date=fields.get('expiry_date'),
                model_spec=fields.get('model_spec'),
                raw_text=raw_text.strip(),
                engine="tesseract",
                confidence=avg_confidence,
                parsed_fields={}
            )

        except Exception as e:
            logger.error(f"Tesseract识别失败: {e}")
            return OCRResult(
                raw_text="",
                engine="tesseract",
                parsed_fields={"error": str(e)}
            )


class OCREngineFactory:
    """OCR引擎工厂"""

    @staticmethod
    def create(engine_type: str = "paddle", **kwargs) -> OCREngine:
        """
        创建OCR引擎实例

        Args:
            engine_type: "paddle" 或 "tesseract"
            **kwargs: 引擎特定参数

        Returns:
            OCREngine实例
        """
        if engine_type.lower() == "paddle":
            return PaddleOCREngine(**kwargs)
        elif engine_type.lower() == "tesseract":
            return TesseractOCREngine(**kwargs)
        else:
            raise ValueError(f"不支持的OCR引擎类型: {engine_type}")


class LabelOCRProcessor:
    """标签OCR处理器 - 整合caption解析和OCR识别"""

    def __init__(self, engine: Optional[OCREngine] = None):
        """
        初始化处理器

        Args:
            engine: OCR引擎实例，默认为PaddleOCR
        """
        self.engine = engine or PaddleOCREngine()

    def process(self, image_path: str, caption: Optional[str] = None) -> Dict[str, Any]:
        """
        处理标签图片

        Args:
            image_path: 图片路径
            caption: 说明文字（可选）

        Returns:
            包含caption解析和OCR结果的字典
        """
        # 解析caption
        caption_result = CaptionParser.parse(caption) if caption else CaptionParseResult()

        # OCR识别
        ocr_result = self.engine.recognize(image_path)

        return {
            "caption": caption_result.to_dict(),
            "ocr": ocr_result.to_dict()
        }

    def process_batch(self, items: List[Tuple[str, Optional[str]]]) -> List[Dict[str, Any]]:
        """
        批量处理标签图片

        Args:
            items: [(image_path, caption), ...] 列表

        Returns:
            处理结果列表
        """
        results = []
        for image_path, caption in items:
            result = self.process(image_path, caption)
            results.append(result)
        return results


# 便捷函数
def extract_subject_name(caption: str) -> str:
    """从caption中提取主体名（便捷函数）"""
    return CaptionParser.parse(caption).subject_name


def is_chinese_label(caption: str) -> bool:
    """判断caption是否为中文标签（便捷函数）"""
    return CaptionParser.parse(caption).is_chinese_label


def extract_fields_from_text(text: str) -> Dict[str, Optional[str]]:
    """从文本中提取字段（便捷函数）"""
    return FieldExtractor.extract_all(text)


def create_ocr_engine(engine_type: str = "paddle", **kwargs) -> OCREngine:
    """创建OCR引擎（便捷函数）"""
    return OCREngineFactory.create(engine_type, **kwargs)


# 测试代码
if __name__ == "__main__":
    # 测试Caption解析
    test_captions = [
        "№113导管动态压力检测仪",
        "№113导管动态压力检测仪 前侧",
        "№113导管动态压力检测仪 中文标签",
        "No.456 测试设备 中文标签样张",
        "Number 789 样品名称 后侧 英文标签",
    ]

    print("=" * 60)
    print("Caption解析测试")
    print("=" * 60)

    for caption in test_captions:
        result = CaptionParser.parse(caption)
        print(f"\n原始: {caption}")
        print(f"  主体名: {result.subject_name}")
        print(f"  前缀编号: {result.prefix_number}")
        print(f"  方位词: {result.orientation}")
        print(f"  类别词: {result.category}")
        print(f"  中文标签: {result.is_chinese_label}")

    # 测试字段提取
    print("\n" + "=" * 60)
    print("字段提取测试")
    print("=" * 60)

    test_texts = [
        "LOT: ABC123\nSN: XYZ789\nMFG Date: 2024-01-15\nEXP: 2026-01-14",
        "批号：B2024001\n序列号：S123456\n生产日期：2024年01月15日\n失效日期：2026年01月14日",
        "Lot No. L123456\nSerial No. S/N 789\nManufacture Date: 2024.01.15\nExpiry Date: 2026.01.14",
    ]

    for text in test_texts:
        fields = FieldExtractor.extract_all(text)
        print(f"\n原文:\n{text}")
        print(f"提取字段: {json.dumps(fields, ensure_ascii=False, indent=2)}")
