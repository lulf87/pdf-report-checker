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

    def test_should_merge_without_table_number_when_joint_evidence_is_strong(self):
        extractor = PTRExtractor()

        p1 = PTRTable(
            table_number=None,
            headers=["参数", "型号", "常规数值", "标准设置", "允许误差"],
            column_paths=[["参数"], ["型号"], ["常规数值"], ["标准设置"], ["允许误差"]],
            rows=[
                ["参数", "型号", "常规数值", "标准设置", "允许误差"],
                ["脉冲宽度(ms)", "全部型号", "0.1...(0.1)...1.5", "0.4", "±20μs"],
            ],
            page=14,
            position=(0, 520),
        )
        p2 = PTRTable(
            table_number=None,
            headers=["参数", "型号", "常规数值", "标准设置", "允许误差"],
            column_paths=[["参数"], ["型号"], ["常规数值"], ["标准设置"], ["允许误差"]],
            rows=[
                ["参数", "型号", "常规数值", "标准设置", "允许误差"],
                ["基础频率(bpm)", "全部型号", "30...(5)...200", "60", "±20ms"],
            ],
            page=15,
            position=(0, 40),
        )

        merged = extractor._merge_continuation_tables([p1, p2])

        assert len(merged) == 1
        assert merged[0].metadata.get("continuation_reason") in {
            "high_structure_similarity",
            "high_structure_with_overlap",
            "top_bottom_with_header_or_path_overlap",
        }
        assert merged[0].metadata.get("continuation_evidence", {}).get("strong_missing_number_evidence") is True
        assert any(row[0] == "基础频率(bpm)" for row in merged[0].rows)

    def test_assess_without_table_number_should_hit_high_structure_with_overlap(self, monkeypatch):
        extractor = PTRExtractor()
        previous = PTRTable(table_number=None, headers=["A", "B", "C"], rows=[["1", "2", "3"]], page=30, position=(0, 300))
        current = PTRTable(table_number=None, headers=["A", "B", "C"], rows=[["4", "5", "6"]], page=31, position=(0, 260))

        monkeypatch.setattr(extractor, "_table_structure_similarity", lambda *args, **kwargs: 0.8)
        monkeypatch.setattr(extractor, "_table_header_text_overlap_ratio", lambda *args, **kwargs: 0.6)
        monkeypatch.setattr(extractor, "_table_column_path_overlap_ratio", lambda *args, **kwargs: 0.0)
        monkeypatch.setattr(extractor, "_is_top_of_page", lambda *args, **kwargs: False)
        monkeypatch.setattr(extractor, "_is_bottom_of_page", lambda *args, **kwargs: False)
        monkeypatch.setattr(extractor, "_is_likely_parameter_continuation", lambda *args, **kwargs: (False, "weak_signal_only"))

        is_continuation, reason, evidence = extractor._assess_table_continuation(previous, current, previous.page)

        assert is_continuation is True
        assert reason == "high_structure_with_overlap"
        assert evidence["strong_evidence"] is True
        assert evidence["missing_table_numbers"] is True
        assert evidence["strong_missing_number_evidence"] is True

    def test_assess_without_table_number_should_hit_top_bottom_with_header_or_path_overlap(self, monkeypatch):
        extractor = PTRExtractor()
        previous = PTRTable(table_number=None, headers=["A", "B", "C"], rows=[["1", "2", "3"]], page=32, position=(0, 520))
        current = PTRTable(table_number=None, headers=["A", "B", "C"], rows=[["4", "5", "6"]], page=33, position=(0, 40))

        monkeypatch.setattr(extractor, "_table_structure_similarity", lambda *args, **kwargs: 0.45)
        monkeypatch.setattr(extractor, "_table_header_text_overlap_ratio", lambda *args, **kwargs: 0.6)
        monkeypatch.setattr(extractor, "_table_column_path_overlap_ratio", lambda *args, **kwargs: 0.0)
        monkeypatch.setattr(extractor, "_is_top_of_page", lambda table: table.page == 33)
        monkeypatch.setattr(extractor, "_is_bottom_of_page", lambda table: table.page == 32)
        monkeypatch.setattr(extractor, "_is_likely_parameter_continuation", lambda *args, **kwargs: (False, "weak_signal_only"))

        is_continuation, reason, evidence = extractor._assess_table_continuation(previous, current, previous.page)

        assert is_continuation is True
        assert reason == "top_bottom_with_header_or_path_overlap"
        assert evidence["strong_evidence"] is True
        assert evidence["strong_missing_number_evidence"] is True

    def test_assess_without_table_number_should_reject_when_only_weak_signal(self, monkeypatch):
        extractor = PTRExtractor()
        previous = PTRTable(table_number=None, headers=["参数", "型号", "常规数值"], rows=[["脉冲宽度", "全部型号", "0.4"]], page=34, position=(0, 300))
        current = PTRTable(table_number=None, headers=["", "", ""], rows=[["", "Edora 8 DR", "其他模式"]], page=35, position=(0, 260))

        monkeypatch.setattr(extractor, "_table_structure_similarity", lambda *args, **kwargs: 0.2)
        monkeypatch.setattr(extractor, "_table_header_text_overlap_ratio", lambda *args, **kwargs: 0.0)
        monkeypatch.setattr(extractor, "_table_column_path_overlap_ratio", lambda *args, **kwargs: 0.0)
        monkeypatch.setattr(extractor, "_is_top_of_page", lambda *args, **kwargs: False)
        monkeypatch.setattr(extractor, "_is_bottom_of_page", lambda *args, **kwargs: False)
        monkeypatch.setattr(
            extractor,
            "_is_likely_parameter_continuation",
            lambda *args, **kwargs: (True, "blank_first_col_with_model_payload"),
        )

        is_continuation, reason, evidence = extractor._assess_table_continuation(previous, current, previous.page)

        assert is_continuation is False
        assert reason == "missing_table_number_without_strong_evidence"
        assert evidence["strong_evidence"] is False
        assert evidence["strong_missing_number_evidence"] is False

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
            "missing_table_number_without_strong_evidence",
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
            table_number=None,
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
        assert merged[1].metadata.get("continuation_reject_reason") in {
            "rejected: no_header_path_overlap",
            "missing_table_number_without_strong_evidence",
        }

    def test_should_not_merge_without_table_number_when_semantics_differ(self):
        extractor = PTRExtractor()

        p1 = PTRTable(
            table_number=None,
            headers=["参数", "型号", "常规数值", "标准设置", "允许误差"],
            column_paths=[["参数"], ["型号"], ["常规数值"], ["标准设置"], ["允许误差"]],
            rows=[["脉冲宽度(ms)", "全部型号", "0.1...1.5", "0.4", "±20μs"]],
            page=16,
            position=(0, 520),
        )
        p2 = PTRTable(
            table_number=None,
            headers=["参数", "通道", "输出模式", "报警策略", "备注"],
            column_paths=[["参数"], ["通道"], ["输出模式"], ["报警策略"], ["备注"]],
            rows=[["器械类型", "A通道", "单次输出", "高优先级", "植入式心脏起搏器"]],
            page=17,
            position=(0, 40),
        )

        merged = extractor._merge_continuation_tables([p1, p2])

        assert len(merged) == 2
        assert merged[1].metadata.get("continuation_reject_reason") in {
            "rejected: no_header_path_overlap",
            "rejected: low_similarity",
            "rejected: insufficient_joint_evidence",
            "missing_table_number_without_strong_evidence",
        }

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
