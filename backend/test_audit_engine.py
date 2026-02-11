"""
核对引擎单元测试
"""

import unittest
from audit_engine import (
    AuditEngine, CaptionParser, OCRFieldExtractor,
    Severity, AuditResult, ComponentRecord, OCRResult, PhotoCaption,
    create_photo_caption, create_ocr_result, create_component_record
)


class TestCaptionParser(unittest.TestCase):
    """测试说明文字解析器"""

    def test_extract_subject_name_basic(self):
        """测试基本主体名提取"""
        caption = "№113导管动态压力检测仪"
        result = CaptionParser.extract_subject_name(caption)
        self.assertEqual(result, "导管动态压力检测仪")

    def test_extract_subject_name_with_direction(self):
        """测试带方位词的主体名提取"""
        caption = "№113导管动态压力检测仪 前侧"
        result = CaptionParser.extract_subject_name(caption)
        self.assertEqual(result, "导管动态压力检测仪")

    def test_extract_subject_name_with_label(self):
        """测试带标签的主体名提取"""
        caption = "№113导管动态压力检测仪 中文标签"
        result = CaptionParser.extract_subject_name(caption)
        self.assertEqual(result, "导管动态压力检测仪")

    def test_extract_subject_name_with_direction_and_label(self):
        """测试带方位词和标签的主体名提取"""
        caption = "№113导管动态压力检测仪 前侧 中文标签样张"
        result = CaptionParser.extract_subject_name(caption)
        self.assertEqual(result, "导管动态压力检测仪")

    def test_extract_subject_name_no_prefix(self):
        """测试无编号前缀的主体名提取"""
        caption = "导管动态压力检测仪 中文标签"
        result = CaptionParser.extract_subject_name(caption)
        self.assertEqual(result, "导管动态压力检测仪")

    def test_is_chinese_label(self):
        """测试中文标签判断"""
        self.assertTrue(CaptionParser.is_chinese_label("中文标签"))
        self.assertTrue(CaptionParser.is_chinese_label("中文标签样张"))
        self.assertFalse(CaptionParser.is_chinese_label("英文标签"))
        self.assertFalse(CaptionParser.is_chinese_label("导管"))


class TestOCRFieldExtractor(unittest.TestCase):
    """测试OCR字段提取器"""

    def test_extract_lot_number(self):
        """测试批号提取"""
        text = "批号：ABC123456"
        result = OCRFieldExtractor.extract_fields(text)
        self.assertEqual(result.get('批号'), "ABC123456")

    def test_extract_lot_number_english(self):
        """测试英文批号提取"""
        text = "LOT No.: ABC123456"
        result = OCRFieldExtractor.extract_fields(text)
        self.assertEqual(result.get('批号'), "ABC123456")

    def test_extract_serial_number(self):
        """测试序列号提取"""
        text = "序列号：SN123456"
        result = OCRFieldExtractor.extract_fields(text)
        self.assertEqual(result.get('序列号'), "SN123456")

    def test_extract_mfg_date(self):
        """测试生产日期提取"""
        text = "生产日期：2024年01月15日"
        result = OCRFieldExtractor.extract_fields(text)
        self.assertEqual(result.get('生产日期'), "2024年01月15日")

    def test_extract_exp_date(self):
        """测试失效日期提取"""
        text = "失效日期：2026年01月14日"
        result = OCRFieldExtractor.extract_fields(text)
        self.assertEqual(result.get('失效日期'), "2026年01月14日")

    def test_extract_model(self):
        """测试型号规格提取"""
        text = "型号规格：ABC-123"
        result = OCRFieldExtractor.extract_fields(text)
        self.assertEqual(result.get('型号规格'), "ABC-123")


class TestAuditEnginePageConsistency(unittest.TestCase):
    """测试首页与第三页一致性核对"""

    def setUp(self):
        self.engine = AuditEngine()

    def test_consistent_fields(self):
        """测试一致的字段"""
        page1 = {
            '委 托 方': '测试公司',
            '样品名称': '测试样品',
            '型号规格': 'ABC-123'
        }
        page3 = {
            '委 托 方': '测试公司',
            '样品名称': '测试样品',
            '型号规格': 'ABC-123'
        }

        results = self.engine.audit(page1, page3, [], [], [])
        info_results = [r for r in results if r.severity == Severity.INFO]
        error_results = [r for r in results if r.severity == Severity.ERROR]

        self.assertEqual(len(error_results), 0)
        self.assertTrue(any('一致' in r.message for r in info_results))

    def test_inconsistent_fields(self):
        """测试不一致的字段"""
        page1 = {
            '委 托 方': '测试公司',
            '样品名称': '测试样品',
            '型号规格': 'ABC-123'
        }
        page3 = {
            '委 托 方': '测试公司',
            '样品名称': '不同样品',  # 不一致
            '型号规格': 'ABC-123'
        }

        results = self.engine.audit(page1, page3, [], [], [])
        error_results = [r for r in results if r.severity == Severity.ERROR]

        self.assertTrue(any('样品名称' in r.message and '不一致' in r.message for r in error_results))

    def test_strict_case_sensitive(self):
        """测试大小写敏感"""
        page1 = {'委 托 方': 'ABC', '样品名称': '', '型号规格': ''}
        page3 = {'委 托 方': 'abc', '样品名称': '', '型号规格': ''}

        results = self.engine.audit(page1, page3, [], [], [])
        error_results = [r for r in results if r.severity == Severity.ERROR]

        self.assertTrue(any('委 托 方' in r.message for r in error_results))


