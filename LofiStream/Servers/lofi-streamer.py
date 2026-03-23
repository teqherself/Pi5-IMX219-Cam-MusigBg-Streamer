#!/usr/bin/env python3
"""
---------------------------------------------------------
 8.7.29-gaussian-sigbusfix + MESH OVERLAY + STALL FIX

 LOFI STREAMER — IMX219 FIFO LTS
 GENDEMIK DIGITAL
---------------------------------------------------------

FIXES APPLIED:
- Atomic writes for drawtext textfile inputs to stop FFmpeg SIGBUS (-7)
- FFmpeg stderr no longer piped unread
- FFmpeg progress heartbeat monitoring
- Automatic FFmpeg/camera restart on dead stream / stalled output
- Runtime network recovery loop
- -nostdin for safe background FFmpeg operation
- Clean child-process termination for track FFmpeg workers

KEPT UNCHANGED:
- IMX219 colour handling
- AWB behaviour
- Gaussian blur region
- Logo overlay position
- Mesh overlay position
---------------------------------------------------------
"""

import os
import time
import random
import socket
import signal
import threading
import subprocess
from pathlib import Path

from picamera2 import Picamera2
from picamera2.encoders import H264Encoder
from picamera2.outputs import FileOutput


# ===================== CONFIG =====================

VERSION = "8.7.29-imx219-fifo-lts-gaussian-sigbusfix-mesh-watchdog"

WIDTH = 1280
HEIGHT = 720
FPS = 25
GOP = FPS * 2

VIDEO_BITRATE = "2600k"
VIDEO_MAXRATE = "3400k"
VIDEO_BUFSIZE = "6800k"
AUDIO_BITRATE = "128k"

SATURATION = "0.88"

# ---- Gaussian blur region ----
BLUR_W = 250
BLUR_H = 160
BLUR_X = 430
BLUR_Y = 60
BLUR_SIGMA = 4

# ---- Watchdog / recovery ----
NETWORK_CHECK_HOST = "1.1.1.1"
NETWORK_CHECK_PORT = 53
NETWORK_CHECK_TIMEOUT = 3
FFMPEG_STARTUP_GRACE = 25
STALL_TIMEOUT = 90
SUPERVISOR_POLL = 2
RESTART_BACKOFF = 4

BASE_DIR = Path(__file__).resolve().parent.parent
PLAYLIST_DIR = BASE_DIR / "Sounds"
LOGO_FILE = BASE_DIR / "Logo" / "picam.png"
STREAM_URL_FILE = BASE_DIR / "stream_url.txt"
LOG_DIR = BASE_DIR / "Logs"

CAM_FIFO = Path("/tmp/camfifo.h264")
AUDIO_FIFO = Path("/tmp/lofi_audio.pcm")

NOWPLAYING_FILE = Path("/tmp/nowplaying.txt")
TIMESTAMP_FILE = Path("/tmp/timestamp.txt")
MESH_CHAT_FILE = Path("/tmp/mesh-chat.txt")
PROGRESS_FILE = Path("/tmp/ffmpeg-progress.txt")

FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FFMPEG_LOG = LOG_DIR / "ffmpeg-stream.log"


# ===================== LOG =====================

def log(msg: str) -> None:
    print(msg, flush=True)


# ===================== VALIDATION =====================

def validate_files() -> None:
    errors = []

    if not PLAYLIST_DIR.exists() or not any(PLAYLIST_DIR.iterdir()):
        errors.append(f"Playlist directory empty or missing: {PLAYLIST_DIR}")

    if not LOGO_FILE.exists():
        errors.append(f"Logo file missing: {LOGO_FILE}")

    if not STREAM_URL_FILE.exists():
        errors.append(f"Stream URL file missing: {STREAM_URL_FILE}")

    if not Path(FONT).exists():
        errors.append(f"Font file missing: {FONT}")

    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        errors.append(f"Failed to create log directory {LOG_DIR}: {e}")

    for optional_file in (NOWPLAYING_FILE, TIMESTAMP_FILE, MESH_CHAT_FILE, PROGRESS_FILE):
        try:
            optional_file.touch(exist_ok=True)
        except Exception:
            pass

    if errors:
        for err in errors:
            log(f"❌ {err}")
        raise FileNotFoundError("Required files missing")

    log("✅ All required files validated")


# ===================== NETWORK =====================

