import os
import requests
import base64
import wave
import time
import urllib.parse
from pipeline.config import GEMINI_API_KEY, GEMINI_FLASH, GEMINI_TTS_MODEL, GEMINI_API_BASE

class TTSError(Exception):
    pass

class GeminiClient:
    def __init__(self):
        self.api_key = GEMINI_API_KEY
        self.base_url = GEMINI_API_BASE

    def generate_text(self, prompt, use_grounding=False, temperature=0.8, max_tokens=8192) -> str:
        url = f"{self.base_url}/models/{GEMINI_FLASH}:generateContent?key={self.api_key}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens
            }
        }
        if use_grounding:
            payload["tools"] = [{"google_search": {}}]
            
        # Retry loop for rate limits (429)
        response = None
        for attempt in range(5):
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=120)
                if response.status_code == 429:
                    wait_time = (attempt + 1) * 6
                    print(f"Rate limited (429) on text generation. Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                    continue
                response.raise_for_status()
                break
            except Exception as e:
                if attempt == 4:
                    raise e
                time.sleep(2)
                
        if not response:
            raise RuntimeError("Failed to get response from Gemini API")
            
        data = response.json()
        try:
            text = data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError) as e:
            raise RuntimeError(f"Unexpected response structure from Gemini API: {data}") from e
            
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return text.strip()

    def generate_image(self, prompt, width=1080, height=1920) -> bytes:
        # Using Pollinations.ai since it's free, has no key, and is highly reliable for image generation.
        encoded_prompt = urllib.parse.quote(prompt)
        url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&model=flux&nologo=true"
        response = requests.get(url, timeout=120)
        response.raise_for_status()
        return response.content

    def generate_tts(self, text, voice="Aoede") -> tuple[bytes, str]:
        url = f"{self.base_url}/models/{GEMINI_TTS_MODEL}:generateContent?key={self.api_key}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{"role": "user", "parts": [{"text": f"Say this clearly with natural pacing: {text}"}]}],
            "generationConfig": {
                "responseModalities": ["AUDIO"],
                "speechConfig": {
                    "voiceConfig": {
                        "prebuiltVoiceConfig": {"voiceName": voice}
                    }
                }
            }
        }
        
        # Retry loop for rate limits (429)
        response = None
        for attempt in range(5):
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=120)
                if response.status_code == 429:
                    wait_time = (attempt + 1) * 6
                    print(f"Rate limited (429) on TTS. Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                    continue
                response.raise_for_status()
                break
            except Exception as e:
                if attempt == 4:
                    raise TTSError(f"Gemini TTS failed: {e}") from e
                time.sleep(2)
                
        if not response:
            raise TTSError("Failed to get response from Gemini TTS API")
            
        try:
            data = response.json()
            part = data["candidates"][0]["content"]["parts"][0]
            inline_data = part["inlineData"]
            mime_type = inline_data["mimeType"]
            base_64_data = inline_data["data"]
            audio_bytes = base64.b64decode(base_64_data)
            return audio_bytes, mime_type
        except Exception as e:
            raise TTSError(f"Gemini TTS parsing failed: {e}") from e
