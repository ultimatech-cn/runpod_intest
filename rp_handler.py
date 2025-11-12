import json
import subprocess
from pathlib import Path
import base64
import uuid
import runpod


def save_base64_to_file(data_base64: str, save_path: Path):
    """保存 base64 编码的数据为文件"""
    save_path.parent.mkdir(parents=True, exist_ok=True)
    with open(save_path, "wb") as f:
        f.write(base64.b64decode(data_base64))
    return save_path


def update_workflow(image_path: str, audio_path: str) -> str:
    """修改 workflow.json 文件，替换图像与音频输入路径"""
    workflow_path = "/workspace/workflow/workflow.json"
    workflow_data = json.loads(Path(workflow_path).read_text())

    # 替换图像与音频输入路径
    workflow_data["305"]["inputs"]["image"] = image_path
    workflow_data["306"]["inputs"]["audio"] = audio_path

    # 保存新的 workflow 文件（加随机名，避免冲突）
    client_id = uuid.uuid4().hex
    new_workflow_dir = Path("/workspace/ComfyUI/Json")
    new_workflow_dir.mkdir(parents=True, exist_ok=True)
    new_workflow_file = new_workflow_dir / f"{client_id}.json"

    with open(new_workflow_file, "w") as f:
        json.dump(workflow_data, f)

    return str(new_workflow_file)

def run_infer(workflow_file: str) -> Path:
    """运行 ComfyUI 工作流生成视频（只取最新的 *audio.mp4 文件）"""
    
    # 输出目录
    output_dir = Path("/workspace/ComfyUI/output/Wan21")
    output_dir.mkdir(parents=True, exist_ok=True)

    # 🚀 运行 ComfyUI（最长等待 30 分钟）
    cmd = f"comfy run --workflow {workflow_file} --wait --timeout 1800 --verbose"
    subprocess.run(cmd, shell=True, check=True)

    # 🎯 查找所有文件名包含 "audio.mp4" 的视频
    audio_videos = list(output_dir.glob("*audio.mp4"))
    if not audio_videos:
        print(f"Warning: no *audio.mp4 file found in {output_dir}")
        return None

    # 按修改时间排序，取最新的一个
    latest_audio_video = max(audio_videos, key=lambda f: f.stat().st_mtime)
    print(f"[INFO] Latest audio video file: {latest_audio_video}")

    return latest_audio_video



def handler(event):
    print("Received event:", event)

    # 从输入中取出 base64 编码的图片和音频
    image_b64 = event.get("input", {}).get("image_base64", "")
    audio_b64 = event.get("input", {}).get("audio_base64", "")

    if not image_b64 or not audio_b64:
        return {"error": "missing image or audio input"}

    # 保存输入文件
    input_dir = Path("/workspace/input")
    image_path = save_base64_to_file(image_b64, input_dir / "input_image.png")
    audio_path = save_base64_to_file(audio_b64, input_dir / "input_audio.wav")

    # 修改 workflow 并运行推理
    workflow_file = update_workflow(str(image_path), str(audio_path))
    video_path = run_infer(workflow_file)

    # 返回结果
    if video_path and video_path.exists():
        with open(video_path, "rb") as f:
            video_bytes = f.read()
            video_base64 = base64.b64encode(video_bytes).decode("utf-8")
        return {"video_base64": video_base64}
    else:
        return {"error": "video not found or generation failed"}


