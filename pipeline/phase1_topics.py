import os
import json
import subprocess
from pipeline.config import TOPIC_LOG_SIZE
from pipeline.gemini import GeminiClient

def select_topic(format_type: str) -> dict:
    # 1. Load published_topics.json
    topic_log_path = "published_topics.json"
    if os.path.exists(topic_log_path):
        try:
            with open(topic_log_path, "r") as f:
                data = json.load(f)
                published = data.get("topics", [])
        except Exception as e:
            print(f"Warning: Failed to load published topics: {e}. Starting fresh.")
            published = []
    else:
        published = []

    # Get last TOPIC_LOG_SIZE topics
    recent_topics = published[-TOPIC_LOG_SIZE:]
    
    # 2. Build Gemini prompt with grounding
    client = GeminiClient()
    prompt = f"""Generate a list of 5 trending science or engineering topics currently being covered by popular science channels like Kurzgesagt, Veritasium, and Bright Side.
Each topic must be framed as a "What if..." or "How does X actually work" question.

CRITICAL: Do not suggest any topic similar to the following list of recently published topics:
{json.dumps(recent_topics, indent=2)}

You MUST return your response ONLY as a raw JSON array of objects (no markdown blocks, no leading/trailing text).
Each object in the array must contain these exact fields:
- "topic": The name/subject (e.g., "quantum entanglement" or "space elevator")
- "short_hook": An opening question of 8 words or less, using a curiosity-gap style
- "hook_type": One of "curiosity_gap", "contrarian", "time_pressure", "self_identification", "narrative_pull"
- "for_format": Either "short", "long", or "both"
"""

    print("Requesting topics from Gemini with grounding...")
    response_text = client.generate_text(prompt, use_grounding=True, temperature=0.7)
    
    try:
        topics_list = json.loads(response_text, strict=False)
        if not isinstance(topics_list, list):
            raise ValueError("Response is not a JSON list")
    except Exception as e:
        print(f"Error parsing Gemini response: {e}. Raw response: {response_text}")
        # Fallback list if parsing fails
        topics_list = [
            {
                "topic": "Why quantum computers don't melt",
                "short_hook": "How do quantum computers stay cold?",
                "hook_type": "curiosity_gap",
                "for_format": "both"
            },
            {
                "topic": "The real danger of space junk",
                "short_hook": "Is space debris about to trap us?",
                "hook_type": "time_pressure",
                "for_format": "both"
            }
        ]

    # 4. Parse JSON. Pick the first topic that matches format_type
    selected_topic = None
    for item in topics_list:
        item_format = item.get("for_format", "both")
        if item_format == format_type or item_format == "both":
            selected_topic = item
            break
            
    if not selected_topic:
        # Fallback if no matching format is found
        selected_topic = topics_list[0]
        selected_topic["for_format"] = format_type

    print(f"Selected Topic: {selected_topic['topic']}")

    # 5. Update published_topics.json
    published.append(selected_topic["topic"])
    published = published[-TOPIC_LOG_SIZE:]
    
    with open(topic_log_path, "w") as f:
        json.dump({"topics": published}, f, indent=2)

    # Git commit/push is handled by the GitHub Actions workflow step
    # to avoid double-commit race conditions with voice_state.json

    return selected_topic
