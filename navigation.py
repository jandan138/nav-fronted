import gradio as gr
import requests
import json
import os
import uuid
import time
import subprocess
from typing import Optional, List
from datetime import datetime
import cv2
import numpy as np

# 后端API配置（可配置化）
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
API_ENDPOINTS = {
    "submit_task": f"{BACKEND_URL}/predict/video",
    "query_status": f"{BACKEND_URL}/predict/task",
    "get_result": f"{BACKEND_URL}//predict"
}

# 模拟场景配置
SCENE_CONFIGS = {
    "scene_1": {
        "description": "scene_1",
        "objects": ["bedroom", "kitchen", "living room", ""],
        "preview_image": "/opt/nav-fronted/assets/scene_1.png"
    },
}

MODEL_CHOICES = []  # 仅占位，不再使用

###############################################################################


# 日志文件路径
LOG_DIR = "/opt/nav-frontend/logs"
os.makedirs(LOG_DIR, exist_ok=True)
ACCESS_LOG = os.path.join(LOG_DIR, "access.log")
SUBMISSION_LOG = os.path.join(LOG_DIR, "submissions.log")

def log_access(user_ip: str = None, user_agent: str = None):
    """记录用户访问日志"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = {
        "timestamp": timestamp,
        "type": "access",
        "user_ip": user_ip or "unknown",
        "user_agent": user_agent or "unknown"
    }
    
    with open(ACCESS_LOG, "a") as f:
        f.write(json.dumps(log_entry) + "\n")

def log_submission(scene: str, prompt: str, model: str, user: str = "anonymous", res: str = "unknown"):
    """记录用户提交日志"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = {
        "timestamp": timestamp,
        "type": "submission",
        "user": user,
        "scene": scene,
        "prompt": prompt,
        "model": model,
        #"max_step": str(max_step),
        "res": res
    }
    
    with open(SUBMISSION_LOG, "a") as f:
        f.write(json.dumps(log_entry) + "\n")

def read_logs(log_type: str = "all", max_entries: int = 50) -> list:
    """读取日志文件"""
    logs = []
    
    if log_type in ["all", "access"]:
        try:
            with open(ACCESS_LOG, "r") as f:
                for line in f:
                    logs.append(json.loads(line.strip()))
        except FileNotFoundError:
            pass
    
    if log_type in ["all", "submission"]:
        try:
            with open(SUBMISSION_LOG, "r") as f:
                for line in f:
                    logs.append(json.loads(line.strip()))
        except FileNotFoundError:
            pass
    
    # 按时间戳排序，最新的在前
    logs.sort(key=lambda x: x["timestamp"], reverse=True)
    return logs[:max_entries]

def format_logs_for_display(logs: list) -> str:
    """格式化日志用于显示"""
    if not logs:
        return "暂无日志记录"
    
    markdown = "### 系统访问日志\n\n"
    markdown += "| 时间 | 类型 | 用户/IP | 详细信息 |\n"
    markdown += "|------|------|---------|----------|\n"
    
    for log in logs:
        timestamp = log.get("timestamp", "unknown")
        log_type = "访问" if log.get("type") == "access" else "提交"
        
        if log_type == "访问":
            user = log.get("user_ip", "unknown")
            details = f"User-Agent: {log.get('user_agent', 'unknown')}"
        else:
            user = log.get("user", "anonymous")
            result = log.get('res', 'unknown')
            if result != "success": 
                if len(result) > 40:  # Adjust this threshold as needed
                    result = f"{result[:20]}...{result[-20:]}"
            details = f"场景: {log.get('scene', 'unknown')}, 指令: {log.get('prompt', '')}, 模型: {log.get('model', 'unknown')}, result: {result}"
        
        markdown += f"| {timestamp} | {log_type} | {user} | {details} |\n"
    
    return markdown



###############################################################################


