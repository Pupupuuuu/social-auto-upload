from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import List

from fastapi import FastAPI, Query
from pydantic import BaseModel

from api_main import upload_to_kuaishou, upload_to_bilibili, upload_to_xhs, upload_to_tencent, upload_to_douyin
from conf import BASE_DIR
from uploader.douyin_uploader.main import douyin_setup
from uploader.ks_uploader.main import ks_setup
from uploader.tencent_uploader.main import weixin_setup
from myUtils.auth import cookie_auth_douyin, cookie_auth_tencent, cookie_auth_ks, cookie_auth_xhs

# 配置 FastAPI 应用，设置标题和描述
app = FastAPI(title="自动化部署视频", description="通过API来自动化部署视频到各个平台。")


# 定义 Pydantic 模型，用于请求体
class UploadRequest(BaseModel):
    file_path: str
    title: str
    tags: List[str]
    headless: bool = True
    location: str | None = None


@app.post("/api/bilibili", summary="将视频部署到 B 站")
async def api_bilibili(request: UploadRequest):
    """测试方法：接收 file_path, title, tags 并触发 Bilibili 视频上传"""
    with ThreadPoolExecutor() as executor:
        # 将 Pydantic 模型的字段传递给上传函数
        executor.submit(
            upload_to_bilibili,
            file=Path(request.file_path),
            title=request.title,
            tags=request.tags
        ).result()
    return {"message": "视频已成功上传至B站!"}


@app.post("/api/xhs", summary="将视频部署到小红书。")
async def api_xhs(request: UploadRequest):
    """测试方法：接收 file_path, title, tags 并触发 小红书 视频上传"""
    with ThreadPoolExecutor() as executor:
        # 将 Pydantic 模型的字段传递给上传函数
        executor.submit(
            upload_to_xhs,
            file=Path(request.file_path),
            title=request.title,
            tags=request.tags
        ).result()
    return {"message": "视频已成功上传至小红书!"}


@app.post("/api/tencent", summary="将视频部署到视频号。")
async def api_tencent(request: UploadRequest):
    """测试方法：接收 file_path, title, tags 并触发 视频号 视频上传"""
    with ThreadPoolExecutor() as executor:
        # 将 Pydantic 模型的字段传递给上传函数
        executor.submit(
            upload_to_tencent,
            file=Path(request.file_path),
            title=request.title,
            tags=request.tags
        ).result()
    return {"message": "视频已成功上传至视频号!"}


@app.post("/api/douyin", summary="将视频部署到抖音。")
async def api_douyin(request: UploadRequest):
    """测试方法：接收 file_path, title, tags 并触发 抖音 视频上传"""
    with ThreadPoolExecutor() as executor:
        # 将 Pydantic 模型的字段传递给上传函数
        executor.submit(
            upload_to_douyin,
            file=Path(request.file_path),
            title=request.title,
            tags=request.tags,
            headless=request.headless,
            location=request.location
        ).result()
    return {"message": "视频已成功上传至抖音!"}


@app.post("/api/kuaishou", summary="将视频部署到快手。")
async def api_kuaishou(request: UploadRequest):
    """测试方法：接收 file_path, title, tags 并触发 kuaishou 视频上传"""
    with ThreadPoolExecutor() as executor:
        # 将 Pydantic 模型的字段传递给上传函数
        executor.submit(
            upload_to_kuaishou,
            file=Path(request.file_path),
            title=request.title,
            tags=request.tags,
            headless=request.headless
        ).result()
    return {"message": "视频已成功上传至快手!"}


@app.post("/auth/douyin", summary="验证抖音的cookie是否有效。")
async def auth_douyin(handle: bool = False):
    """验证抖音平台的cookie是否生效"""
    account_file = Path(BASE_DIR / "cookies" / "douyin_uploader" / "account.json")
    account_file.parent.mkdir(exist_ok=True)
    print(f"打印参数 handle : {handle}")

    flag = await douyin_setup(str(account_file), handle=handle)
    print(f"抖音 cookie 是否生效: {flag}")

    return {"flag": flag}


@app.post("/auth/kuaishou", summary="验证快手的cookie是否有效。")
async def auth_kuaishou(handle: bool = False):
    """验证快手平台的cookie是否生效"""
    account_file = Path(BASE_DIR / "cookies" / "ks_uploader" / "account.json")
    account_file.parent.mkdir(exist_ok=True)
    print(f"打印参数 handle : {handle}")
    print("打印参数cookie")

    flag = await ks_setup(str(account_file), handle=handle)
    print(f"快手 cookie 是否生效: {flag}")

    return {"flag": flag}


@app.post("/auth/tencent", summary="验证视频号的cookie是否有效。")
async def auth_tencent(handle: bool = False):
    """验证视频号平台的cookie是否生效"""
    account_file = Path(BASE_DIR / "cookies" / "tencent_uploader" / "account.json")
    account_file.parent.mkdir(exist_ok=True)
    print(f"打印参数 handle : {handle}")

    flag = await weixin_setup(str(account_file), handle=handle)
    print(f"视频号 cookie 是否生效: {flag}")

    return {"flag": flag}


@app.get("/checkCookie", summary="检查指定平台的Cookie是否有效")
async def check_cookie_endpoint(platform: str = Query(..., description="平台名称 (douyin, kuaishou, tencent, xiaohongshu)")):
    platform_name = platform.lower()

    # Map platform name to path component
    platform_info = {
        "xiaohongshu": "xiaohongshu_uploader",
        "tencent": "tencent_uploader",
        "douyin": "douyin_uploader",
        "kuaishou": "ks_uploader"
    }

    path_component = platform_info.get(platform_name)

    if not path_component:
        return {"code": 400, "msg": "Invalid platform name"}

    # Construct the path based on the old structure
    account_file_path = Path(BASE_DIR / "cookies" / path_component / "account.json")

    if not account_file_path.exists():
        return {"code": 404, "msg": f"Cookie file not found for platform {platform_name}"}

    is_valid = False

    # Call the appropriate auth function
    if platform_name == "xiaohongshu":
        is_valid = await cookie_auth_xhs(account_file_path)
    elif platform_name == "tencent":
        is_valid = await cookie_auth_tencent(account_file_path)
    elif platform_name == "douyin":
        is_valid = await cookie_auth_douyin(account_file_path)
    elif platform_name == "kuaishou":
        is_valid = await cookie_auth_ks(account_file_path)

    return {"code": 200, "data": {"isValid": is_valid}}


# 如果脚本作为主程序运行
if __name__ == "__main__":
    # 导入 uvicorn，用于运行 FastAPI 应用
    import uvicorn
    # 导入uvicorn 用于隐形Fastapi
    # 如果作为脚本为主程序运行.

    # 启动 FastAPI 应用，监听所有网络接口的 8000 端口
    uvicorn.run(app, host="0.0.0.0", port=8000)