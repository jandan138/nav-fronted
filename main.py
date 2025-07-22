# main.py
# 主入口文件，负责启动 Gradio UI
import gradio as gr
from config import SCENE_CONFIGS, MODEL_CHOICES, MODE_CHOICES
from backend_api import submit_to_backend, get_task_status, get_task_result
from logging_utils import log_access, log_submission, is_request_allowed
from simulation import stream_simulation_results, convert_to_h264
from ui_components import update_history_display, update_scene_display, update_log_display
import os
from datetime import datetime

SESSION_TASKS = {}

def run_simulation(scene, model, mode, prompt, history, request: gr.Request):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    scene_desc = SCENE_CONFIGS.get(scene, {}).get("description", scene)
    user_ip = request.client.host if request else "unknown"
    session_id = request.session_hash
    if not is_request_allowed(user_ip):
        log_submission(scene, prompt, model, user_ip, "IP blocked temporarily")
        raise gr.Error("Too many requests from this IP. Please wait and try again one minute later.")
    # 传递model和mode给后端
    submission_result = submit_to_backend(scene, prompt)  # 可根据后端接口调整
    if submission_result.get("status") != "pending":
        log_submission(scene, prompt, model, user_ip, "Submission failed")
        raise gr.Error(f"Submission failed: {submission_result.get('message', 'unknown issue')}")
    try:
        task_id = submission_result["task_id"]
        SESSION_TASKS[session_id] = task_id
        gr.Info(f"Simulation started, task_id: {task_id}")
        import time
        time.sleep(5)
        status = get_task_status(task_id)
        result_folder = status.get("result", "")
    except Exception as e:
        log_submission(scene, prompt, model, user_ip, str(e))
        raise gr.Error(f"error occurred when parsing submission result from backend: {str(e)}")
    if not os.path.exists(result_folder):
        log_submission(scene, prompt, model, user_ip, "Result folder provided by backend doesn't exist")
        raise gr.Error(f"Result folder provided by backend doesn't exist: <PATH>{result_folder}")
    try:
        for video_path in stream_simulation_results(result_folder, task_id):
            if video_path:
                yield video_path, history
    except Exception as e:
        log_submission(scene, prompt, model, user_ip, str(e))
        raise gr.Error(f"流式输出过程中出错: {str(e)}")
    status = get_task_status(task_id)
    if status.get("status") == "completed":
        video_path = os.path.join(status.get("result"), "output.mp4")
        video_path = convert_to_h264(video_path)
        new_entry = {
            "timestamp": timestamp,
            "scene": scene,
            "model": model,
            "mode": mode,
            "prompt": prompt,
            "video_path": video_path
        }
        updated_history = history + [new_entry]
        if len(updated_history) > 10:
            updated_history = updated_history[:10]
        log_submission(scene, prompt, model, user_ip, "success")
        gr.Info("Simulation completed successfully!")
        yield None, updated_history
    elif status.get("status") == "failed":
        log_submission(scene, prompt, model, user_ip, status.get('result', 'backend error'))
        raise gr.Error(f"任务执行失败: {status.get('result', 'backend 未知错误')}")
        yield None, history
    elif status.get("status") == "terminated":
        log_submission(scene, prompt, model, user_ip, "terminated")
        video_path = os.path.join(result_folder, "output.mp4")
        if os.path.exists(video_path):
            return f"⚠️ 任务 {task_id} 被终止，已生成部分结果", video_path, history
        else:
            return f"⚠️ 任务 {task_id} 被终止，未生成结果", None, history
    else:
        log_submission(scene, prompt, model, user_ip, "missing task's status from backend")
        raise gr.Error("missing task's status from backend")
        yield None, history

def cleanup_session(request: gr.Request):
    session_id = request.session_hash
    task_id = SESSION_TASKS.pop(session_id, None)
    from config import BACKEND_URL
    import requests
    if task_id:
        try:
            requests.post(f"{BACKEND_URL}/predict/terminate/{task_id}", timeout=3)
        except Exception:
            pass

