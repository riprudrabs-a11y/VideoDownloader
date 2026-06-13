<div align="center">

<img src="https://img.shields.io/badge/StreamVault-Premium%20Media%20Downloader-black?style=for-the-badge&logo=youtube&logoColor=white" alt="StreamVault"/>

<br/>
<br/>

[![Python](https://img.shields.io/badge/Python-3.8%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.0.0-000000?style=flat-square&logo=flask&logoColor=white)](https://flask.palletsprojects.com)
[![yt-dlp](https://img.shields.io/badge/yt--dlp-2024.3.10-FF0000?style=flat-square&logo=youtube&logoColor=white)](https://github.com/yt-dlp/yt-dlp)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

**A self-hosted, full-stack video downloader web app with a clean UI and multi-platform support.**

[Features](#-features) • [Quick Start](#-quick-start) • [API Docs](#-api-endpoints) • [Platforms](#-supported-platforms) • [Contact](#-contact)

</div>

---

## 📌 Overview

**StreamVault** is a self-hosted media downloader built with **Flask** and **yt-dlp**. Paste any video URL, analyze it, pick your quality, and download — all from a beautiful web interface. Files are stored for **24 hours** and cleaned up automatically.

> ⚡ Designed for speed — concurrent fragment downloads, multiple fallback methods, and real-time progress tracking.

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
| 🌐 **Multi-Platform** | 20+ platforms via yt-dlp |
| 🔒 **CORS Enabled** | API-ready with Flask-CORS |
| 🖥️ **Responsive UI** | Clean white & black theme, works on mobile |

---

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- `ffmpeg` installed and in PATH (required for audio extraction & merging)

### Installation

```bash
# 1. Clone the repo
git clone https://github.com/SiamBhau69/VideoDownloader.git
cd VideoDownloader

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the app
```

**Linux / Mac:**
```bash
chmod +x run.sh
./run.sh
```

**Windows:**
```bash
run.bat
```

**Or manually:**
```bash
python main.py
```

Then open your browser at → **http://localhost:5000**

---

## 🎮 How to Use

```
1. Paste URL   →   Paste any supported video link into the input box
2. Analyze     →   Click "Analyze" to fetch video title & thumbnail
3. Pick Format →   Choose from Best / HD 720p / Mobile / Audio MP3
4. Download    →   Watch live progress bar as it downloads
5. Get File    →   Click the file in History to download to your device
```

---

## 🌐 Supported Platforms

| Platform | Status |
|---|---|
| YouTube | ✅ Supported |
| Facebook | ✅ Supported |
| Instagram | ✅ Supported |
| TikTok | ✅ Supported |
| Twitter / X | ✅ Supported |
| Vimeo | ✅ Supported |
| 20+ others | ✅ via yt-dlp |

> Full list of supported sites: [yt-dlp supported sites](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md)

---

## 📁 Project Structure

```
VideoDownloader/
├── main.py                  # Flask app — all routes & download logic
├── requirements.txt         # Python dependencies
├── run.sh                   # Linux/Mac startup script
├── run.bat                  # Windows startup script
├── downloads.db             # SQLite DB for download history
├── templates/
│   └── index.html           # Frontend UI (Jinja2)
├── static/
│   ├── css/style.css        # Styling
│   └── js/app.js            # Frontend logic
├── downloads/               # Downloaded files (auto-cleaned after 24h)
└── Firebase Database/       # Optional Firebase variant of the app
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

**Response:**
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

### Optional: YouTube Cookies

If YouTube downloads fail due to age restriction or bot detection, place a `cookies.txt` file (Netscape format) in the project root. The app will use it automatically.

---

## 📦 Dependencies

```
Flask==3.0.0
flask-cors==4.0.0
yt-dlp==2024.3.10
Werkzeug==3.0.1
```

---

## 🤝 Contributing

Pull requests are welcome. For major changes, open an issue first to discuss what you'd like to change.

1. Fork the repo
2. Create your feature branch → `git checkout -b feature/my-feature`
3. Commit your changes → `git commit -m 'Add my feature'`
4. Push to the branch → `git push origin feature/my-feature`
5. Open a Pull Request

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).

---

## 👨‍💻 Contact

**SiamBhau69**

[![Facebook](https://img.shields.io/badge/Facebook-SiamBhau69-1877F2?style=flat-square&logo=facebook&logoColor=white)](https://facebook.com/SiamBhau69)
[![Telegram](https://img.shields.io/badge/Telegram-@SiamBhau-2CA5E0?style=flat-square&logo=telegram&logoColor=white)](https://t.me/SiamBhau69)
[![Email](https://img.shields.io/badge/Email-siamxus69@gmail.com-D14836?style=flat-square&logo=gmail&logoColor=white)](mailto:siamxus69@gmail.com)

---

<div align="center">

Made with ❤️ by **SiamBhau69**

⭐ If this project helped you, give it a star!

</div>
