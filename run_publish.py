import json
import os
import sys
import google.auth.exceptions
import pipeline.phase9_upload as phase9

def main():
    metadata_path = "output/metadata.json"
    if not os.path.exists(metadata_path):
        print(f"Error: Metadata file not found at {metadata_path}. Have you run generation first?")
        sys.exit(1)
        
    with open(metadata_path, "r") as f:
        metadata = json.load(f)
        
    # Extract format and files
    fmt = metadata.get("format", "short")
    video_path = metadata.get("video_path")
    thumbnail_path = metadata.get("thumbnail")
    
    # Resilient path check: if the absolute path from generation doesn't exist,
    # look in the local output/ folder
    if not video_path or not os.path.exists(video_path):
        fallback_video = f"output/final_{fmt}.mp4"
        if os.path.exists(fallback_video):
            video_path = fallback_video
        else:
            print(f"Error: Video file not found. Checked: {video_path} and {fallback_video}")
            sys.exit(1)
            
    if not thumbnail_path or not os.path.exists(thumbnail_path):
        fallback_thumb = "output/thumbnail.jpg"
        if os.path.exists(fallback_thumb):
            thumbnail_path = fallback_thumb
        else:
            print(f"Error: Thumbnail file not found. Checked: {thumbnail_path} and {fallback_thumb}")
            sys.exit(1)
            
    print(f"Publishing {fmt} video...")
    print(f"Video: {video_path}")
    print(f"Thumbnail: {thumbnail_path}")
    print(f"Title: {metadata.get('title')}")
    
    try:
        video_id = phase9.upload_to_youtube(video_path, thumbnail_path, metadata)
        print(f"\n✅ Successfully published to YouTube! Video ID: {video_id}")
        print(f"Direct Link: https://www.youtube.com/watch?v={video_id}")
    except google.auth.exceptions.RefreshError as ref_err:
        print("\n❌ Authentication Error: Refresh token may have expired or is invalid.")
        print("Re-generate your refresh token at: https://developers.google.com/oauthplayground")
        print(f"Details: {ref_err}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Publish failed with error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
