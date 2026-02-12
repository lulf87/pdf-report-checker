"""
测试标准条款跨多行时的单项结论判定
Bug修复验证：当标准条款跨多行时，应该使用最后一行的单项结论
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from services.inspection_item_checker import InspectionItemChecker
from models.schemas import TableData


def test_cross_row_conclusion_update():
    """测试：标准条款跨多行时，单项结论应该使用最后一行"""

    # 模拟用户描述的场景
    # 序号 27，标准条款 7.2.3，有两行数据
    # 第一行：检验结果 "——"，单项结论 ""
    # 第二行：检验结果 "符合要求"，单项结论 "符合"
    table_data = TableData(
        page_num=1,
        table_index=0,
        headers=['序号', '检验项目', '标准条款', '标准要求', '检验结果', '单项结论', '备注'],
        rows=[
            ['27', '工作温度下的电介质强度', '7.2.3', '要求1', '——', '', ''],
            ['', '', '', '要求2', '符合要求', '符合', ''],  # 续行，继承序号和标准条款
        ],
        row_count=2,
        col_count=7
    )

    checker = InspectionItemChecker()
    result = checker.parse_inspection_table(table_data)

    # 验证
    assert len(result) == 1, f"应该有1个检验项目，实际有{len(result)}"

    item = result[0]
    assert item.item_number == '27', f"序号应该是27，实际是{item.item_number}"

    # 应该只有一个标准条款 7.2.3
    assert len(item.clauses) == 1, f"应该有1个标准条款，实际有{len(item.clauses)}"

    clause = item.clauses[0]
    assert clause.clause_number == '7.2.3', f"标准条款应该是7.2.3，实际是{clause.clause_number}"

    # 应该有2个标准要求
    assert len(clause.requirements) == 2, f"应该有2个标准要求，实际有{len(clause.requirements)}"

    # 检验结果
    assert clause.requirements[0].inspection_result == '——', "第一行检验结果应该是'——'"
    assert clause.requirements[1].inspection_result == '符合要求', "第二行检验结果应该是'符合要求'"

    # 关键验证：单项结论应该是"符合"（使用最后一行）
    assert clause.conclusion == '符合', f"实际单项结论应该是'符合'，实际是'{clause.conclusion}'"

    # 期望的单项结论也应该是"符合"
    assert clause.expected_conclusion == '符合', f"期望单项结论应该是'符合'，实际是'{clause.expected_conclusion}'"

    # 结论应该正确
    assert clause.is_conclusion_correct is True, "单项结论判定应该是正确的"

    print("✓ 测试通过：标准条款跨多行时，正确使用了最后一行的单项结论")
    return True


def test_cross_row_conclusion_wrong():
    """测试：标准条款跨多行时，如果结论错误应该被检测出来"""

    # 场景：两行都是"——"，但单项结论标为"符合"（应该是"/"）
    table_data = TableData(
        page_num=1,
        table_index=0,
        headers=['序号', '检验项目', '标准条款', '标准要求', '检验结果', '单项结论', '备注'],
        rows=[
            ['27', '测试项目', '7.2.3', '要求1', '——', '', ''],
            ['', '', '', '要求2', '——', '符合', ''],  # 错误：两行都是"——"，但结论标为"符合"
        ],
        row_count=2,
        col_count=7
    )

    checker = InspectionItemChecker()
    result = checker.parse_inspection_table(table_data)

    item = result[0]
    clause = item.clauses[0]

    # 实际结论应该是"符合"（最后一行）
    assert clause.conclusion == '符合', f"实际单项结论应该是'符合'，实际是'{clause.conclusion}'"

    # 期望的单项结论应该是"/"（因为两行都是"——"）
    assert clause.expected_conclusion == '/', f"期望单项结论应该是'/'，实际是'{clause.expected_conclusion}'"

    # 结论应该错误
    assert clause.is_conclusion_correct is False, "单项结论判定应该是错误的"

    print("✓ 测试通过：正确检测出跨多行时的单项结论错误")
    return True


if __name__ == '__main__':
    print("=" * 60)
    print("Bug修复验证：标准条款跨多行单项结论判定")
    print("=" * 60)

    try:
        test_cross_row_conclusion_update()
        test_cross_row_conclusion_wrong()
        print("\n" + "=" * 60)
        print("✓ 所有测试通过！Bug已修复。")
        print("=" * 60)
    except AssertionError as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