class TestAuditEngineTableVsOCR(unittest.TestCase):
    """测试表格与OCR比对"""

    def setUp(self):
        self.engine = AuditEngine()

    def test_single_component_match(self):
        """测试单一部件匹配"""
        page1 = {'委 托 方': '', '样品名称': '', '型号规格': ''}
        page3 = {'委 托 方': '', '样品名称': '', '型号规格': ''}

        component = create_component_record(
            1, "测试部件",
            批号="LOT123",
            生产日期="2024-01-15"
        )

        ocr = create_ocr_result(
            "label1.jpg",
            "№1测试部件 中文标签",
            "批号：LOT123\n生产日期：2024-01-15"
        )

        results = self.engine.audit(page1, page3, [component], [], [ocr])
        info_results = [r for r in results if r.severity == Severity.INFO]

        self.assertTrue(any('批号' in r.message and '一致' in r.message for r in info_results))

    def test_empty_table_slash_equivalence(self):
        """测试/与空白等价规则 - 表格为空OCR也为空"""
        page1 = {'委 托 方': '', '样品名称': '', '型号规格': ''}
        page3 = {'委 托 方': '', '样品名称': '', '型号规格': ''}

        component = create_component_record(
            1, "测试部件",
            批号="/",  # 表格为/
            生产日期=""
        )

        ocr = create_ocr_result(
            "label1.jpg",
            "№1测试部件 中文标签",
            "生产日期：2024-01-15"  # OCR没有批号
        )

        results = self.engine.audit(page1, page3, [component], [], [ocr])
        info_results = [r for r in results if r.severity == Severity.INFO]

        self.assertTrue(any('批号' in r.message and '均为空' in r.message for r in info_results))

    def test_empty_table_ocr_has_value(self):
        """测试/与空白等价规则 - 表格为空OCR有值（漏填）"""
        page1 = {'委 托 方': '', '样品名称': '', '型号规格': ''}
        page3 = {'委 托 方': '', '样品名称': '', '型号规格': ''}

        component = create_component_record(
            1, "测试部件",
            批号="/",  # 表格为/
            生产日期=""
        )

        ocr = create_ocr_result(
            "label1.jpg",
            "№1测试部件 中文标签",
            "批号：LOT123\n生产日期：2024-01-15"  # OCR有批号
        )

        results = self.engine.audit(page1, page3, [component], [], [ocr])
        error_results = [r for r in results if r.severity == Severity.ERROR]

        self.assertTrue(any('批号' in r.message and '漏填' in r.message for r in error_results))

    def test_multi_component_match(self):
        """测试同名多行匹配"""
        page1 = {'委 托 方': '', '样品名称': '', '型号规格': ''}
        page3 = {'委 托 方': '', '样品名称': '', '型号规格': ''}

        # 同名多行，用批号区分
        component1 = create_component_record(
            1, "导管",
            批号="LOT001",
            生产日期="2024-01-01"
        )
        component2 = create_component_record(
            2, "导管",
            批号="LOT002",
            生产日期="2024-02-01"
        )

        ocr1 = create_ocr_result(
            "label1.jpg",
            "№1导管 中文标签",
            "批号：LOT001\n生产日期：2024-01-01"
        )
        ocr2 = create_ocr_result(
            "label2.jpg",
            "№2导管 中文标签",
            "批号：LOT002\n生产日期：2024-02-01"
        )

        results = self.engine.audit(
            page1, page3,
            [component1, component2],
            [],
            [ocr1, ocr2]
        )
        info_results = [r for r in results if r.severity == Severity.INFO]

        # 两个部件都应该匹配成功
        self.assertEqual(sum(1 for r in info_results if '批号' in r.message and '一致' in r.message), 2)


