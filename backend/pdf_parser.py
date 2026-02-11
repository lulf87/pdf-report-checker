"""
PDF解析模块 - 用于解析检验报告PDF文件
提取首页字段、表格数据、照片页信息等
"""

import re
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Tuple
from pathlib import Path

import pdfplumber


# ============== 数据模型 ==============

@dataclass
class HeaderInfo:
    """页眉信息"""
    raw_text: str
    cleaned_text: str
    page_number: int


@dataclass
class FirstPageFields:
    """首页三字段"""
    委托方: Optional[str] = None
    样品名称: Optional[str] = None
    型号规格: Optional[str] = None

    def to_dict(self) -> Dict[str, Optional[str]]:
        return {
            "委托方": self.委托方,
            "样品名称": self.样品名称,
            "型号规格": self.型号规格,
        }


@dataclass
class ThirdPageTable:
    """第三页表格数据"""
    委托方: Optional[str] = None
    样品名称: Optional[str] = None
    型号规格: Optional[str] = None
    产品编号_批号: Optional[str] = None
    生产日期: Optional[str] = None

    def to_dict(self) -> Dict[str, Optional[str]]:
        return {
            "委托方": self.委托方,
            "样品名称": self.样品名称,
            "型号规格": self.型号规格,
            "产品编号/批号": self.产品编号_批号,
            "生产日期": self.生产日期,
        }


@dataclass
class SampleDescriptionRow:
    """样品描述表格行"""
    序号: str
    部件名称: str
    规格型号: str
    序列号_批号: str
    生产日期: str
    备注: str
    # 原始数据保留
    raw_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SampleDescriptionTable:
    """样品描述表格"""
    headers: List[str]
    rows: List[SampleDescriptionRow]
    start_page: int
    end_page: int


@dataclass
class PhotoCaption:
    """照片说明"""
    caption: str
    page_number: int
    row_index: int
    is_chinese_label: bool = False
    subject_name: Optional[str] = None


@dataclass
class PhotoPage:
    """照片页信息"""
    page_number: int
    captions: List[PhotoCaption]


@dataclass
class ParsedReport:
    """解析后的完整报告"""
    file_path: str
    total_pages: int

    # 各页定位
    first_page_idx: int = 0  # 首页通常是第1页 (索引0)
    third_page_idx: int = 2  # 第三页通常是第3页 (索引2)
    sample_desc_start_idx: int = 3  # 样品描述从第4页开始 (索引3)
    photo_pages_start_idx: Optional[int] = None

    # 提取的数据
    first_page_fields: Optional[FirstPageFields] = None
    third_page_table: Optional[ThirdPageTable] = None
    sample_description: Optional[SampleDescriptionTable] = None
    photo_pages: List[PhotoPage] = field(default_factory=list)

    # 页眉锚点记录
    page_headers: Dict[int, HeaderInfo] = field(default_factory=dict)


# ============== 工具函数 ==============

def clean_header_text(text: str) -> str:
    """
    清理页眉文本，去除所有空白字符用于匹配

    Args:
        text: 原始文本

    Returns:
        去除空白后的文本
    """
    # 去除各种空白字符：空格、全角空格、制表符、换行等
    return re.sub(r'\s+', '', text)


def detect_header_type(header_cleaned: str) -> Optional[str]:
    """
    检测页眉类型

    Args:
        header_cleaned: 清理后的页眉文本

    Returns:
        页眉类型: 'first_page', 'report_page', 'photo_page', 或 None
    """
    # 第三页：页眉 = "检验报告首页" 或 "首页"
    if '检验报告首页' in header_cleaned or \
       (header_cleaned.endswith('首页') and '检验报告' in header_cleaned):
        return 'first_page'

    # 照片页：页眉 = "检验报告照片页"
    if '检验报告照片页' in header_cleaned or \
       (header_cleaned.endswith('照片页') and '检验报告' in header_cleaned):
        return 'photo_page'

    # 第四页起：页眉 = "检验报告" (但不是首页或照片页)
    if '检验报告' in header_cleaned:
        return 'report_page'

    return None


