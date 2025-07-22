# config.py
# 配置相关：API、场景等
import os

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
API_ENDPOINTS = {
    "submit_task": f"{BACKEND_URL}/predict/video",
    "query_status": f"{BACKEND_URL}/predict/task",
    "get_result": f"{BACKEND_URL}//predict"
}

SCENE_CONFIGS = {
    "scene_1": {
        "description": "scene_1",
        "objects": ["bedroom", "kitchen", "living room", ""],
        "preview_image": "/opt/nav-fronted/assets/scene_1.png"
    },
}

MODEL_CHOICES = []  # 仅占位，不再使用
