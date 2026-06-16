import base64
import io
import json
from PIL import Image
from pipeline.gemini import _post_with_rotation
from pipeline.config import GEMINI_FLASH, GEMINI_API_BASE

def _shrink(img_bytes: bytes, max_dim: int = 768) -> bytes:
    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    img.thumbnail((max_dim, max_dim))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=80)
    return buf.getvalue()

def vision_rank_broll(thumbnails: list[bytes], narration: str, query: str) -> tuple[int | None, bool]:
    """Returns (best_index, match_found). Empty/failed input -> (None, False) so the
    pipeline continues the waterfall rather than silently accepting garbage."""
    if not thumbnails:
        return None, False
    parts = [{"text": (
        f'Narration for this moment: "{narration}"\n'
        f'Search query used: "{query}"\n\n'
        f"{len(thumbnails)} candidate thumbnails follow, indexed 0..{len(thumbnails)-1}. "
        f"Pick the index whose image most literally shows the SUBJECT of the narration "
        f'(e.g. narration about cats -> must show an actual cat, NOT excavators, '
        f"cable, scans, or other keyword-collision results).\n\n"
        f'Return ONLY JSON: {{"best_index": <int or null>, "match_found": <bool>}}. '
        f"Set match_found=false, best_index=null if NONE clearly show the subject."
    )}]
    for t in thumbnails:
        parts.append({"inlineData": {"mimeType": "image/jpeg",
                                      "data": base64.b64encode(_shrink(t)).decode()}})
    url = f"{GEMINI_API_BASE}/models/{GEMINI_FLASH}:generateContent?key={{key}}"
    payload = {"contents": [{"role": "user", "parts": parts}],
               "generationConfig": {"temperature": 0.1, "responseMimeType": "application/json"}}
    try:
        resp = _post_with_rotation(url, payload, timeout=60)
        data = json.loads(resp.json()["candidates"][0]["content"]["parts"][0]["text"])
        idx, found = data.get("best_index"), bool(data.get("match_found"))
        if not (found and isinstance(idx, int) and 0 <= idx < len(thumbnails)):
            return None, False
        return idx, True
    except Exception as e:
        print(f"[B-roll] Vision ranking failed: {e}. Continuing waterfall…")
        return None, False