def extract_subject_name_from_caption(caption: str) -> Optional[str]:
    """
    从照片说明中提取主体名

    规则：
    1) 去除前缀编号：形如 №\\s*\\d+ (№ 也可能为 No. / NO. / Number 等)
    2) 去除尾部方位词：如 前侧/后侧/左侧/右侧/正面/背面/侧面/俯视/仰视/顶部/底部/局部
    3) 去除尾部类别词：中文标签/中文标签样张/英文标签/原文标签/标签
    4) 剩余文本即主体名

    Args:
        caption: 照片说明文本

    Returns:
        提取的主体名
    """
    if not caption:
        return None

    text = caption.strip()

    # 1) 去除前缀编号
    # 匹配 №、No.、NO.、Number 后跟数字
    text = re.sub(r'^(?:№|No\.?|NO\.?|Number)\s*\d+\s*', '', text, flags=re.IGNORECASE)

    # 2) 去除尾部方位词
    direction_words = [
        '前侧', '后侧', '左侧', '右侧', '正面', '背面', '侧面',
        '俯视', '仰视', '顶部', '底部', '局部'
    ]
    for word in direction_words:
        if text.endswith(word):
            text = text[:-len(word)].strip()
            break

    # 3) 去除尾部类别词
    category_words = ['中文标签样张', '中文标签', '英文标签', '原文标签', '标签']
    for word in category_words:
        if text.endswith(word):
            text = text[:-len(word)].strip()
            break

    return text if text else None


def is_chinese_label_caption(caption: str) -> bool:
    """
    判断是否为中文标签说明

    Args:
        caption: 照片说明

    Returns:
        是否包含"中文标签"或"中文标签样张"
    """
    if not caption:
        return False
    return '中文标签' in caption or '中文标签样张' in caption


# ============== 解析函数 ==============

def parse_page_header(page, page_idx: int) -> HeaderInfo:
    """
    解析页眉信息

    Args:
        page: pdfplumber页面对象
        page_idx: 页索引 (0-based)

    Returns:
        HeaderInfo对象
    """
    text = page.extract_text()
    if not text:
        return HeaderInfo(raw_text="", cleaned_text="", page_number=page_idx + 1)

    # 获取前3行作为页眉区域
    lines = text.split('\n')[:3]
    header_text = ' '.join(lines)
    cleaned = clean_header_text(header_text)

    return HeaderInfo(
        raw_text=header_text,
        cleaned_text=cleaned,
        page_number=page_idx + 1
    )


def extract_first_page_fields(page) -> FirstPageFields:
    """
    提取首页三字段：委托方、样品名称、型号规格

    取值规则：
    - 以字段名所在单元格/段落为定位
    - 取其右侧相邻单元格或同一行的文本作为值

    Args:
        page: pdfplumber页面对象 (首页)

    Returns:
        FirstPageFields对象
    """
    result = FirstPageFields()

    text = page.extract_text()
    if not text:
        return result

    lines = text.split('\n')

    # 字段名模式 - 首页字段在同一行
    for i, line in enumerate(lines):
        # 委托方 - 在同一行
        if '委' in line and '托' in line and '方' in line and result.委托方 is None:
            # 尝试在当前行提取
            match = re.search(r'委\s*托\s*方\s*[:：]?\s*(.+)', line)
            if match:
                value = match.group(1).strip()
                # 清理可能的后续字段名（注意：上海是公司名的一部分，不能作为分隔符）
                # 使用更精确的分隔符匹配
                for sep in ['检验类别', '样品名称', '型号规格']:
                    if sep in value:
                        value = value.split(sep)[0].strip()
                        break
                result.委托方 = value

        # 样品名称
        if '样品名称' in line and result.样品名称 is None:
            match = re.search(r'样品名称\s*[:：]?\s*(.+)', line)
            if match:
                value = match.group(1).strip()
                # 清理可能的后续字段名
                for sep in ['型号规格', '委托方', '检验类别']:
                    if sep in value:
                        value = value.split(sep)[0].strip()
                        break
                result.样品名称 = value

        # 型号规格
        if '型号规格' in line and result.型号规格 is None:
            match = re.search(r'型号规格\s*[:：]?\s*(.+)', line)
            if match:
                value = match.group(1).strip()
                # 清理可能的后续字段名
                for sep in ['检验类别', '样品名称', '委托方']:
                    if sep in value:
                        value = value.split(sep)[0].strip()
                        break
                result.型号规格 = value

    return result


