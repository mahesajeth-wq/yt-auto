import os
import random
import requests
import urllib.parse
import subprocess
from pipeline.config import PEXELS_API_KEY, PIXABAY_API_KEY

def fetch_pexels_video(query: str, orientation: str, api_key: str) -> str:
    if not api_key:
        return None
    url = "https://api.pexels.com/videos/search"
    try:
        r = requests.get(
            url,
            headers={"Authorization": api_key},
            params={"query": query, "per_page": 5, "orientation": orientation},
            timeout=30
        )
        r.raise_for_status()
        videos = r.json().get("videos", [])
        if not videos:
            return None
        video = random.choice(videos[:3])
        # Get HD or SD quality file
        files = [f for f in video["video_files"] if f.get("quality") in ("hd", "sd")]
        files.sort(key=lambda f: f.get("width", 0), reverse=True)
        return files[0]["link"] if files else None
    except Exception as e:
        print(f"Pexels fetch failed for query '{query}': {e}")
        return None

def fetch_pixabay_video(query: str, api_key: str) -> str:
    if not api_key:
        return None
    url = "https://pixabay.com/api/videos/"
    try:
        r = requests.get(
            url,
            params={"key": api_key, "q": query, "per_page": 3},
            timeout=30
        )
        r.raise_for_status()
        hits = r.json().get("hits", [])
        if not hits:
            return None
        # Retrieve the URL for a large video or medium video
        videos_data = hits[0].get("videos", {})
        for size in ["large", "medium", "small", "tiny"]:
            if size in videos_data and videos_data[size].get("url"):
                return videos_data[size]["url"]
        return None
    except Exception as e:
        print(f"Pixabay fetch failed for query '{query}': {e}")
        return None

def fetch_broll(query: str, format_type: str, segment_index: int) -> str:
    orientation = "portrait" if format_type == "short" else "landscape"
    out_path = f"output/broll_{segment_index}.mp4"
    img_path = f"output/broll_{segment_index}.jpg"
    
    os.makedirs("output", exist_ok=True)
    
    # Try video sources first
    print(f"Attempting to fetch video B-roll for segment {segment_index} (Query: '{query}')...")
    video_url = None
    if PEXELS_API_KEY:
        video_url = fetch_pexels_video(query, orientation, PEXELS_API_KEY)
    if not video_url and PIXABAY_API_KEY:
        video_url = fetch_pixabay_video(query, PIXABAY_API_KEY)
        
    if video_url:
        print(f"Downloading video from {video_url}...")
        try:
            r = requests.get(video_url, stream=True, timeout=60)
            r.raise_for_status()
            with open(out_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            print(f"B-roll video segment {segment_index} saved to {out_path}")
            return out_path
        except Exception as download_err:
            print(f"Failed to download video: {download_err}. Falling back to image...")

    # Fallback: Image generation (Pollinations.ai)
    print(f"Falling back to image generation for segment {segment_index}...")
    w, h = (1080, 1920) if format_type == "short" else (1920, 1080)
    try:
        encoded_query = urllib.parse.quote(query)
        img_url = f"https://image.pollinations.ai/prompt/{encoded_query}?width={w}&height={h}&model=flux&nologo=true"
        r = requests.get(img_url, timeout=60)
        r.raise_for_status()
        with open(img_path, "wb") as f:
            f.write(r.content)
            
        # Convert image to 6-second video clip using FFmpeg
        print(f"Converting generated image {img_path} to video {out_path} using FFmpeg...")
        cmd = [
            "ffmpeg", "-y", "-loop", "1", "-i", img_path, "-t", "6",
            "-vf", f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,setsar=1",
            "-r", "30", "-c:v", "libx264", "-pix_fmt", "yuv420p", out_path
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"B-roll image-video segment {segment_index} saved to {out_path}")
        return out_path
    except Exception as e:
        raise RuntimeError(f"All B-roll sources and image generation fallback failed for query '{query}': {e}") from e