def network_up() -> bool:
    try:
        conn = socket.create_connection(
            (NETWORK_CHECK_HOST, NETWORK_CHECK_PORT),
            timeout=NETWORK_CHECK_TIMEOUT
        )
        conn.close()
        return True
    except OSError:
        return False


def wait_for_network(stop: threading.Event | None = None) -> bool:
    log("🌐 Waiting for network...")
    while True:
        if stop is not None and stop.is_set():
            return False
        if network_up():
            log("✅ Network available")
            return True
        time.sleep(2)


# ===================== FIFO =====================

def mkfifo_safe(p: Path) -> None:
    try:
        if p.exists():
            if p.is_fifo():
                return
            p.unlink()
    except Exception:
        pass

    try:
        os.mkfifo(p, 0o666)
    except FileExistsError:
        pass


def ensure_fifos() -> None:
    mkfifo_safe(CAM_FIFO)
    mkfifo_safe(AUDIO_FIFO)


# ===================== TRACKS =====================

def valid_track(p: Path) -> bool:
    try:
        return p.is_file() and p.suffix.lower() == ".mp3" and p.stat().st_size > 100_000
    except Exception:
        return False


def shuffled_tracks():
    tracks = [p for p in PLAYLIST_DIR.iterdir() if valid_track(p)]
    random.shuffle(tracks)
    return tracks


# ===================== ATOMIC TEXTFILE WRITES =====================

write_lock = threading.Lock()


def safe_write(filepath: Path, content: str) -> None:
    tmp = filepath.with_name("." + filepath.name + ".tmp")
    data = content.rstrip("\n") + "\n"

    with write_lock:
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, filepath)
        except Exception:
            try:
                if tmp.exists():
                    tmp.unlink()
            except Exception:
                pass


def timestamp_writer(stop: threading.Event) -> None:
    while not stop.is_set():
        safe_write(TIMESTAMP_FILE, time.strftime("%Y-%m-%d %H:%M:%S"))
        time.sleep(1)


# ===================== PROCESS HELPERS =====================

def kill_process_group(proc: subprocess.Popen | None, sig=signal.SIGTERM, wait_sec: int = 5) -> None:
    if proc is None:
        return

    try:
        pgid = os.getpgid(proc.pid)
    except Exception:
        pgid = None

    try:
        if pgid is not None:
            os.killpg(pgid, sig)
        else:
            proc.send_signal(sig)
    except Exception:
        pass

    deadline = time.time() + wait_sec
    while time.time() < deadline:
        if proc.poll() is not None:
            return
        time.sleep(0.2)

    try:
        if pgid is not None:
            os.killpg(pgid, signal.SIGKILL)
        else:
            proc.kill()
    except Exception:
        pass


# ===================== AUDIO =====================

def audio_feeder(stop: threading.Event) -> None:
    while not stop.is_set():
        tracks = shuffled_tracks()
        if not tracks:
            safe_write(NOWPLAYING_FILE, "No valid tracks")
            time.sleep(5)
            continue

        try:
            with open(AUDIO_FIFO, "wb", buffering=0) as fifo:
                for track in tracks:
                    if stop.is_set():
                        break

                    safe_write(NOWPLAYING_FILE, track.stem)
                    log(f"🎧 Now playing: {track.stem}")

                    p = None
                    try:
                        p = subprocess.Popen(
                            [
                                "ffmpeg",
                                "-hide_banner",
                                "-loglevel", "quiet",
                                "-nostdin",
                                "-re",
                                "-i", str(track),
                                "-vn",
                                "-f", "s16le",
                                "-ar", "44100",
                                "-ac", "2",
                                "pipe:1",
                            ],
                            stdout=fifo,
                            stderr=subprocess.DEVNULL,
                            stdin=subprocess.DEVNULL,
                            preexec_fn=os.setsid,
                        )

                        while p.poll() is None and not stop.is_set():
                            time.sleep(0.5)

                        if stop.is_set() and p.poll() is None:
                            kill_process_group(p)

                    except BrokenPipeError:
                        log("⚠️ Audio FIFO broken; waiting for pipeline rebuild")
                        if p is not None and p.poll() is None:
                            kill_process_group(p)
                        time.sleep(1)
                        break

                    except Exception as e:
                        log(f"⚠️ audio_feeder track error: {e}")
                        if p is not None and p.poll() is None:
                            kill_process_group(p)
                        time.sleep(1)

        except Exception:
            time.sleep(1)


# ===================== CAMERA =====================

