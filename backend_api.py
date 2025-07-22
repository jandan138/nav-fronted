# backend_api.py
# 后端API交互相关
import requests
import uuid
import json
from typing import Optional
from config import API_ENDPOINTS

def submit_to_backend(scene: str, prompt: str, user: str = "Gradio-user") -> dict:
    job_id = str(uuid.uuid4())
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
    try:
        response = requests.get(f"{API_ENDPOINTS['query_status']}/{task_id}", timeout=5)
        try:
            return response.json()
        except json.JSONDecodeError:
            return {"status": "error", "message": response.text}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def get_task_result(task_id: str) -> Optional[dict]:
    try:
        response = requests.get(
            f"{API_ENDPOINTS['get_result']}/{task_id}",
            timeout=5
        )
        return response.json()
    except Exception as e:
        return None
