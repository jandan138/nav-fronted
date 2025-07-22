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
    "scene_2": {
        "description": "scene_2",
        "objects": ["office", "meeting room", "corridor"],
        "preview_image": "/opt/nav-fronted/assets/scene_2.png"
    },
    "scene_3": {
        "description": "scene_3",
        "objects": ["garage", "workshop", "storage"],
        "preview_image": "/opt/nav-fronted/assets/scene_3.png"
    },
    "scene_4": {
        "description": "scene_4",
        "objects": ["garden", "patio", "pool"],
        "preview_image": "/opt/nav-fronted/assets/scene_4.png"
    },
    "scene_5": {
        "description": "scene_5",
        "objects": ["library", "hall", "lounge"],
        "preview_image": "/opt/nav-fronted/assets/scene_5.png"
    },
}

MODEL_CHOICES = ["RDP", "CMA"]
MODE_CHOICES = ["vlnPE", "vlnCE"]

