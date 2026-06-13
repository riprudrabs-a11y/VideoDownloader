from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import uuid
import threading
import time
import json
from datetime import datetime, timedelta
from yt_dlp import YoutubeDL
import logging
from werkzeug.utils import secure_filename

# Firestore imports
try:
    import firebase_admin
    from firebase_admin import credentials, firestore
    FIRESTORE_AVAILABLE = True
except ImportError:
    FIRESTORE_AVAILABLE = False
    print("⚠️ Firebase not installed. Run: pip install firebase-admin")

app = Flask(__name__)
CORS(app)

# Configuration
DOWNLOAD_DIR = 'downloads'
TEMP_DIR = 'temp'
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database setup - Firestore with in-memory fallback
USE_FIRESTORE = False
db = None
memory_history = {}

def init_firestore():
    """Initialize Firestore if credentials are available"""
    global USE_FIRESTORE, db
    
    if not FIRESTORE_AVAILABLE:
        logger.warning("⚠️ Firebase library not installed")
        return False
    
    try:
        # Method 1: Using service account JSON file
        if os.path.exists('firebase-credentials.json'):
            cred = credentials.Certificate('firebase-credentials.json')
            firebase_admin.initialize_app(cred)
            db = firestore.client()
            USE_FIRESTORE = True
            logger.info("✅ Firestore initialized with credentials file")
            return True
            
        # Method 2: Using environment variable (for Render deployment)
        elif os.environ.get('FIREBASE_CREDENTIALS'):
            cred_dict = json.loads(os.environ.get('FIREBASE_CREDENTIALS'))
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
            db = firestore.client()
            USE_FIRESTORE = True
            logger.info("✅ Firestore initialized with environment variable")
            return True
        else:
            logger.warning("⚠️ Firebase credentials not found. Using in-memory storage.")
            return False
            
    except Exception as e:
        logger.error(f"❌ Firestore initialization failed: {e}")
        logger.warning("Using in-memory storage as fallback")
        return False

# Try to initialize Firestore
init_firestore()

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

# Database helper functions
def save_to_history(download_id, url, title, platform, filename, thumbnail):
    """Save download to history (Firestore or memory)"""
    timestamp = datetime.now()
    expiry = datetime.now() + timedelta(hours=24)
    
    history_data = {
        'id': download_id,
        'url': url,
        'title': title,
        'platform': platform,
        'filename': filename,
        'thumbnail': thumbnail,
        'timestamp': timestamp,
        'expiry': expiry
    }
    
    if USE_FIRESTORE:
        try:
            db.collection('history').document(download_id).set(history_data)
            logger.info(f"✅ Saved to Firestore: {download_id}")
        except Exception as e:
            logger.error(f"❌ Firestore save failed: {e}")
            memory_history[download_id] = history_data
    else:
        memory_history[download_id] = history_data
        logger.info(f"📝 Saved to memory: {download_id}")

def get_history(limit=10):
    """Get download history (Firestore or memory)"""
    if USE_FIRESTORE:
        try:
            docs = db.collection('history').order_by('timestamp', direction=firestore.Query.DESCENDING).limit(limit).stream()
            history_list = []
            for doc in docs:
                data = doc.to_dict()
                # Convert datetime to string for JSON
                if isinstance(data.get('timestamp'), datetime):
                    data['timestamp'] = data['timestamp'].isoformat()
                if isinstance(data.get('expiry'), datetime):
                    data['expiry'] = data['expiry'].isoformat()
                history_list.append(data)
            return history_list
        except Exception as e:
            logger.error(f"❌ Firestore get failed: {e}")
            # Fallback to memory
            history_list = sorted(memory_history.values(), 
                                key=lambda x: x['timestamp'], 
                                reverse=True)
            return history_list[:limit]
    else:
        # Get from memory, sorted by timestamp
        history_list = sorted(memory_history.values(), 
                            key=lambda x: x['timestamp'], 
                            reverse=True)
        return history_list[:limit]

def get_file_info(download_id):
    """Get file info by download ID"""
    if USE_FIRESTORE:
        try:
            doc = db.collection('history').document(download_id).get()
            if doc.exists:
                return doc.to_dict()
            return None
        except Exception as e:
            logger.error(f"❌ Firestore get failed: {e}")
            return memory_history.get(download_id)
    else:
        return memory_history.get(download_id)

def delete_expired_files():
    """Delete expired files (24h+)"""
    now = datetime.now()
    
    if USE_FIRESTORE:
        try:
            # Get all expired documents
            docs = db.collection('history').where('expiry', '<', now).stream()
            
            for doc in docs:
                data = doc.to_dict()
                download_id = doc.id
                
                # Delete file
                filename = data.get('filename')
                if filename:
                    filepath = os.path.join(DOWNLOAD_DIR, filename)
                    if os.path.exists(filepath):
                        os.remove(filepath)
                        logger.info(f"🗑️ Deleted expired file: {filename}")
                
                # Delete from Firestore
                doc.reference.delete()
                logger.info(f"🗑️ Deleted from Firestore: {download_id}")
                    
        except Exception as e:
            logger.error(f"❌ Firestore cleanup failed: {e}")
    else:
        # Clean from memory
        to_delete = []
        for download_id, data in memory_history.items():
            expiry = data.get('expiry')
            if now > expiry:
                filename = data.get('filename')
                if filename:
                    filepath = os.path.join(DOWNLOAD_DIR, filename)
                    if os.path.exists(filepath):
                        os.remove(filepath)
                        logger.info(f"🗑️ Deleted expired file: {filename}")
                to_delete.append(download_id)
        
        for download_id in to_delete:
            del memory_history[download_id]
            logger.info(f"🗑️ Deleted from memory: {download_id}")