def extract_third_page_table(page) -> ThirdPageTable:
    """
    提取第三页表格数据

    包含字段：委托方、样品名称、型号规格、产品编号/批号、生产日期

    Args:
        page: pdfplumber页面对象 (第三页)

    Returns:
        ThirdPageTable对象
    """
    result = ThirdPageTable()

    # 首先尝试从文本提取
    text = page.extract_text()
    if text:
        lines = text.split('\n')

        # 委托方 - 从文本提取（在同一行）
        for line in lines:
            if '委托方' in line and '委托方地址' not in line:
                match = re.search(r'委托方\s*[:：]?\s*(.+?)(?:\s+检验类别|$)', line)
                if match:
                    result.委托方 = match.group(1).strip()
                    break

        # 样品名称
        for line in lines:
            match = re.search(r'样品名称\s*[:：]?\s*(.+?)(?:\s+样品编号|$)', line)
            if match:
                result.样品名称 = match.group(1).strip()
                break

        # 型号规格
        for line in lines:
            match = re.search(r'型号规格\s*[:：]?\s*(.+?)(?:\s+委托方|$)', line)
            if match:
                result.型号规格 = match.group(1).strip()
                break

        # 产品编号/批号
        for line in lines:
            match = re.search(r'产品编号[／/]批号\s*[:：]?\s*(.+?)(?:\s+|$)', line)
            if match:
                result.产品编号_批号 = match.group(1).strip()
                break

        # 生产日期
        for line in lines:
            match = re.search(r'生产日期\s*[:：]?\s*(.+?)(?:\s+|$)', line)
            if match:
                result.生产日期 = match.group(1).strip()
                break

    # 从表格提取（表格数据更准确）- 优先使用表格数据
    tables = page.extract_tables()
    table_result = ThirdPageTable()

    for table in tables:
        if not table:
            continue

        # 遍历表格查找字段
        for row in table:
            if not row:
                continue

            # 处理合并单元格（None值）
            cleaned_row = [cell or '' for cell in row]

            for i, cell in enumerate(cleaned_row):
                cell_clean = cell.strip().replace('\n', '')

                # 委托方 - 精确匹配"委托方"而不是"委托方地址"
                if cell_clean == '委托方' and i + 1 < len(cleaned_row):
                    value = cleaned_row[i + 1].strip()
                    if value and value != '/':
                        table_result.委托方 = value.split('\n')[0].strip()

                # 样品名称
                if cell_clean == '样品名称' and i + 1 < len(cleaned_row):
                    value = cleaned_row[i + 1].strip()
                    if value and value != '/':
                        table_result.样品名称 = value.split('\n')[0].strip()

                # 型号规格
                if cell_clean == '型号规格' and i + 1 < len(cleaned_row):
                    value = cleaned_row[i + 1].strip()
                    if value and value != '/':
                        table_result.型号规格 = value.split('\n')[0].strip()

                # 产品编号/批号
                if ('产品编号' in cell_clean or '批号' in cell_clean) and i + 1 < len(cleaned_row):
                    value = cleaned_row[i + 1].strip()
                    if value and value != '/':
                        table_result.产品编号_批号 = value.split('\n')[0].strip()

                # 生产日期
                if cell_clean == '生产日期' and i + 1 < len(cleaned_row):
                    value = cleaned_row[i + 1].strip()
                    if value and value != '/':
                        table_result.生产日期 = value.split('\n')[0].strip()

    # 优先使用表格提取的结果（更可靠）
    if table_result.委托方:
        result.委托方 = table_result.委托方
    if table_result.样品名称:
        result.样品名称 = table_result.样品名称
    if table_result.型号规格:
        result.型号规格 = table_result.型号规格
    if table_result.产品编号_批号:
        result.产品编号_批号 = table_result.产品编号_批号
    if table_result.生产日期:
        result.生产日期 = table_result.生产日期

    return result


