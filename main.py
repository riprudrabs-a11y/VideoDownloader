from datetime import datetime, timedelta
import hashlib
import logging
import os
import re
import sqlite3
import threading
import time
import uuid

from flask import Flask, jsonify, render_template, request, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
from yt_dlp import YoutubeDL

# Initialize Flask App
app = Flask(__name__)
CORS(app)

# Configuration
DOWNLOAD_DIR = 'downloads'
TEMP_DIR = 'temp'
DB_PATH = 'downloads.db'

os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global state for tracking download progress
download_state = {}


class MyLogger:

  def debug(self, msg):
    pass

  def warning(self, msg):
    pass

  def error(self, msg):
    logger.error(msg)


def progress_hook(d):
  download_id = d.get('info_dict', {}).get('download_id')
  if download_id and download_id in download_state:
    if d['status'] == 'downloading':
      download_state[download_id]['progress'] = (
          d.get('_percent_str', '0%').replace('%', '').strip()
      )
      download_state[download_id]['speed'] = d.get('_speed_str', 'N/A')
      download_state[download_id]['status'] = 'downloading'
    elif d['status'] == 'finished':
      download_state[download_id]['status'] = 'processing_files'


def init_db():
  conn = sqlite3.connect(DB_PATH)
  c = conn.cursor()
  c.execute('''CREATE TABLE IF NOT EXISTS history (
        id TEXT PRIMARY KEY, 
        url TEXT, 
        title TEXT, 
        platform TEXT, 
        filename TEXT, 
        thumbnail TEXT, 
        timestamp DATETIME, 
        expiry DATETIME
    )''')
  conn.commit()
  conn.close()


init_db()


def get_platform(url):
  url = url.lower()
  if 'youtube.com' in url or 'youtu.be' in url:
    return 'YouTube'
  if 'instagram.com' in url:
    return 'Instagram'
  if 'tiktok.com' in url:
    return 'TikTok'
  if 'twitter.com' in url or 'x.com' in url:
    return 'Twitter'
  if 'facebook.com' in url:
    return 'Facebook'
  return 'Social Media'


@app.route('/')
def index():
  return render_template('index.html')


@app.route('/api/analyze', methods=['POST'])
def analyze():
  data = request.json
  url = data.get('url')
  if not url:
    return jsonify({'error': 'No URL provided'}), 400

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
          'duration': info.get('duration_string'),
      })
  except Exception as e:
    return jsonify({'error': str(e)}), 400


@app.route('/api/download', methods=['POST'])
def download():
  data = request.json
  url = data.get('url')
  format_type = data.get('format', 'best')

  if not url:
    return jsonify({'error': 'No URL provided'}), 400

  download_id = str(uuid.uuid4())
  download_state[download_id] = {
      'status': 'starting',
      'progress': '0',
      'title': 'Initializing...',
      'thumbnail': None,
  }

  thread = threading.Thread(
      target=run_download, args=(download_id, url, format_type)
  )
  thread.start()

  return jsonify({'id': download_id})


def run_download(download_id, url, format_type):
  try:
    with YoutubeDL({'quiet': True, 'no_warnings': True}) as ydl:
      info_pre = ydl.extract_info(url, download=False)
      download_state[download_id]['title'] = info_pre.get('title', 'Video')
      download_state[download_id]['thumbnail'] = info_pre.get('thumbnail')

    opts = {
        'quiet': True,
        'logger': MyLogger(),
        'progress_hooks': [progress_hook],
        'outtmpl': os.path.join(
            DOWNLOAD_DIR, f'{download_id}_%(title).100s.%(ext)s'
        ),
        'restrictfilenames': True,
        'windowsfilenames': True,
        'concurrent_fragment_downloads': 5,
        'retries': 15,
        'fragment_retries': 15,
        'socket_timeout': 20,
        'http_chunk_size': 10485760,
        # YouTube Bot Bypass
        'cookiefile': 'cookies.txt' if os.path.exists('cookies.txt') else None,
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'web'],
                'player_skip': ['configs', 'webpage'],
            }
        },
        'http_headers': {
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            ),
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
      opts['format'] = (
          'best[height<=720][ext=mp4]/best[height<=720]/best'
      )
    elif format_type == 'small':
      opts['format'] = (
          'best[height<=480][ext=mp4]/best[height<=480]/worst'
      )
    else:
      opts['format'] = (
          'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
      )

    with YoutubeDL(opts) as ydl:
      info = ydl.extract_info(url, download=True)
      info['download_id'] = download_id
      filename = ydl.prepare_filename(info)

      if format_type == 'audio':
        filename = os.path.splitext(filename)[0] + '.mp3'

      if not os.path.exists(filename):
        base_name = os.path.splitext(filename)[0]
        for ext in ['.mp4', '.mkv', '.webm', '.mp3', '.m4a', '.m4v']:
          if os.path.exists(base_name + ext):
            filename = base_name + ext
            break

      final_filename = os.path.basename(filename)
      expiry = datetime.now() + timedelta(hours=24)

      conn = sqlite3.connect(DB_PATH)
      c = conn.cursor()
      c.execute(
          'INSERT INTO history VALUES (?,?,?,?,?,?,?,?)',
          (
              download_id,
              url,
              info.get('title'),
              get_platform(url),
              final_filename,
              info.get('thumbnail'),
              datetime.now(),
              expiry,
          ),
      )
      conn.commit()
      conn.close()

      download_state[download_id].update({
          'status': 'completed',
          'filename': final_filename,
          'progress': '100',
      })
  except Exception as e:
    logger.error(f'Download error: {str(e)}')
    download_state[download_id].update({'status': 'error', 'error': str(e)})


@app.route('/api/status/<download_id>')
def get_status(download_id):
  status = download_state.get(download_id)
  if not status:
    return jsonify({'error': 'Download ID not found'}), 404
  return jsonify(status)


@app.route('/downloads/<path:filename>')
def serve_file(filename):
  return send_from_directory(DOWNLOAD_DIR, filename, as_attachment=True)


if __name__ == '__main__':
  app.run(debug=True, port=5000)
