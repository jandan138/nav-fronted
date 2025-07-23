# logging_utils.py
# 日志相关工具
import os
import json
from datetime import datetime,timedelta
from collections import defaultdict

LOG_DIR = "/opt/nav-fronted/logs"
ACCESS_LOG = os.path.join(LOG_DIR, "access.log")
SUBMISSION_LOG = os.path.join(LOG_DIR, "submissions.log")

os.makedirs(LOG_DIR, exist_ok=True)

IP_REQUEST_RECORDS = defaultdict(list)
IP_LIMIT = 5

def is_request_allowed(ip: str) -> bool:
    now = datetime.now()
    IP_REQUEST_RECORDS[ip] = [t for t in IP_REQUEST_RECORDS[ip] if now - t < timedelta(minutes=1)]
    if len(IP_REQUEST_RECORDS[ip]) < IP_LIMIT:
        IP_REQUEST_RECORDS[ip].append(now)
        return True
    return False

def log_access(user_ip: str = None, user_agent: str = None):
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
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = {
        "timestamp": timestamp,
        "type": "submission",
        "user": user,
        "scene": scene,
        "prompt": prompt,
        "model": model,
        "res": res
    }
    with open(SUBMISSION_LOG, "a") as f:
        f.write(json.dumps(log_entry) + "\n")

def read_logs(log_type: str = "all", max_entries: int = 50) -> list:
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
    logs.sort(key=lambda x: x["timestamp"], reverse=True)
    return logs[:max_entries]

def format_logs_for_display(logs: list) -> str:
    if not logs:
        return "No log record"
    markdown = "### System Access Log\n\n"
    markdown += "| Time | Type | User/IP | Details |\n"
    markdown += "|------|------|---------|----------|\n"
    for log in logs:
        timestamp = log.get("timestamp", "unknown")
        log_type = "Access" if log.get("type") == "access" else "Submission"
        if log_type == "Access":
            user = log.get("user_ip", "unknown")
            details = f"User-Agent: {log.get('user_agent', 'unknown')}"
        else:
            user = log.get("user", "anonymous")
            result = log.get('res', 'unknown')
            if result != "success":
                if len(result) > 40:
                    result = f"{result[:20]}...{result[-20:]}"
            details = f"Scene: {log.get('scene', 'unknown')}, Prompt: {log.get('prompt', '')}, Model: {log.get('model', 'unknown')}, result: {result}"
        markdown += f"| {timestamp} | {log_type} | {user} | {details} |\n"
    return markdown
