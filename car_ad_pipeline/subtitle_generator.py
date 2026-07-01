import os
import json

def align_subtitles(tts_audio_path: str, hinglish_text: str) -> list:
    """
    Transcribes the generated TTS audio to get word-level timestamps,
    and maps these timestamps to the Hinglish words.
def align_subtitles(tts_audio_path: str, hinglish_text: str) -> list:
    """
    Distributes the Hinglish words evenly across the duration of the audio clip.
    This avoids loading the heavy Whisper model, saving RAM and CPU.
    """
    import subprocess
    print(f"Timing alignment (even distribution) for: {tts_audio_path}")
    
    hinglish_words = [w.strip() for w in hinglish_text.split() if w.strip()]
    aligned = []
    num_hinglish = len(hinglish_words)
    
    cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", tts_audio_path]
    try:
        dur = float(subprocess.check_output(cmd).decode().strip())
    except Exception:
        dur = 5.0
        
    step = dur / max(1, num_hinglish)
    for i, word in enumerate(hinglish_words):
        aligned.append({
            "word": word,
            "start": i * step,
            "end": (i + 1) * step
        })
    return aligned

def generate_ass_subtitles(aligned_scenes: list, output_path: str):
    """
    Generates an Advanced SubStation Alpha (.ass) file with karaoke styling.
    """
    ass_template = """[Script Info]
Title: Car Ad Karaoke Subtitles
ScriptType: v4.00+
PlayResX: 720
PlayResY: 1280
Timer: 100.0000

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Bebas Neue,64,&H00FFFFFF,&H0000FFFF,&H00000000,&H60000000,-1,0,0,0,100,100,0,0,1,3,0,2,30,30,120,1
Style: Highlight,Bebas Neue,66,&H0000FFFF,&H0000FFFF,&H00000000,&H60000000,-1,0,0,0,100,100,0,0,1,3,0,2,30,30,120,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    for scene_idx, scene in enumerate(aligned_scenes):
        scene_start = scene["scene_start"]
        scene_aligned_words = scene["words"]
        
        # We construct a karaoke effect line using the {\k} tag
        # ASS timing tag \k is in centiseconds (1/100 of a second)
        current_time = scene_start
        
        # Construct the subtitle text line
        subtitle_text_parts = []
        for word_info in scene_aligned_words:
            w_start = word_info["start"] + scene_start
            w_end = word_info["end"] + scene_start
            w_dur_cs = int((w_end - w_start) * 100)
            if w_dur_cs <= 0:
                w_dur_cs = 10
            
            # Format time representation
            # Highlight numbers with different styling (e.g. bold or colored)
            is_number = any(char.isdigit() for char in word_info["word"]) or word_info["word"].lower() in ["lakh", "lakhs", "cr", "crore"]
            if is_number:
                subtitle_text_parts.append(f"{{\\k{w_dur_cs}}}{{\\c&H0000FF&}}{word_info['word']}{{\\c&HFFFFFF&}}")
            else:
                subtitle_text_parts.append(f"{{\\k{w_dur_cs}}}{word_info['word']}")
                
        line_text = " ".join(subtitle_text_parts)
        
        # Calculate full scene duration
        if scene_aligned_words:
            line_start_s = scene_aligned_words[0]["start"] + scene_start
            line_end_s = scene_aligned_words[-1]["end"] + scene_start
        else:
            line_start_s = scene_start
            line_end_s = scene_start + 5.0
            
        def format_ass_time(seconds: float) -> str:
            h = int(seconds // 3600)
            m = int((seconds % 3600) // 60)
            s = int(seconds % 60)
            cs = int((seconds % 1) * 100)
            return f"{h:01d}:{m:02d}:{s:02d}.{cs:02d}"
            
        events.append(
            f"Dialogue: 0,{format_ass_time(line_start_s)},{format_ass_time(line_end_s)},Default,,0,0,0,,{line_text}"
        )
        
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(ass_template + "\n".join(events))
    print(f"ASS subtitle file written to {output_path}")
