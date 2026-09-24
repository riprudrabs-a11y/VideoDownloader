from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import uuid
import threading
import time
import sqlite3
from datetime import datetime, timedelta
from yt_dlp import YoutubeDL
import logging
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)

`'extractor_args': {'youtube': {'player_client': ['android']}}`[9]
# Configuration
DOWNLOAD_DIR = 'downloads'
TEMP_DIR = 'temp'
DB_PATH = 'downloads.db'
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global state for tracking download progress and info
download_state = {}

class MyLogger:
    def debug(self, msg): pass
    def warning(self, msg): pass
    def error(self, msg): logger.error(msg)

def progress_hook(d):
    download_id = d.get('info_dict', {}).get('download_id')
    if download_id and download_id in download_state:
        if d['status'] == 'downloading':
            download_state[download_id]['progress'] = d.get('_percent_str', '0%').replace('%', '').strip()
            download_state[download_id]['speed'] = d.get('_speed_str', 'N/A')
            download_state[download_id]['status'] = 'downloading'
        elif d['status'] == 'finished':
            download_state[download_id]['status'] = 'processing_files'

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS history 
                 (id TEXT PRIMARY KEY, url TEXT, title TEXT, platform TEXT, 
                  filename TEXT, thumbnail TEXT, timestamp DATETIME, expiry DATETIME)''')
    conn.commit()
    conn.close()

init_db()

def get_platform(url):
    url = url.lower()
    if 'youtube.com' in url or 'youtu.be' in url: return 'YouTube'
    if 'instagram.com' in url: return 'Instagram'
    if 'tiktok.com' in url: return 'TikTok'
    if 'twitter.com' in url or 'x.com' in url: return 'Twitter'
    if 'facebook.com' in url: return 'Facebook'
    return 'Social Media'

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/analyze', methods=['POST'])
def analyze():
    data = request.json
    url = data.get('url')
    if not url: return jsonify({'error': 'No URL provided'}), 400
    
    try:
        with YoutubeDL({
            'quiet': True, 
            'no_warnings': True,
            'extract_flat': False,
            'skip_download': True,
            'socket_timeout': 15,  # Faster timeout
        }) as ydl:
            info = ydl.extract_info(url, download=False)
            return jsonify({
                'title': info.get('title', 'Unknown Title'),
                'thumbnail': info.get('thumbnail'),
                'platform': get_platform(url),
                'duration': info.get('duration_string')
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/download', methods=['POST'])
def download():
    data = request.json
    url = data.get('url')
    format_type = data.get('format', 'best')
    
    if not url: return jsonify({'error': 'No URL provided'}), 400
    
    download_id = str(uuid.uuid4())
    download_state[download_id] = {
        'status': 'starting',
        'progress': '0',
        'title': 'Initializing...',
        'thumbnail': None
    }
    
    thread = threading.Thread(target=run_download, args=(download_id, url, format_type))
    thread.start()
    
    return jsonify({'id': download_id})

def run_download(download_id, url, format_type):
    try:
        # Initial info extraction for metadata
        with YoutubeDL({'quiet': True, 'no_warnings': True}) as ydl:
            info_pre = ydl.extract_info(url, download=False)
            download_state[download_id]['title'] = info_pre.get('title', 'Video')
            download_state[download_id]['thumbnail'] = info_pre.get('thumbnail')

        opts = {
            'quiet': True,
            'no_warnings': False,
            'ignoreerrors': False,
            'logger': MyLogger(),
            'progress_hooks': [progress_hook],
            'outtmpl': os.path.join(DOWNLOAD_DIR, f"{download_id}_%(title).100s.%(ext)s"),
            'restrictfilenames': True,
            'windowsfilenames': True,
            
            # Speed optimizations
            'concurrent_fragment_downloads': 5,  # Download 5 fragments at once
            'retries': 15,
            'fragment_retries': 15,
            'skip_unavailable_fragments': False,
            'socket_timeout': 20,  # Reduced timeout
            'http_chunk_size': 10485760,  # 10MB chunks for faster download
            
            # Fix for YouTube
            'cookiefile': 'cookies.txt' if os.path.exists('cookies.txt') else None,
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'web'],
                    'player_skip': ['configs', 'webpage'],
                }
            },
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            },
        }
        
        if format_type == 'audio':
            opts['format'] = 'bestaudio/best'
            opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]
        elif format_type == 'medium':
            opts['format'] = 'best[height<=720][ext=mp4]/best[height<=720]/best'
        elif format_type == 'small':
            opts['format'] = 'best[height<=480][ext=mp4]/best[height<=480]/worst'
        else:
            opts['format'] = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'

        # Try download with fallback methods
        platform = get_platform(url)
        downloaded = False
        
        # Method 1: Try primary format
        try:
            with YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
                info['download_id'] = download_id
                filename = ydl.prepare_filename(info)
                if format_type == 'audio':
                    filename = os.path.splitext(filename)[0] + '.mp3'
                downloaded = True
        except Exception as e1:
            logger.warning(f"Method 1 failed: {str(e1)[:100]}")
            
            # Method 2: Try simpler format for YouTube
            if platform == 'YouTube' and format_type != 'audio':
                try:
                    alt_opts = opts.copy()
                    alt_opts['format'] = 'best[height<=720]' if format_type == 'best' else 'best[height<=480]'
                    with YoutubeDL(alt_opts) as ydl:
                        info = ydl.extract_info(url, download=True)
                        info['download_id'] = download_id
                        filename = ydl.prepare_filename(info)
                        downloaded = True
                except Exception as e2:
                    logger.warning(f"Method 2 failed: {str(e2)[:100]}")
                    
                    # Method 3: Try audio only as last resort
                    try:
                        audio_opts = opts.copy()
                        audio_opts['format'] = 'bestaudio'
                        audio_opts['postprocessors'] = [{
                            'key': 'FFmpegExtractAudio',
                            'preferredcodec': 'mp3',
                            'preferredquality': '192',
                        }]
                        with YoutubeDL(audio_opts) as ydl:
                            info = ydl.extract_info(url, download=True)
                            info['download_id'] = download_id
                            filename = ydl.prepare_filename(info)
                            filename = os.path.splitext(filename)[0] + '.mp3'
                            downloaded = True
                    except Exception as e3:
                        raise Exception(f"All download methods failed: {str(e3)}")
            else:
                raise e1
        
        if not downloaded:
            raise Exception("Download failed")
        
        # Check if file exists (handle different extensions)
        if not os.path.exists(filename):
            base_name = os.path.splitext(filename)[0]
            for ext in ['.mp4', '.mkv', '.webm', '.mp3', '.m4a', '.m4v']:
                test_path = base_name + ext
                if os.path.exists(test_path):
                    filename = test_path
                    break
        
        if not os.path.exists(filename):
            raise Exception("Downloaded file not found")
        
        # Sanitize filename
        import re
        import hashlib
        original_filename = os.path.basename(filename)
        sanitized = re.sub(r'[<>:"/\\|?*]', '', original_filename)
        sanitized = re.sub(r'[^\w\s.-]', '', sanitized)
        
        MAX_LENGTH = 100
        if len(sanitized) > MAX_LENGTH:
            name, ext = os.path.splitext(sanitized)
            name_hash = hashlib.md5(name.encode()).hexdigest()[:8]
            sanitized = name[:MAX_LENGTH - len(ext) - 9] + '_' + name_hash + ext
        
        if original_filename != sanitized:
            new_path = os.path.join(os.path.dirname(filename), sanitized)
            os.rename(filename, new_path)
            filename = new_path
        
        final_filename = os.path.basename(filename)
        expiry = datetime.now() + timedelta(hours=24)
        
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT INTO history VALUES (?,?,?,?,?,?,?,?)", 
                  (download_id, url, info.get('title'), get_platform(url), 
                   final_filename, info.get('thumbnail'), datetime.now(), expiry))
        conn.commit()
        conn.close()
        
        download_state[download_id]['status'] = 'completed'
        download_state[download_id]['filename'] = final_filename
        download_state[download_id]['progress'] = '100'
        
    except Exception as e:
        logger.error(f"Download error: {str(e)}")
        download_state[download_id]['status'] = 'error'
        download_state[download_id]['error'] = str(e)

@app.route('/api/status/<download_id>')
def status(download_id):
    state = download_state.get(download_id)
    if not state:
        # Check database if thread finished and state cleared
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT title, filename, thumbnail FROM history WHERE id=?", (download_id,))
        res = c.fetchone()
        conn.close()
        if res:
            return jsonify({'status': 'completed', 'title': res[0], 'filename': res[1], 'thumbnail': res[2]})
        return jsonify({'status': 'not_found'})
    return jsonify(state)

@app.route('/api/history')
def history():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, title, platform, thumbnail, timestamp, filename FROM history ORDER BY timestamp DESC LIMIT 10")
    rows = c.fetchall()
    conn.close()
    return jsonify([{
        'id': r[0], 'title': r[1], 'platform': r[2], 
        'thumbnail': r[3], 'date': r[4], 'filename': r[5]
    } for r in rows])

@app.route('/file/<download_id>')
def get_file(download_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT filename FROM history WHERE id=?", (download_id,))
    res = c.fetchone()
    conn.close()
    if res:
        return send_from_directory(DOWNLOAD_DIR, res[0], as_attachment=True)
    return "File not found", 404

def cleanup_loop():
    while True:
        try:
            now = datetime.now()
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT id, filename FROM history WHERE expiry < ?", (now,))
            to_delete = c.fetchall()
            for fid, fname in to_delete:
                path = os.path.join(DOWNLOAD_DIR, fname)
                if os.path.exists(path):
                    os.remove(path)
                c.execute("DELETE FROM history WHERE id=?", (fid,))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
        time.sleep(3600)

threading.Thread(target=cleanup_loop, daemon=True).start()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
