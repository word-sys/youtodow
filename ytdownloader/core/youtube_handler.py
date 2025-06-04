# YTDownloaderPro/ytdownloader/core/youtube_handler.py
from pytubefix import YouTube
from pytubefix.exceptions import RegexMatchError, VideoUnavailable, PytubeFixError, AgeRestrictedError

def get_video_info(url):
    """
    Fetches video information from a YouTube URL using pytubefix.

    Returns:
        dict: A dictionary containing video information or an error message.
    """
    try:
        yt = YouTube(url)
        _ = yt.title # Access title to ensure metadata is loaded and video is accessible

        video_info = {
            "success": True,
            "title": yt.title,
            "thumbnail_url": yt.thumbnail_url,
            "streams": {
                "mp4": {
                    "progressive": [],    # resolution strings (e.g., "720p")
                    "adaptive_video": [], # resolution strings (e.g., "1080p (60fps)")
                    "adaptive_audio": []  # abr strings (e.g., "128kbps") - for merging
                },
                "audio_only": [] # list of dicts: {'desc': 'opus (160kbps)', 'itag': 251}
            },
            "pytube_object": yt
        }

        # MP4: Progressive streams (video + audio combined)
        for stream in yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc():
            if stream.resolution and stream.resolution not in video_info["streams"]["mp4"]["progressive"]:
                 video_info["streams"]["mp4"]["progressive"].append(stream.resolution)

        # MP4: Adaptive video-only streams
        for stream in yt.streams.filter(adaptive=True, only_video=True, file_extension='mp4').order_by('resolution').desc():
            res = stream.resolution
            if hasattr(stream, 'is_hdr') and stream.is_hdr:
                res += " HDR"
            if hasattr(stream, 'fps') and stream.fps > 30: # Typically 50 or 60 fps
                 res += f" ({stream.fps}fps)"
            if res and res not in video_info["streams"]["mp4"]["adaptive_video"]:
                video_info["streams"]["mp4"]["adaptive_video"].append(res)

        # MP4: Adaptive audio-only streams (typically m4a, for merging with adaptive video)
        for stream in yt.streams.filter(only_audio=True, file_extension='mp4').order_by('abr').desc():
             if stream.abr and stream.abr not in video_info["streams"]["mp4"]["adaptive_audio"]:
                video_info["streams"]["mp4"]["adaptive_audio"].append(stream.abr)

        # Audio Only (for MP3 conversion target - e.g., webm/opus, m4a/aac)
        # Store as a list of dicts: {'desc': 'opus (160kbps)', 'itag': 251}
        temp_audio_descs_seen = set() # To avoid exact duplicate descriptions
        for stream in yt.streams.filter(only_audio=True).order_by('abr').desc():
            # Try to get a clean mime subtype (opus, aac, etc.)
            mime_subtype = stream.mime_type.split('/')[-1] if stream.mime_type else "unknown"
            desc = f"{mime_subtype} ({stream.abr if stream.abr else 'N/A'})"

            if desc not in temp_audio_descs_seen:
                video_info["streams"]["audio_only"].append({'desc': desc, 'itag': stream.itag})
                temp_audio_descs_seen.add(desc)

        return video_info

    except RegexMatchError:
        return {"success": False, "error": "Invalid YouTube URL format."}
    except VideoUnavailable:
        return {"success": False, "error": "Video is unavailable (private, deleted, or restricted)."}
    except AgeRestrictedError:
        return {"success": False, "error": "Video is age-restricted. This downloader may not support age-restricted content without login."}
    except PytubeFixError as e:
        return {"success": False, "error": f"A Pytubefix error occurred: {str(e)}"}
    except Exception as e:
        import traceback
        print("------ UNEXPECTED ERROR IN YOUTUBE_HANDLER ------")
        traceback.print_exc()
        print("-------------------------------------------------")
        return {"success": False, "error": f"An unexpected critical error occurred: {str(e)}"}


if __name__ == '__main__':
    urls_to_test = {
        "Valid Public": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", # Rick Astley
        "Valid Short": "https://youtu.be/jNQXAC9IVRw", # Me at the zoo
        "Invalid Format": "htp://www.youtube.com/invalid",
        "Unavailable Video": "https://www.youtube.com/watch?v=xxxxxxxxxxx", # Non-existent
        # Add an age-restricted URL if you have one to test, e.g., some game trailers
        # "Age Restricted": "https://www.youtube.com/watch?v=..."
    }

    for name, url in urls_to_test.items():
        print(f"\n--- Testing {name} URL ({url}) ---")
        info = get_video_info(url)
        if info.get("success"):
            print(f"Title: {info['title']}")
            print(f"Thumbnail: {info['thumbnail_url']}")
            print("MP4 Progressive Streams (res):", info["streams"]["mp4"]["progressive"])
            print("MP4 Adaptive Video Streams (res):", info["streams"]["mp4"]["adaptive_video"])
            print("MP4 Adaptive Audio Streams (abr, for merging):", info["streams"]["mp4"]["adaptive_audio"])
            print("Audio Only Streams (for MP3):", info["streams"]["audio_only"])
        else:
            print(f"Error: {info.get('error', 'Unknown error structure')}")
