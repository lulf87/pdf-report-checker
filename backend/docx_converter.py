"""
DOCX to PDF Converter Module
============================

将DOCX文件转换为PDF，使用LibreOffice作为渲染引擎，确保格式一致性。

Requirements:
    - LibreOffice 7.x 或更高版本

Usage:
    from docx_converter import convert_docx_to_pdf, ConversionError

    pdf_path = convert_docx_to_pdf("input.docx", "/output/dir")
"""

import os
import subprocess
import tempfile
import shutil
import logging
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ConversionError(Exception):
    """DOCX转PDF转换错误"""
    pass


class LibreOfficeNotFoundError(ConversionError):
    """LibreOffice未找到错误"""
    pass


class ConversionTimeoutError(ConversionError):
    """转换超时错误"""
    pass


@dataclass
class ConversionConfig:
    """转换配置"""
    # LibreOffice可执行文件路径（None则自动查找）
    soffice_path: Optional[str] = None
    # 转换超时时间（秒）
    timeout: int = 120
    # 是否保留临时文件（调试用）
    keep_temp: bool = False
    # PDF导出过滤器选项
    pdf_quality: int = 90
    # 是否嵌入字体
    embed_fonts: bool = True


# 全局配置实例
_default_config = ConversionConfig()


def find_libreoffice() -> str:
    """
    查找LibreOffice可执行文件路径

    Returns:
        str: soffice可执行文件的完整路径

    Raises:
        LibreOfficeNotFoundError: 未找到LibreOffice
    """
    # 常见路径列表
    possible_paths = [
        # macOS
        "/Applications/LibreOffice.app/Contents/MacOS/soffice",
        "/Applications/LibreOffice.app/Contents/MacOS/soffice.bin",
        # Linux
        "/usr/bin/soffice",
        "/usr/bin/libreoffice",
        "/usr/lib/libreoffice/program/soffice",
        # Windows
        r"C:\Program Files\LibreOffice\program\soffice.exe",
        r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
    ]

    # 首先检查环境变量
    env_path = os.environ.get("LIBREOFFICE_PATH")
    if env_path and os.path.isfile(env_path):
        return env_path

    # 尝试使用which命令查找
    try:
        result = subprocess.run(
            ["which", "soffice"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            path = result.stdout.strip()
            if os.path.isfile(path):
                return path
    except (subprocess.SubprocessError, FileNotFoundError):
        pass

    # 检查常见路径
    for path in possible_paths:
        if os.path.isfile(path):
            return path

    raise LibreOfficeNotFoundError(
        "未找到LibreOffice。请安装LibreOffice或设置LIBREOFFICE_PATH环境变量。"
        "下载地址: https://www.libreoffice.org/download/download/"
    )


def get_soffice_version(soffice_path: str) -> Optional[str]:
    """
    获取LibreOffice版本信息

    Args:
        soffice_path: soffice可执行文件路径

    Returns:
        str: 版本号字符串，或None如果获取失败
    """
    try:
        result = subprocess.run(
            [soffice_path, "--version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            # 输出格式类似: LibreOffice 7.6.4.1 ...
            output = result.stdout.strip()
            parts = output.split()
            if len(parts) >= 2:
                return parts[1]
    except (subprocess.SubprocessError, FileNotFoundError):
        pass
    return None


def convert_docx_to_pdf(
    docx_path: str,
    output_dir: Optional[str] = None,
    config: Optional[ConversionConfig] = None
) -> str:
    """
    将DOCX文件转换为PDF

    使用LibreOffice作为渲染引擎，确保与直接导出的PDF格式一致。
    转换后的PDF文件名将基于原DOCX文件名（仅扩展名改为.pdf）。

    Args:
        docx_path: DOCX文件的完整路径
        output_dir: 输出目录，默认为DOCX所在目录
        config: 转换配置，默认使用全局配置

    Returns:
        str: 生成的PDF文件的完整路径

    Raises:
        ConversionError: 转换过程中发生错误
        LibreOfficeNotFoundError: 未找到LibreOffice
        ConversionTimeoutError: 转换超时
        FileNotFoundError: DOCX文件不存在

    Examples:
        >>> pdf_path = convert_docx_to_pdf("/path/to/report.docx", "/output/dir")
        >>> print(pdf_path)
        '/output/dir/report.pdf'
    """
    docx_path = Path(docx_path).resolve()

    # 验证输入文件
    if not docx_path.exists():
        raise FileNotFoundError(f"DOCX文件不存在: {docx_path}")

    if not docx_path.suffix.lower() in (".docx", ".doc"):
        raise ConversionError(f"不支持的文件格式: {docx_path.suffix}")

    # 确定输出目录
    if output_dir is None:
        output_dir = docx_path.parent
    else:
        output_dir = Path(output_dir).resolve()
        if not output_dir.exists():
            output_dir.mkdir(parents=True, exist_ok=True)

    # 使用配置
    cfg = config or _default_config

    # 查找LibreOffice
    soffice_path = cfg.soffice_path or find_libreoffice()

    # 验证LibreOffice版本
    version = get_soffice_version(soffice_path)
    if version:
        logger.info(f"使用LibreOffice版本: {version}")
    else:
        logger.warning("无法获取LibreOffice版本信息")

    # 构建输出文件名
    output_filename = docx_path.stem + ".pdf"
    output_path = output_dir / output_filename

    # 创建临时工作目录
    temp_dir = tempfile.mkdtemp(prefix="docx_convert_")

    try:
        # 构建LibreOffice命令
        # --headless: 无头模式
        # --convert-to pdf: 转换为PDF
        # --outdir: 输出目录
        cmd = [
            soffice_path,
            "--headless",
            "--convert-to", "pdf",
            "--outdir", temp_dir,
            str(docx_path)
        ]

        logger.info(f"开始转换: {docx_path} -> {output_path}")
        logger.debug(f"执行命令: {' '.join(cmd)}")

        # 执行转换
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=cfg.timeout
            )
        except subprocess.TimeoutExpired as e:
            raise ConversionTimeoutError(
                f"转换超时（{cfg.timeout}秒）: {docx_path}"
            ) from e

        # 检查命令执行结果
        if result.returncode != 0:
            error_msg = result.stderr.strip() if result.stderr else "未知错误"
            raise ConversionError(
                f"LibreOffice转换失败 (exit code {result.returncode}): {error_msg}"
            )

        # 查找生成的PDF文件
        temp_files = list(Path(temp_dir).glob("*.pdf"))
        if not temp_files:
            raise ConversionError(
                f"转换后未找到PDF文件，临时目录: {temp_dir}"
            )

        generated_pdf = temp_files[0]

        # 移动到目标位置
        if output_path.exists():
            logger.warning(f"目标文件已存在，将被覆盖: {output_path}")
            output_path.unlink()

        shutil.move(str(generated_pdf), str(output_path))

        logger.info(f"转换成功: {output_path}")
        return str(output_path)

    except ConversionError:
        raise
    except Exception as e:
        raise ConversionError(f"转换过程中发生错误: {e}") from e

    finally:
        # 清理临时目录
        if not cfg.keep_temp and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
        elif cfg.keep_temp:
            logger.debug(f"保留临时目录: {temp_dir}")


def batch_convert(
    docx_paths: list[str],
    output_dir: str,
    config: Optional[ConversionConfig] = None
) -> dict[str, str]:
    """
    批量转换DOCX文件为PDF

    Args:
        docx_paths: DOCX文件路径列表
        output_dir: 输出目录
        config: 转换配置

    Returns:
        dict: {原始路径: 输出路径或错误信息}
              成功项值为PDF路径，失败项值为错误描述字符串

    Examples:
        >>> results = batch_convert(["a.docx", "b.docx"], "/output")
        >>> print(results)
        {'a.docx': '/output/a.pdf', 'b.docx': 'ConversionError: ...'}
    """
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    results = {}

    for docx_path in docx_paths:
        try:
            pdf_path = convert_docx_to_pdf(docx_path, str(output_dir), config)
            results[docx_path] = pdf_path
        except Exception as e:
            results[docx_path] = f"{type(e).__name__}: {e}"
            logger.error(f"转换失败 {docx_path}: {e}")

    return results


def set_default_config(config: ConversionConfig) -> None:
    """
    设置全局默认配置

    Args:
        config: 新的默认配置
    """
    global _default_config
    _default_config = config


def get_default_config() -> ConversionConfig:
    """
    获取当前全局默认配置

    Returns:
        ConversionConfig: 当前默认配置的副本
    """
    return ConversionConfig(
        soffice_path=_default_config.soffice_path,
        timeout=_default_config.timeout,
        keep_temp=_default_config.keep_temp,
        pdf_quality=_default_config.pdf_quality,
        embed_fonts=_default_config.embed_fonts
    )


# 便捷函数

def is_libreoffice_available() -> bool:
    """
    检查LibreOffice是否可用

    Returns:
        bool: 如果LibreOffice可用返回True
    """
    try:
        find_libreoffice()
        return True
    except LibreOfficeNotFoundError:
        return False


def validate_docx(docx_path: str) -> bool:
    """
    验证DOCX文件是否有效

    Args:
        docx_path: DOCX文件路径

    Returns:
        bool: 文件存在且格式正确返回True
    """
    path = Path(docx_path)
    return path.exists() and path.suffix.lower() in (".docx", ".doc")


if __name__ == "__main__":
    # 简单的命令行接口
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    if len(sys.argv) < 2:
        print("Usage: python docx_converter.py <docx_file> [output_dir]")
        sys.exit(1)

    docx_file = sys.argv[1]
    out_dir = sys.argv[2] if len(sys.argv) > 2 else None

    try:
        result = convert_docx_to_pdf(docx_file, out_dir)
        print(f"转换成功: {result}")
    except Exception as e:
        print(f"转换失败: {e}", file=sys.stderr)
        sys.exit(1)
