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

app = Flask(__name__)

SMTP_EMAIL = "rbhatia_be23@thapar.edu"
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

jobs = {}

def send_email(receiver, file_path):
    try:
        if not receiver or "@" not in receiver or "." not in receiver:
            raise ValueError("Invalid receiver email")

        if not os.path.exists(file_path):
            raise FileNotFoundError("Attachment file missing")

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

        with smtplib.SMTP("smtp.gmail.com", 587, timeout=60) as server:
            server.starttls()
            if not SMTP_PASSWORD:
                raise RuntimeError("SMTP password not configured")
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

        if not singer or not singer.strip():
            raise ValueError("Singer name empty")

        if not isinstance(n_videos,int) or n_videos<=10:
            raise ValueError("Invalid number of videos")

        if not isinstance(duration,int) or duration<=20:
            raise ValueError("Invalid duration")

        ydl_opts = {
            "format": "bestaudio[ext=m4a]/bestaudio",
            "outtmpl": os.path.join(audios, "%(id)s.%(ext)s"),
            "quiet": True,
            "noplaylist": True,
            "extract_flat": False,
            "http_headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                "Accept-Language": "en-US,en;q=0.9"
            },
            "sleep_interval": 2,
            "max_sleep_interval": 5,
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3"
            }]
        }

        jobs[job_id].update({"status":"downloading","percent":20,"message":"Downloading audio"})

        try:
            with YoutubeDL(ydl_opts) as ydl:
            query = f"ytsearch{n_videos}:{singer} official audio"
            ydl.download([query])
        except Exception as e:
            raise RuntimeError(f"Download failed: {e}")

        jobs[job_id].update({"status":"processing","percent":60,"message":"Processing audio"})

        try:
            files=os.listdir(audios)
        except Exception:
            raise RuntimeError("Audio folder inaccessible")

        if not files:
            raise RuntimeError("No videos found for this singer")

        trimmed=[]

        for f in files:
            if f.endswith(".mp3"):
                inp=os.path.join(audios,f)
                out=os.path.join(audios,"trim_"+f)
                cmd=f'ffmpeg -y -i "{inp}" -t {duration} -vn "{out}"'
                ret=os.system(cmd)
                if ret==0 and os.path.exists(out):
                    trimmed.append(out)

        if not trimmed:
            raise RuntimeError("No valid clips generated")

        list_file=os.path.join(audios,"list.txt")

        with open(list_file,"w") as lf:
            for t in trimmed:
                lf.write(f"file '{os.path.abspath(t)}'\n")

        os.makedirs("outputs",exist_ok=True)

        mp3_path=f"outputs/{job_id}.mp3"

        merge_cmd=f'ffmpeg -y -f concat -safe 0 -i "{list_file}" -c copy "{mp3_path}"'
        if os.system(merge_cmd)!=0:
            raise RuntimeError("Audio merge failed")

        zip_path=f"outputs/{job_id}.zip"

        try:
            with zipfile.ZipFile(zip_path,"w") as z:
                z.write(mp3_path,arcname="mashup.mp3")
        except Exception as e:
            raise RuntimeError(f"ZIP creation failed: {e}")

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
    try:
        singer=request.form.get("singer","").strip()
        email=request.form.get("email","").strip()
        n_videos=int(request.form.get("n_videos",0))
        duration=int(request.form.get("duration",0))

        if not singer:
            return jsonify({"status":"error","percent":100,"message":"Singer required"})

        if "@" not in email or "." not in email:
            return jsonify({"status":"error","percent":100,"message":"Invalid email"})

        if n_videos<=10 or duration<=20:
            return jsonify({"status":"error","percent":100,"message":"Invalid parameters"})

        job_id=str(uuid.uuid4())

        threading.Thread(
            target=mashup_worker,
            args=(job_id,singer,n_videos,duration,email),
            daemon=True
        ).start()

        return jsonify({"job_id":job_id})

    except Exception as e:
        return jsonify({"status":"error","percent":100,"message":str(e)})


@app.route("/progress/<job_id>")
def progress(job_id):
    return jsonify(jobs.get(job_id,{}))


if __name__=="__main__":
    app.run(host="0.0.0.0",port=5000)
