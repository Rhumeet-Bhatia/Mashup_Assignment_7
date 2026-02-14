import os
import uuid
import zipfile
import threading
import tempfile
import shutil
import smtplib
from flask import Flask, request, jsonify, render_template
from email.message import EmailMessage
from yt_dlp import YoutubeDL
from pydub import AudioSegment

from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)

SMTP_EMAIL = "rbhatia_be23@thapar.edu"
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

jobs = {}

def send_email(receiver, file_path):

    try:
        msg = EmailMessage()
        msg["Subject"] = "Mashup File"
        msg["From"] = SMTP_EMAIL
        msg["To"] = receiver
        msg.set_content("Mashup attached")

        with open(file_path, "rb") as f:
            msg.add_attachment(
                f.read(),
                maintype="application",
                subtype="zip",
                filename=os.path.basename(file_path)
            )

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            server.send_message(msg)

        print("Email sent")

    except Exception as e:
        print("Email error:", e)


def mashup_worker(job_id, singer, n_videos, duration, email):

    jobs[job_id] = {"status":"searching","percent":5,"message":"Searching videos"}

    tmp = tempfile.mkdtemp(prefix="mashup_")
    audios = os.path.join(tmp,"audios")
    os.makedirs(audios,exist_ok=True)

    try:

        ydl_opts = {
            "format":"bestaudio[ext=m4a]/bestaudio",
            "outtmpl":os.path.join(audios,"%(id)s.%(ext)s"),
            "quiet":True,
            "noplaylist":True,
            "postprocessors":[{
                "key":"FFmpegExtractAudio",
                "preferredcodec":"mp3"
            }]
        }

        jobs[job_id].update({"status":"downloading","percent":20,"message":"Downloading audio"})

        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([f"ytsearch{n_videos}:{singer} songs"])

        jobs[job_id].update({"status":"processing","percent":60,"message":"Processing audio"})

        clips=[]
        for f in os.listdir(audios):
            if f.endswith(".mp3"):
                path=os.path.join(audios,f)
                audio=AudioSegment.from_file(path)
                if len(audio)>=duration*1000:
                    clips.append(audio[:duration*1000])

        final=AudioSegment.empty()
        for c in clips:
            final+=c

        os.makedirs("outputs",exist_ok=True)
        mp3_path=f"outputs/{job_id}.mp3"
        final.export(mp3_path,format="mp3")

        zip_path=f"outputs/{job_id}.zip"

        with zipfile.ZipFile(zip_path,"w") as z:
            z.write(mp3_path,arcname="mashup.mp3")

        jobs[job_id].update({"status":"email","percent":90,"message":"Sending email"})

        threading.Thread(target=send_email,args=(email,zip_path),daemon=True).start()

        jobs[job_id].update({"status":"done","percent":100,"message":"Completed"})

    except Exception as e:
        jobs[job_id].update({"status":"error","percent":100,"message":str(e)})

    finally:
        shutil.rmtree(tmp,ignore_errors=True)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/create",methods=["POST"])
def create():

    singer=request.form["singer"]
    email=request.form["email"]
    n_videos=int(request.form["n_videos"])
    duration=int(request.form["duration"])

    if n_videos<=10 or duration<=20:
        return jsonify({"error":"Invalid parameters"})

    job_id=str(uuid.uuid4())

    threading.Thread(
        target=mashup_worker,
        args=(job_id,singer,n_videos,duration,email),
        daemon=True
    ).start()

    return jsonify({"job_id":job_id})


@app.route("/progress/<job_id>")
def progress(job_id):
    return jsonify(jobs.get(job_id,{}))


if __name__=="__main__":
    app.run(host="0.0.0.0",port=5000)
