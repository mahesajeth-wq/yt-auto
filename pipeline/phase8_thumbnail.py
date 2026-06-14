import os
import subprocess

def clean_thumbnail_text(text: str) -> str:
    # Remove chars that frequently break FFmpeg filter parsing (e.g. colons, commas, semicolons, backslashes)
    cleaned = "".join(c for c in text if c.isalnum() or c in " -!?")
    # Escape single quotes for shell/ffmpeg drawtext argument
    return cleaned.replace("'", "'\\\\''")

def generate_thumbnail(final_video_path: str, thumbnail_text: str) -> str:
    print(f"Generating thumbnail for {final_video_path} with text: '{thumbnail_text}'...")
    os.makedirs("output", exist_ok=True)
    
    hook_frame_path = "output/hook_frame.jpg"
    thumbnail_path = "output/thumbnail.jpg"
    
    # 1. Extract first frame of video
    print("Extracting first frame from video...")
    cmd_frame = [
        "ffmpeg", "-y", "-i", final_video_path, "-vframes", "1", "-q:v", "2", hook_frame_path
    ]
    subprocess.run(cmd_frame, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # 2. Scale and draw text
    cleaned_text = clean_thumbnail_text(thumbnail_text)
    
    # We will try with DejaVu Sans Bold first, and fallback to generic sans if it fails.
    drawtext_filter = (
        f"scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,"
        f"drawtext=text='{cleaned_text}':font='DejaVu Sans':style=Bold:fontsize=90:"
        f"fontcolor=white:borderw=5:bordercolor=black:x=(w-text_w)/2:y=h*0.15"
    )
    
    cmd_thumb = [
        "ffmpeg", "-y", "-i", hook_frame_path,
        "-vf", drawtext_filter,
        "-q:v", "2", thumbnail_path
    ]
    
    try:
        print("Drawing thumbnail text...")
        subprocess.run(cmd_thumb, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        print("Font DejaVu Sans failed, retrying with generic 'sans' font...")
        # Fallback filter without specific font name
        drawtext_filter_fallback = (
            f"scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,"
            f"drawtext=text='{cleaned_text}':font='sans':fontsize=90:"
            f"fontcolor=white:borderw=5:bordercolor=black:x=(w-text_w)/2:y=h*0.15"
        )
        cmd_thumb_fallback = [
            "ffmpeg", "-y", "-i", hook_frame_path,
            "-vf", drawtext_filter_fallback,
            "-q:v", "2", thumbnail_path
        ]
        subprocess.run(cmd_thumb_fallback, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
    print(f"Thumbnail generated successfully: {thumbnail_path}")
    return thumbnail_path
