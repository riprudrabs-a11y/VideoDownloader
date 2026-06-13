<div align="center">

<img src="https://img.shields.io/badge/StreamVault-Premium%20Media%20Downloader-black?style=for-the-badge&logo=youtube&logoColor=white" alt="StreamVault"/>

<br/>
<br/>

[![Python](https://img.shields.io/badge/Python-3.8%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.0.0-000000?style=flat-square&logo=flask&logoColor=white)](https://flask.palletsprojects.com)
[![yt-dlp](https://img.shields.io/badge/yt--dlp-2026.06.09-FF0000?style=flat-square&logo=youtube&logoColor=white)](https://github.com/yt-dlp/yt-dlp)

**A self-hosted, full-stack video downloader web app with a clean UI and 1000+ platform support.**

[Overview](#-overview) • [Features](#-features) • [Quick Start](#-quick-start) • [VPS Deploy](#-vps-deployment) • [Firebase Variant](#-firebase-variant) • [API](#-api-endpoints)

</div>

---

## 📌 Overview

**StreamVault** is a self-hosted media downloader built with **Flask** and **yt-dlp**. Paste any video URL, analyze it, pick your quality, and download — all from a clean web interface. Files are stored for **24 hours** and cleaned up automatically.

> ⚡ Concurrent fragment downloads, 3-method fallback system, and real-time progress tracking.

---

## ✨ Features

| Feature | Description |
|---|---|
| 🎯 **Smart Analyze** | Extracts title, thumbnail & platform info before downloading |
| 🎬 **Quality Options** | Best, HD 720p, Mobile 480p, Audio MP3 |
| 📊 **Real-time Progress** | Live progress bar with download speed |
| 🔁 **Fallback System** | 3-method fallback for failed downloads |
| 🧹 **Auto Cleanup** | Files auto-deleted after 24 hours |
| 📜 **Download History** | Last 10 downloads stored in SQLite |
| 🌐 **1000+ Platforms** | Powered by yt-dlp |
| 🔒 **CORS Enabled** | API-ready with Flask-CORS |
| 🖥️ **Responsive UI** | Clean white & black theme, works on mobile |

---

## 🌐 Supported Platforms

Powered by **yt-dlp** — supports **1000+ sites** out of the box.

| Platform | URLs |
|---|---|
| ![YouTube](https://img.shields.io/badge/YouTube-FF0000?style=flat-square&logo=youtube&logoColor=white) | `youtube.com`, `youtu.be` |
| ![Facebook](https://img.shields.io/badge/Facebook-1877F2?style=flat-square&logo=facebook&logoColor=white) | `facebook.com`, `fb.watch` |
| ![Instagram](https://img.shields.io/badge/Instagram-E4405F?style=flat-square&logo=instagram&logoColor=white) | `instagram.com` — Reels, Stories, Posts |
| ![TikTok](https://img.shields.io/badge/TikTok-000000?style=flat-square&logo=tiktok&logoColor=white) | `tiktok.com`, `vm.tiktok.com` |
| ![Twitter/X](https://img.shields.io/badge/Twitter%2FX-000000?style=flat-square&logo=x&logoColor=white) | `twitter.com`, `x.com` |
| ![Vimeo](https://img.shields.io/badge/Vimeo-1AB7EA?style=flat-square&logo=vimeo&logoColor=white) | `vimeo.com` |
| ![Dailymotion](https://img.shields.io/badge/Dailymotion-0066DC?style=flat-square&logo=dailymotion&logoColor=white) | `dailymotion.com` |
| ![Reddit](https://img.shields.io/badge/Reddit-FF4500?style=flat-square&logo=reddit&logoColor=white) | `reddit.com`, `redd.it` |
| ![Twitch](https://img.shields.io/badge/Twitch-9146FF?style=flat-square&logo=twitch&logoColor=white) | `twitch.tv` — VODs & Clips |
| ![SoundCloud](https://img.shields.io/badge/SoundCloud-FF3300?style=flat-square&logo=soundcloud&logoColor=white) | `soundcloud.com` |
| ![Bilibili](https://img.shields.io/badge/Bilibili-00A1D6?style=flat-square&logo=bilibili&logoColor=white) | `bilibili.com` |
| ![Pinterest](https://img.shields.io/badge/Pinterest-E60023?style=flat-square&logo=pinterest&logoColor=white) | `pinterest.com` |
| + 1000 more | [Full list →](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md) |

---

## 📁 Project Structure

```
VideoDownloader/
├── main.py                   # Flask app — all routes & download logic
├── requirements.txt          # Python dependencies
├── run.sh                    # Linux/Mac startup script
├── run.bat                   # Windows startup script
├── downloads.db              # SQLite DB for download history
├── templates/
│   └── index.html            # Frontend UI (Jinja2)
├── static/
│   ├── css/style.css         # Styling
│   └── js/app.js             # Frontend logic
├── downloads/                # Downloaded files (auto-cleaned after 24h)
├── temp/                     # Temp processing directory
└── Firebase Database/        # Optional Firebase/Firestore variant
    ├── main.py
    ├── requirements.txt
    ├── FIREBASE_SETUP.md
    └── ...
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- `ffmpeg` installed and in PATH

### Local Setup

```bash
# 1. Clone the repo
git clone https://github.com/siambhau/VideoDownloader.git
cd VideoDownloader

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run
```

**Linux / Mac:**
```bash
chmod +x run.sh && ./run.sh
```

**Windows:**
```bash
run.bat
```

**Manual:**
```bash
python main.py
```

Open browser → **http://localhost:5000**

---

## 🖥️ VPS Deployment

### 1. Server Setup

```bash
# Update & install dependencies
sudo apt update && sudo apt upgrade -y
sudo apt install python3 python3-pip ffmpeg -y
```

### 2. Clone & Install

```bash
git clone https://github.com/siambhau/VideoDownloader.git
cd VideoDownloader
pip3 install -r requirements.txt
```

### 3. Run with Gunicorn (Recommended)

```bash
pip3 install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 main:app
```

### 4. Run as systemd Service (Auto-restart on reboot)

Create service file:
```bash
sudo nano /etc/systemd/system/streamvault.service
```

Paste this:
```ini
[Unit]
Description=StreamVault Video Downloader
After=network.target

[Service]
User=root
WorkingDirectory=/root/VideoDownloader
ExecStart=/usr/local/bin/gunicorn -w 4 -b 0.0.0.0:5000 main:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable streamvault
sudo systemctl start streamvault

# Check status
sudo systemctl status streamvault
```

---

## 🔥 Firebase Variant

The [`Firebase Database/`](./Firebase%20Database/) folder contains a **Firestore-backed version** — ideal for cloud deployments like Render where the local filesystem resets on restart.

| | SQLite Version | Firebase Version |
|---|---|---|
| **Storage** | Local `downloads.db` | Cloud Firestore |
| **Best for** | VPS / local | Render / cloud |
| **History persistence** | Lost on restart | Survives restarts ✅ |
| **Setup** | Zero config | Needs credentials |

### Quick Firebase Setup

1. Create project at [Firebase Console](https://console.firebase.google.com/)
2. Enable **Firestore Database** (Production mode)
3. Go to **Project Settings → Service Accounts → Generate new private key**
4. Save the JSON as `firebase-credentials.json` inside `Firebase Database/`
5. Run:
```bash
cd "Firebase Database"
pip install -r requirements.txt
python main.py
```

📖 Full guide → [`Firebase Database/FIREBASE_SETUP.md`](./Firebase%20Database/FIREBASE_SETUP.md)

---

## 🎮 How to Use

```
1. Paste URL    →   Paste any supported video link
2. Analyze      →   Fetches title, thumbnail & platform info
3. Pick Format  →   Best / HD 720p / Mobile 480p / Audio MP3
4. Download     →   Watch live progress bar
5. Get File     →   Download from History section
```

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Main web interface |
| `POST` | `/api/analyze` | Analyze a video URL |
| `POST` | `/api/download` | Start a download job |
| `GET` | `/api/status/<id>` | Check download progress |
| `GET` | `/api/history` | Get last 10 downloads |
| `GET` | `/file/<id>` | Download the finished file |

### Example — Analyze

```bash
curl -X POST http://localhost:5000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}'
```

```json
{
  "title": "Rick Astley - Never Gonna Give You Up",
  "thumbnail": "https://...",
  "platform": "YouTube",
  "duration": "3:33"
}
```

---

## ⚙️ Configuration

| Variable | Default | Description |
|---|---|---|
| `DOWNLOAD_DIR` | `downloads/` | Where files are saved |
| `DB_PATH` | `downloads.db` | SQLite database path |
| Port | `5000` | Change in `main.py` → `app.run(port=5000)` |
| File Expiry | 24 hours | Hardcoded in `run_download()` |

### ⚠️ YouTube Cookies (Required for YouTube Downloads)

YouTube has strict bot detection — without a `cookies.txt` file, YouTube downloads will likely fail.

**How to get it:**
1. Install a browser extension that exports cookies in Netscape format
   - Chrome/Edge: **Get cookies.txt LOCALLY**
   - Firefox: **cookies.txt**
2. Log in to your YouTube account in the browser
3. While on `youtube.com`, click the extension → Export
4. Save the file as `cookies.txt` in the project root (same folder as `main.py`)

The app detects it automatically — no extra config needed.

> 🔒 **Never upload `cookies.txt` to GitHub.** It contains your YouTube session. Add it to `.gitignore`.

---

## 📦 Dependencies

```
Flask==3.0.0
flask-cors==4.0.0
yt-dlp==2024.12.13
Werkzeug==3.0.1
```

---

## 👨‍💻 Contact

**SiamBhau**

[![Facebook](https://img.shields.io/badge/Facebook-SiamBhau69-1877F2?style=flat-square&logo=facebook&logoColor=white)](https://facebook.com/SiamBhau2.0)
[![Telegram](https://img.shields.io/badge/Telegram-@SiamBhau-2CA5E0?style=flat-square&logo=telegram&logoColor=white)](https://t.me/SiamBhau69)
[![Email](https://img.shields.io/badge/Email-siamxus69@gmail.com-D14836?style=flat-square&logo=gmail&logoColor=white)](mailto:siamxus69@gmail.com)

---

<div align="center">

Made with ❤️ by **SiamBhau**

⭐ Star this repo if it helped you!

</div>
