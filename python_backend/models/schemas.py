"""
Pydantic模型定义 - 数据校验与序列化
"""

from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str
    timestamp: str
    version: str


class UploadResponse(BaseModel):
    """文件上传响应"""
    success: bool
    file_id: str
    filename: str
    file_path: str
    file_type: str
    message: str


class PageInfo(BaseModel):
    """页面信息"""
    page_num: int
    page_header: Optional[str] = None
    text_content: Optional[str] = None
    has_table: bool = False
    has_image: bool = False
    tables: List[Dict[str, Any]] = []
    images: List[Dict[str, Any]] = []


class TableData(BaseModel):
    """表格数据"""
    page_num: int
    table_index: int
    headers: List[str]
    rows: List[List[str]]
    row_count: int
    col_count: int


class OCRTextBlock(BaseModel):
    """OCR文本块"""
    text: str
    confidence: float
    bbox: List[float]  # [x1, y1, x2, y2]


class OCRResult(BaseModel):
    """OCR识别结果"""
    page_num: Optional[int] = None
    image_path: Optional[str] = None
    text_blocks: List[OCRTextBlock] = []
    full_text: str = ""
    structured_data: Dict[str, Any] = {}


class FieldComparison(BaseModel):
    """字段比对结果"""
    field_name: str
    table_value: str
    ocr_value: str
    is_match: bool
    issue_type: Optional[str] = None  # "missing", "mismatch", "empty"
    page_num: Optional[int] = None
    row_index: Optional[int] = None


class ComponentCheck(BaseModel):
    """部件核对结果"""
    model_config = {"extra": "allow"}  # 允许额外字段

    component_name: str
    has_photo: bool
    has_chinese_label: bool
    field_comparisons: List[FieldComparison] = []
    issues: List[str] = []
    status: str  # "pass", "fail", "warning"


class ComparisonDetail(BaseModel):
    """单个比对步骤详情"""
    step: str  # 比对步骤名称，如"caption提取"、"名称匹配"、"OCR字段提取"
    input_data: Dict[str, Any] = {}  # 输入数据
    output_data: Dict[str, Any] = {}  # 输出结果
    method: str = ""  # 使用的方法/算法
    confidence: float = 1.0  # 置信度
    execution_time_ms: Optional[int] = None  # 执行时间
    is_success: bool = True  # 是否成功
    error_message: Optional[str] = None  # 错误信息


class DetailedComponentCheck(BaseModel):
    """带详细比对过程的部件核对结果"""
    # 基础字段 (继承自ComponentCheck)
    component_name: str
    has_photo: bool
    has_chinese_label: bool
    field_comparisons: List[FieldComparison] = []
    issues: List[str] = []
    status: str  # "pass", "fail", "warning"
    # 扩展字段
    comparison_details: List[ComparisonDetail] = []  # 详细比对过程
    matched_photos: List[Dict[str, Any]] = []  # 匹配到的照片列表
    matched_labels: List[Dict[str, Any]] = []  # 匹配到的标签列表
    match_reason: str = ""  # 匹配/不匹配的原因说明


class ErrorItem(BaseModel):
    """错误项"""
    level: str  # "ERROR", "WARN", "INFO"
    message: str
    page_num: Optional[int] = None
    location: Optional[str] = None
    details: Dict[str, Any] = {}


class RequirementCheck(BaseModel):
    """标准要求核对 - 检验项目表格"""
    requirement_text: str      # 标准要求内容
    inspection_result: str     # 检验结果
    remark: str                # 备注


class ClauseCheck(BaseModel):
    """标准条款核对 - 检验项目表格"""
    clause_number: str         # 标准条款编号
    requirements: List[RequirementCheck]  # 标准要求列表
    conclusion: str            # 单项结论（文档中的实际值）
    expected_conclusion: str   # 期望的单项结论
    is_conclusion_correct: bool  # 结论是否正确


class InspectionItemCheck(BaseModel):
    """检验项目核对"""
    item_number: str           # 序号
    item_name: str             # 检验项目名称
    clauses: List[ClauseCheck] # 标准条款列表
    issues: List[str]          # 问题列表
    status: str                # pass/warning/fail


class InspectionItemCheckResult(BaseModel):
    """检验项目核对结果"""
    has_table: bool               # 是否检测到检验项目表格
    total_items: int              # 检验项目总数
    total_clauses: int            # 标准条款总数
    correct_conclusions: int      # 单项结论正确的条款数
    incorrect_conclusions: int    # 单项结论错误的条款数
    item_checks: List[InspectionItemCheck]  # 各检验项目核对详情
    cross_page_continuations: int  # 跨页续表数量
    errors: List[ErrorItem]       # 错误列表


class CheckResult(BaseModel):
    """核对结果"""
    model_config = {"extra": "allow"}  # 允许额外字段

    success: bool
    file_id: str
    filename: str
    check_time: str
    total_pages: int

    # 首页字段
    home_page_fields: Dict[str, str] = {}

    # 第三页字段
    third_page_fields: Dict[str, str] = {}

    # 首页与第三页比对
    home_third_comparison: List[FieldComparison] = []

    # 样品描述表格
    sample_description_table: Optional[TableData] = None

    # 部件核对
    component_checks: List[ComponentCheck] = []

    # 照片页检查
    photo_page_check: Dict[str, Any] = {}

    # 检验项目核对结果（新增 v2.1）
    inspection_item_check: Optional[InspectionItemCheckResult] = None

    # 错误汇总
    errors: List[ErrorItem] = []
    warnings: List[ErrorItem] = []
    info: List[ErrorItem] = []

    # 统计
    total_components: int = 0
    passed_components: int = 0
    failed_components: int = 0

    # 导出路径
    report_path: Optional[str] = None


class DetailedCheckResult(BaseModel):
    """带详细比对信息的核对结果"""
    # 基础字段 (继承自CheckResult)
    success: bool
    file_id: str
    filename: str
    check_time: str
    total_pages: int
    home_page_fields: Dict[str, str] = {}
    third_page_fields: Dict[str, str] = {}
    home_third_comparison: List[FieldComparison] = []
    sample_description_table: Optional[TableData] = None
    component_checks: List[ComponentCheck] = []
    photo_page_check: Dict[str, Any] = {}
    errors: List[ErrorItem] = []
    warnings: List[ErrorItem] = []
    info: List[ErrorItem] = []
    total_components: int = 0
    passed_components: int = 0
    failed_components: int = 0
    report_path: Optional[str] = None
    # 扩展字段
    enable_detailed_comparison: bool = False  # 是否启用详细比对
    detailed_checks: List[DetailedComponentCheck] = []  # 详细核对结果
    llm_usage_info: Dict[str, Any] = {}  # LLM使用信息


class ExportRequest(BaseModel):
    """导出请求"""
    file_id: str
    format: str = "json"  # json, excel, pdf
    include_images: bool = False