def start_camera():
    log("📷 Starting camera...")
    cam = Picamera2()

    cfg = cam.create_video_configuration(
        main={"size": (WIDTH, HEIGHT), "format": "YUV420"},
        controls={
            "FrameRate": FPS,
            "AwbEnable": True,
        },
    )

    cam.configure(cfg)

    encoder = H264Encoder(
        bitrate=int(VIDEO_BITRATE[:-1]) * 1000,
        profile="baseline",
        repeat=True,
        framerate=FPS,
        iperiod=GOP,
    )

    cam.start_recording(encoder, FileOutput(str(CAM_FIFO)))
    log("✅ Camera started")
    return cam


def stop_camera(cam) -> None:
    if cam is None:
        return

    try:
        log("🛑 Stopping camera...")
        cam.stop_recording()
    except Exception:
        pass

    try:
        cam.close()
    except Exception:
        pass


# ===================== FFMPEG =====================

def build_filter_chain() -> str:
    return (
        f"[2:v]format=yuva420p,scale=iw:ih[logo];"
        f"[0:v]format=yuv420p,eq=saturation={SATURATION},split=2[base][blur];"
        f"[blur]crop={BLUR_W}:{BLUR_H}:{BLUR_X}:{BLUR_Y},gblur=sigma={BLUR_SIGMA}[blurred];"
        f"[base][blurred]overlay={BLUR_X}:{BLUR_Y}[v1];"
        f"[v1][logo]overlay=W-w-40:40:format=yuv420[v2];"
        f"[v2]drawtext=fontfile={FONT}:textfile='{TIMESTAMP_FILE}':reload=1:"
        f"x=40:y=40:fontsize=20:fontcolor=white:borderw=2:bordercolor=black[v3];"
        f"[v3]drawtext=fontfile={FONT}:textfile='{NOWPLAYING_FILE}':reload=1:"
        f"x=w-tw-40:y=h-th-40:fontsize=20:fontcolor=white:borderw=2:bordercolor=black[v4];"
        f"[v4]drawtext=fontfile={FONT}:textfile='{MESH_CHAT_FILE}':reload=1:"
        f"x=40:y=h-th-40:fontsize=20:line_spacing=6:"
        f"fontcolor=white:borderw=2:bordercolor=black[vout]"
    )


def build_stream_url(raw_url: str) -> str:
    url = raw_url.strip()
    if not url:
        raise ValueError("stream_url.txt is empty")

    if "tcp_keepalive=1" not in url:
        if "?" in url:
            url += "&tcp_keepalive=1"
        else:
            url += "?tcp_keepalive=1"

    return url


def start_ffmpeg(url: str):
    q = "16384"

    try:
        if PROGRESS_FILE.exists():
            PROGRESS_FILE.unlink()
    except Exception:
        pass

    logf = open(FFMPEG_LOG, "ab", buffering=0)

    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel", "warning",
        "-nostdin",

        "-fflags", "+nobuffer",
        "-flags", "low_delay",
        "-flush_packets", "1",

        "-thread_queue_size", q,
        "-f", "h264",
        "-i", str(CAM_FIFO),

        "-thread_queue_size", q,
        "-f", "s16le",
        "-ar", "44100",
        "-ac", "2",
        "-i", str(AUDIO_FIFO),

        "-loop", "1",
        "-framerate", str(FPS),
        "-i", str(LOGO_FILE),

        "-progress", str(PROGRESS_FILE),
        "-stats_period", "5",

        "-filter_complex", build_filter_chain(),
        "-map", "[vout]",
        "-map", "1:a",

        "-c:v", "libx264",
        "-preset", "veryfast",
        "-profile:v", "baseline",
        "-pix_fmt", "yuv420p",

        "-r", str(FPS),
        "-fps_mode", "cfr",
        "-g", str(GOP),
        "-keyint_min", str(GOP),
        "-sc_threshold", "0",

        "-b:v", VIDEO_BITRATE,
        "-maxrate", VIDEO_MAXRATE,
        "-bufsize", VIDEO_BUFSIZE,

        "-c:a", "aac",
        "-b:a", AUDIO_BITRATE,
        "-ar", "44100",

        "-f", "flv",
        url,
    ]

    log("🎥 Starting FFmpeg stream...")

    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=logf,
        preexec_fn=os.setsid,
    )

    proc._log_handle = logf
    proc._started_at = time.time()
    return proc


