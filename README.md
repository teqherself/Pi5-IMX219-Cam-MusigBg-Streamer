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
* Gaussian blur region

All overlays use **atomic file replacement** to prevent FFmpeg memory faults.

---

## 4. Stability Improvements (RC)

* Eliminates FFmpeg **SIGBUS crashes**
* Prevents **stderr pipe blocking**
* Adds **FFmpeg progress monitoring**
* Automatic pipeline restart
* Network loss recovery
* FIFO resilience improvements

---

## 5. Dashboard (In Development)

A **standalone Flask-based dashboard** is currently in development.

### Planned Features

* Stream status + system metrics
* Start / Stop / Restart controls
* Live logs
* Network diagnostics
* Overlay + config editor
* Meshtastic integration
* AI interaction layer

> The dashboard is optional and **not required for operation**.

---

## 6. Supported Camera Hardware

### ✅ Fully Supported (Tested & Stable)

| Camera             | Status         | Notes                      |
| ------------------ | -------------- | -------------------------- |
| IMX219 (Camera v2) | ✅ LTS BASELINE | Primary reference hardware |
| IMX477 (HQ Camera) | ✅ Supported    | Minor tuning recommended   |
| IMX708 (Camera v3) | ✅ Supported    | Autofocus optional         |
| OV5647 (v1 Camera) | ✅ Supported    | Legacy support             |

---

### ⚠️ Not Supported (Current Build)

| Camera Type               | Status          | Reason                   |
| ------------------------- | --------------- | ------------------------ |
| USB Webcam                | ❌ Not supported | Uses V4L2, not Picamera2 |
| CSI non-libcamera devices | ❌               | Incompatible pipeline    |

---

## 7. Camera Configuration (Current)

```python
cfg = cam.create_video_configuration(
    main={"size": (1280, 720), "format": "YUV420"},
    controls={
        "FrameRate": 25,
        "AwbEnable": True,
    },
)
```

### Behaviour

* Auto Exposure: Enabled
* Auto Gain: Enabled
* Auto White Balance: Enabled
* Format: YUV420 (Rec709)

---

## 8. Adapting for Other Cameras

### 🔧 IMX477 (HQ Camera)

Recommended changes:

```python
main={"size": (1280, 720), "format": "YUV420"}
```

Optional tuning:

```python
controls={
    "FrameRate": 25,
    "AwbEnable": True,
    "AnalogueGain": 1.5,
}
```

---

### 🔧 IMX708 (Camera Module 3)

Optional autofocus enable:

```python
controls={
    "FrameRate": 25,
    "AwbEnable": True,
    "AfMode": 2,
}
```

---

### 🔧 Low Light Optimisation (All Cameras)

```python
controls={
    "FrameRate": 25,
    "AwbEnable": True,
    "ExposureTime": 30000,
    "AnalogueGain": 3.0,
}
```

---

### 🔧 Higher Resolution Mode

```python
main={"size": (1920, 1080), "format": "YUV420"}
```

⚠️ Requires bitrate adjustment:

```python
VIDEO_BITRATE = "4000k"
VIDEO_MAXRATE = "5000k"
VIDEO_BUFSIZE = "8000k"
```

---

## 9. System Requirements

### Hardware

* Raspberry Pi 4 or 5
* IMX219 or supported camera
* Stable network

### OS

* Raspberry Pi OS (Bookworm)

---

## 10. Installation

```bash
sudo apt update
sudo apt install -y ffmpeg python3-venv python3-libcamera libcamera-apps
```

```bash
python3 -m venv ~/lofi-venv
source ~/lofi-venv/bin/activate
pip install picamera2
```

---

## 11. Project Setup

```bash
mkdir -p ~/LofiStream/{Servers,Sounds,Logo,Logs}
```

Place:

* `lofi-streamer.py` → Servers
* `.mp3` files → Sounds
* `picam.png` → Logo
* `stream_url.txt` → root

---

## 12. Stream Configuration

```
rtmp://a.rtmp.youtube.com/live2/YOUR_KEY
```

---

## 13. systemd Service

```ini
[Unit]
Description=GENBOT LTS Lofi Streamer (IMX219 FIFO)
After=network-online.target

[Service]
User=woo
Group=video
WorkingDirectory=/home/woo/LofiStream/Servers
ExecStart=/home/woo/lofi-venv/bin/python3 /home/woo/LofiStream/Servers/lofi-streamer.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

---

## 14. Monitoring

```bash
journalctl -u woobot-streamer -f
```

---

## 15. Encoding Configuration

| Parameter  | Value    |
| ---------- | -------- |
| Resolution | 1280×720 |
| FPS        | 25       |
| GOP        | 50       |
| Bitrate    | 2600k    |
| Audio      | AAC 128k |

---

## 16. Known Limitations

* Low-light noise (sensor gain)
* No HDR
* USB cameras unsupported

---

## 17. Release Status

**Release Candidate**

* Stable for extended runtime testing
* Suitable for production validation

---

## 18. Future Enhancements

* Multi-camera support
* Dashboard integration
* Exposure profiles
* Overlay UI

---

## 19. Support Notes

Before deployment:

```bash
python3 -m py_compile lofi-streamer.py
```

---

**GENDEMIK DIGITAL — Streaming Systems Engineering**
