"""
页码连续性校验模块
- 从第三页（页眉包含"检验报告首页"）开始校验页码
- 检查页码格式：共XXX页 第Y页
- 校验规则：
  1. Y应从1开始连续递增，无跳号、无重复
  2. 最后一页的Y值必须等于XXX
  3. 所有页的XXX值必须相同
"""

import re
import fitz  # PyMuPDF
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from models.schemas import ErrorItem, PageInfo


@dataclass
class PageNumberInfo:
    """单页页码信息"""
    page_num: int          # 文档实际页码（从1开始）
    total_pages: int       # XXX（总页数）
    current_page: int      # Y（当前页码）
    raw_text: str          # 原始页码文本


class PageNumberChecker:
    """页码连续性校验器"""

    # 页码正则模式：匹配 "共XXX页 第Y页" 格式
    PAGE_NUMBER_PATTERN = re.compile(
        r'共\s*(\d+)\s*页\s*第\s*(\d+)\s*页'
    )

    # 错误代码定义
    ERROR_CODES = {
        'PAGE_NUMBER_ERROR_001': '页码Y不连续（跳号或重复）',
        'PAGE_NUMBER_ERROR_002': '末页Y不等于XXX',
        'PAGE_NUMBER_ERROR_003': '各页XXX不一致',
    }

    def __init__(self):
        pass

    def check_page_numbers(
        self,
        pdf_path: str,
        pages: List[PageInfo]
    ) -> Tuple[List[PageNumberInfo], List[ErrorItem]]:
        """
        执行页码连续性校验

        Args:
            pdf_path: PDF文件路径
            pages: 页面信息列表

        Returns:
            Tuple[List[PageNumberInfo], List[ErrorItem]]: (页码信息列表, 错误列表)
        """
        # 1. 定位第三页（检验报告首页）
        start_page_idx = self._find_third_page_index(pages)

        if start_page_idx is None:
            return [], []

        # 2. 提取从第三页开始的所有页码
        page_number_infos = []
        doc = fitz.open(pdf_path)

        try:
            for i in range(start_page_idx, len(pages)):
                page_info = pages[i]
                page = doc[page_info.page_num - 1]  # 0-based index

                # 提取右上角页码
                page_number_info = self._extract_page_number(
                    page, page_info.page_num
                )

                if page_number_info:
                    page_number_infos.append(page_number_info)

        finally:
            doc.close()

        # 3. 校验页码连续性
        errors = self._validate_page_numbers(page_number_infos)

        return page_number_infos, errors

    def _find_third_page_index(self, pages: List[PageInfo]) -> Optional[int]:
        """
        定位第三页（页眉包含"检验报告首页"）的索引

        Returns:
            第三页的索引（0-based），如果未找到则返回None
        """
        for idx, page in enumerate(pages):
            if page.page_header:
                # 清理空白字符进行匹配
                cleaned_header = re.sub(r'\s+', '', page.page_header)
                if '检验报告首页' in cleaned_header:
                    return idx
        return None

    def _extract_page_number(
        self,
        page: Any,
        page_num: int
    ) -> Optional[PageNumberInfo]:
        """
        从页面右上角提取页码文本

        Args:
            page: PyMuPDF页面对象
            page_num: 页码（1-based）

        Returns:
            PageNumberInfo对象，如果未找到则返回None
        """
        # 获取页面右上角区域（右上20%区域）
        page_rect = page.rect
        header_right_rect = fitz.Rect(
            page_rect.x1 - page_rect.width * 0.5,  # 右侧50%宽度
            page_rect.y0,                           # 顶部
            page_rect.x1,                           # 右边界
            page_rect.y0 + page_rect.height * 0.20  # 顶部20%高度
        )

        # 提取该区域文本
        text = page.get_text("text", clip=header_right_rect)

        if not text:
            return None

        # 匹配页码格式
        match = self.PAGE_NUMBER_PATTERN.search(text)

        if match:
            total_pages = int(match.group(1))
            current_page = int(match.group(2))

            return PageNumberInfo(
                page_num=page_num,
                total_pages=total_pages,
                current_page=current_page,
                raw_text=match.group(0)
            )

        return None

    def _validate_page_numbers(
        self,
        page_number_infos: List[PageNumberInfo]
    ) -> List[ErrorItem]:
        """
        校验页码连续性

        校验规则：
        1. Y应从1开始连续递增，无跳号、无重复
        2. 最后一页的Y值必须等于XXX
        3. 所有页的XXX值必须相同

        Args:
            page_number_infos: 页码信息列表

        Returns:
            错误列表
        """
        errors = []

        if not page_number_infos:
            return errors

        # 校验规则3：XXX一致性
        first_total = page_number_infos[0].total_pages
        for info in page_number_infos:
            if info.total_pages != first_total:
                errors.append(ErrorItem(
                    level="ERROR",
                    message=f"页码总页数不一致：第{info.page_num}页标记为'共{info.total_pages}页'，"
                           f"但首页标记为'共{first_total}页'",
                    page_num=info.page_num,
                    location=f"页码区域",
                    details={
                        'error_code': 'PAGE_NUMBER_ERROR_003',
                        'expected_total': first_total,
                        'actual_total': info.total_pages,
                        'raw_text': info.raw_text
                    }
                ))

        # 校验规则1：Y连续性
        expected_current = 1
        last_page_num = None
        last_current = None

        for info in page_number_infos:
            if info.current_page != expected_current:
                # 检查是否是重复
                if last_current is not None and info.current_page == last_current:
                    errors.append(ErrorItem(
                        level="ERROR",
                        message=f"页码重复：第{info.page_num}页标记为'第{info.current_page}页'，"
                               f"与第{last_page_num}页重复",
                        page_num=info.page_num,
                        location=f"页码区域",
                        details={
                            'error_code': 'PAGE_NUMBER_ERROR_001',
                            'expected': expected_current,
                            'actual': info.current_page,
                            'last_page_num': last_page_num,
                            'raw_text': info.raw_text
                        }
                    ))
                else:
                    # 跳号
                    errors.append(ErrorItem(
                        level="ERROR",
                        message=f"页码跳号：第{info.page_num}页标记为'第{info.current_page}页'，"
                               f"期望为'第{expected_current}页'",
                        page_num=info.page_num,
                        location=f"页码区域",
                        details={
                            'error_code': 'PAGE_NUMBER_ERROR_001',
                            'expected': expected_current,
                            'actual': info.current_page,
                            'raw_text': info.raw_text
                        }
                    ))
            else:
                expected_current += 1

            last_page_num = info.page_num
            last_current = info.current_page

        # 校验规则2：末页Y等于XXX
        if page_number_infos:
            last_info = page_number_infos[-1]
            if last_info.current_page != last_info.total_pages:
                errors.append(ErrorItem(
                    level="ERROR",
                    message=f"末页页码错误：最后一页（第{last_info.page_num}页）标记为"
                           f"'共{last_info.total_pages}页 第{last_info.current_page}页'，"
                           f"但当前页码{last_info.current_page}不等于总页数{last_info.total_pages}",
                    page_num=last_info.page_num,
                    location=f"页码区域",
                    details={
                        'error_code': 'PAGE_NUMBER_ERROR_002',
                        'expected': last_info.total_pages,
                        'actual': last_info.current_page,
                        'raw_text': last_info.raw_text
                    }
                ))

        return errors

    def extract_page_number_info(
        self,
        pdf_path: str,
        pages: List[PageInfo]
    ) -> List[Dict[str, Any]]:
        """
        提取页码信息（用于外部调用）

        Args:
            pdf_path: PDF文件路径
            pages: 页面信息列表

        Returns:
            页码信息字典列表
        """
        page_number_infos, _ = self.check_page_numbers(pdf_path, pages)

        return [
            {
                'page_num': info.page_num,
                'total_pages': info.total_pages,
                'current_page': info.current_page,
                'raw_text': info.raw_text
            }
            for info in page_number_infos
        ]
