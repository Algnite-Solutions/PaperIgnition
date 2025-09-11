#!/usr/bin/env python3
"""
Simple HTTP server for serving the PaperIgnition web application.
Usage: python server.py [port]
"""

import http.server
import socketserver
import os
import sys
from pathlib import Path

# Default port
PORT = 3000

# Get port from command line argument if provided
if len(sys.argv) > 1:
    try:
        PORT = int(sys.argv[1])
    except ValueError:
        print("Invalid port number. Using default port 3000.")

# Change to the web directory
web_dir = Path(__file__).parent
os.chdir(web_dir)

class CustomHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # Add CORS headers for development
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

if __name__ == "__main__":
    try:
        with socketserver.TCPServer(("", PORT), CustomHTTPRequestHandler) as httpd:
            print(f"🚀 PaperIgnition Web App serving at:")
            print(f"   http://localhost:{PORT}")
            print(f"   http://127.0.0.1:{PORT}")
            print(f"\n📁 Serving from: {web_dir}")
            print(f"\n✨ Press Ctrl+C to stop the server")
            print(f"\n📖 Available pages:")
            print(f"   • Main page: http://localhost:{PORT}/")
            print(f"   • Paper detail: http://localhost:{PORT}/paper.html?id=1")
            httpd.serve_forever()
    except KeyboardInterrupt:
        print(f"\n🛑 Server stopped.")
    except OSError as e:
        if e.errno == 48:  # Address already in use
            print(f"❌ Port {PORT} is already in use. Try a different port:")
            print(f"   python server.py {PORT + 1}")
        else:
            print(f"❌ Error starting server: {e}")