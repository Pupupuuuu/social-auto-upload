from fastapi import FastAPI, HTTPException
import subprocess
import logging
from pathlib import Path

# 配置 FastAPI
app = FastAPI(title="Video Upload API", description="API to trigger api_main.py execution")

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 脚本路径
BASE_DIR = Path(r"C:\Users\Missi\Framework\social-auto-upload-main")
SCRIPT_PATH = BASE_DIR / "api_main.py"
PYTHON_EXEC = BASE_DIR / ".venv" / "Scripts" / "python.exe"

@app.post("/upload", summary="Trigger api_main.py to upload videos")
async def trigger_upload():
    """
    Execute api_main.py to upload videos to Bilibili.
    Returns logs of the process.
    """
    try:
        if not SCRIPT_PATH.exists():
            raise HTTPException(status_code=404, detail="api_main.py not found")
        if not PYTHON_EXEC.exists():
            raise HTTPException(status_code=404, detail="Python executable not found in .venv")

        logs = ["=== Bilibili ==="]
        logger.info(f"[DEBUG] 运行脚本：{SCRIPT_PATH}")

        # 使用虚拟环境的 Python 执行脚本
        try:
            result = subprocess.run(
                [str(PYTHON_EXEC), str(SCRIPT_PATH)],
                capture_output=True,
                text=True,
                encoding="utf-8",  # 强制 UTF-8
                check=True
            )
        except UnicodeDecodeError:
            logs.append("[ERROR] 输出解码失败，可能含特殊字符")
            raise HTTPException(status_code=500, detail="输出解码失败，可能含特殊字符")

        # 解析输出
        stdout = result.stdout.splitlines() if result.stdout else []
        stderr = result.stderr.splitlines() if result.stderr else []

        # 过滤无关日志
        filtered_logs = [line for line in stdout if not line.startswith("INFO:biliup:")]
        logs.extend(filtered_logs)

        if stderr:
            logs.extend(["=== Errors ==="])
            logs.extend(stderr)
            logger.error(f"脚本错误：{stderr}")
            raise HTTPException(status_code=500, detail="Bilibili 上传失败，请检查日志")

        logs.append("=== 所有平台上传完成！ ===")

        return {
            "status": "success",
            "logs": logs
        }
    except subprocess.CalledProcessError as e:
        logger.error(f"脚本执行失败：{e.stderr}")
        raise HTTPException(status_code=500, detail=f"脚本执行失败：{e.stderr}")
    except Exception as e:
        logger.error(f"上传失败：{str(e)}")
        raise HTTPException(status_code=500, detail=f"上传失败：{str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)