def get_platform(url):
    url = url.lower()
    # YouTube
    if 'youtube.com' in url or 'youtu.be' in url: 
        return 'YouTube'
    # Facebook - all possible formats
    if 'facebook.com' in url or 'fb.watch' in url or 'fb.com' in url or 'm.facebook.com' in url: 
        return 'Facebook'
    # Instagram
    if 'instagram.com' in url or 'instagr.am' in url: 
        return 'Instagram'
    # TikTok
    if 'tiktok.com' in url or 'vm.tiktok.com' in url: 
        return 'TikTok'
    # Twitter/X
    if 'twitter.com' in url or 'x.com' in url or 't.co' in url: 
        return 'Twitter'
    # Additional platforms
    if 'vimeo.com' in url: 
        return 'Vimeo'
    if 'dailymotion.com' in url or 'dai.ly' in url: 
        return 'Dailymotion'
    if 'reddit.com' in url or 'redd.it' in url: 
        return 'Reddit'
    if 'twitch.tv' in url: 
        return 'Twitch'
    if 'soundcloud.com' in url: 
        return 'SoundCloud'
    if 'bandcamp.com' in url: 
        return 'Bandcamp'
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
            'socket_timeout': 15,
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
            'concurrent_fragment_downloads': 5,
            'retries': 15,
            'fragment_retries': 15,
            'skip_unavailable_fragments': False,
            'socket_timeout': 20,
            'http_chunk_size': 10485760,
            
            # Enhanced extractor arguments
            'cookiefile': 'cookies.txt' if os.path.exists('cookies.txt') else None,
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'web'],
                    'player_skip': ['configs', 'webpage'],
                },
                'facebook': {
                    'skip_dash_manifest': True,
                },
                'instagram': {
                    'include_stories': True,
                },
                'tiktok': {
                    'api_hostname': 'api22-normal-c-useast2a.tiktokv.com',
                }
            },
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-us,en;q=0.5',
                'Sec-Fetch-Mode': 'navigate',
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
            
            # Method 2: Platform-specific fallback
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
            
            elif platform == 'Facebook':
                # Facebook-specific fallback
                try:
                    fb_opts = opts.copy()
                    fb_opts['format'] = 'best/bestvideo+bestaudio'
                    # Remove format restrictions for Facebook
                    if 'format' in fb_opts and 'height' in fb_opts['format']:
                        fb_opts['format'] = 'best'
                    with YoutubeDL(fb_opts) as ydl:
                        info = ydl.extract_info(url, download=True)
                        info['download_id'] = download_id
                        filename = ydl.prepare_filename(info)
                        downloaded = True
                        logger.info("✅ Facebook fallback method succeeded")
                except Exception as e2:
                    logger.warning(f"Facebook fallback failed: {str(e2)[:100]}")
            
            # Method 3: Last resort - try basic download for all platforms
            if not downloaded:
                try:
                    basic_opts = {
                        'quiet': True,
                        'format': 'best',
                        'outtmpl': os.path.join(DOWNLOAD_DIR, f"{download_id}_%(title).100s.%(ext)s"),
                        'http_headers': {
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                        },
                    }
                    with YoutubeDL(basic_opts) as ydl:
                        info = ydl.extract_info(url, download=True)
                        info['download_id'] = download_id
                        filename = ydl.prepare_filename(info)
                        downloaded = True
                        logger.info("✅ Basic fallback method succeeded")
                except Exception as e3:
                    logger.error(f"All methods failed: {str(e3)[:200]}")
                    if platform == 'YouTube' and format_type != 'audio':
                        # YouTube audio fallback as absolute last resort
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
                        except Exception as e4:
                            raise Exception(f"All download methods failed: {str(e4)}")
        
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
        
        # Save to Firestore or memory
        save_to_history(
            download_id=download_id,
            url=url,
            title=info.get('title'),
            platform=get_platform(url),
            filename=final_filename,
            thumbnail=info.get('thumbnail')
        )
        
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
        file_info = get_file_info(download_id)
        if file_info:
            # Convert datetime to string if needed
            timestamp = file_info.get('timestamp')
            if isinstance(timestamp, datetime):
                timestamp = timestamp.isoformat()
            return jsonify({
                'status': 'completed', 
                'title': file_info.get('title'), 
                'filename': file_info.get('filename'), 
                'thumbnail': file_info.get('thumbnail')
            })
        return jsonify({'status': 'not_found'})
    return jsonify(state)

@app.route('/api/history')
def history():
    history_list = get_history(limit=10)
    result = []
    for item in history_list:
        # Convert datetime to string for JSON serialization
        timestamp = item.get('timestamp')
        if isinstance(timestamp, datetime):
            timestamp = timestamp.isoformat()
        
        result.append({
            'id': item.get('id'),
            'title': item.get('title'),
            'platform': item.get('platform'),
            'thumbnail': item.get('thumbnail'),
            'date': timestamp,
            'filename': item.get('filename')
        })
    return jsonify(result)

@app.route('/file/<download_id>')
def get_file(download_id):
    file_info = get_file_info(download_id)
    if file_info:
        filename = file_info.get('filename')
        if filename:
            return send_from_directory(DOWNLOAD_DIR, filename, as_attachment=True)
    return "File not found", 404

def cleanup_loop():
    while True:
        try:
            delete_expired_files()
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
        time.sleep(3600)  # Run every hour

threading.Thread(target=cleanup_loop, daemon=True).start()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
