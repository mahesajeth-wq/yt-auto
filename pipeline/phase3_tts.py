import os
import random
import wave
from pipeline.config import GEMINI_VOICES
from pipeline.gemini import GeminiClient

def generate_audio(script: dict) -> list[str]:
    gemini_client = GeminiClient()
    voice = random.choice(GEMINI_VOICES)
    audio_files = []
    
    # Ensure output directory exists
    os.makedirs("output", exist_ok=True)
    
    for seg in script["segments"]:
        seg_id = seg["id"]
        out_path = f"output/tts_segment_{seg_id}.wav"
        
        # Check if file already exists and is valid (greater than 1KB)
        if os.path.exists(out_path) and os.path.getsize(out_path) > 1000:
            print(f"TTS segment {seg_id} already exists, skipping generation.")
            audio_files.append(out_path)
            continue
            
        print(f"Generating TTS for Segment {seg_id}...")
        
        # Primary: Gemini TTS
        try:
            audio_bytes, mime_type = gemini_client.generate_tts(seg["narration"], voice=voice)
            
            # Check if it starts with the RIFF/WAVE header or mimeType suggests wav
            if audio_bytes.startswith(b"RIFF") or "wav" in mime_type.lower():
                with open(out_path, "wb") as wf:
                    wf.write(audio_bytes)
            else:
                # Wrapped PCM L16 in WAV header
                # Typically rate is 24000, mono, 16-bit PCM (2 bytes)
                with wave.open(out_path, "wb") as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)  # 16-bit
                    wf.setframerate(24000)
                    wf.writeframes(audio_bytes)
            print(f"Gemini TTS succeeded for segment {seg_id} (Voice: {voice})")
            
        except Exception as e:
            print(f"Gemini TTS failed for segment {seg_id}: {e}. Trying gTTS fallback...")
            try:
                from gtts import gTTS
                temp_mp3 = f"output/tts_temp_{seg_id}.mp3"
                tts = gTTS(text=seg["narration"], lang='en')
                tts.save(temp_mp3)
                
                # Convert MP3 to WAV 24000Hz mono 16-bit PCM using FFmpeg
                import subprocess
                cmd = [
                    "ffmpeg", "-y", "-i", temp_mp3,
                    "-ar", "24000", "-ac", "1", "-c:a", "pcm_s16le",
                    out_path
                ]
                subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if os.path.exists(temp_mp3):
                    os.remove(temp_mp3)
                print(f"gTTS fallback succeeded for segment {seg_id}")
            except Exception as e2:
                raise RuntimeError(f"Both TTS engines failed for segment {seg_id}: {e} | {e2}")
        
        audio_files.append(out_path)
        
    return audio_files
