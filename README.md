# 🌙 GENDEMIK DIGITAL — LOFI STREAMER (GENBOT LTS)

**Version:** 8.7.29
**Platform:** Raspberry Pi (IMX219 + Picamera2)
**Mode:** FIFO → FFmpeg → RTMP
**Status:** 🔒 LTS BASELINE (WATCHDOG STABLE)

---

## 🧠 Overview

The **GENBOT LOFI STREAMER** is a long-running, self-healing RTMP streaming system designed for 24/7 operation.

It uses:

* 🎥 **Picamera2 (IMX219)** → H264 FIFO
* 🎧 **MP3 playlist** → PCM FIFO
* 🎬 **FFmpeg compositor** → RTMP (YouTube / Restream)
* 🧾 **Textfile overlays (atomic safe)**
* 🛰 **Meshtastic overlay (read-only)**
* 🔁 **Supervisor loop with stall detection + auto-restart**

---

## 🔥 Key Features

### 🎥 Video Pipeline

* 1280×720 @ 25fps
* H264 baseline profile
* CFR locked (YouTube safe)
* Gaussian blur region (HUD safe zone)
* PNG logo overlay (top-right)

### 🎧 Audio Pipeline

* MP3 playlist shuffle
* FIFO-fed raw PCM
* Seamless continuous playback

### 🧾 Overlays

* ⏱ Timestamp (top-left)
* 🎵 Now Playing (bottom-right)
* 🛰 Mesh Chat (bottom-left)

All overlays use:

* **atomic file writes** → prevents FFmpeg SIGBUS crash

---

## 🛡 Stability & Reliability

### ✅ Fixed Issues

* ❌ FFmpeg SIGBUS from textfile mmap → **FIXED**
* ❌ Thread queue blocking → **INCREASED BUFFERS**
* ❌ Silent FFmpeg stall → **WATCHDOG + PROGRESS MONITOR**
* ❌ Long uptime freeze → **stderr pipe fix**
* ❌ RTMP drop with live process → **AUTO RESTART**

---

## 🔁 Watchdog System

The streamer continuously monitors FFmpeg health via:

* `-progress /tmp/ffmpeg-progress.txt`
* `out_time_ms` tracking
* file timestamp freshness

### Restart Triggers:

* FFmpeg exits
* No progress updates
* Output time stops increasing
* Network loss
* FIFO break

---

## 🌐 Network Handling

* Waits for network on boot
* Detects runtime drop
* Rebuilds full pipeline on reconnect

---

## 📁 File Structure

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

## 🧾 Runtime Files (tmp)

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

## ⚙️ Service (systemd)

**Service Name:**

```
woobot-streamer.service
```

### Control:

```bash
sudo systemctl start woobot-streamer
sudo systemctl stop woobot-streamer
sudo systemctl restart woobot-streamer
```

### Logs:

```bash
journalctl -u woobot-streamer -f
```

---

## 🎛 Encoding Settings

| Setting    | Value    |
| ---------- | -------- |
| Resolution | 1280x720 |
| FPS        | 25       |
| GOP        | 50       |
| Bitrate    | 2600k    |
| Maxrate    | 3400k    |
| Bufsize    | 6800k    |
| Audio      | AAC 128k |

---

## 🎨 Image Processing

* YUV420 pipeline (Rec709)
* Saturation reduced:

  ```
  eq=saturation=0.88
  ```
* Gaussian blur:

  ```
  crop → gblur → overlay
  ```

---

## 🎥 Camera Behaviour

* Auto Exposure ✅
* Auto Gain ✅
* Auto White Balance ✅
* No manual colour overrides

---

## ⚠️ Known Trade-offs

| Behaviour                   | Reason                     |
| --------------------------- | -------------------------- |
| Slight desaturation         | Lofi aesthetic             |
| Possible noise in low light | Auto gain                  |
| No HDR                      | Streaming latency priority |

---

## 🚀 Recommended Usage

* 24/7 YouTube lofi stream
* Ambient cam overlays
* Mesh-based chat visualisation
* Headless Pi appliance deployments

---

## 🧠 Future Expansion

* 🌗 Day/Night auto profile switching
* 🎛 Dashboard exposure controls
* 🧠 AI-triggered scene modes
* 🛰 Mesh-triggered overlays
* 🎙 Voice / TTS integration

---

## 🔒 LTS Policy

This version is **LOCKED BASELINE**.

Only allow:

* targeted fixes
* non-breaking additions

Do NOT:

* refactor pipeline
* change encoding structure
* alter overlay chain

---

## 👤 GENDEMIK DIGITAL

> Built for persistence.
> Designed for signal stability.
> Running where others drop.

---