if __name__ == "__main__":
    import os
    import sys
    import time
    
    print("=" * 80, flush=True)
    print("[INFO] RunPod Handler starting...", flush=True)
    print("=" * 80, flush=True)
    
    print(f"[INFO] Python version: {sys.version}", flush=True)
    print(f"[INFO] RunPod version: {runpod.__version__ if hasattr(runpod, '__version__') else 'unknown'}", flush=True)
    
    # 检查关键环境变量
    env_vars = ["RUNPOD_POD_ID", "RUNPOD_API_KEY", "RUNPOD_ENDPOINT_ID"]
    print("[INFO] Checking environment variables:", flush=True)
    missing_vars = []
    for var in env_vars:
        value = os.environ.get(var, "NOT SET")
        if value == "NOT SET":
            missing_vars.append(var)
        # 隐藏敏感信息
        if "KEY" in var and value != "NOT SET":
            value = f"{value[:8]}...{value[-4:]}" if len(value) > 12 else "***"
        print(f"  {var}: {value}", flush=True)
    
    if missing_vars:
        print(f"[WARNING] Missing environment variables: {missing_vars}", flush=True)
        print("[WARNING] Handler may not work correctly without these variables", flush=True)
    
    # 检查所有 RUNPOD 相关的环境变量
    runpod_envs = {k: v for k, v in os.environ.items() if k.startswith("RUNPOD")}
    print(f"[INFO] All RUNPOD environment variables: {len(runpod_envs)} found", flush=True)
    if runpod_envs:
        print("[INFO] RUNPOD environment variables:", flush=True)
        for k, v in runpod_envs.items():
            # 隐藏敏感信息
            if "KEY" in k or "SECRET" in k:
                v = f"{v[:8]}...{v[-4:]}" if len(v) > 12 else "***"
            print(f"  {k}: {v}", flush=True)
    
    # 检查是否是 serverless 模式
    is_serverless = os.environ.get("RUNPOD_POD_ID") is not None
    print(f"[INFO] Serverless mode detected: {is_serverless}", flush=True)
    
    if not is_serverless:
        print("[WARNING] RUNPOD_POD_ID not found - this may not be a serverless environment", flush=True)
        print("[WARNING] Handler may not work correctly", flush=True)
    
    # 检查工作目录和关键路径
    print("[INFO] Checking workspace paths:", flush=True)
    workspace_paths = [
        "/workspace",
        "/workspace/ComfyUI",
        "/workspace/workflow",
        "/workspace/input"
    ]
    for path in workspace_paths:
        exists = os.path.exists(path)
        print(f"  {path}: {'EXISTS' if exists else 'MISSING'}", flush=True)
    
    print("[INFO] Starting RunPod serverless handler...", flush=True)
    print("[INFO] This is a blocking call - handler will wait for requests...", flush=True)
    print("=" * 80, flush=True)
    sys.stdout.flush()
    
    # 添加一个启动成功的标记
    try:
        print("[INFO] Calling runpod.serverless.start()...", flush=True)
        print("[INFO] If you see this message, the handler is attempting to start...", flush=True)
        sys.stdout.flush()
        
        # 尝试启动 RunPod serverless handler
        # runpod.serverless.start() 是一个阻塞调用，会一直运行等待请求
        # 它应该启动一个 HTTP 服务器并等待请求
        print("[INFO] About to call runpod.serverless.start()...", flush=True)
        
        # 检查 runpod 模块是否可用
        try:
            import runpod.serverless
            print(f"[INFO] runpod.serverless module loaded: {runpod.serverless}", flush=True)
        except Exception as e:
            print(f"[ERROR] Failed to import runpod.serverless: {e}", flush=True)
            raise
        
        # 调用 start 方法
        print("[INFO] Calling runpod.serverless.start() now...", flush=True)
        print("[INFO] Note: runpod.serverless.start() should output 'Starting Serverless Worker'", flush=True)
        print("[INFO] If you see that message, the handler is starting correctly", flush=True)
        sys.stdout.flush()
        
        # 使用 threading 在后台定期输出心跳，证明进程还在运行
        import threading
        import time as time_module
        
        def heartbeat():
            # 立即输出第一次心跳，然后每5秒输出一次
            time_module.sleep(2)  # 等待 start() 开始初始化
            count = 0
            while True:
                count += 1
                elapsed = count * 5
                print(f"[HEARTBEAT] Handler still running... ({elapsed}s)", flush=True)
                time_module.sleep(5)  # 每5秒输出一次心跳
        
        heartbeat_thread = threading.Thread(target=heartbeat, daemon=True)
        heartbeat_thread.start()
        print("[INFO] Heartbeat thread started - will report every 5 seconds (first after 2s)", flush=True)
        sys.stdout.flush()
        
        # 在调用 start() 之前输出确认消息
        print("[INFO] About to enter runpod.serverless.start() - this will block...", flush=True)
        print("[INFO] If handler is working, you should see heartbeat messages every 5 seconds", flush=True)
        sys.stdout.flush()
        
        # 调用 start() - 这是一个阻塞调用
        # 注意：start() 内部会输出 "Starting Serverless Worker"
        result = runpod.serverless.start({"handler": handler})
        
        # 如果 start() 返回了（不应该发生），记录信息
        print(f"[WARNING] runpod.serverless.start() returned: {result}", flush=True)
        print("[WARNING] This should not happen - start() should block forever", flush=True)
        
    except KeyboardInterrupt:
        print("[INFO] Handler interrupted by user", flush=True)
        sys.exit(0)
    except SystemExit as e:
        print(f"[INFO] Handler exited with code: {e.code}", flush=True)
        # 在退出前等待一段时间，以便查看日志
        print("[INFO] Waiting 10 seconds before exit to allow log viewing...", flush=True)
        time.sleep(10)
        raise
    except Exception as e:
        print(f"[ERROR] Failed to start RunPod handler: {e}", flush=True)
        print(f"[ERROR] Exception type: {type(e).__name__}", flush=True)
        import traceback
        print("[ERROR] Full traceback:", flush=True)
        traceback.print_exc(file=sys.stdout)
        sys.stdout.flush()
        # 在退出前等待一段时间，以便查看日志
        print("[ERROR] Waiting 30 seconds before exit to allow log viewing...", flush=True)
        time.sleep(30)
        sys.exit(1)
    finally:
        print("[INFO] Handler process ending...", flush=True)
