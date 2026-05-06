#!/usr/bin/env python3
"""
NBA 2K26 Playbook API Server
--------------------------
Serves playbook operations via HTTP API.

Usage:
    python playbook_server.py
    
Then access:
    GET /api/plays - Get all available plays
    GET /api/playbook?team=PHI - Get team's playbook
    POST /api/playbook - Set team's playbook
"""

import sys
import json
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import threading

# Add parent dir to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from Playbook.playbook_editor import PlaybookEditor

PORT = 8765

# Play catalog cache
PLAY_CATALOG = {}

def load_play_catalog():
    """Load play catalog mapping"""
    global PLAY_CATALOG
    try:
        playbook_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Playbook')
        catalog_file = os.path.join(playbook_dir, 'game files', 'all_play_names.txt')
        
        if os.path.exists(catalog_file):
            with open(catalog_file, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if ': ' in line:
                        parts = line.split(': ', 1)
                        if len(parts) == 2:
                            name = parts[1].strip(" '")
                            PLAY_CATALOG[line_num] = name
        else:
            print(f"Warning: Catalog not found at {catalog_file}")
            # Fallback
            PLAY_CATALOG = {
                1: "FIST 1-4", 2: "HIGH 1-4", 3: "QUICK 42 1-4",
                6: "00 ISO BOX 3 QUICK", 7: "00 ISO RIP 3", 11: "00 PUNCH 15",
                25: "01 LAL ISO 2 QUICK DBL", 26: "01 LAL ISO 2 QUICK TRI",
                27: "01 LAL ISO 2 SLIP", 28: "01 LAL ISO 2 TRI",
                53: "01 SAC HIGH PUNCH 4 QUICK", 117: "02 FIST 14 QUICK CURL DBL",
                126: "02 FIST 14 SIDE OUT"
            }
    except Exception as e:
        print(f"Error loading catalog: {e}")
        PLAY_CATALOG = {}

load_play_catalog()

class PlaybookAPIHandler(BaseHTTPRequestHandler):
    """HTTP API Handler"""
    
    def log_message(self, format, *args):
        print(f"[API] {args[0]}")
    
    def send_json(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
    
    def do_GET(self):
        path = urlparse(self.path).path
        query = parse_qs(urlparse(self.path).query)
        
        if path == '/api/plays':
            self.send_json(PLAY_CATALOG)
            
        elif path == '/api/playbook':
            team = query.get('team', [None])[0]
            if not team:
                self.send_json({'error': 'Missing team parameter'}, 400)
                return
            
            try:
                pb = PlaybookEditor()
                if not pb.connect():
                    self.send_json({'error': 'Game not running'}, 503)
                    return
                
                plays = pb.get_team_playbook(team)
                pb.disconnect()
                
                # Convert indices to names
                named_plays = [{'index': p, 'name': PLAY_CATALOG.get(p, f'Play {p}')} for p in plays]
                
                self.send_json({'team': team, 'plays': plays, 'named': named_plays})
            except Exception as e:
                self.send_json({'error': str(e)}, 500)
                
        else:
            self.send_json({'error': 'Not found'}, 404)
    
    def do_POST(self):
        path = urlparse(self.path).path
        
        if path == '/api/playbook':
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length)
            
            try:
                data = json.loads(body)
                team = data.get('team')
                plays = data.get('plays', [])
                
                if not team:
                    self.send_json({'error': 'Missing team'}, 400)
                    return
                
                try:
                    pb = PlaybookEditor()
                    if not pb.connect():
                        self.send_json({'error': 'Game not running'}, 503)
                        return
                    
                    success = pb.set_team_playbook(team, plays)
                    pb.disconnect()
                    
                    if success:
                        self.send_json({'ok': True, 'team': team, 'plays': len(plays)})
                    else:
                        self.send_json({'error': 'Failed to write playbook'}, 500)
                except Exception as e:
                    self.send_json({'error': str(e)}, 500)
                    
            except json.JSONDecodeError:
                self.send_json({'error': 'Invalid JSON'}, 400)
        else:
            self.send_json({'error': 'Not found'}, 404)
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

def start_server(port=PORT):
    """Start the API server"""
    server = HTTPServer(('', port), PlaybookAPIHandler)
    print(f"Playbook API running on http://localhost:{port}")
    print(f"  GET /api/plays - List all plays")
    print(f"  GET /api/playbook?team=PHI - Get team playbook")
    print(f"  POST /api/playbook - Set team playbook")
    return server

if __name__ == '__main__':
    server = start_server()
    server.serve_forever()