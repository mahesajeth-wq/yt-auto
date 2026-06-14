import os
import torch
import numpy as np
import scipy.io.wavfile
from transformers import AutoProcessor, MusicgenForConditionalGeneration

def generate_music(topic: str, duration_seconds: int = 35) -> str:
    print(f"Generating background music for topic '{topic}' ({duration_seconds}s)...")
    os.makedirs("output", exist_ok=True)
    out_path = "output/music.wav"
    
    try:
        print("Loading MusicGen Small model (first run downloads weights, cached afterwards)...")
        processor = AutoProcessor.from_pretrained("facebook/musicgen-small")
        model = MusicgenForConditionalGeneration.from_pretrained("facebook/musicgen-small")
        
        # Ensure model is on CPU and in evaluation mode
        model = model.to("cpu")
        model.eval()
        
        prompt = f"calm upbeat educational background music about {topic}, subtle electronic, no vocals, loopable"
        inputs = processor(text=[prompt], padding=True, return_tensors="pt")
        
        sampling_rate = model.config.audio_encoder.sampling_rate  # Typically 32000 Hz
        max_new_tokens = int(duration_seconds * 50)  # ~50 tokens per second of audio
        
        print(f"Generating music tensor (max_new_tokens={max_new_tokens})...")
        with torch.no_grad():
            audio_values = model.generate(**inputs, max_new_tokens=max_new_tokens)
            
        # Extract audio numpy array
        audio_np = audio_values[0, 0].cpu().numpy()
        # Scale to 16-bit PCM integer range
        audio_int16 = (audio_np * 32767).clip(-32768, 32767).astype(np.int16)
        
        scipy.io.wavfile.write(out_path, sampling_rate, audio_int16)
        print(f"Music generated successfully and saved to {out_path}")
        return out_path
        
    except Exception as e:
        print(f"MusicGen failed/out of memory: {e}. Generating a generic synth loop as fallback...")
        # Fallback: simple synthetic loop using numpy
        sampling_rate = 32000
        t = np.linspace(0, duration_seconds, int(sampling_rate * duration_seconds), endpoint=False)
        # Combine a couple of sine waves to make a simple drone/ambient sound
        signal = 0.5 * np.sin(2 * np.pi * 220 * t) + 0.3 * np.sin(2 * np.pi * 330 * t)
        # Apply simple volume envelope
        envelope = 0.5 + 0.5 * np.sin(2 * np.pi * 0.1 * t)
        signal = signal * envelope
        audio_int16 = (signal * 32767).clip(-32768, 32767).astype(np.int16)
        scipy.io.wavfile.write(out_path, sampling_rate, audio_int16)
        print(f"Fallback music saved to {out_path}")
        return out_path
