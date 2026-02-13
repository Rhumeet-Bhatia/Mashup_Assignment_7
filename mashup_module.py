import os
import sys
import shutil
from yt_dlp import YoutubeDL
from pydub import AudioSegment

def create_mashup(singer, n_videos, duration, output_file):

    if n_videos <= 10:
        raise ValueError("Number of videos must be greater than 10")

    if duration <= 20:
        raise ValueError("Duration must be greater than 20 seconds")

    if os.path.exists("audios"):
        shutil.rmtree("audios")

    os.makedirs("audios", exist_ok=True)

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

    with YoutubeDL(ydl_opts) as ydl:
        ydl.download([f"ytsearch{n_videos}:{singer} songs"])

    clips = []

    for file in os.listdir("audios"):
        if file.endswith(".mp3"):
            path = os.path.join("audios", file)
            audio = AudioSegment.from_file(path)

            if len(audio) < duration * 1000:
                continue

            clip = audio[: duration * 1000]
            clips.append(clip)

    if not clips:
        raise Exception("No valid clips found")

    final = AudioSegment.empty()

    for c in clips:
        final += c

    final.export(output_file, format="mp3")

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

        create_mashup(singer, n_videos, duration, output_file)
        print("Mashup created successfully")

    except Exception as e:
        print("Error:", e)
