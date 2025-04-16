import logging
import subprocess
from pathlib import Path

from fastapi import FastAPI, HTTPException

# 配置 FastAPI 应用，设置标题和描述
app = FastAPI(title="Video Upload API", description="API to trigger platform-specific video upload scripts")

# 配置日志记录，设置日志级别为 INFO
logging.basicConfig(level=logging.INFO)
# 创建一个日志记录器，名称为当前模块的名称
logger = logging.getLogger(__name__)

# 定义脚本所在的基础目录
BASE_DIR = Path(r"C:\Users\Missi\Framework\social-auto-upload-main")

# 定义各个平台上传脚本的路径
BILIBILI_PATH = BASE_DIR / "examples/upload_video_to_bilibili.py"
DOUYIN_PATH = BASE_DIR / "examples/upload_video_to_douyin.py"
KS_PATH = BASE_DIR / "examples/upload_video_to_kuaishou.py"
TENCENT_PATH = BASE_DIR / "examples/upload_video_to_tencent.py"
XHS_PATH = BASE_DIR / "examples/upload_video_to_xhs.py"

# 定义虚拟环境中 Python 可执行文件的路径
PYTHON_EXEC = BASE_DIR / ".venv" / "Scripts" / "python.exe"


# 异步函数，用于执行指定平台的上传脚本
async def upload_video(script_path: Path):
    """
    执行指定的上传脚本，上传视频到对应的平台。
    实时打印日志到控制台，并返回执行过程中的日志。
    """
    try:
        # 检查脚本文件是否存在
        if not script_path.exists():
            raise HTTPException(status_code=404, detail=f"Script not found: {script_path}")
        # 检查 Python 可执行文件是否存在
        if not PYTHON_EXEC.exists():
            raise HTTPException(status_code=404, detail="Python executable not found in .venv")

        # 初始化日志列表，添加标题
        logs = [f"=== {script_path.stem} ==="]
        # 记录调试信息，显示正在运行的脚本路径
        logger.info(f"[DEBUG] 运行脚本：{script_path}")

        # 使用 Popen 运行脚本，实时捕获输出
        process = subprocess.Popen(
            [str(PYTHON_EXEC), str(script_path)],  # 命令行参数：Python 可执行文件和脚本路径
            stdout=subprocess.PIPE,  # 捕获标准输出
            stderr=subprocess.PIPE,  # 捕获标准错误
            text=True,  # 以文本模式返回输出
            encoding="utf-8",  # 强制使用 UTF-8 编码
            errors="replace"  # 解码失败时替换特殊字符，防止 UnicodeDecodeError
        )

        # 初始化标准输出和标准错误的日志列表
        stdout_logs = []
        stderr_logs = []

        # 实时读取标准输出
        while True:
            line = process.stdout.readline()
            if not line and process.poll() is not None:
                break
            if line:
                line = line.strip()
                print(f"[STDOUT] {line}")  # 实时打印到控制台
                stdout_logs.append(line)

        # 实时读取标准错误
        while True:
            line = process.stderr.readline()
            if not line and process.poll() is not None:
                break
            if line:
                line = line.strip()
                print(f"[STDERR] {line}")  # 实时打印到控制台
                stderr_logs.append(line)

        # 等待进程结束并获取退出码
        return_code = process.wait()

        # 过滤掉以 "INFO:biliup:" 开头的日志行
        filtered_logs = [line for line in stdout_logs if not line.startswith("INFO:biliup:")]
        # 将过滤后的日志添加到 logs 列表
        logs.extend(filtered_logs)

        # 如果存在标准错误输出
        if stderr_logs:
            # 添加错误标题到日志
            logs.extend(["=== Errors ==="])
            # 添加错误日志到日志列表
            logs.extend(stderr_logs)
            # 记录错误日志
            logger.error(f"脚本错误：{stderr_logs}")
            raise HTTPException(status_code=500, detail=f"上传失败，请检查日志：{stderr_logs}")

        # 检查脚本是否成功执行
        if return_code != 0:
            logger.error(f"脚本执行失败，退出码：{return_code}")
            raise HTTPException(status_code=500, detail=f"脚本执行失败，退出码：{return_code}")

        # 添加上传完成信息到日志
        logs.append("=== 上传完成！ ===")

        # 返回成功响应，包含状态和日志
        return {
            "status": "success",
            "logs": logs
        }, 200
    except Exception as e:
        # 记录其他未预期的错误信息
        logger.error(f"上传失败：{str(e)}")
        # 抛出 500 异常，包含错误详情
        raise HTTPException(status_code=500, detail=f"上传失败：{str(e)}")


# 定义 POST 端点 /upload，用于触发指定平台的视频上传
@app.post("/upload", summary="Trigger platform-specific script to upload videos")
async def trigger_upload(platform: str | None = None):
    """
    根据指定的 platform 参数，触发对应的视频上传脚本。
    platform 可选值为：bilibili, douyin, kuaishou, tencent, xhs。
    如果 platform 为 None 或无效值，返回错误。
    """
    # 打印接收到的 platform 参数，用于调试
    print(f"platform: {platform}")

    # 使用 match-case 语句根据 platform 值选择上传脚本
    match platform:
        case "bilibili":
            # 调用 bilibili 上传脚本
            return await upload_video(BILIBILI_PATH)
        case "douyin":
            # 调用 douyin 上传脚本
            return await upload_video(DOUYIN_PATH)
        case "kuaishou":
            # 调用 kuaishou 上传脚本
            return await upload_video(KS_PATH)
        case "tencent":
            # 调用 tencent 上传脚本
            return await upload_video(TENCENT_PATH)
        case "xhs":
            # 调用 xhs 上传脚本
            return await upload_video(XHS_PATH)
        case None:
            # 如果 platform 未提供，抛出 400 异常
            raise HTTPException(status_code=400, detail="Platform parameter is required")
        case _:
            # 如果 platform 值无效，抛出 400 异常
            raise HTTPException(status_code=400, detail=f"Invalid platform: {platform}. Valid options: bilibili, douyin, kuaishou, tencent, xhs")


# 如果脚本作为主程序运行
if __name__ == "__main__":
    # 导入 uvicorn，用于运行 FastAPI 应用
    import uvicorn

    # 启动 FastAPI 应用，监听所有网络接口的 8000 端口
    uvicorn.run(app, host="0.0.0.0", port=8000)