def stream_simulation_results(result_folder: str, task_id: str, fps: int = 30):
    """
    流式输出仿真结果，同时监控图片文件夹和后端任务状态
    
    参数:
        result_folder: 包含生成图片的文件夹路径
        task_id: 后端任务ID用于状态查询
        fps: 输出视频的帧率
        
    生成:
        生成的视频文件路径 (分段输出)
    """
    # 初始化变量
    result_folder = os.path.join(result_folder, "image")
    os.makedirs(result_folder, exist_ok=True)
    frame_buffer: List[np.ndarray] = []
    frames_per_segment = fps * 2  # 每2秒60帧
    processed_files = set()
    width, height = 0, 0
    last_status_check = 0
    status_check_interval = 5  # 每5秒检查一次后端状态
    max_time = 240

    while max_time > 0:
        max_time -= 1
        current_time = time.time()
        
        # 定期检查后端状态
        if current_time - last_status_check > status_check_interval:
            status = get_task_status(task_id)
            print("status: ", status)
            if status.get("status") == "completed":
                # 确保处理完所有已生成的图片
                process_remaining_images(result_folder, processed_files, frame_buffer)
                if frame_buffer:
                    yield create_video_segment(frame_buffer, fps, width, height)
                break
            elif status.get("status") == "failed":
                raise gr.Error(f"任务执行失败: {status.get('result', '未知错误')}")
            last_status_check = current_time

        # 处理新生成的图片
        current_files = sorted(
            [f for f in os.listdir(result_folder) 
             if f.lower().endswith(('.png', '.jpg', '.jpeg'))],
            key=lambda x: os.path.splitext(x)[0]  # 按文件名排序
        )
        
        new_files = [f for f in current_files if f not in processed_files]
        has_new_frames = False
        
        for filename in new_files:
            try:
                img_path = os.path.join(result_folder, filename)
                frame = cv2.imread(img_path)
                if frame is not None:
                    if width == 0:  # 第一次获取图像尺寸
                        height, width = frame.shape[:2]
                    
                    frame_buffer.append(frame)
                    processed_files.add(filename)
                    has_new_frames = True
            except Exception as e:
                print(f"Error processing {filename}: {e}")

        # 如果有新帧且积累够60帧，输出视频片段
        if has_new_frames and len(frame_buffer) >= frames_per_segment:
            segment_frames = frame_buffer[:frames_per_segment]
            frame_buffer = frame_buffer[frames_per_segment:]
            yield create_video_segment(segment_frames, fps, width, height)

        time.sleep(1)  # 避免过于频繁检查
    
    if max_time <= 0:
        raise gr.Error("timeout 240s")

def create_video_segment(frames: List[np.ndarray], fps: int, width: int, height: int) -> str:
    """创建视频片段"""
    os.makedirs("/opt/gradio_demo/tasks/video_chunk", exist_ok=True)
    segment_name = f"/opt/gradio_demo/tasks/video_chunk/output_{uuid.uuid4()}.mp4"
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(segment_name, fourcc, fps, (width, height))
    
    for frame in frames:
        out.write(frame)
    out.release()
    
    return segment_name

def process_remaining_images(result_folder: str, processed_files: set, frame_buffer: List[np.ndarray]):
    """处理剩余的图片"""
    current_files = sorted(
        [f for f in os.listdir(result_folder) 
         if f.lower().endswith(('.png', '.jpg', '.jpeg'))],
        key=lambda x: os.path.splitext(x)[0]
    )
    
    new_files = [f for f in current_files if f not in processed_files]
    
    for filename in new_files:
        try:
            img_path = os.path.join(result_folder, filename)
            frame = cv2.imread(img_path)
            if frame is not None:
                frame_buffer.append(frame)
                processed_files.add(filename)
        except Exception as e:
            print(f"Error processing remaining {filename}: {e}")




###############################################################################