def extract_sample_description_tables(
    pdf,
    start_page_idx: int,
    max_pages: int = 10
) -> Optional[SampleDescriptionTable]:
    """
    提取样品描述表格（可能跨页）

    Args:
        pdf: pdfplumber PDF对象
        start_page_idx: 开始页索引
        max_pages: 最大搜索页数

    Returns:
        SampleDescriptionTable对象或None
    """
    all_rows = []
    headers = []
    end_page_idx = start_page_idx
    found_table = False

    for page_idx in range(start_page_idx, min(start_page_idx + max_pages, len(pdf.pages))):
        page = pdf.pages[page_idx]

        # 检查是否是样品描述页
        text = page.extract_text()
        if text and page_idx == start_page_idx:
            # 第一页应该有"样品描述"字样
            if '样品描述' not in text:
                continue

        tables = page.extract_tables()
        page_has_table = False

        for table in tables:
            if not table or len(table) < 2:
                continue

            # 检查是否是目标表格（表头包含特定列）
            first_row = [cell or '' for cell in table[0]]
            first_row_text = ' '.join(first_row)

            # 判断是否为样品描述表格
            is_target_table = (
                '部件名称' in first_row_text or
                '产品名称' in first_row_text or
                '规格型号' in first_row_text or
                '序列号' in first_row_text or
                ('序号' in first_row_text and '生产日期' in first_row_text)
            )

            # 如果不是目标表格，但已经有数据且当前表格有数据行，可能是续表
            if not is_target_table and found_table:
                # 检查是否是数据行（第一列是数字）
                for row in table:
                    if row and row[0] and re.match(r'^\d+$', str(row[0]).strip()):
                        is_target_table = True
                        break

            if not is_target_table:
                continue

            found_table = True
            page_has_table = True

            # 提取表头（只在第一页）
            if not headers and page_idx == start_page_idx:
                headers = [cell.strip() if cell else '' for cell in table[0]]

            # 提取数据行
            start_row = 1 if page_idx == start_page_idx else 0

            for row in table[start_row:]:
                if not row:
                    continue

                # 清理单元格
                cleaned_cells = []
                for cell in row:
                    if cell:
                        # 处理换行
                        cleaned = cell.replace('\n', '').strip()
                        cleaned_cells.append(cleaned)
                    else:
                        cleaned_cells.append('')

                # 跳过空行
                if not any(cleaned_cells):
                    continue

                # 跳过表头重复行
                if cleaned_cells[0] == '序号' or '部件名称' in cleaned_cells[0]:
                    continue

                # 创建行对象
                row_data = {
                    '序号': cleaned_cells[0] if len(cleaned_cells) > 0 else '',
                    '部件名称': cleaned_cells[1] if len(cleaned_cells) > 1 else '',
                    '规格型号': cleaned_cells[2] if len(cleaned_cells) > 2 else '',
                    '序列号_批号': cleaned_cells[3] if len(cleaned_cells) > 3 else '',
                    '生产日期': cleaned_cells[4] if len(cleaned_cells) > 4 else '',
                    '备注': cleaned_cells[5] if len(cleaned_cells) > 5 else '',
                }

                sample_row = SampleDescriptionRow(
                    序号=row_data['序号'],
                    部件名称=row_data['部件名称'],
                    规格型号=row_data['规格型号'],
                    序列号_批号=row_data['序列号_批号'],
                    生产日期=row_data['生产日期'],
                    备注=row_data['备注'],
                    raw_data={'original_cells': cleaned_cells, 'page': page_idx + 1}
                )

                all_rows.append(sample_row)

            break  # 只处理第一个匹配的表格

        # 如果当前页没有表格数据，且已经有数据，说明表格结束了
        if found_table and not page_has_table:
            break

        if page_has_table:
            end_page_idx = page_idx

    if not all_rows:
        return None

    return SampleDescriptionTable(
        headers=headers or ['序号', '部件名称', '规格型号', '序列号/批号', '生产日期', '备注'],
        rows=all_rows,
        start_page=start_page_idx + 1,
        end_page=end_page_idx + 1
    )


