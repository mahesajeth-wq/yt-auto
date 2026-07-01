import os
import subprocess
import json

def get_audio_duration(audio_path: str) -> float:
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        audio_path
    ]
    try:
        return float(subprocess.check_output(cmd).decode().strip())
    except Exception as e:
        print(f"Error getting audio duration for {audio_path}: {e}")
        return 5.0

def build_scene_clip(raw_video: str, start: float, end: float, tts_audio: str, output_path: str):
    vdur = end - start
    adur = get_audio_duration(tts_audio)
    
    print(f"Processing scene clip: video={vdur:.2f}s, tts={adur:.2f}s")
    
    temp_v = output_path.replace(".mp4", "_v.mp4")
    
    if vdur >= adur:
        # Cut video to match audio length
        cmd_v = [
            "ffmpeg", "-y",
            "-ss", f"{start:.3f}",
            "-i", raw_video,
            "-t", f"{adur:.3f}",
            "-an",
            "-c:v", "libx264",
            "-crf", "23",
            "-pix_fmt", "yuv420p",
            temp_v
        ]
    else:
        # Pad last frame (static hold) using tpad
        pad_dur = adur - vdur
        cmd_v = [
            "ffmpeg", "-y",
            "-ss", f"{start:.3f}",
            "-to", f"{end:.3f}",
            "-i", raw_video,
            "-vf", f"tpad=stop_mode=clone:stop_duration={pad_dur:.3f}",
            "-an",
            "-c:v", "libx264",
            "-crf", "23",
            "-pix_fmt", "yuv420p",
            temp_v
        ]
        
    subprocess.run(cmd_v, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # Merge video and TTS audio
    cmd_merge = [
        "ffmpeg", "-y",
        "-i", temp_v,
        "-i", tts_audio,
        "-c:v", "copy",
        "-c:a", "aac",
        "-map", "0:v",
        "-map", "1:a",
        output_path
    ]
    subprocess.run(cmd_merge, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    if os.path.exists(temp_v):
        os.remove(temp_v)

def compile_ad(raw_video: str, scene_cues: list, tts_audios: list, bg_music: str, subtitle_ass: str, output_dir: str, final_path: str):
    print("Compiling final ad video...")
    os.makedirs(output_dir, exist_ok=True)
    
    scene_clips = []
    
    for i, scene in enumerate(scene_cues):
        start = scene["start_time"]
        end = scene["end_time"]
        tts_audio = tts_audios[i]
        
        if not tts_audio or not os.path.exists(tts_audio):
            continue
            
        scene_clip_path = os.path.join(output_dir, f"scene_{i+1}_final.mp4")
        build_scene_clip(raw_video, start, end, tts_audio, scene_clip_path)
        scene_clips.append(scene_clip_path)
        
    # Write concat list
    concat_list_path = os.path.join(output_dir, "concat_list.txt")
    with open(concat_list_path, "w") as f:
        for clip in scene_clips:
            f.write(f"file '{clip}'\n")
            
    # Concatenate clips
    concatenated_raw = os.path.join(output_dir, "concatenated_raw.mp4")
    cmd_concat = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", concat_list_path,
        "-c", "copy",
        concatenated_raw
    ]
    result = subprocess.run(cmd_concat, check=True, capture_output=True)
    if result.returncode != 0:
        print(f"FFmpeg concat stderr: {result.stderr.decode()}")
    
    # Mix background music and burn ASS subtitles with LUT/contrast filter
    print("Mixing background music and burning subtitles...")
    
    # If the video is portrait (which it is since rotation -90 is shown in ffprobe), 
    # we need to be careful with filter syntax. Standard ass filter burns directly.
    # We add contrast and saturation using eq filter.
    vf_filter = f"ass={subtitle_ass},eq=contrast=1.05:saturation=1.1"
    
    cmd_final = [
        "ffmpeg", "-y",
        "-i", concatenated_raw,
        "-i", bg_music,
        "-filter_complex", f"[0:a]volume=1.0[v_a];[1:a]volume=0.06[m_a];[v_a][m_a]amix=inputs=2:duration=first[a];[0:v]{vf_filter}[v]",
        "-map", "[v]",
        "-map", "[a]",
        "-c:v", "libx264",
        "-crf", "21",
        "-preset", "fast",
        "-c:a", "aac",
        "-b:a", "192k",
        final_path
    ]
    
    result = subprocess.run(cmd_final, capture_output=True)
    if result.returncode != 0:
        print(f"FFmpeg final stderr: {result.stderr.decode()[-500:]}")
        raise RuntimeError(f"FFmpeg final render failed with exit code {result.returncode}")
    
    if not os.path.exists(final_path):
        raise RuntimeError(f"Final video not found at {final_path} after ffmpeg!")
    print(f"Final video successfully generated at {final_path}!")
