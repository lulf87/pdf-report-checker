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
        assert merged[0].metadata.get("continuation_reason") in {
            "high_structure_similarity",
            "high_structure_with_overlap",
            "top_bottom_with_header_or_path_overlap",
        }
        assert [r[0] for r in merged[0].rows].count("参数") == 1
        assert any(r[0] == "基础频率(bpm)" for r in merged[0].rows)

    def test_should_merge_continuation_without_table_number_when_structure_matches(self):
        extractor = PTRExtractor()

        p1 = PTRTable(
            table_number=1,
            headers=["参数", "型号", "常规数值", "标准设置", "允许误差"],
            column_paths=[["参数"], ["型号"], ["常规数值"], ["标准设置"], ["允许误差"]],
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
            column_paths=[["参数"], ["型号"], ["常规数值"], ["标准设置"], ["允许误差"]],
            rows=[
                ["", "Edora 8 DR", "CLS模式下:20...(5)...350", "150-140-130", "±20"],
            ],
            page=9,
            position=(0, 40),
        )

        merged = extractor._merge_continuation_tables([p1, p2])

        assert len(merged) == 1
        assert merged[0].page_end == 9
        assert merged[0].metadata.get("continuation_reason") in {
            "high_structure_similarity",
            "top_bottom_with_header_or_path_overlap",
            "parameter_continuation_with_joint_evidence",
            "top_bottom_with_path_overlap",
        }
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
        # same width and both look parameter-like, but header semantics differ sharply
        p2 = PTRTable(
            table_number=None,
            headers=["参数", "通道", "输出模式", "报警策略", "备注"],
            rows=[["器械类型", "A通道", "单次输出", "高优先级", "植入式心脏起搏器"]],
            page=6,
            position=(0, 60),
        )

        merged = extractor._merge_continuation_tables([p1, p2])
        assert len(merged) == 2
        assert merged[1].metadata.get("continuation_reject_reason") in {
            "rejected: low_similarity",
            "rejected: no_header_path_overlap",
            "rejected: insufficient_position_evidence",
            "rejected: insufficient_joint_evidence",
        }

    def test_should_reject_continuation_when_similarity_is_low(self):
        extractor = PTRExtractor()

        p1 = PTRTable(
            table_number=1,
            headers=["参数", "型号", "常规数值", "标准设置", "允许误差"],
            rows=[
                ["脉冲宽度(ms)", "全部型号", "0.1...1.5", "0.4", "±20μs"],
            ],
            page=5,
            position=(0, 520),
        )
        p2 = PTRTable(
            table_number=None,
            headers=["目录", "章节", "摘要", "说明", "备注"],
            rows=[
                ["其他内容", "A", "B", "C", "D"],
            ],
            page=6,
            position=(0, 40),
        )

        merged = extractor._merge_continuation_tables([p1, p2])
        assert len(merged) == 2
        reasons = [m.metadata.get("continuation_reject_reason") for m in merged]
        assert "rejected: no_header_path_overlap" in reasons or "rejected: low_similarity" in reasons

    def test_should_reject_weak_parameter_signal_without_overlap(self):
        extractor = PTRExtractor()

        p1 = PTRTable(
            table_number=1,
            headers=["参数", "型号", "常规数值", "标准设置", "允许误差"],
            rows=[
                ["脉冲宽度(ms)", "Edora 8 DR", "20...(5)...350", "180-170-160", "±20"],
            ],
            page=10,
            position=(0, 520),
        )
        p2 = PTRTable(
            table_number=None,
            headers=["", "", "", "", ""],
            rows=[
                ["", "Edora 8 DR", "其他模式", "单次输出", "备注值"],
            ],
            page=11,
            position=(0, 40),
        )

        merged = extractor._merge_continuation_tables([p1, p2])

        assert len(merged) == 2
        assert merged[1].metadata.get("continuation_reject_reason") == "rejected: no_header_path_overlap"

    def test_should_not_merge_when_table_number_conflicts(self):
        extractor = PTRExtractor()

        p1 = PTRTable(
            table_number=7,
            headers=["参数", "型号", "常规数值", "标准设置", "允许误差"],
            rows=[["脉冲宽度(ms)", "全部型号", "0.1...1.5", "0.4", "±20μs"]],
            page=12,
            position=(0, 520),
        )
        p2 = PTRTable(
            table_number=8,
            headers=["参数", "型号", "常规数值", "标准设置", "允许误差"],
            rows=[["基础频率(bpm)", "全部型号", "30...200", "60", "±20ms"]],
            page=13,
            position=(0, 40),
        )

        merged = extractor._merge_continuation_tables([p1, p2])

        assert len(merged) == 2
        assert merged[1].metadata.get("continuation_reject_reason") == "table_number_conflict"
