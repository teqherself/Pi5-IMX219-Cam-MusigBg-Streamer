# Lofi Streamer (IMX219 FIFO LTS)

**Release Candidate v8.7.29**

---

## Overview

Lofi Streamer is a **resilient RTMP streaming application** designed for continuous, unattended operation on Raspberry Pi systems using the libcamera stack.

It provides a deterministic media pipeline with integrated fault recovery, ensuring stable long-duration streaming to platforms such as YouTube or Restream.

---

## Core Capabilities

* Continuous 24/7 streaming operation
* Deterministic video and audio pipelines
* Automatic recovery from stream stalls and failures
* Safe overlay rendering using atomic file updates
* FIFO-based separation of capture and encoding stages

---

## Architecture

```
Camera (Picamera2 / libcamera)
        │
        ▼
H264 FIFO (/tmp/camfifo.h264)

Audio Source (MP3 Playlist)
        │
        ▼
PCM FIFO (/tmp/lofi_audio.pcm)

        ▼
      FFmpeg
 (composition + encoding)

        ▼
      RTMP Output
```

---

## Features

### Video

* 1280×720 resolution
* 25 FPS constant frame rate
* H264 encoding (libx264 baseline profile)
* Fixed GOP structure (2 seconds)

### Audio

* MP3 playlist ingestion
* Real-time PCM conversion
* Continuous playback

### Overlays

* Timestamp
* Now Playing
* Optional mesh/chat text
* Static logo
* Gaussian blur region

All overlays are written using atomic file replacement to prevent memory faults in FFmpeg.

---

## Stability Mechanisms

This release introduces key reliability improvements:

* Prevention of FFmpeg SIGBUS errors from text overlays
* Removal of stderr pipe blocking conditions
* FFmpeg progress monitoring using `-progress` output
* Automatic restart on:

  * encoder stall
  * process exit
  * network loss
* FIFO integrity handling

---

## Supported Hardware

### Supported Cameras (libcamera / Picamera2)

| Camera | Status                               |
| ------ | ------------------------------------ |
| IMX219 | Fully supported (reference platform) |
| IMX477 | Supported                            |
| IMX708 | Supported                            |
| OV5647 | Supported                            |

### Unsupported

| Device      | Reason                                 |
| ----------- | -------------------------------------- |
| USB webcams | Not compatible with Picamera2 pipeline |

---

## Default Camera Configuration

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

* Auto exposure enabled
* Auto gain enabled
* Auto white balance enabled
* Rec709 colour space

---

## Configuration and Adaptation

### Resolution

Default:

```python
(1280, 720)
```

Optional 1080p:

```python
(1920, 1080)
```

Bitrate adjustment required:

```python
VIDEO_BITRATE = "4000k"
VIDEO_MAXRATE = "5000k"
VIDEO_BUFSIZE = "8000k"
```

---

### Low-Light Adjustment (Optional)

```python
controls={
    "FrameRate": 25,
    "AwbEnable": True,
    "ExposureTime": 30000,
    "AnalogueGain": 3.0,
}
```

---

### Camera Variants

* IMX477: may require reduced gain for noise control
* IMX708: optional autofocus configuration
* OV5647: lower performance expected

---

## System Requirements

* Raspberry Pi 4 or 5
* Raspberry Pi OS (Bookworm)
* libcamera-compatible camera module
* Stable network connection

---

## Installation

### System Packages

```bash
sudo apt update
sudo apt install -y ffmpeg python3-venv python3-libcamera libcamera-apps
```

### Python Environment

```bash
python3 -m venv ~/lofi-venv
source ~/lofi-venv/bin/activate
pip install picamera2
```

---

## Project Layout

```
~/LofiStream/
├── Servers/
│   └── lofi-streamer.py
├── Sounds/
│   └── *.mp3
├── Logo/
│   └── picam.png
├── Logs/
│   └── ffmpeg-stream.log
├── stream_url.txt
```

---

## Stream Configuration

Example:

```
rtmp://a.rtmp.youtube.com/live2/YOUR_STREAM_KEY
```

---

## Execution

```bash
cd ~/LofiStream/Servers
source ~/lofi-venv/bin/activate
python3 lofi-streamer.py
```

---

## Service Deployment (systemd)

```
/etc/systemd/system/lofi-streamer.service
```

```ini
[Unit]
Description=Lofi Streamer (IMX219 FIFO)
After=network-online.target

[Service]
User=pi
Group=video
WorkingDirectory=/home/pi/LofiStream/Servers
ExecStart=/home/pi/lofi-venv/bin/python3 /home/pi/LofiStream/Servers/lofi-streamer.py

Restart=always
RestartSec=5

KillMode=control-group
TimeoutStopSec=120

Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

---

## Monitoring

```bash
journalctl -u lofi-streamer -f
```

Log file:

```
~/LofiStream/Logs/ffmpeg-stream.log
```

---

## Runtime Files

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

## Known Limitations

* Low-light noise due to sensor gain
* No HDR processing
* No USB camera support

---

## Release Status

Release Candidate

This version is suitable for:

* extended runtime validation
* controlled production deployment

---

## Validation

```bash
python3 -m py_compile lofi-streamer.py
```

---

## Notes

* Designed for stability over feature complexity
* Avoid structural changes in production deployments
* Apply incremental updates only

---
