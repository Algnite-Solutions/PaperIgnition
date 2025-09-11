from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
import os

router = APIRouter(tags=["static"])

@router.get("/ssets/icons/{icon_name}")
async def get_icon_ssets(icon_name: str):
    """处理Taro bug导致的错误路径请求 /api/ssets/icons/"""
    return await _get_icon_file(icon_name)

@router.get("/assets/icons/{icon_name}")
async def get_icon_assets(icon_name: str):
    """处理正常的图标路径请求 /api/assets/icons/"""
    return await _get_icon_file(icon_name)

async def _get_icon_file(icon_name: str):
    """获取图标文件的共用逻辑"""
    # 图标文件路径
    icon_path = f"frontend/src/assets/icons/{icon_name}"
    
    # 检查文件是否存在
    if os.path.exists(icon_path):
        return FileResponse(
            path=icon_path,
            media_type="image/png",
            headers={"Cache-Control": "public, max-age=3600"}  # 缓存1小时
        )
    
    # 如果文件不存在，返回404
    raise HTTPException(status_code=404, detail=f"Icon '{icon_name}' not found") 