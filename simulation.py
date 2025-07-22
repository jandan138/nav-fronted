# simulation.py
# 仿真与视频相关
import os
import time
import uuid
import cv2
import numpy as np
from typing import List
import gradio as gr
from backend_api import get_task_status

def stream_simulation_results(result_folder: str, task_id: str, fps: int = 6):
    result_folder = os.path.join(result_folder, "images")
    os.makedirs(result_folder, exist_ok=True)
    frame_buffer: List[np.ndarray] = []
    frames_per_segment = fps * 2
    processed_files = set()
    width, height = 0, 0
    last_status_check = 0
    status_check_interval = 5
    max_time = 240
    while max_time > 0:
        max_time -= 1
        current_time = time.time()
        if current_time - last_status_check > status_check_interval:
            status = get_task_status(task_id)
            if status.get("status") == "completed":
                process_remaining_images(result_folder, processed_files, frame_buffer)
                if frame_buffer:
                    yield create_video_segment(frame_buffer, fps, width, height)
                break
            elif status.get("status") == "failed":
                raise gr.Error(f"任务执行失败: {status.get('result', '未知错误')}")
            elif status.get("status") == "terminated":
                break
            last_status_check = current_time
        current_files = sorted(
            [f for f in os.listdir(result_folder) if f.lower().endswith(('.png', '.jpg', '.jpeg'))],
            key=lambda x: os.path.splitext(x)[0]
        )
        new_files = [f for f in current_files if f not in processed_files]
        has_new_frames = False
        for filename in new_files:
            try:
                img_path = os.path.join(result_folder, filename)
                frame = cv2.imread(img_path)
                if frame is not None:
                    if width == 0:
                        height, width = frame.shape[:2]
                    frame_buffer.append(frame)
                    processed_files.add(filename)
                    has_new_frames = True
            except Exception:
                pass
        if has_new_frames and len(frame_buffer) >= frames_per_segment:
            segment_frames = frame_buffer[:frames_per_segment]
            frame_buffer = frame_buffer[frames_per_segment:]
            yield create_video_segment(segment_frames, fps, width, height)
        time.sleep(1)
    if max_time <= 0:
        raise gr.Error("timeout 240s")

def create_video_segment(frames: List[np.ndarray], fps: int, width: int, height: int) -> str:
    os.makedirs("/opt/gradio_demo/tasks/video_chunk", exist_ok=True)
    segment_name = f"/opt/gradio_demo/tasks/video_chunk/output_{uuid.uuid4()}.mp4"
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(segment_name, fourcc, fps, (width, height))
    for frame in frames:
        out.write(frame)
    out.release()
    return segment_name

def process_remaining_images(result_folder: str, processed_files: set, frame_buffer: List[np.ndarray]):
    current_files = sorted(
        [f for f in os.listdir(result_folder) if f.lower().endswith(('.png', '.jpg', '.jpeg'))],
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
        except Exception:
            pass

def convert_to_h264(video_path):
    import shutil
    base, ext = os.path.splitext(video_path)
    video_path_h264 = f"{base}_h264.mp4"
    ffmpeg_bin = "/root/anaconda3/envs/gradio/bin/ffmpeg"
    if not os.path.exists(ffmpeg_bin):
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
    import subprocess
    try:
        result = subprocess.run(ffmpeg_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if not os.path.exists(video_path_h264):
            raise FileNotFoundError(f"⚠️ H.264 文件未生成: {video_path_h264}")
        return video_path_h264
    except Exception as e:
        raise
