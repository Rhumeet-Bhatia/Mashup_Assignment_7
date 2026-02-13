import sys
from mashup_module import create_mashup

def main(argv):
    if len(argv) != 5:
        print("usage: python <RollNumber>.py \"Singer\" NumberOfVideos DurationSeconds output.mp3")
        return
    singer = argv[1]
    try:
        n = int(argv[2])
        d = int(argv[3])
    except Exception:
        print("n and duration must be integers")
        return
    out = argv[4]
    try:
        res = create_mashup(singer, n, d, out, log_fn=print)
        print("completed", res)
    except Exception as e:
        print("error", str(e))

if __name__ == "__main__":
    main(sys.argv)
