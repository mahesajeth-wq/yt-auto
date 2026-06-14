import os
import soundfile as sf
from faster_whisper import WhisperModel

def fmt_time(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h}:{m:02d}:{s:05.2f}"

def generate_captions(audio_files: list[str], script: dict, format_type: str = "short") -> str:
    print("Loading faster-whisper 'tiny' model on CPU...")
    # Use compute_type="int8" as standard for CPU run
    model = WhisperModel("tiny", device="cpu", compute_type="int8")
    
    ass_events = []
    time_offset = 0.0
    
    for i, (audio_path, seg) in enumerate(zip(audio_files, script["segments"])):
        print(f"Transcribing TTS file: {audio_path}...")
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
            
        segments_out, info = model.transcribe(audio_path, word_timestamps=True)
        
        for whisper_seg in segments_out:
            if whisper_seg.words:
                for word_info in whisper_seg.words:
                    start = time_offset + word_info.start
                    end   = time_offset + word_info.end
                    word  = word_info.word.strip().upper()
                    # Skip empty words
                    if not word:
                        continue
                    # Format word styling: bold, white fill, black outline.
                    # {\blur3} adds outline softness.
                    ass_events.append(f"Dialogue: 0,{fmt_time(start)},{fmt_time(end)},Default,,0,0,0,,{{\\blur3}}{word}")
        
        # Advance offset by actual audio duration
        data, sr = sf.read(audio_path)
        duration = len(data) / sr
        time_offset += duration
        print(f"Segment {seg['id']} duration: {duration:.2f}s, Cumulative offset: {time_offset:.2f}s")
        
    # Dynamic ASS subtitle configuration based on format
    if format_type == "short":
        play_res_x = 1080
        play_res_y = 1920
        font_size = 72
        # Position captions in the middle-ish/lower-third of portrait mode
        margin_v = 300
    else:
        play_res_x = 1920
        play_res_y = 1080
        font_size = 54
        margin_v = 120

    ass_header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {play_res_x}
PlayResY: {play_res_y}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, Bold, Italic, Alignment, MarginL, MarginR, MarginV, Outline, Shadow
Style: Default,Arial,{font_size},&H00FFFFFF,&H00000000,-1,0,2,30,30,{margin_v},3,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    
    os.makedirs("output", exist_ok=True)
    ass_path = "output/captions.ass"
    with open(ass_path, "w") as f:
        f.write(ass_header)
        f.write("\n".join(ass_events))
        f.write("\n")
        
    print(f"Generated ASS captions saved to {ass_path}")
    return ass_path
