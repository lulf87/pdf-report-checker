"""
报告审核工具 - Python后端服务
FastAPI + PaddleOCR + PDF/DOCX解析
"""

import os
import sys
import uuid
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# 导入本地模块
from services.pdf_parser import PDFParser
from services.docx_parser import DocxParser
from services.ocr_service import OCRService
from services.report_checker import ReportChecker
from models.schemas import (
    UploadResponse,
    CheckResult,
    HealthResponse,
    PageInfo,
    TableData,
    OCRResult,
    FieldComparison
)

# 创建FastAPI应用
app = FastAPI(
    title="报告审核工具API",
    description="PDF/DOCX报告解析与OCR核对服务",
    version="1.0.0"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制为Electron前端
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化服务
pdf_parser = PDFParser()
docx_parser = DocxParser()
ocr_service = OCRService()
report_checker = ReportChecker()

# 上传文件存储目录
UPLOAD_DIR = Path("./uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# 临时文件存储目录
TEMP_DIR = Path("./temp")
TEMP_DIR.mkdir(exist_ok=True)


# ============ 健康检查 ============

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """健康检查端点"""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        version="1.0.0"
    )


# ============ 文件上传 ============

@app.post("/api/upload", response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...)):
    """
    上传PDF或DOCX文件
    """
    # 验证文件类型
    allowed_extensions = {'.pdf', '.docx'}
    file_ext = Path(file.filename).suffix.lower()

    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型: {file_ext}，仅支持PDF和DOCX"
        )

    # 生成唯一文件名
    file_id = str(uuid.uuid4())
    safe_filename = f"{file_id}{file_ext}"
    file_path = UPLOAD_DIR / safe_filename

    try:
        # 保存上传的文件
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        return UploadResponse(
            success=True,
            file_id=file_id,
            filename=file.filename,
            file_path=str(file_path),
            file_type=file_ext.replace('.', ''),
            message="文件上传成功"
        )

    except Exception as e:
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(status_code=500, detail=f"文件保存失败: {str(e)}")

    finally:
        file.file.close()


# ============ 文件解析 ============

