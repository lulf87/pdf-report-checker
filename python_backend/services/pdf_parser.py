"""
PDF解析服务
- 提取文本、表格、图片
- 识别页眉
- 定位特定页面
"""

import fitz  # PyMuPDF
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import json

from models.schemas import PageInfo, TableData


class PDFParser:
    """PDF文档解析器"""

    # 页眉关键词映射
    HEADER_PATTERNS = {
        'home_page': ['检验报告首页', '检验报告首页'],
        'report_page': ['检验报告'],
        'photo_page': ['检验报告照片页']
    }

    def __init__(self):
        self.current_doc = None
        self.current_path = None

    def parse(self, pdf_path: str) -> List[PageInfo]:
        """
        解析PDF文件，返回所有页面信息
        """
        doc = fitz.open(pdf_path)
        self.current_doc = doc
        self.current_path = pdf_path

        pages = []
        for page_num in range(len(doc)):
            page_info = self._parse_page(doc, page_num)
            pages.append(page_info)

        return pages

    def _parse_page(self, doc: fitz.Document, page_num: int) -> PageInfo:
        """解析单个页面"""
        page = doc[page_num]

        # 提取文本
        text = page.get_text()

        # 识别页眉（页面顶部区域）
        header = self._extract_header(page, text)

        # 检测表格
        tables = self._extract_tables(page)

        # 检测图片
        images = self._extract_images(page, page_num)

        return PageInfo(
            page_num=page_num + 1,  # 1-based page number
            page_header=header,
            text_content=text[:2000] if text else None,  # 限制长度
            has_table=len(tables) > 0,
            has_image=len(images) > 0,
            tables=tables,
            images=images
        )

    def _extract_header(self, page: fitz.Page, text: str) -> Optional[str]:
        """
        提取页眉文本
        策略：检查页面顶部区域和文本开头
        按模式长度从长到短匹配，避免"检验报告"误匹配"检验报告照片页"
        """
        # 获取页面顶部区域的文本（顶部10%区域）
        page_rect = page.rect
        header_rect = fitz.Rect(
            page_rect.x0,
            page_rect.y0,
            page_rect.x1,
            page_rect.y0 + page_rect.height * 0.15
        )

        header_text = page.get_text("text", clip=header_rect)

        # 清理空白字符进行匹配
        cleaned_header = self._clean_whitespace(header_text)

        # 收集所有模式并按长度排序（从长到短匹配）
        all_patterns = []
        for header_type, patterns in self.HEADER_PATTERNS.items():
            for pattern in patterns:
                all_patterns.append((len(pattern), pattern))

        # 按长度降序排序，确保先匹配更具体的模式
        all_patterns.sort(key=lambda x: -x[0])

        # 检查是否匹配已知页眉模式
        for _, pattern in all_patterns:
            cleaned_pattern = self._clean_whitespace(pattern)
            if cleaned_pattern in cleaned_header:
                return pattern

        # 返回原始页眉文本（前100字符）
        return header_text[:100].strip() if header_text else None

    def _clean_whitespace(self, text: str) -> str:
        """移除所有空白字符用于匹配"""
        return re.sub(r'\s+', '', text)

    def _extract_tables(self, page: fitz.Page) -> List[Dict[str, Any]]:
        """
        提取页面中的表格
        使用PyMuPDF的表格检测功能
        """
        tables = []

        try:
            # 查找表格
            tab = page.find_tables()

            if tab.tables:
                for idx, table in enumerate(tab.tables):
                    # 提取表格内容
                    data = table.extract()

                    if data:
                        headers = data[0] if data else []
                        rows = data[1:] if len(data) > 1 else []
                        tables.append({
                            'index': idx,
                            'row_count': len(rows),
                            'col_count': len(headers),
                            'headers': headers,
                            'preview': rows[:5]
                        })

        except Exception as e:
            print(f"表格提取失败: {e}")

        return tables

    def _extract_images(self, page: fitz.Page, page_num: int) -> List[Dict[str, Any]]:
        """
        提取页面中的图片信息
        """
        images = []

        try:
            # 获取页面中的图片列表
            image_list = page.get_images(full=True)

            for img_index, img in enumerate(image_list):
                xref = img[0]
                base_image = self.current_doc.extract_image(xref)

                if base_image:
                    images.append({
                        'index': img_index,
                        'xref': xref,
                        'width': base_image.get('width'),
                        'height': base_image.get('height'),
                        'ext': base_image.get('ext'),
                        'size': len(base_image.get('image', b''))
                    })

        except Exception as e:
            print(f"图片提取失败: {e}")

        return images

    def extract_table_detailed(self, pdf_path: str, page_num: int, table_index: int = 0) -> Optional[TableData]:
        """
        提取指定页面的详细表格数据
        """
        doc = fitz.open(pdf_path)

        try:
            page = doc[page_num - 1]  # 0-based index
            tab = page.find_tables()

            if not tab.tables or table_index >= len(tab.tables):
                return None

            table = tab.tables[table_index]
            data = table.extract()

            if not data:
                return None

            # 转换为字符串列表
            headers = [str(h) if h is not None else '' for h in data[0]]
            rows = []
            for row_data in data[1:]:
                rows.append([str(cell) if cell is not None else '' for cell in row_data])

            return TableData(
                page_num=page_num,
                table_index=table_index,
                headers=headers,
                rows=rows,
                row_count=len(rows),
                col_count=len(headers)
            )

        finally:
            doc.close()

    def extract_page_as_image(self, pdf_path: str, page_num: int, dpi: int = 150) -> str:
        """
        将指定页面转换为图片并保存
        返回图片路径
        """
        doc = fitz.open(pdf_path)

        try:
            page = doc[page_num - 1]

            # 设置缩放比例
            zoom = dpi / 72
            mat = fitz.Matrix(zoom, zoom)

            # 渲染为图片
            pix = page.get_pixmap(matrix=mat)

            # 保存图片
            output_path = f"temp/page_{page_num}.png"
            Path(output_path).parent.mkdir(exist_ok=True)
            pix.save(output_path)

            return output_path

        finally:
            doc.close()

    def find_pages_by_header(self, pages: List[PageInfo], header_pattern: str) -> List[int]:
        """
        根据页眉查找页面

        使用精确匹配，避免误匹配：
        - "检验报告" 不应匹配 "检验报告照片页"
        - "检验报告首页" 不应匹配 "检验报告"
        """
        result = []
        cleaned_pattern = self._clean_whitespace(header_pattern)

        for page in pages:
            if page.page_header:
                cleaned_header = self._clean_whitespace(page.page_header)

                # 仅使用精确匹配
                if cleaned_header == cleaned_pattern:
                    result.append(page.page_num)

        return result

    def extract_home_page_fields(self, pdf_path: str) -> Dict[str, str]:
        """
        提取首页的三个关键字段：
        - 委 托 方
        - 样品名称
        - 型号规格
        """
        doc = fitz.open(pdf_path)

        try:
            page = doc[0]  # 第一页
            text = page.get_text()

            fields = {}
            field_names = ['委 托 方', '样品名称', '型号规格']

            for field_name in field_names:
                value = self._extract_field_value(text, field_name)
                fields[field_name] = value

            return fields

        finally:
            doc.close()

    def _extract_field_value(self, text: str, field_name: str) -> str:
        """
        从文本中提取字段值
        策略：查找字段名，然后取右侧或下一行的内容
        """
        lines = text.split('\n')

        for i, line in enumerate(lines):
            # 清理字段名中的空格进行匹配
            cleaned_field = field_name.replace(' ', '')
            cleaned_line = line.replace(' ', '')

            if cleaned_field in cleaned_line:
                # 尝试在同一行获取值（字段名右侧）
                field_pos = cleaned_line.find(cleaned_field)
                if field_pos >= 0:
                    # 获取原始行中对应位置右侧的内容
                    original_pos = self._find_original_position(line, cleaned_line, field_pos + len(cleaned_field))
                    if original_pos < len(line):
                        value = line[original_pos:].strip()
                        if value:
                            return value

                # 尝试下一行
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    if next_line and not any(f.replace(' ', '') in next_line.replace(' ', '') for f in ['委 托 方', '样品名称', '型号规格']):
                        return next_line

        return ''

    def _find_original_position(self, original: str, cleaned: str, cleaned_pos: int) -> int:
        """
        将清理后的位置映射回原始字符串位置
        """
        original_pos = 0
        cleaned_idx = 0

        for char in original:
            if cleaned_idx >= cleaned_pos:
                return original_pos
            if not char.isspace():
                cleaned_idx += 1
            original_pos += 1

        return len(original)

    def close(self):
        """关闭当前文档"""
        if self.current_doc:
            self.current_doc.close()
            self.current_doc = None
            self.current_path = None