def convert_to_h264(video_path):
    """
    将视频转换为 H.264 编码的 MP4 格式
    生成新文件路径在原路径基础上添加 _h264 后缀）
    """
    # 
    base, ext = os.path.splitext(video_path)
    video_path_h264 = f"{base}_h264.mp4"

    # 自动查找 ffmpeg 可执行路径
    ffmpeg_bin = "/root/anaconda3/envs/gradio/bin/ffmpeg"
    if not os.path.exists(ffmpeg_bin):
        print("⚠️ 找不到 ffmpeg，请确保其已安装并在 PATH 中")
        ffmpeg_bin = shutil.which("ffmpeg")
    if ffmpeg_bin is None:
        raise RuntimeError("❌ 找不到 ffmpeg，请确保其已安装并在 PATH 中")

    ffmpeg_cmd = [
        ffmpeg_bin,
        "-i", video_path,
        "-c:v", "libx264",
        "-preset", "slow",
        "-crf", "23",
        "-c:a", "aac",
        "-movflags", "+faststart",
        video_path_h264
    ]

    try:
        print("🚀 正在执行 FFmpeg 命令：", " ".join(ffmpeg_cmd))
        result = subprocess.run(ffmpeg_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("✅ FFmpeg 执行完成")

        if not os.path.exists(video_path_h264):
            raise FileNotFoundError(f"⚠️ H.264 文件未生成: {video_path_h264}")

        print(f"🎉 转换成功！输出文件路径：{video_path_h264}")
        return video_path_h264

    except subprocess.CalledProcessError as e:
        print(f"❌ FFmpeg 执行失败:\n{e.stderr.decode(errors='ignore')}")
        raise

    except Exception as e:
        print(f"❌ 转换过程中发生错误: {str(e)}")
        raise

def submit_to_backend(
    scene: str,
    prompt: str,
    start_position: str,
    user: str = "Gradio-user",
) -> dict:
    job_id = str(uuid.uuid4())

    #data = {
    #   "scene_type": scene,
    #    "instruction": prompt,
    #    "start_position": start_position,
    #}

    data = {
        "model_type": "rdp",
        
        "instruction": "Exit the bedroom and turn left. Walk straight passing the gray couch and stop near the rug.",
        "episode_type": "demo1",
    }
    
    payload = {
        "user": user,
        "task": "robot_navigation",
        "job_id": job_id,
        "data": json.dumps(data)
    }
    
    try:
        headers = {"Content-Type": "application/json"}
        response = requests.post(
            API_ENDPOINTS["submit_task"],
            json=payload,
            headers=headers,
            timeout=200
        )
        return response.json()
    except Exception as e:
        return {"status": "error", "message": str(e)}

def get_task_status(task_id: str) -> dict:
    """
    查询任务状态
    """
    try:
        response = requests.get(
            f"{API_ENDPOINTS['query_status']}/{task_id}",
            timeout=5
        )
        return response.json()
    except Exception as e:
        return {"status": "error", "message": str(e)}

def get_task_result(task_id: str) -> Optional[dict]:
    """
    获取任务结果
    """
    try:
        response = requests.get(
            f"{API_ENDPOINTS['get_result']}/{task_id}",
            timeout=5
        )
        return response.json()
    except Exception as e:
        print(f"Error fetching result: {e}")
        return None

def run_simulation(
    scene: str,
    prompt: str,
    start_position: str,
    history: list
) -> dict:
    """运行仿真并更新历史记录"""
    # 获取当前时间
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    scene_desc = SCENE_CONFIGS.get(scene, {}).get("description", scene)

    # 记录用户提交
    user_ip = request.client.host if request else "unknown"
    
    # 提交任务到后端
    submission_result = submit_to_backend(scene, prompt, start_position)
    
    if submission_result.get("status") != "pending":
        raise gr.Error(f"提交失败: {submission_result.get('message', '未知错误')}")
    
    task_id = submission_result["task_id"]

    # 轮询config
    max_checks = 50  # 增加最大检查次数
    initial_delay = 15.0  # 初始延迟
    max_delay = 3.0  # 最终延迟
    current_delay = initial_delay
    
    for i in range(max_checks):
        # 在检查前等待
        time.sleep(current_delay)
        
        # 获取任务状态
        status = get_task_status(task_id)
        print("status: ", status)
        if status.get("status") == "completed":
            video_path = os.path.join(status.get("result"), "output.mp4")
            print("video_path: ", video_path)
            video_path = convert_to_h264(video_path)

            # 创建新的历史记录条目
            new_entry = {
                "timestamp": timestamp,
                "scene": scene,
                "start_pos": start_position,
                "prompt": prompt,
                "video_path": video_path
            }
            
            # 将新条目添加到历史记录顶部
            updated_history = history + [new_entry]
            
            # 限制历史记录数量，避免内存问题
            if len(updated_history) > 10:
                updated_history = updated_history[:10]
            
            print("updated_history:", updated_history)
            
            return video_path, updated_history

        elif status.get("status") == "failed":
            print(f"❌ Task ID 失败: {task_id}")
            print(f"❌ 后端返回信息: {status}")
            raise gr.Error(f"任务执行失败: {status.get('message', '未知错误')}")
            return None, history
        
        current_delay = max(current_delay * 0.8, max_delay)
    
    raise gr.Error(f"任务执行超时，超过最大等待时间({max_checks * max_delay:.0f}秒)")
    return None, history

def update_history_display(history: list) -> list:
    updates = []
    
    for i in range(10):
        if i < len(history):
            entry = history[i]
            updates.extend([
                gr.update(visible=True),
                gr.update(visible=True, label=f"仿真记录 {i+1}  scene: {entry['scene']}, start: {entry['start_pos']}, prompt: {entry['prompt']}", open=False),
                gr.update(value=entry['video_path'], visible=True),
                gr.update(value=f"{entry['timestamp']}")
            ])
        else:
            updates.extend([
                gr.update(visible=False),
                gr.update(visible=False),
                gr.update(value=None, visible=False),
                gr.update(value="")
            ])
    
    return updates

def update_scene_display(scene: str) -> tuple[str, Optional[str]]:
    config = SCENE_CONFIGS.get(scene, {})
    desc = config.get("description", "无描述")
    objects = "、".join(config.get("objects", []))
    image = config.get("preview_image", None)
    
    markdown = f"**{desc}**  \n包含地点: {objects}"
    return markdown, image

custom_css = """
#simulation-panel {
    border-radius: 8px;
    padding: 20px;
    background: #f9f9f9;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}
#result-panel {
    border-radius: 8px;
    padding: 20px;
    background: #f0f8ff;
}
.dark #simulation-panel { background: #2a2a2a; }
.dark #result-panel { background: #1a2a3a; }

.history-container {
    max-height: 600px;
    overflow-y: auto;
    margin-top: 20px;
}

.history-accordion {
    margin-bottom: 10px;
}
"""

with gr.Blocks(title="机器人导航训练系统", css=custom_css) as demo:
    gr.Markdown("""
    # 🧭 IsaacSim 机器人导航演示
    ### 基于GRNavigation框架的仿真导航测试
    """)
    
    history_state = gr.State([])

    with gr.Row():
        with gr.Column(elem_id="simulation-panel"):
            gr.Markdown("### 仿真任务配置")
            
            scene_dropdown = gr.Dropdown(
                label="选择场景配置",
                choices=list(SCENE_CONFIGS.keys()),
                value="scene_1",
                interactive=True
            )
            
            scene_description = gr.Markdown("")
            scene_preview = gr.Image(
                label="场景预览",
                elem_classes=["scene-preview"],
                interactive=False
            )
            
            scene_dropdown.change(
                update_scene_display,
                inputs=scene_dropdown,
                outputs=[scene_description, scene_preview]
            )
            
            prompt_input = gr.Textbox(
                label="导航指令",
                value="Exit the bedroom and turn left. Walk straight passing the gray couch and stop near the rug.",
                placeholder="例如: 'Exit the bedroom and turn left. Walk straight passing the gray couch and stop near the rug.'",
                lines=2,
                max_lines=4
            )
            
            start_pos_input = gr.Textbox(
                label="起始坐标 (x, y, z)",
                value="0.0, 0.0, 0.2",
                placeholder="例如: 0.0, 0.0, 0.2"
            )
            
            submit_btn = gr.Button("开始导航仿真", variant="primary")
        
        with gr.Column(elem_id="result-panel"):
            gr.Markdown("### 最新仿真结果")
            
            video_output = gr.Video(
                label="导航过程回放",
                interactive=False,
                format="mp4",
                autoplay=True
            )
            
            with gr.Column() as history_container:
                gr.Markdown("### 历史记录")
                history_slots = []
                for i in range(10):
                    with gr.Column(visible=False) as slot:
                        with gr.Accordion(visible=False, open=False) as accordion:
                            video = gr.Video(interactive=False)
                            detail_md = gr.Markdown()
                    history_slots.append((slot, accordion, video, detail_md))

    gr.Examples(
        examples=[
            ["scene_1", "Exit the bedroom and turn left. Walk straight passing the gray couch and stop near the rug.", "0.0, 0.0, 0.2"]
        ],
        inputs=[scene_dropdown, prompt_input, start_pos_input],
        label="导航任务示例"
    )
    
    submit_btn.click(
        fn=run_simulation,
        inputs=[scene_dropdown, prompt_input, start_pos_input, history_state],
        outputs=[video_output, history_state],
        api_name="run_simulation"
    ).then(
        fn=update_history_display,
        inputs=history_state,
        outputs=[comp for slot in history_slots for comp in slot]
    )
    
    demo.load(
        fn=lambda: update_scene_display("scene_1"),
        outputs=[scene_description, scene_preview]
    )

    demo.queue(default_concurrency_limit=8)

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=55005, share=False, debug=True, allowed_paths=["/opt"])
