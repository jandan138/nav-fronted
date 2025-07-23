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
    "demo1": {
        "description": "Demo 1",
        "objects": ["bedroom", "kitchen", "living room", ""],
        "preview_image": "/opt/nav-fronted/assets/scene_1.png",
        "default_instruction": "Walk past the left side of the bed and stop in the doorway."
    },
    "demo2": {
        "description": "Demo 2",
        "objects": ["office", "meeting room", "corridor"],
        "preview_image": "/opt/nav-fronted/assets/scene_2.png",
        "default_instruction": "Walk through the bathroom, past the sink and toilet. Stop in front of the counter with the two suitcase."
    },
    "demo3": {
        "description": "Demo 3",
        "objects": ["garage", "workshop", "storage"],
        "preview_image": "/opt/nav-fronted/assets/scene_3.png",
        "default_instruction": "Do a U-turn. Walk forward through the kitchen, heading to the black door. Walk out of the door and take a right onto the deck. Walk out on to the deck and stop."
    },
    "demo4": {
        "description": "Demo 4",
        "objects": ["garden", "patio", "pool"],
        "preview_image": "/opt/nav-fronted/assets/scene_4.png",
        "default_instruction": "Walk out of bathroom and stand on white bath mat."
    },
    "demo5": {
        "description": "Demo 5",
        "objects": ["library", "hall", "lounge"],
        "preview_image": "/opt/nav-fronted/assets/scene_5.png",
        "default_instruction": "Walk straight through the double wood doors, follow the red carpet straight to the next doorway and stop where the carpet splits off."
    },
}

MODEL_CHOICES = ["rdp", "cma"]
MODE_CHOICES = ["vlnPE", "vlnCE"]
