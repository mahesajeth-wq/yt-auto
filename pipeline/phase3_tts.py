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
            print(f"Gemini TTS failed for segment {seg_id}: {e}. Trying Kokoro fallback...")
            # Fallback: Kokoro TTS (CPU)
            try:
                from kokoro import KPipeline
                import numpy as np
                import scipy.io.wavfile
                
                # Setup Kokoro pipeline for American English
                ko = KPipeline(lang_code='a')
                # Generator yields graphemes, phonemes, audio (numpy array)
                generator = ko(seg["narration"], voice='af_heart', speed=1.0)
                samples = []
                for _, _, audio in generator:
                    if audio is not None:
                        samples.append(audio)
                        
                if not samples:
                    raise RuntimeError("Kokoro generated no audio samples")
                    
                audio_np = np.concatenate(samples)
                # Save as WAV at 24000Hz (Kokoro output is typically 24000Hz)
                scipy.io.wavfile.write(out_path, 24000, audio_np)
                print(f"Kokoro fallback succeeded for segment {seg_id}")
            except Exception as e2:
                raise RuntimeError(f"Both TTS engines failed for segment {seg_id}: {e} | {e2}")
        
        audio_files.append(out_path)
        
    return audio_files