def record_access(request: gr.Request):
    user_ip = request.client.host if request else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    log_access(user_ip, user_agent)
    return update_log_display()

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

with gr.Blocks(title="Robot Navigation Training System", css=custom_css) as demo:
    gr.Markdown("""
    # 🧭 IsaacSim Robot Navigation Demo
    ### Simulation Test Based on GRNavigation Framework
    """)
    history_state = gr.State([])
    with gr.Row():
        with gr.Column(elem_id="simulation-panel"):
            gr.Markdown("### Simulation Task Configuration")
            scene_dropdown = gr.Dropdown(
                label="Select Scene",
                choices=list(SCENE_CONFIGS.keys()),
                value="scene_1",
                interactive=True
            )
            model_dropdown = gr.Dropdown(
                label="Select Model",
                choices=MODEL_CHOICES,
                value=MODEL_CHOICES[0],
                interactive=True
            )
            mode_dropdown = gr.Dropdown(
                label="Select Mode",
                choices=MODE_CHOICES,
                value=MODE_CHOICES[0],
                interactive=True
            )
            scene_description = gr.Markdown("")
            scene_preview = gr.Image(
                label="Scene Preview",
                elem_classes=["scene-preview"],
                interactive=False
            )
            scene_dropdown.change(
                update_scene_display,
                inputs=scene_dropdown,
                outputs=[scene_description, scene_preview]
            )
            prompt_input = gr.Textbox(
                label="Navigation Instruction",
                value="Exit the bedroom and turn left. Walk straight passing the gray couch and stop near the rug.",
                placeholder="e.g.: 'Exit the bedroom and turn left. Walk straight passing the gray couch and stop near the rug.'",
                lines=2,
                max_lines=4
            )
            # ...existing code...
            submit_btn = gr.Button("Start Navigation Simulation", variant="primary")
        with gr.Column(elem_id="result-panel"):
            gr.Markdown("### Latest Simulation Result")
            video_output = gr.Video(
                label="Live",
                interactive=False,
                format="mp4",
                autoplay=True,
                streaming=True
            )
            with gr.Column() as history_container:
                gr.Markdown("### History")
                gr.Markdown("#### History will be reset after refresh")
                history_slots = []
                for i in range(10):
                    with gr.Column(visible=False) as slot:
                        with gr.Accordion(visible=False, open=False) as accordion:
                            video = gr.Video(interactive=False)
                            detail_md = gr.Markdown()
                    history_slots.append((slot, accordion, video, detail_md))
    with gr.Accordion("查看系统访问日志(DEV ONLY)", open=False):
        logs_display = gr.Markdown()
        refresh_logs_btn = gr.Button("刷新日志", variant="secondary")
        refresh_logs_btn.click(
            update_log_display,
            outputs=logs_display
        )
    gr.Examples(
        examples=[
            ["scene_1", "RDP", "vlnPE", "Exit the bedroom and turn left. Walk straight passing the gray couch and stop near the rug."]
        ],
        inputs=[scene_dropdown, model_dropdown, mode_dropdown, prompt_input],
        label="Navigation Task Example"
    )
    submit_btn.click(
        fn=run_simulation,
        inputs=[scene_dropdown, model_dropdown, mode_dropdown, prompt_input, history_state],
        outputs=[video_output, history_state],
        queue=True,
        api_name="run_simulation"
    ).then(
        fn=update_history_display,
        inputs=history_state,
        outputs=[comp for slot in history_slots for comp in slot],
        queue=True
    ).then(
        fn=update_log_display,
        outputs=logs_display,
    )
    demo.load(
        fn=lambda: update_scene_display("scene_1"),
        outputs=[scene_description, scene_preview]
    ).then(
        fn=update_log_display,
        outputs=logs_display
    )
    demo.load(
        fn=record_access,
        inputs=None,
        outputs=logs_display,
        queue=False
    )
    demo.queue(default_concurrency_limit=8)
    demo.unload(fn=cleanup_session)

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=55005, share=False, debug=True, allowed_paths=["/opt"])