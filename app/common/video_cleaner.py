import subprocess
from pathlib import Path

FFMPEG_PATH = Path(__file__).parent / "bin" / "ffmpeg.exe"

def clean_video(input_path, output_path):
    command = [
        str(FFMPEG_PATH),
        "-i", input_path,
        "-map_metadata", "-1",
        "-map_chapters", "-1",
        "-vcodec", "libx264",
        "-preset", "slow",
        "-crf", "28",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        "-acodec", "aac",
        "-b:a", "96k",
        output_path
    ]

    subprocess.run(command, check=True)
    return output_path