class TestAuditEnginePhotoCoverage(unittest.TestCase):
    """测试照片覆盖性检查"""

    def setUp(self):
        self.engine = AuditEngine()

    def test_photo_coverage_pass(self):
        """测试照片覆盖通过"""
        page1 = {'委 托 方': '', '样品名称': '', '型号规格': ''}
        page3 = {'委 托 方': '', '样品名称': '', '型号规格': ''}

        component = create_component_record(1, "测试部件")

        caption = create_photo_caption("№1测试部件", "photo1.jpg")
        label_caption = create_photo_caption("№1测试部件 中文标签", "label1.jpg")

        results = self.engine.audit(
            page1, page3,
            [component],
            [caption, label_caption],
            []
        )
        info_results = [r for r in results if r.severity == Severity.INFO]

        self.assertTrue(any('照片说明' in r.message and '覆盖' in r.message for r in info_results))
        self.assertTrue(any('中文标签' in r.message and '覆盖' in r.message for r in info_results))

    def test_photo_coverage_missing_photo(self):
        """测试缺少照片说明"""
        page1 = {'委 托 方': '', '样品名称': '', '型号规格': ''}
        page3 = {'委 托 方': '', '样品名称': '', '型号规格': ''}

        component = create_component_record(1, "测试部件")

        # 只有标签说明，没有照片说明
        label_caption = create_photo_caption("№1测试部件 中文标签", "label1.jpg")

        results = self.engine.audit(
            page1, page3,
            [component],
            [label_caption],
            []
        )
        error_results = [r for r in results if r.severity == Severity.ERROR]

        self.assertTrue(any('照片说明' in r.message and '缺少' in r.message for r in error_results))

    def test_photo_coverage_missing_label(self):
        """测试缺少中文标签"""
        page1 = {'委 托 方': '', '样品名称': '', '型号规格': ''}
        page3 = {'委 托 方': '', '样品名称': '', '型号规格': ''}

        component = create_component_record(1, "测试部件")

        # 只有照片说明，没有标签
        caption = create_photo_caption("№1测试部件", "photo1.jpg")

        results = self.engine.audit(
            page1, page3,
            [component],
            [caption],
            []
        )
        error_results = [r for r in results if r.severity == Severity.ERROR]

        self.assertTrue(any('中文标签' in r.message and '缺少' in r.message for r in error_results))


class TestAuditEngineExtraFields(unittest.TestCase):
    """测试额外字段核对"""

    def setUp(self):
        self.engine = AuditEngine()

    def test_extra_fields_when_not_sample_desc(self):
        """测试当首页值不是'见样品描述栏'时的额外核对"""
        page1 = {
            '委 托 方': '某公司',  # 不是"见'样品描述'栏"
            '样品名称': '某产品',
            '型号规格': 'ABC'
        }
        page3 = {
            '委 托 方': '某公司',
            '样品名称': '某产品',
            '型号规格': 'ABC',
            '产品编号/批号': 'LOT123',
            '生产日期': '2024-01-15'
        }

        component = create_component_record(1, "某产品")

        caption = create_photo_caption("某产品 LOT123 2024-01-15", "photo1.jpg")
        label_caption = create_photo_caption("某产品 中文标签", "label1.jpg")

        ocr = create_ocr_result(
            "label1.jpg",
            "某产品 中文标签",
            "批号：LOT123\n生产日期：2024-01-15"
        )

        results = self.engine.audit(
            page1, page3,
            [component],
            [caption, label_caption],
            [ocr]
        )
        info_results = [r for r in results if r.severity == Severity.INFO]

        self.assertTrue(any('额外字段' in r.message and '批号' in r.message for r in info_results))

    def test_no_extra_audit_when_sample_desc(self):
        """测试当首页值是'见样品描述栏'时不进行额外核对"""
        page1 = {
            '委 托 方': "见'样品描述'栏",
            '样品名称': "见'样品描述'栏",
            '型号规格': "见'样品描述'栏"
        }
        page3 = {
            '委 托 方': "见'样品描述'栏",
            '样品名称': "见'样品描述'栏",
            '型号规格': "见'样品描述'栏",
            '产品编号/批号': 'LOT123',
            '生产日期': '2024-01-15'
        }

        component = create_component_record(1, "某产品")

        results = self.engine.audit(page1, page3, [component], [], [])

        # 不应该有额外字段核对的INFO结果
        self.assertFalse(any('额外字段' in r.message for r in results))


class TestAuditEngineSummary(unittest.TestCase):
    """测试核对结果汇总"""

    def setUp(self):
        self.engine = AuditEngine()

    def test_summary(self):
        """测试汇总功能"""
        page1 = {'委 托 方': 'A', '样品名称': 'B', '型号规格': 'C'}
        page3 = {'委 托 方': 'A', '样品名称': 'X', '型号规格': 'C'}  # 有一个不一致

        results = self.engine.audit(page1, page3, [], [], [])
        summary = self.engine.get_summary()

        self.assertEqual(summary['total'], len(results))
        self.assertEqual(summary['error'], 1)  # 一个不一致
        self.assertFalse(summary['passed'])


if __name__ == '__main__':
    unittest.main()
