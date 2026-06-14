import argparse
import json
import os
import sys
import traceback

from pipeline.config import validate_config
import pipeline.phase1_topics as phase1
import pipeline.phase2_script as phase2
import pipeline.phase3_tts as phase3
import pipeline.phase4_broll as phase4
import pipeline.phase5_captions as phase5
import pipeline.phase6_music as phase6
import pipeline.phase7_assemble as phase7
import pipeline.phase8_thumbnail as phase8

def main():
    parser = argparse.ArgumentParser(description="yt-auto Video Generator")
    parser.add_argument("--format", choices=["short", "long"], required=True, help="Video format to generate")
    args = parser.parse_args()
    
    # 0. Validate Config
    try:
        validate_config()
    except ValueError as val_err:
        print(f"Configuration Error: {val_err}")
        sys.exit(1)
        
    os.makedirs("output", exist_ok=True)
    
    try:
        print(f"[Phase 1] Selecting trending topic for {args.format}...")
        topic = phase1.select_topic(args.format)
        
        print(f"[Phase 2] Generating script for topic: '{topic['topic']}'...")
        script = phase2.generate_script(topic, args.format)
        print(f"Generated title: '{script['title']}'")
        
        print(f"[Phase 3] Generating TTS audio ({len(script['segments'])} segments)...")
        audio_files = phase3.generate_audio(script)
        
        print("[Phase 4] Fetching B-roll media...")
        broll_files = []
        for i, seg in enumerate(script["segments"]):
            broll_file = phase4.fetch_broll(seg["broll_query"], args.format, i)
            broll_files.append(broll_file)
            
        print("[Phase 5] Generating captions with word-level timing...")
        # Pass args.format to customize resolution/style
        captions_ass = phase5.generate_captions(audio_files, script, args.format)
        
        print("[Phase 6] Generating background music...")
        # Determine music duration. Shorts = 35s, Long-form = total duration + padding
        if args.format == "short":
            music_duration = 35
        else:
            # For long-form, calculate total audio duration and pad it
            from pipeline.phase7_assemble import get_wav_duration
            total_audio = sum(get_wav_duration(f) for f in audio_files)
            music_duration = int(total_audio) + 15
            
        music_path = phase6.generate_music(topic["topic"], duration_seconds=music_duration)
        
        print("[Phase 7] Assembling final video with FFmpeg...")
        final_video = phase7.assemble_video(broll_files, audio_files, captions_ass, music_path, script, args.format)
        
        print("[Phase 8] Generating thumbnail...")
        thumbnail = phase8.generate_thumbnail(final_video, script["thumbnail_text"])
        
        # Save metadata for publish step
        metadata_path = "output/metadata.json"
        metadata = {
            "title":       script["title"],
            "description": script["description"],
            "tags":        script["tags"],
            "category_id": script.get("category_id", "27"),
            "publish_at":  script.get("publish_at"),
            "format":      args.format,
            "video_path":  final_video,
            "thumbnail":   thumbnail
        }
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)
            
        print(f"\n✅ Generation complete. Video: {final_video}")
        print("Artifact ready. Trigger the Publish workflow in GitHub mobile app to upload.")
        
    except Exception as err:
        print(f"\n❌ Pipeline failed during execution: {err}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