def extract_photo_page_captions(page, page_idx: int) -> Optional[PhotoPage]:
    """
    提取照片页的说明文字

    Args:
        page: pdfplumber页面对象
        page_idx: 页索引

    Returns:
        PhotoPage对象或None
    """
    text = page.extract_text()
    if not text:
        return None

    lines = text.split('\n')

    # 查找"照片和说明"表头
    photo_table_start = -1
    for i, line in enumerate(lines):
        if '照片和说明' in line:
            photo_table_start = i
            break

    if photo_table_start < 0:
        return None

    # 提取说明文字（通常在表头后的行）
    captions = []
    caption_lines = lines[photo_table_start + 1:]

    for i, line in enumerate(caption_lines):
        line = line.strip()
        if not line:
            continue

        # 跳过页脚信息
        if '第' in line and '页' in line and '号' in line:
            continue

        # 识别说明文字格式：通常以 № 或 No. 开头，或包含中文标签
        is_caption = (
            re.match(r'^(?:№|No\.?|NO\.?)\s*\d+', line, re.IGNORECASE) or
            '中文标签' in line or
            '标签' in line
        )

        if is_caption:
            subject_name = extract_subject_name_from_caption(line)
            is_chinese = is_chinese_label_caption(line)

            caption = PhotoCaption(
                caption=line,
                page_number=page_idx + 1,
                row_index=i,
                is_chinese_label=is_chinese,
                subject_name=subject_name
            )
            captions.append(caption)

    if not captions:
        return None

    return PhotoPage(
        page_number=page_idx + 1,
        captions=captions
    )


def find_all_photo_pages(pdf, start_search_idx: int = 0) -> List[PhotoPage]:
    """
    查找所有照片页

    Args:
        pdf: pdfplumber PDF对象
        start_search_idx: 开始搜索的页索引

    Returns:
        PhotoPage对象列表
    """
    photo_pages = []

    for page_idx in range(start_search_idx, len(pdf.pages)):
        page = pdf.pages[page_idx]
        header = parse_page_header(page, page_idx)

        header_type = detect_header_type(header.cleaned_text)
        if header_type == 'photo_page':
            photo_page = extract_photo_page_captions(page, page_idx)
            if photo_page:
                photo_pages.append(photo_page)

    return photo_pages


# ============== 主解析函数 ==============

