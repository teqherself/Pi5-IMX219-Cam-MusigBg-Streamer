# GENDEMIK DIGITAL

## LOFI STREAMER — GENBOT IMX219 FIFO LTS

**Release Candidate (RC) — v8.7.29**

---

## 1. Overview

The **GENBOT LOFI STREAMER (RC v8.7.29)** is a production-ready, long-duration RTMP streaming system designed for **continuous 24/7 operation** on Raspberry Pi hardware.

This release candidate focuses on:

* Stability over extended uptime
* Deterministic video/audio pipeline behaviour
* Automatic recovery from runtime faults
* Safe overlay rendering using atomic file operations

---

## 2. System Architecture

```
Picamera2 (IMX219)
        │
        ▼
H264 FIFO (/tmp/camfifo.h264)

MP3 Playlist
        │
        ▼
PCM FIFO (/tmp/lofi_audio.pcm)

        ▼
      FFmpeg
 (composition + encoding)

        ▼
      RTMP
 (YouTube / Restream)
```

---

## 3. Key Features

### Video Pipeline

* Resolution: **1280×720**
* Frame rate: **25 FPS (CFR)**
* Encoder: **libx264 (baseline profile)**
* Stable GOP structure (2 seconds)

### Audio Pipeline

* MP3 playlist ingestion
* Real-time PCM conversion
* Continuous playback with seamless transitions

### Overlay System

* Timestamp (top-left)
* Now Playing (bottom-right)
* Mesh Chat (bottom-left)
* PNG Logo (top-right)
* Gaussian blur region for protected UI zones

All overlays use **atomic file replacement** to prevent FFmpeg memory faults.

---

## 4. Stability Improvements (RC)

This release introduces critical fixes for long-term reliability:

* Eliminates FFmpeg **SIGBUS crashes** from text overlays
* Prevents **stderr pipe blocking** (long uptime freeze)
* Adds **FFmpeg progress monitoring**
* Implements **automatic pipeline restart**
* Detects and recovers from:

  * RTMP disconnects
  * network loss
  * stalled encoding output
* Improves FIFO handling and thread queue resilience

---

## 5. Dashboard (In Development)

A **standalone web-based dashboard** is currently in active development as part of the GENBOT ecosystem.

### Planned Capabilities

* Real-time streamer status (CPU, RAM, uptime, temperature)
* Service control (start / stop / restart)
* Live log viewing (FFmpeg + systemd)
* Network diagnostics
* Stream configuration editor
* Overlay management (Now Playing / Mesh / text)
* Meshtastic integration (chat + node status)
* AI-assisted interaction layer

### Architecture

* Flask-based web application
* Runs independently from the streamer process
* Communicates via:

  * systemd service state
  * local files (`/tmp/*.txt`)
  * system metrics (psutil)

### Design Goals

* Non-breaking: dashboard failure must **never interrupt streaming**
* Appliance-style UI (clean, always-on display)
* Remote access capable (LAN / secure WAN)

> ⚠️ The dashboard is not required for operation and is **not included in this release candidate**.
> The streamer is fully standalone and production-capable without it.

---

## 6. System Requirements

### Hardware

* Raspberry Pi 4 or 5 (recommended)
* IMX219 camera module
* Stable network connection (Ethernet recommended)

### OS

* Raspberry Pi OS (Bookworm)

### Software

```bash
sudo apt update
sudo apt install -y \
  ffmpeg \
  python3-pip \
  python3-venv \
  python3-libcamera \
  libcamera-apps \
  git
```

---

## 7. Python Environment Setup

```bash
python3 -m venv ~/lofi-venv
source ~/lofi-venv/bin/activate
pip install picamera2
```

---

## 8. Installation

```bash
mkdir -p ~/LofiStream/{Servers,Sounds,Logo,Logs}
cd ~/LofiStream
```

### Required Files

| File               | Location                      |
| ------------------ | ----------------------------- |
| `lofi-streamer.py` | `~/LofiStream/Servers/`       |
| MP3 files          | `~/LofiStream/Sounds/`        |
| Logo image         | `~/LofiStream/Logo/picam.png` |
| Stream URL         | `~/LofiStream/stream_url.txt` |

---

## 9. Stream Configuration

```bash
nano ~/LofiStream/stream_url.txt
```

Example:

```
rtmp://a.rtmp.youtube.com/live2/YOUR_STREAM_KEY
```

---

## 10. Running (Manual Test)

```bash
cd ~/LofiStream/Servers
source ~/lofi-venv/bin/activate
python3 lofi-streamer.py
```

---

## 11. systemd Service Setup

```bash
sudo nano /etc/systemd/system/woobot-streamer.service
```

```
[Unit]
Description=GENBOT LTS Lofi Streamer (IMX219 FIFO)
After=network-online.target
Wants=network-online.target

[Service]
User=woo
Group=video
WorkingDirectory=/home/woo/LofiStream/Servers
ExecStart=/home/woo/lofi-venv/bin/python3 /home/woo/LofiStream/Servers/lofi-streamer.py

Restart=always
RestartSec=5

KillMode=control-group
TimeoutStopSec=120

Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

---

## 12. Enable & Start

```bash
sudo systemctl daemon-reexec
sudo systemctl daemon-reload
sudo systemctl enable woobot-streamer
sudo systemctl start woobot-streamer
```

---

## 13. Monitoring

```bash
journalctl -u woobot-streamer -f
```

Log file:

```
~/LofiStream/Logs/ffmpeg-stream.log
```

---

## 14. Runtime Files

```
/tmp/
├── camfifo.h264
├── lofi_audio.pcm
├── timestamp.txt
├── nowplaying.txt
├── mesh-chat.txt
├── ffmpeg-progress.txt
```

---

## 15. Encoding Configuration

| Parameter  | Value    |
| ---------- | -------- |
| Resolution | 1280×720 |
| FPS        | 25       |
| GOP        | 50       |
| Bitrate    | 2600k    |
| Maxrate    | 3400k    |
| Buffer     | 6800k    |
| Audio      | AAC 128k |

---

## 16. Camera Behaviour

* Auto Exposure: Enabled
* Auto Gain: Enabled
* Auto White Balance: Enabled
* Format: YUV420 (Rec709)

---

## 17. Known Limitations

* Increased noise in low-light conditions
* No HDR processing
* Dependent on RTMP ingest stability

---

## 18. Release Status

**Release Candidate**

* Stable for long-duration testing
* Suitable for production validation
* Pending final LTS lock

---

## 19. Future Enhancements

* Dynamic exposure profiles (day/night)
* Dashboard integration (see Section 5)
* Overlay configuration UI
* Telemetry and health metrics

---

## 20. Support & Maintenance

* Validate changes before deployment:

  ```bash
  python3 -m py_compile lofi-streamer.py
  ```
* Avoid structural pipeline changes in production
* Apply incremental updates only

---

**GENDEMIK DIGITAL — Streaming Systems Engineering**
