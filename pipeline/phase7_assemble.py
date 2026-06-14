import os
import wave
import shutil
import subprocess

def get_wav_duration(filepath: str) -> float:
    with wave.open(filepath, 'rb') as f:
        frames = f.getnframes()
        rate = f.getframerate()
        return frames / float(rate)

def assemble_video(broll_files: list[str], tts_files: list[str], captions_ass: str, music_path: str, script: dict, format_type: str) -> str:
    print("Starting video assembly...")
    os.makedirs("output", exist_ok=True)
    
    # Step 1: Normalize all B-roll clips to uniform spec
    print("Step 1: Normalizing B-roll clips...")
    normalized_brolls = []
    durations = []
    
    w, h = (1080, 1920) if format_type == "short" else (1920, 1080)
    
    for i, (broll_path, tts_path) in enumerate(zip(broll_files, tts_files)):
        duration = get_wav_duration(tts_path)
        durations.append(duration)
        norm_path = f"output/broll_{i}_norm.mp4"
        
        print(f"Normalizing segment {i} B-roll to duration {duration:.3f}s...")
        cmd = [
            "ffmpeg", "-y", "-stream_loop", "-1", "-i", broll_path, "-t", f"{duration:.3f}",
            "-vf", f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,setsar=1",
            "-r", "30", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-an", norm_path
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        normalized_brolls.append(norm_path)

    # Step 2: Concatenate B-roll (no audio)
    print("Step 2: Concatenating B-roll clips...")
    concat_list_path = "output/concat_list.txt"
    with open(concat_list_path, "w") as f:
        for norm_path in normalized_brolls:
            abs_path = os.path.abspath(norm_path)
            f.write(f"file '{abs_path}'\n")
            
    assembled_video_path = "output/assembled_video.mp4"
    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list_path,
        "-c", "copy", assembled_video_path
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Step 3: Concatenate TTS audio segments
    print("Step 3: Concatenating TTS audio segments...")
    audio_list_path = "output/audio_list.txt"
    with open(audio_list_path, "w") as f:
        for tts_path in tts_files:
            abs_path = os.path.abspath(tts_path)
            f.write(f"file '{abs_path}'\n")
            
    tts_combined_path = "output/tts_combined.wav"
    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", audio_list_path,
        "-c", "copy", tts_combined_path
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Step 4: Add karaoke captions to video
    print("Step 4: Adding captions...")
    assembled_capped_path = "output/assembled_capped.mp4"
    cmd = [
        "ffmpeg", "-y", "-i", assembled_video_path,
        "-vf", f"ass={captions_ass}",
        "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p",
        assembled_capped_path
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Step 5: Add Segment 4 flash overlay (rewatch trigger) - Shorts only
    print("Step 5: Adding flash overlay (Shorts only)...")
    assembled_flashed_path = "output/assembled_flashed.mp4"
    if format_type == "short" and len(durations) >= 4:
        seg4_start = sum(durations[:3])
        seg4_end = seg4_start + 0.8
        
        # Use simple text with no special characters to avoid FFmpeg escaping issues
        drawtext_filter = (
            f"drawtext=text='pause - catch the hidden detail':fontsize=40:fontcolor=yellow:"
            f"x=(w-text_w)/2:y=h*0.15:enable='between(t,{seg4_start:.3f},{seg4_end:.3f})':"
            f"box=1:boxcolor=black@0.5"
        )
        cmd = [
            "ffmpeg", "-y", "-i", assembled_capped_path,
            "-vf", drawtext_filter,
            "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p",
            assembled_flashed_path
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        shutil.copy(assembled_capped_path, assembled_flashed_path)

    # Step 6: Final mix: video + TTS + music with seamless audio loop
    print("Step 6: Mixing video, narration, and background music...")
    final_output_path = f"output/final_{format_type}.mp4"
    
    # We mix narration (volume=2.0) and music (volume=0.12).
    # Music loops infinitely so it covers the whole duration.
    # The output audio ends when the first stream (narration) ends.
    filter_complex = (
        "[1:a]volume=2.0[tts];"
        "[2:a]volume=0.12,aloop=loop=-1:size=2147483647[music_loop];"
        "[tts][music_loop]amix=inputs=2:duration=first[audio_final]"
    )
    
    cmd = [
        "ffmpeg", "-y",
        "-i", assembled_flashed_path,
        "-i", tts_combined_path,
        "-i", music_path,
        "-filter_complex", filter_complex,
        "-map", "0:v",
        "-map", "[audio_final]",
        "-c:v", "libx264", "-preset", "slow", "-crf", "18",
        "-b:v", "10M", "-maxrate", "12M", "-bufsize", "24M",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-r", "30",
        "-movflags", "+faststart",
        final_output_path
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    print(f"Assembly completed. Final video: {final_output_path}")
    return final_output_path
