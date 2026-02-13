import os
import sys
import shutil
from yt_dlp import YoutubeDL
from pydub import AudioSegment
from pydub.exceptions import CouldntDecodeError

def create_mashup(singer, n_videos, duration, output_file):

    if not isinstance(singer, str) or not singer.strip():
        raise ValueError("Singer name cannot be empty")

    if not isinstance(n_videos, int) or n_videos <= 10:
        raise ValueError("Number of videos must be greater than 10")

    if not isinstance(duration, int) or duration <= 20:
        raise ValueError("Duration must be greater than 20 seconds")

    if not output_file.lower().endswith(".mp3"):
        raise ValueError("Output file must be .mp3")

    try:
        if os.path.exists("audios"):
            shutil.rmtree("audios")
        os.makedirs("audios", exist_ok=True)
    except Exception as e:
        raise RuntimeError(f"Failed to prepare working directory: {e}")

    ydl_opts = {
        "format": "bestaudio[ext=m4a]/bestaudio",
        "outtmpl": "audios/%(id)s.%(ext)s",
        "quiet": True,
        "noplaylist": True,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
        }]
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([f"ytsearch{n_videos}:{singer} songs"])
    except Exception as e:
        raise RuntimeError(f"YouTube download failed: {e}")

    clips = []

    try:
        files = os.listdir("audios")
    except Exception:
        raise RuntimeError("Audio folder not accessible")

    if not files:
        raise RuntimeError("No videos found for this singer")

    for file in files:
        if file.endswith(".mp3"):
            path = os.path.join("audios", file)
            try:
                audio = AudioSegment.from_file(path)
            except CouldntDecodeError:
                continue
            except Exception as e:
                raise RuntimeError(f"Audio decoding error: {e}")

            if len(audio) < duration * 1000:
                continue

            clip = audio[: duration * 1000]
            clips.append(clip)

    if not clips:
        raise RuntimeError("No valid clips found after trimming")

    try:
        final = AudioSegment.empty()
        for c in clips:
            final += c
    except Exception as e:
        raise RuntimeError(f"Audio merge failed: {e}")

    try:
        final.export(output_file, format="mp3")
    except Exception as e:
        raise RuntimeError(f"Export failed (ffmpeg issue?): {e}")

    return output_file


if __name__ == "__main__":

    if len(sys.argv) != 5:
        print("Usage: python mashup.py <SingerName> <NumberOfVideos> <AudioDuration> <OutputFileName>")
        sys.exit(1)

    try:
        singer = sys.argv[1]
        n_videos = int(sys.argv[2])
        duration = int(sys.argv[3])
        output_file = sys.argv[4]

        result = create_mashup(singer, n_videos, duration, output_file)
        print("Mashup created successfully:", result)

    except ValueError as ve:
        print("Input Error:", ve)

    except RuntimeError as re:
        print("Processing Error:", re)

    except Exception as e:
        print("Unexpected Error:", e)
