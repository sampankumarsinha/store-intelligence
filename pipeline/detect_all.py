import os
import subprocess

VIDEOS = [
    "CAM 1.mp4",
    "CAM 2.mp4",
    "CAM 3.mp4",
    "CAM 4.mp4",
    "CAM 5.mp4"
]

for video in VIDEOS:
    print(f"\nProcessing {video}")

    os.environ["VIDEO_FILE"] = video

    subprocess.run(
        ["python3", "pipeline/detect.py"],
        check=True
    )

print("\nAll videos processed")