import gradio as gr
import requests
import json
import os
import uuid
import time
import subprocess
from typing import Optional
from datetime import datetime

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
        "objects": ["番茄酱", "盐瓶", "餐刀", "杯子"],
        "preview_image": "/opt/nav-fronted/assets/scene_1.png"
    },
}

MODEL_CHOICES = []  # 仅占位，不再使用

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
    
    markdown = f"**{desc}**  \n包含物体: {objects}"
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
            ["scene_1", "Navigate to the ketchup bottle while avoiding the knife.", "0.0, 0.0, 0.2"]
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