@app.post("/api/parse/{file_id}")
async def parse_file(file_id: str):
    """
    解析上传的文件，提取页面信息和表格数据
    """
    # 查找文件
    pdf_path = UPLOAD_DIR / f"{file_id}.pdf"
    docx_path = UPLOAD_DIR / f"{file_id}.docx"

    file_path = None
    file_type = None

    if pdf_path.exists():
        file_path = pdf_path
        file_type = "pdf"
    elif docx_path.exists():
        file_path = docx_path
        file_type = "docx"
    else:
        raise HTTPException(status_code=404, detail="文件不存在")

    try:
        # 根据文件类型选择解析器
        if file_type == "pdf":
            pages = pdf_parser.parse(str(file_path))
        else:
            # DOCX先转换为PDF再解析
            temp_pdf = TEMP_DIR / f"{file_id}.pdf"
            pages = docx_parser.parse_to_pdf(str(file_path), str(temp_pdf))

        return {
            "success": True,
            "file_id": file_id,
            "file_type": file_type,
            "total_pages": len(pages),
            "pages": [page.dict() for page in pages]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件解析失败: {str(e)}")


# ============ OCR识别 ============

@app.post("/api/ocr/{file_id}/page/{page_num}")
async def ocr_page(file_id: str, page_num: int):
    """
    对指定页面进行OCR识别
    """
    pdf_path = UPLOAD_DIR / f"{file_id}.pdf"

    if not pdf_path.exists():
        # 检查是否有docx需要转换
        docx_path = UPLOAD_DIR / f"{file_id}.docx"
        if docx_path.exists():
            temp_pdf = TEMP_DIR / f"{file_id}.pdf"
            if not temp_pdf.exists():
                docx_parser.parse_to_pdf(str(docx_path), str(temp_pdf))
            pdf_path = temp_pdf
        else:
            raise HTTPException(status_code=404, detail="文件不存在")

    try:
        ocr_result = ocr_service.recognize_page(str(pdf_path), page_num)

        return {
            "success": True,
            "file_id": file_id,
            "page_num": page_num,
            "ocr_result": ocr_result.dict()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OCR识别失败: {str(e)}")


@app.post("/api/ocr/{file_id}/image")
async def ocr_image(file_id: str, image_path: str):
    """
    对指定图片进行OCR识别
    """
    try:
        ocr_result = ocr_service.recognize_image(image_path)

        return {
            "success": True,
            "file_id": file_id,
            "ocr_result": ocr_result.dict()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OCR识别失败: {str(e)}")


# ============ 报告核对 ============

from fastapi import Query
from config import settings as app_settings

@app.post("/api/check/{file_id}", response_model=CheckResult)
async def check_report(
    file_id: str,
    background_tasks: BackgroundTasks,
    enable_detailed: bool = Query(False, description="启用详细比对信息"),
    enable_llm: bool = Query(False, description="启用LLM增强比对")
):
    """
    执行完整的报告核对流程

    - **enable_detailed**: 返回详细的比对过程信息
    - **enable_llm**: 启用大模型(LLM)辅助比对
    """
    pdf_path = UPLOAD_DIR / f"{file_id}.pdf"

    if not pdf_path.exists():
        docx_path = UPLOAD_DIR / f"{file_id}.docx"
        if docx_path.exists():
            temp_pdf = TEMP_DIR / f"{file_id}.pdf"
            if not temp_pdf.exists():
                docx_parser.parse_to_pdf(str(docx_path), str(temp_pdf))
            pdf_path = temp_pdf
        else:
            raise HTTPException(status_code=404, detail="文件不存在")

    # 临时设置LLM开关
    original_llm_setting = app_settings.ENABLE_LLM_COMPARISON
    if enable_llm:
        app_settings.ENABLE_LLM_COMPARISON = True

    try:
        # 执行核对
        result = await report_checker.check(
            str(pdf_path),
            file_id,
            enable_detailed=enable_detailed
        )

        # 添加元信息
        result.enable_detailed_comparison = enable_detailed
        if enable_llm:
            result.llm_usage_info = {
                "enabled": True,
                "mode": app_settings.LLM_COMPARISON_MODE,
                "model": app_settings.LLM_MODEL
            }

        # 后台清理临时文件
        background_tasks.add_task(cleanup_temp_files, file_id)

        return result

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"核对失败: {str(e)}")
    finally:
        # 恢复原始设置
        app_settings.ENABLE_LLM_COMPARISON = original_llm_setting


# ============ 获取核对结果 ============

@app.get("/api/result/{file_id}")
async def get_result(file_id: str):
    """
    获取核对结果
    """
    result_path = TEMP_DIR / f"{file_id}_result.json"

    if not result_path.exists():
        raise HTTPException(status_code=404, detail="结果不存在，请先执行核对")

    try:
        import json
        with open(result_path, 'r', encoding='utf-8') as f:
            result = json.load(f)
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取结果失败: {str(e)}")


# ============ 导出结果 ============

from fastapi.responses import FileResponse
from services.report_export_service import get_export_service

@app.get("/api/export/{file_id}")
async def export_result(file_id: str, format: str = "pdf"):
    """
    导出核对结果报告

    - **format**: 导出格式 (pdf, excel, json)
    """
    result_path = TEMP_DIR / f"{file_id}_result.json"

    if not result_path.exists():
        raise HTTPException(status_code=404, detail="结果不存在，请先执行核对")

    try:
        import json
        with open(result_path, 'r', encoding='utf-8') as f:
            result = json.load(f)

        if format == "json":
            return JSONResponse(content=result)

        elif format == "pdf":
            export_service = get_export_service()
            output_path = TEMP_DIR / f"{file_id}_report.pdf"
            export_service.export_pdf(result, str(output_path))

            return FileResponse(
                path=str(output_path),
                filename=f"核对报告_{result.get('filename', file_id)}.pdf",
                media_type="application/pdf"
            )

        elif format in ["excel", "xlsx"]:
            export_service = get_export_service()
            output_path = TEMP_DIR / f"{file_id}_report.xlsx"
            export_service.export_excel(result, str(output_path))

            return FileResponse(
                path=str(output_path),
                filename=f"核对报告_{result.get('filename', file_id)}.xlsx",
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        else:
            raise HTTPException(status_code=400, detail=f"不支持的导出格式: {format}，支持: pdf, excel, json")

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"导出失败: {str(e)}")


# ============ 工具函数 ============

def cleanup_temp_files(file_id: str):
    """清理临时文件"""
    try:
        temp_files = [
            TEMP_DIR / f"{file_id}.pdf",
            TEMP_DIR / f"{file_id}_*.png",
        ]
        for pattern in temp_files:
            for file in Path('.').glob(str(pattern)):
                if file.exists():
                    file.unlink()
    except Exception as e:
        print(f"清理临时文件失败: {e}")


# ============ 启动入口 ============

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
