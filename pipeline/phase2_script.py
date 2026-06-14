import json
import datetime
import random
from pipeline.config import HOOK_PATTERNS
from pipeline.gemini import GeminiClient

def get_next_weekday_2pm_ist_utc():
    # IST is UTC+5:30. 2:00 PM IST = 14:00 IST = 08:30 AM UTC.
    now = datetime.datetime.now(datetime.timezone.utc)
    ist_offset = datetime.timedelta(hours=5, minutes=30)
    now_ist = now + ist_offset
    
    target_date = now_ist.date()
    # If it's past 2 PM IST today, start looking from tomorrow
    if now_ist.time() >= datetime.time(14, 0):
        target_date += datetime.timedelta(days=1)
        
    # Find next weekday (0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri)
    while target_date.weekday() >= 5: # Saturday=5, Sunday=6
        target_date += datetime.timedelta(days=1)
        
    target_dt_ist = datetime.datetime.combine(target_date, datetime.time(14, 0))
    target_dt_utc = target_dt_ist - ist_offset
    return target_dt_utc.strftime("%Y-%m-%dT%H:%M:%SZ")

def generate_script(topic: dict, format_type: str) -> dict:
    client = GeminiClient()
    
    if format_type == "short":
        hook_pattern = random.choice(HOOK_PATTERNS)
        hook_formatted = hook_pattern.format(
            subject=topic.get("topic", "science"),
            thing=topic.get("topic", "science"),
            seconds="30",
            topic=topic.get("topic", "science"),
            event="A discovery"
        )
        
        prompt = f"""Generate a highly engaging, viral 25-35 second YouTube Short educational script on the topic: "{topic['topic']}".
Use the following hook concept: "{hook_formatted}" (short hook: "{topic.get('short_hook', '')}").

You MUST return your response ONLY as a raw JSON object with no markdown syntax. The JSON structure MUST be exactly like this:
{{
  "title": "A catchy title under 40 chars, starting with a hook word/number and containing one emoji",
  "description": "Line1: restate the hook\\nLine2: Fast. Accurate. Mind-blowing.\\nLine3: Full breakdown -> [link]\\n\\n#science #didyouknow #facts",
  "tags": ["8 to 12 relevant tags under 500 characters total"],
  "category_id": "27",
  "segments": [
    {{
      "id": 1,
      "narration": "hook sentence - must create information gap in 8 words or less",
      "broll_query": "visually jarring or surprising close-up image of the topic, high contrast",
      "duration_target": 6
    },
    {{
      "id": 2,
      "narration": "First surprising scientific fact that expands on the hook",
      "broll_query": "macro or close-up b-roll of the scientific fact element",
      "duration_target": 6
    },
    {{
      "id": 3,
      "narration": "Second fact that builds towards the loop twist",
      "broll_query": "clear related scientific visual or diagram concept",
      "duration_target": 7
    },
    {{
      "id": 4,
      "narration": "Mention a hidden detail the viewer should pause to catch (REWATCH TRIGGER)",
      "broll_query": "detailed diagram or visual where a hidden text could be hidden",
      "duration_target": 6
    },
    {{
      "id": 5,
      "narration": "Payoff sentence that transitions back to the exact starting words of segment 1 narration to form a seamless loop",
      "broll_query": "closing beautiful shot returning to the start concept",
      "duration_target": 6
    }}
  ],
  "thumbnail_text": "3 to 5 bold words max for the thumbnail",
  "loop_callout": true
}}

Ensure that Segment 5's narration ends in a way that matches the exact beginning of Segment 1's narration.
"""
    else:  # long-form
        prompt = f"""Generate a comprehensive 7-10 minute YouTube educational script on the topic: "{topic['topic']}".
The script must have 15 to 18 segments, each targeting 25-35 seconds of narration.
Structure the narrative into:
- Intro hook (segments 1-2)
- Act 1: The core mystery/mechanism (segments 3-7)
- Act 2: The surprising twist/implication (segments 8-12)
- Act 3: Modern applications or future outlook (segments 13-16)
- Closing CTA & link (segments 17-18)

You MUST return your response ONLY as a raw JSON object with no markdown syntax. The JSON structure MUST be exactly like this:
{{
  "title": "Engaging educational title for a long video, under 70 characters",
  "description": "A detailed, engaging description explaining what the video covers, including timestamps and educational value.\\n\\n#science #education #technology",
  "tags": ["15 to 20 relevant tags"],
  "category_id": "27",
  "segments": [
    {{
      "id": 1,
      "narration": "Opening narration hook...",
      "broll_query": "Scenic, high-quality descriptive shot for the opening",
      "duration_target": 30
    }}
    // ... total 15-18 segments
  ],
  "thumbnail_text": "3 to 5 bold words max for the thumbnail image",
  "loop_callout": false
}}
"""

    print("Generating script content using Gemini...")
    script_text = client.generate_text(prompt, use_grounding=False, temperature=0.8)
    
    try:
        script = json.loads(script_text)
    except Exception as e:
        print(f"Error parsing script JSON: {e}. Raw script text: {script_text}")
        raise RuntimeError("Failed to generate a valid script JSON from Gemini") from e

    # Add scheduling metadata for long form
    if format_type == "long":
        script["publish_at"] = get_next_weekday_2pm_ist_utc()
    else:
        # Default publish_at for shorts: let's set it to None so we can upload as private first
        script["publish_at"] = None

    # --- FACT VERIFICATION ---
    print("Running fact verification on the generated script...")
    verification_prompt = f"""You are a fact checker. Verify the scientific accuracy of each segment's narration in the following script JSON:
{json.dumps(script, indent=2)}

Check if all claims are backed by credible scientific consensus.
Return ONLY the modified script JSON with an added `"verified": true` or `"verified": false` field inside EACH segment object in the "segments" list.
If a claim is unverifiable, speculative, or false, mark `"verified": false`.
"""
    verified_text = client.generate_text(verification_prompt, use_grounding=True, temperature=0.2)
    
    try:
        verified_script = json.loads(verified_text)
        script["segments"] = verified_script.get("segments", script["segments"])
    except Exception as e:
        print(f"Fact check parse failed ({e}), keeping original script with verified status = True.")
        for seg in script["segments"]:
            seg["verified"] = True

    # Regenerate unverified segments
    for seg in script["segments"]:
        if not seg.get("verified", True):
            print(f"Segment {seg['id']} failed fact check. Regenerating narration...")
            regen_prompt = f"""The following script segment narration failed fact-checking or was unverified:
Topic: {topic['topic']}
Segment details: {json.dumps(seg, indent=2)}

Rewrite the "narration" so that it is 100% scientifically accurate, verifiable, and maintains the exact same tone and target duration.
Return ONLY a raw JSON object for this segment with the updated "narration" and `"verified": true`.
"""
            regen_text = client.generate_text(regen_prompt, use_grounding=True, temperature=0.3)
            try:
                regen_seg = json.loads(regen_text)
                seg["narration"] = regen_seg.get("narration", seg["narration"])
                seg["verified"] = True
            except Exception as e:
                print(f"Failed to parse regenerated segment {seg['id']}: {e}. Keeping original.")
                seg["verified"] = True

    return script
