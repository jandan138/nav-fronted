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
            label_text = f"Simulation {i+1}  scene: {entry['scene']}, model: {entry.get('model','')}, mode: {entry.get('mode','')}, prompt: {entry['prompt']}"
            updates.extend([
                gr.update(visible=True),
                gr.update(visible=True, label=label_text, open=False),
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

def get_scene_instruction(scene: str):
    """根据场景获取默认指令"""
    config = SCENE_CONFIGS.get(scene, {})
    return config.get("default_instruction", "")

def update_log_display():
    logs = read_logs()
    return format_logs_for_display(logs)
