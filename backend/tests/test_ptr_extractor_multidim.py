"""Synthetic multidimensional continuation tests for PTR extractor."""

from app.models.ptr_models import PTRTable
from app.services.ptr_extractor import PTRExtractor


class TestPTRContinuationByStructure:
    def test_should_merge_cross_page_with_repeated_header(self):
        extractor = PTRExtractor()

        p1 = PTRTable(
            table_number=1,
            headers=["参数", "型号", "常规数值", "标准设置", "允许误差"],
            rows=[
                ["参数", "型号", "常规数值", "标准设置", "允许误差"],
                ["脉冲宽度(ms)", "全部型号", "0.1...(0.1)...1.5", "0.4", "±20μs"],
            ],
            page=3,
            position=(0, 500),
        )
        p2 = PTRTable(
            table_number=None,
            headers=["参数", "型号", "常规数值", "标准设置", "允许误差"],
            rows=[
                ["参数", "型号", "常规数值", "标准设置", "允许误差"],
                ["基础频率(bpm)", "全部型号", "30...(5)...200", "60", "±20ms"],
            ],
            page=4,
            position=(0, 50),
        )

        merged = extractor._merge_continuation_tables([p1, p2])

        assert len(merged) == 1
        assert merged[0].table_number == 1
        assert merged[0].page == 3
        assert merged[0].page_end == 4
        assert [r[0] for r in merged[0].rows].count("参数") == 1
        assert any(r[0] == "基础频率(bpm)" for r in merged[0].rows)

    def test_should_merge_continuation_without_table_number_when_structure_matches(self):
        extractor = PTRExtractor()

        p1 = PTRTable(
            table_number=1,
            headers=["参数", "型号", "常规数值", "标准设置", "允许误差"],
            rows=[
                ["脉冲宽度(ms)", "Edora 8 DR", "20...(5)...350", "180-170-160", "±20"],
            ],
            page=8,
            position=(0, 520),
        )
        # no table number and no explicit headers on continuation page
        p2 = PTRTable(
            table_number=None,
            headers=["", "", "", "", ""],
            rows=[
                ["", "Edora 8 DR", "CLS模式下:20...(5)...350", "150-140-130", "±20"],
            ],
            page=9,
            position=(0, 40),
        )

        merged = extractor._merge_continuation_tables([p1, p2])

        assert len(merged) == 1
        assert merged[0].page_end == 9
        # first-column context should be repaired for continuation row
        assert merged[0].rows[-1][0] == "脉冲宽度(ms)"

    def test_should_not_merge_when_structure_fingerprint_differs(self):
        extractor = PTRExtractor()

        p1 = PTRTable(
            table_number=1,
            headers=["参数", "型号", "常规数值", "标准设置", "允许误差"],
            rows=[["脉冲宽度(ms)", "全部型号", "0.1...1.5", "0.4", "±20μs"]],
            page=5,
            position=(0, 600),
        )
        # same page adjacency but entirely different two-column narrative table
        p2 = PTRTable(
            table_number=None,
            headers=["字段", "内容"],
            rows=[["器械类型", "植入式心脏起搏器"]],
            page=6,
            position=(0, 60),
        )

        merged = extractor._merge_continuation_tables([p1, p2])
        assert len(merged) == 2