def stop_ffmpeg(proc) -> None:
    if proc is None:
        return

    kill_process_group(proc)

    try:
        if hasattr(proc, "_log_handle") and proc._log_handle:
            proc._log_handle.close()
    except Exception:
        pass


def parse_progress_file() -> dict:
    if not PROGRESS_FILE.exists():
        return {}

    data = {}
    try:
        with open(PROGRESS_FILE, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if "=" not in line:
                    continue
                k, v = line.split("=", 1)
                data[k.strip()] = v.strip()
    except Exception:
        return {}

    return data


def ffmpeg_is_stalled(proc):
    if proc is None:
        return True, "ffmpeg-missing"

    if proc.poll() is not None:
        return True, f"ffmpeg-exited-{proc.returncode}"

    now = time.time()
    age = now - getattr(proc, "_started_at", now)

    progress = parse_progress_file()

    try:
        mtime = PROGRESS_FILE.stat().st_mtime if PROGRESS_FILE.exists() else 0
    except Exception:
        mtime = 0

    if age < FFMPEG_STARTUP_GRACE:
        return False, "startup-grace"

    if not progress:
        if mtime and (now - mtime) <= STALL_TIMEOUT:
            return False, "progress-file-young"
        return True, "no-progress"

    out_time_ms = progress.get("out_time_ms")
    progress_state = progress.get("progress", "")

    if progress_state == "continue":
        if mtime and (now - mtime) <= STALL_TIMEOUT:
            return False, "progress-advancing"

    if out_time_ms is not None:
        try:
            current = int(out_time_ms)
        except Exception:
            current = None

        prev = getattr(proc, "_last_out_time_ms", None)
        if current is not None:
            if prev is None or current > prev:
                proc._last_out_time_ms = current
                proc._last_progress_seen = now
                return False, "out-time-advanced"

    last_seen = getattr(proc, "_last_progress_seen", None)
    if last_seen is None and mtime:
        proc._last_progress_seen = mtime
        return False, "initial-progress-seen"

    if last_seen is not None and (now - last_seen) > STALL_TIMEOUT:
        return True, "progress-stalled"

    if mtime and (now - mtime) > STALL_TIMEOUT:
        return True, "progress-file-stale"

    return False, "healthy"


# ===================== MAIN =====================

def main() -> None:
    log(f"🌙 LOFI STREAMER {VERSION}")

    validate_files()
    wait_for_network()

    ensure_fifos()

    safe_write(NOWPLAYING_FILE, "Starting...")
    safe_write(TIMESTAMP_FILE, time.strftime("%Y-%m-%d %H:%M:%S"))
    safe_write(MESH_CHAT_FILE, "")

    stop = threading.Event()

    def _handle_signal(*_args):
        log("🛑 Shutdown requested")
        stop.set()

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    threading.Thread(target=timestamp_writer, args=(stop,), daemon=True).start()
    threading.Thread(target=audio_feeder, args=(stop,), daemon=True).start()

    raw_url = STREAM_URL_FILE.read_text(encoding="utf-8").strip()
    url = build_stream_url(raw_url)

    cam = None
    ff = None

    try:
        while not stop.is_set():
            if not network_up():
                log("⚠️ Network lost")

                if ff is not None:
                    stop_ffmpeg(ff)
                    ff = None

                if cam is not None:
                    stop_camera(cam)
                    cam = None

                wait_for_network(stop=stop)
                if stop.is_set():
                    break

                time.sleep(RESTART_BACKOFF)
                continue

            needs_restart = False
            reason = "healthy"

            if ff is None:
                needs_restart = True
                reason = "ffmpeg-not-running"
            else:
                stalled, reason = ffmpeg_is_stalled(ff)
                if stalled:
                    needs_restart = True

            if needs_restart:
                log(f"⚠️ Pipeline rebuild requested: {reason}")

                if ff is not None:
                    stop_ffmpeg(ff)
                    ff = None

                if cam is not None:
                    stop_camera(cam)
                    cam = None

                time.sleep(1)
                ensure_fifos()

                ff = start_ffmpeg(url)
                time.sleep(2)
                cam = start_camera()
                log("✅ Pipeline running")

            time.sleep(SUPERVISOR_POLL)

    finally:
        stop.set()

        if cam is not None:
            stop_camera(cam)

        if ff is not None:
            stop_ffmpeg(ff)

        log("👋 Shutdown complete")


if __name__ == "__main__":
    main()
