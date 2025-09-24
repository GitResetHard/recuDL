from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS

from .config import Config
from .state import load as load_state, record as record_state
from .console import info, warn, error, success


class WebServer:
    def __init__(self, config_path: str = "config.json", host: str = "127.0.0.1", port: int = 8080):
        self.app = Flask(__name__, 
                        template_folder=str(Path(__file__).parent / "templates"),
                        static_folder=str(Path(__file__).parent / "static"))
        CORS(self.app)
        
        self.config_path = config_path
        self.host = host
        self.port = port
        self.current_downloads: Dict[str, Dict[str, Any]] = {}
        self.download_lock = threading.Lock()
        
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup Flask routes"""
        
        @self.app.route('/')
        def dashboard():
            return render_template('dashboard.html')
        
        @self.app.route('/config')
        def config_page():
            return render_template('config.html')
        
        @self.app.route('/history')
        def history_page():
            return render_template('history.html')
        
        @self.app.route('/get-started')
        def get_started_page():
            return render_template('get_started.html')
        
        @self.app.route('/faq')
        def faq_page():
            return render_template('faq.html')
        
        # API Routes
        @self.app.route('/api/config', methods=['GET'])
        def get_config():
            try:
                if os.path.exists(self.config_path):
                    config = Config.load_from_file(self.config_path)
                    return jsonify({
                        'urls': config.urls,
                        'header': config.header,
                        'post_process': config.post_process
                    })
                else:
                    return jsonify({'error': 'Config file not found'}), 404
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/config', methods=['POST'])
        def update_config():
            try:
                data = request.get_json()
                config = Config(
                    urls=data.get('urls', []),
                    header=data.get('header', {}),
                    post_process_cfg=data.get('post_process', {}),
                    config_path=self.config_path
                )
                error_result = config.save()
                if error_result:
                    return jsonify({'error': str(error_result)}), 500
                return jsonify({'success': True})
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/downloads', methods=['GET'])
        def get_downloads():
            with self.download_lock:
                return jsonify(list(self.current_downloads.values()))
        
        @self.app.route('/api/downloads', methods=['POST'])
        def start_download():
            try:
                data = request.get_json()
                urls = data.get('urls', [])
                mode = data.get('mode', 'parallel')  # parallel, series, hybrid
                
                if not urls:
                    return jsonify({'error': 'No URLs provided'}), 400
                
                # Create temporary config for this download
                config = Config.load_from_file(self.config_path) if os.path.exists(self.config_path) else Config.default()
                config.urls = urls
                
                # Start download in background thread
                download_id = f"download_{int(time.time())}"
                
                with self.download_lock:
                    self.current_downloads[download_id] = {
                        'id': download_id,
                        'urls': urls,
                        'mode': mode,
                        'status': 'starting',
                        'progress': 0,
                        'started_at': time.time(),
                        'current_file': None
                    }
                
                thread = threading.Thread(target=self._run_download, args=(download_id, config, mode))
                thread.daemon = True
                thread.start()
                
                return jsonify({'download_id': download_id, 'status': 'started'})
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/downloads/<download_id>', methods=['DELETE'])
        def cancel_download(download_id):
            with self.download_lock:
                if download_id in self.current_downloads:
                    self.current_downloads[download_id]['status'] = 'cancelled'
                    return jsonify({'success': True})
                return jsonify({'error': 'Download not found'}), 404
        
        @self.app.route('/api/history', methods=['GET'])
        def get_history():
            try:
                state_data = load_state()
                entries = state_data.get('entries', [])
                # Sort by timestamp, newest first
                entries.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
                return jsonify(entries)
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/status', methods=['GET'])
        def get_status():
            return jsonify({
                'server': 'running',
                'config_exists': os.path.exists(self.config_path),
                'active_downloads': len([d for d in self.current_downloads.values() if d['status'] in ['running', 'starting']]),
                'total_downloads': len(self.current_downloads)
            })
    
    def _run_download(self, download_id: str, config: Config, mode: str):
        """Run download in background thread"""
        try:
            with self.download_lock:
                if download_id not in self.current_downloads:
                    return
                self.current_downloads[download_id]['status'] = 'running'
            
            # Import download functions
            from . import __main__ as main_module
            
            # Run appropriate download mode
            if mode == 'series':
                main_module._serial_service(config)
            elif mode == 'hybrid':
                main_module._hybrid_service(config)
            else:  # parallel (default)
                main_module._parallel_service(config)
            
            with self.download_lock:
                if download_id in self.current_downloads:
                    self.current_downloads[download_id]['status'] = 'completed'
                    self.current_downloads[download_id]['completed_at'] = time.time()
        
        except Exception as e:
            with self.download_lock:
                if download_id in self.current_downloads:
                    self.current_downloads[download_id]['status'] = 'failed'
                    self.current_downloads[download_id]['error'] = str(e)
    
    def run(self, debug: bool = False):
        """Start the web server"""
        info(f"🌐 Starting web server at http://{self.host}:{self.port}")
        self.app.run(host=self.host, port=self.port, debug=debug, threaded=True)


def start_web_server(config_path: str = "config.json", host: str = "127.0.0.1", port: int = 8080, debug: bool = False):
    """Start the web server"""
    server = WebServer(config_path, host, port)
    server.run(debug)
