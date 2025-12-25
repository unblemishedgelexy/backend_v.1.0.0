import subprocess
import os

def compress_video(input_path, output_path):
    command = [
        "ffmpeg",
        "-i", input_path,
        "-map_metadata", "-1",
        "-vcodec", "libx264",
        "-crf", "28",
        "-preset", "slow",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        "-acodec", "aac",
        "-b:a", "96k",
        output_path
    ]
    subprocess.run(command, check=True)