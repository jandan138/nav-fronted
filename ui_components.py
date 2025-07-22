# ui_components.py
# Gradio界面相关和辅助函数
import gradio as gr
from config import SCENE_CONFIGS
from logging_utils import read_logs, format_logs_for_display

def update_history_display(history: list) -> list:
    updates = []
    for i in range(10):
        if i < len(history):
            entry = history[i]
            updates.extend([
                gr.update(visible=True),
                gr.update(visible=True, label=f"Simulation {i+1}  scene: {entry['scene']}, start: {entry['start_pos']}, prompt: {entry['prompt']}", open=False),
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

def update_scene_display(scene: str):
    config = SCENE_CONFIGS.get(scene, {})
    desc = config.get("description", "No Description")
    objects = "、".join(config.get("objects", []))
    image = config.get("preview_image", None)
    markdown = f"**{desc}**  \nPlaces Included: {objects}"
    return markdown, image

def update_log_display():
    logs = read_logs()
    return format_logs_for_display(logs)
