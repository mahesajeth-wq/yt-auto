import os
import sys
import time
import base64
import mimetypes
import requests
from car_ad_pipeline.config import GEMINI_API_BASE, GEMINI_MODEL, GEMINI_TTS_MODEL, get_api_keys

class GeminiClient:
    def __init__(self):
        self.keys = get_api_keys()
        self.current_key_idx = 0
        if not self.keys:
            raise RuntimeError("No Gemini API keys found. Configure GEMINI_API_KEY or GEMINI_API_KEYS.")

    def get_key(self) -> str:
        return self.keys[self.current_key_idx]

    def rotate_key(self):
        self.current_key_idx = (self.current_key_idx + 1) % len(self.keys)
        print(f"[GeminiClient] Rotated to key slot {self.current_key_idx + 1}/{len(self.keys)}")

    def upload_file(self, filepath: str) -> str:
        mime_type, _ = mimetypes.guess_type(filepath)
        if not mime_type:
            mime_type = "video/mp4"
            
        file_size = os.path.getsize(filepath)
        filename = os.path.basename(filepath)
        
        print(f"Uploading file '{filename}' ({file_size / (1024*1024):.2f} MB) to Gemini Files API...")
        
        for attempt in range(len(self.keys) * 2):
            key = self.get_key()
            url = f"https://generativelanguage.googleapis.com/upload/v1beta/files?uploadType=media&key={key}"
            headers = {
                "Content-Type": mime_type,
                "Content-Length": str(file_size),
                "X-Goog-Upload-Header-Content-Length": str(file_size),
                "X-Goog-Upload-Header-Content-Type": mime_type,
            }
            try:
                with open(filepath, "rb") as f:
                    file_bytes = f.read()
                response = requests.post(url, headers=headers, data=file_bytes, timeout=300)
                if response.status_code == 429:
                    print(f"[GeminiClient] File upload returned 429. Rotating key and retrying.")
                    self.rotate_key()
                    continue
                response.raise_for_status()
                res_data = response.json()
                file_name = res_data["file"]["name"]
                file_uri = res_data["file"]["uri"]
                print(f"Uploaded successfully: {file_name} -> {file_uri}")
                return file_name, file_uri
            except Exception as e:
                print(f"[GeminiClient] Upload failed: {e}. Rotating key.")
                self.rotate_key()
                time.sleep(2)
        raise RuntimeError("Failed to upload file to Gemini Files API after multiple key rotations.")

    def wait_for_file_active(self, file_name: str, max_timeout_seconds: int = 180) -> bool:
        start_time = time.time()
        while time.time() - start_time < max_timeout_seconds:
            key = self.get_key()
            url = f"{GEMINI_API_BASE}/{file_name}?key={key}"
            try:
                response = requests.get(url, timeout=30)
                if response.status_code == 429:
                    self.rotate_key()
                    time.sleep(5)
                    continue
                response.raise_for_status()
                data = response.json()
                state = data.get("state")
                if state == "ACTIVE":
                    print(f"File {file_name} is ACTIVE.")
                    return True
                elif state == "FAILED":
                    raise RuntimeError(f"Gemini File API processing failed: {data}")
                else:
                    print(f"File state is {state}. Retrying in 5 seconds...")
                    time.sleep(5)
            except Exception as e:
                print(f"[GeminiClient] Error polling file status: {e}. Retrying...")
                time.sleep(5)
        return False

    def generate_content(self, contents: list, response_schema: dict = None, low_res: bool = False, model: str = None) -> str:
        model_name = model or GEMINI_MODEL
        for attempt in range(len(self.keys) * 3):
            key = self.get_key()
            url = f"{GEMINI_API_BASE}/models/{model_name}:generateContent?key={key}"
            
            gen_config = {
                "temperature": 0.2 if response_schema else 0.7,
            }
            if response_schema:
                gen_config["responseMimeType"] = "application/json"
                gen_config["responseSchema"] = response_schema



            payload = {
                "contents": contents,
                "generationConfig": gen_config
            }

            try:
                response = requests.post(url, json=payload, timeout=180)
                if response.status_code == 429:
                    print(f"[GeminiClient] generateContent returned 429. Rotating key.")
                    self.rotate_key()
                    time.sleep(5)
                    continue
                response.raise_for_status()
                res_data = response.json()
                text = res_data["candidates"][0]["content"]["parts"][0]["text"]
                return text
            except Exception as e:
                print(f"[GeminiClient] generateContent failed: {e}. Rotating key.")
                self.rotate_key()
                time.sleep(2)
        raise RuntimeError("Failed to generate content from Gemini after multiple key rotations.")

    def generate_tts(self, text: str, voice: str = "Aoede", vocal_tone: str = "confident") -> bytes:
        for attempt in range(len(self.keys) * 2):
            key = self.get_key()
            url = f"{GEMINI_API_BASE}/models/{GEMINI_TTS_MODEL}:generateContent?key={key}"
            
            director_instructions = (
                f"Vocal Delivery Guide: Speak in a salesman tone: confident, conversational, and persuasive. "
                f"Pitch is natural, pacing has deliberate short pauses for dramatic effect. "
                f"Speak clearly and with high quality. Tone setting: {vocal_tone}."
            )
            full_prompt = (
                f"Director Instructions:\n{director_instructions}\n\n"
                f"Narration text to speak (Speak ONLY the following Hindi text): {text}"
            )
            
            payload = {
                "contents": [{"role": "user", "parts": [{"text": full_prompt}]}],
                "generationConfig": {
                    "responseModalities": ["AUDIO"],
                    "speechConfig": {
                        "voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice}}
                    },
                },
            }
            try:
                response = requests.post(url, json=payload, timeout=120)
                if response.status_code == 429:
                    self.rotate_key()
                    time.sleep(5)
                    continue
                response.raise_for_status()
                res_data = response.json()
                inline = res_data["candidates"][0]["content"]["parts"][0]["inlineData"]
                return base64.b64decode(inline["data"])
            except Exception as e:
                print(f"[GeminiClient] generate_tts failed: {e}. Rotating key.")
                self.rotate_key()
                time.sleep(2)
        raise RuntimeError("Failed to generate TTS from Gemini after multiple key rotations.")
