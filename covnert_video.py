import os
import subprocess
import shutil

def convert_to_h264(video_path):
    """
    将视频转换为 H.264 编码的 MP4 格式
    自动查找 ffmpeg 可执行路径
    """
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


if __name__ == "__main__":
    input_video = "/opt/nav-fronted/assets/output.mp4"
    if not os.path.exists(input_video):
        print(f"❌ 输入文件不存在: {input_video}")
    else:
        convert_to_h264(input_video)
