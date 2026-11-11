"""Turn an audio file plus a still image into an H.264 clip for a slide."""

import subprocess
import sys
from pathlib import Path

from PIL import Image

MAX_WIDTH = 1600


def even_frame(image: Path, out: Path) -> Path:
    """Write the still as RGB PNG, at most MAX_WIDTH wide, with even sides (H.264 needs them)."""
    picture = Image.open(image).convert("RGB")
    scale = min(1.0, MAX_WIDTH / picture.width)
    width = round(picture.width * scale) // 2 * 2
    height = round(picture.height * scale) // 2 * 2
    picture.resize((width, height), Image.LANCZOS).save(out)
    return out


def duration(media: Path) -> str:
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(media)],
        check=True, capture_output=True, text=True,
    )
    return probe.stdout.strip()


def still_clip(image: Path, audio: Path, out: Path) -> Path:
    frame = even_frame(image, out.with_suffix(".frame.png"))
    # -shortest alone leaves the looped still running past the audio, so cut at the audio's length.
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-loop", "1", "-framerate", "1", "-i", str(frame),
         "-i", str(audio), "-t", duration(audio), "-map", "0:v", "-map", "1:a",
         "-c:v", "libx264", "-tune", "stillimage", "-pix_fmt", "yuv420p", "-r", "1",
         "-c:a", "aac", "-b:a", "96k", "-shortest", "-movflags", "+faststart", str(out)],
        check=True,
    )
    return out


if __name__ == "__main__":
    image, audio, out = map(Path, sys.argv[1:4])
    print(still_clip(image, audio, out))
