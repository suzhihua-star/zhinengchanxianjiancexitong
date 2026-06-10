"""报表 API 路由"""
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas import ReportRequest
from app.services.report_service import generate_csv_report, generate_report

router = APIRouter(prefix="/api/v1/reports", tags=["报表"])


@router.post("/generate")
async def create_report(req: ReportRequest, db: AsyncSession = Depends(get_db)):
    """生成报表（JSON 格式）"""
    result = await generate_report(db, req.report_type, req.line_id)
    return {"code": 0, "message": "success", "data": result}


@router.post("/generate/csv")
async def download_csv(
    req: ReportRequest,
    db: AsyncSession = Depends(get_db),
):
    """下载 CSV 格式报表"""
    csv_bytes = await generate_csv_report(db, req.report_type, req.line_id)
    return StreamingResponse(
        iter([csv_bytes]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=report_{req.report_type}_{req.line_id or 'all'}.csv"
        },
    )
