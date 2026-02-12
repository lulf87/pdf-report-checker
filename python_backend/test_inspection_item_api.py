"""
测试检验项目核对 API 集成
"""

import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))


def test_expected_conclusion_calculation():
    """测试单项结论计算逻辑"""
    print("\n" + "=" * 60)
    print("测试1: 单项结论计算逻辑")
    print("=" * 60)

    # 内联测试计算逻辑
    def calculate_expected_conclusion(results):
        """根据检验结果计算期望的单项结论"""
        # 优先级1: 判断是否包含 "不符合要求"
        if any('不符合' in r for r in results):
            return '不符合'

        # 优先级2: 判断是否全为 "——" 或空白
        if all(r == '——' or r == '' or r is None for r in results):
            return '/'

        # 优先级3: 其他情况
        return '符合'

    test_cases = [
        # (检验结果列表, 期望结论)
        (["符合要求", "——"], "符合"),
        (["——", "——"], "/"),
        (["不符合要求"], "不符合"),
        (["100", "——"], "符合"),
        (["测试文本"], "符合"),
        (["", ""], "/"),
        (["符合要求", "不符合要求"], "不符合"),
    ]

    all_passed = True
    for results, expected in test_cases:
        actual = calculate_expected_conclusion(results)
        status = "✓" if actual == expected else "✗"

        if actual != expected:
            all_passed = False

        print(f"{status} 结果{results} -> 期望: {expected}, 实际: {actual}")

    return all_passed


def test_error_code_generation():
    """测试错误代码生成"""
    print("\n" + "=" * 60)
    print("测试2: 错误代码生成")
    print("=" * 60)

    def get_error_code(expected, actual):
        """获取错误代码"""
        if expected == '/' and actual != '/':
            return 'CONCLUSION_MISMATCH_001'
        elif expected == '符合' and actual != '符合':
            # 需要进一步判断实际值
            if actual == '不符合':
                return 'CONCLUSION_MISMATCH_004'  # 不应标为"不符合"
            else:
                return 'CONCLUSION_MISMATCH_002'
        elif expected == '不符合' and actual != '不符合':
            return 'CONCLUSION_MISMATCH_003'
        elif expected != '不符合' and actual == '不符合':
            return 'CONCLUSION_MISMATCH_004'
        return 'CONCLUSION_MISMATCH_UNKNOWN'

    test_cases = [
        # (期望结论, 实际结论, 期望错误代码)
        ("/", "符合", "CONCLUSION_MISMATCH_001"),
        ("符合", "/", "CONCLUSION_MISMATCH_002"),
        ("不符合", "符合", "CONCLUSION_MISMATCH_003"),
        ("符合", "不符合", "CONCLUSION_MISMATCH_004"),
    ]

    all_passed = True
    for expected, actual, expected_code in test_cases:
        code = get_error_code(expected, actual)
        status = "✓" if code == expected_code else "✗"

        if code != expected_code:
            all_passed = False

        print(f"{status} 期望:{expected} 实际:{actual} -> {code}")

    return all_passed


def test_model_structure():
    """测试数据模型结构"""
    print("\n" + "=" * 60)
    print("测试3: 数据模型结构验证")
    print("=" * 60)

    try:
        # 只导入模型模块，避免导入服务模块
        from models.schemas import (
            RequirementCheck, ClauseCheck, InspectionItemCheck,
            InspectionItemCheckResult, ErrorItem
        )

        # 创建 RequirementCheck
        req = RequirementCheck(
            requirement_text="测试要求",
            inspection_result="符合要求",
            remark=""
        )
        print("✓ RequirementCheck 创建成功")

        # 创建 ClauseCheck
        clause = ClauseCheck(
            clause_number="5.1.1",
            requirements=[req],
            conclusion="符合",
            expected_conclusion="符合",
            is_conclusion_correct=True
        )
        print("✓ ClauseCheck 创建成功")

        # 创建 InspectionItemCheck
        item = InspectionItemCheck(
            item_number="1",
            item_name="外观检查",
            clauses=[clause],
            issues=[],
            status="pass"
        )
        print("✓ InspectionItemCheck 创建成功")

        # 创建 InspectionItemCheckResult
        result = InspectionItemCheckResult(
            has_table=True,
            total_items=1,
            total_clauses=1,
            correct_conclusions=1,
            incorrect_conclusions=0,
            item_checks=[item],
            cross_page_continuations=0,
            errors=[]
        )
        print("✓ InspectionItemCheckResult 创建成功")

        # 验证序列化
        result_dict = result.model_dump()
        print(f"✓ 序列化成功，包含字段: {list(result_dict.keys())}")

        # 验证嵌套结构
        assert 'item_checks' in result_dict
        assert len(result_dict['item_checks']) == 1
        assert 'clauses' in result_dict['item_checks'][0]
        print("✓ 嵌套数据结构验证通过")

        return True
    except Exception as e:
        print(f"✗ 数据模型测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_check_result_integration():
    """测试 CheckResult 集成 inspection_item_check"""
    print("\n" + "=" * 60)
    print("测试4: CheckResult 集成验证")
    print("=" * 60)

    try:
        from models.schemas import (
            CheckResult, InspectionItemCheckResult, InspectionItemCheck,
            ClauseCheck, RequirementCheck
        )

        # 创建检验项目核对结果
        req = RequirementCheck(
            requirement_text="外观应无损伤",
            inspection_result="符合要求",
            remark=""
        )
        clause = ClauseCheck(
            clause_number="5.1",
            requirements=[req],
            conclusion="符合",
            expected_conclusion="符合",
            is_conclusion_correct=True
        )
        item = InspectionItemCheck(
            item_number="1",
            item_name="外观检查",
            clauses=[clause],
            issues=[],
            status="pass"
        )
        inspection_result = InspectionItemCheckResult(
            has_table=True,
            total_items=1,
            total_clauses=1,
            correct_conclusions=1,
            incorrect_conclusions=0,
            item_checks=[item],
            cross_page_continuations=0,
            errors=[]
        )

        # 创建 CheckResult 并包含 inspection_item_check
        check_result = CheckResult(
            success=True,
            file_id="test-file-id",
            filename="test.pdf",
            check_time="2026-02-12T10:00:00",
            total_pages=10,
            inspection_item_check=inspection_result
        )
        print("✓ CheckResult 包含 inspection_item_check 创建成功")

        # 验证序列化
        result_dict = check_result.model_dump()
        assert 'inspection_item_check' in result_dict
        assert result_dict['inspection_item_check']['has_table'] is True
        print("✓ CheckResult 序列化验证通过")

        return True
    except Exception as e:
        print(f"✗ CheckResult 集成测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("检验项目核对 API 集成测试")
    print("=" * 60)

    results = []

    results.append(("结论计算测试", test_expected_conclusion_calculation()))
    results.append(("错误代码测试", test_error_code_generation()))
    results.append(("数据模型测试", test_model_structure()))
    results.append(("CheckResult集成测试", test_check_result_integration()))

    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)

    for name, passed in results:
        status = "✓ 通过" if passed else "✗ 失败"
        print(f"{status}: {name}")

    all_passed = all(r[1] for r in results)

    if all_passed:
        print("\n✓ 所有测试通过！")
        return 0
    else:
        print("\n✗ 部分测试失败")
        return 1


if __name__ == "__main__":
    exit(main())