def parse_report_pdf(file_path: str) -> ParsedReport:
    """
    解析检验报告PDF文件

    Args:
        file_path: PDF文件路径

    Returns:
        ParsedReport对象
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"PDF文件不存在: {file_path}")

    with pdfplumber.open(file_path) as pdf:
        total_pages = len(pdf.pages)

        result = ParsedReport(
            file_path=str(file_path),
            total_pages=total_pages
        )

        # 第一步：扫描所有页眉，确定各页类型
        page_types = {}
        for page_idx in range(total_pages):
            page = pdf.pages[page_idx]
            header = parse_page_header(page, page_idx)
            result.page_headers[page_idx] = header

            header_type = detect_header_type(header.cleaned_text)
            page_types[page_idx] = header_type

        # 第二步：定位关键页
        # 第三页（检验报告首页）
        third_page_idx = None
        for page_idx, ptype in page_types.items():
            if ptype == 'first_page':
                third_page_idx = page_idx
                result.third_page_idx = page_idx
                break

        # 第四页起（检验报告正文）
        report_start_idx = None
        for page_idx, ptype in page_types.items():
            if ptype == 'report_page':
                report_start_idx = page_idx
                result.sample_desc_start_idx = page_idx
                break

        # 照片页起始
        photo_start_idx = None
        for page_idx, ptype in page_types.items():
            if ptype == 'photo_page':
                photo_start_idx = page_idx
                result.photo_pages_start_idx = page_idx
                break

        # 第三步：提取首页字段（第1页）
        if total_pages > 0:
            first_page = pdf.pages[0]
            result.first_page_fields = extract_first_page_fields(first_page)

        # 第四步：提取第三页表格
        if third_page_idx is not None:
            third_page = pdf.pages[third_page_idx]
            result.third_page_table = extract_third_page_table(third_page)

        # 第五步：提取样品描述表格
        if report_start_idx is not None:
            result.sample_description = extract_sample_description_tables(
                pdf, report_start_idx
            )

        # 第六步：提取所有照片页
        if photo_start_idx is not None:
            result.photo_pages = find_all_photo_pages(pdf, photo_start_idx)

    return result


# ============== 辅助函数 ==============

def format_parsed_result(result: ParsedReport) -> Dict[str, Any]:
    """
    将解析结果格式化为字典

    Args:
        result: ParsedReport对象

    Returns:
        格式化的字典
    """
    output = {
        "file_path": result.file_path,
        "total_pages": result.total_pages,
        "page_structure": {
            "first_page": result.first_page_idx + 1,
            "third_page": result.third_page_idx + 1 if result.third_page_idx is not None else None,
            "sample_description_start": result.sample_desc_start_idx + 1 if result.sample_desc_start_idx is not None else None,
            "photo_pages_start": result.photo_pages_start_idx + 1 if result.photo_pages_start_idx is not None else None,
        },
        "first_page_fields": result.first_page_fields.to_dict() if result.first_page_fields else None,
        "third_page_table": result.third_page_table.to_dict() if result.third_page_table else None,
        "sample_description": None,
        "photo_pages": [],
    }

    # 样品描述表格
    if result.sample_description:
        output["sample_description"] = {
            "headers": result.sample_description.headers,
            "row_count": len(result.sample_description.rows),
            "start_page": result.sample_description.start_page,
            "end_page": result.sample_description.end_page,
            "rows": [
                {
                    "序号": row.序号,
                    "部件名称": row.部件名称,
                    "规格型号": row.规格型号,
                    "序列号/批号": row.序列号_批号,
                    "生产日期": row.生产日期,
                    "备注": row.备注,
                }
                for row in result.sample_description.rows
            ]
        }

    # 照片页
    for photo_page in result.photo_pages:
        page_data = {
            "page_number": photo_page.page_number,
            "captions": [
                {
                    "caption": cap.caption,
                    "is_chinese_label": cap.is_chinese_label,
                    "subject_name": cap.subject_name,
                }
                for cap in photo_page.captions
            ]
        }
        output["photo_pages"].append(page_data)

    return output


def compare_first_and_third_page(result: ParsedReport) -> Dict[str, Any]:
    """
    比较首页和第三页的三字段是否一致

    Args:
        result: ParsedReport对象

    Returns:
        比较结果
    """
    if not result.first_page_fields or not result.third_page_table:
        return {"error": "缺少首页或第三页数据"}

    first = result.first_page_fields
    third = result.third_page_table

    fields = ['委托方', '样品名称', '型号规格']
    comparisons = {}

    for field in fields:
        first_val = getattr(first, field, None)
        third_val = getattr(third, field, None)

        # 处理 / 与空白等价
        first_normalized = first_val if first_val and first_val.strip() not in ['', '/'] else '/'
        third_normalized = third_val if third_val and third_val.strip() not in ['', '/'] else '/'

        comparisons[field] = {
            "first_page": first_val,
            "third_page": third_val,
            "match": first_normalized == third_normalized,
            "is_sample_description_reference": first_val == '见"样品描述"栏' if first_val else False
        }

    return {
        "all_match": all(c["match"] for c in comparisons.values()),
        "comparisons": comparisons
    }


# ============== 命令行测试 ==============

if __name__ == "__main__":
    import json
    import sys

    # 测试解析
    test_files = [
        "/Users/lulingfeng/Documents/工作/开发/报告核对工具2026.2.9/QW2025-2795 Draft.pdf",
        "/Users/lulingfeng/Documents/工作/开发/报告核对工具2026.2.9/QW2025-1541 Draft.pdf",
    ]

    for pdf_path in test_files:
        print(f"\n{'='*60}")
        print(f"解析文件: {pdf_path}")
        print('='*60)

        try:
            result = parse_report_pdf(pdf_path)
            formatted = format_parsed_result(result)

            # 输出关键信息
            print(f"\n总页数: {result.total_pages}")
            print(f"\n页面结构:")
            print(f"  - 首页: 第{result.first_page_idx + 1}页")
            print(f"  - 第三页表格: 第{result.third_page_idx + 1}页" if result.third_page_idx else "  - 第三页表格: 未找到")
            print(f"  - 样品描述: 第{result.sample_desc_start_idx + 1}页起" if result.sample_desc_start_idx else "  - 样品描述: 未找到")
            print(f"  - 照片页: 第{result.photo_pages_start_idx + 1}页起" if result.photo_pages_start_idx else "  - 照片页: 未找到")

            print(f"\n首页三字段:")
            if result.first_page_fields:
                for k, v in result.first_page_fields.to_dict().items():
                    print(f"  {k}: {v}")

            print(f"\n第三页表格字段:")
            if result.third_page_table:
                for k, v in result.third_page_table.to_dict().items():
                    print(f"  {k}: {v}")

            print(f"\n首页与第三页比对:")
            comparison = compare_first_and_third_page(result)
            print(f"  全部一致: {comparison['all_match']}")
            for field, comp in comparison['comparisons'].items():
                status = "✓" if comp['match'] else "✗"
                print(f"  {status} {field}: 首页='{comp['first_page']}' vs 第三页='{comp['third_page']}'")

            print(f"\n样品描述表格:")
            if result.sample_description:
                print(f"  行数: {len(result.sample_description.rows)}")
                print(f"  页范围: 第{result.sample_description.start_page}页 - 第{result.sample_description.end_page}页")
                print(f"  前5行:")
                for i, row in enumerate(result.sample_description.rows[:5]):
                    print(f"    {i+1}. {row.部件名称} | {row.规格型号} | {row.序列号_批号}")

            print(f"\n照片页统计:")
            print(f"  照片页数: {len(result.photo_pages)}")
            chinese_label_count = sum(
                1 for pp in result.photo_pages
                for cap in pp.captions if cap.is_chinese_label
            )
            print(f"  中文标签数: {chinese_label_count}")

            if result.photo_pages:
                print(f"  前3页照片说明:")
                for pp in result.photo_pages[:3]:
                    for cap in pp.captions:
                        label_type = "[中文标签]" if cap.is_chinese_label else "[照片]"
                        print(f"    第{pp.page_number}页 {label_type} {cap.subject_name}")

        except Exception as e:
            print(f"错误: {e}")
            import traceback
            traceback.print_exc()
