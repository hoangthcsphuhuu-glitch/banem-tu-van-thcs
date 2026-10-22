#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Khởi chạy Web App Trợ Lý Tư Vấn Học Sinh THCS (13-15 tuổi) trên:
1. Máy tính cục bộ (http://localhost:3000)
2. Mạng nội bộ Wi-Fi/LAN (http://<IP_LAN>:3000)
3. Mạng Internet công cộng toàn cầu (https://...lhr.life) thông qua SSH Tunnel (localhost.run)
"""

import os
import sys
import socket
import threading
import subprocess
import re
from http.server import HTTPServer, SimpleHTTPRequestHandler
from socketserver import ThreadingMixIn

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

WORKSPACE_DIR = os.path.dirname(os.path.abspath(__file__))
WWW_DIR = os.path.join(WORKSPACE_DIR, "www")
PORT = 3000


class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


class AppRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WWW_DIR, **kwargs)

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def guess_type(self, path):
        if path.endswith(".apk"):
            return "application/vnd.android.package-archive"
        if path.endswith(".webmanifest") or path.endswith("manifest.json"):
            return "application/manifest+json"
        if path.endswith(".svg"):
            return "image/svg+xml"
        if path.endswith(".js"):
            return "application/javascript; charset=utf-8"
        if path.endswith(".css"):
            return "text/css; charset=utf-8"
        if path.endswith(".html"):
            return "text/html; charset=utf-8"
        return super().guess_type(path)

    def log_message(self, fmt, *args):
        pass


def get_lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def main():
    server = ThreadingHTTPServer(("0.0.0.0", PORT), AppRequestHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    lan_ip = get_lan_ip()
    print("=" * 68)
    print("🌐 WEB APP TRỢ LÝ TƯ VẤN HỌC SINH THCS (13, 14, 15 TUỔI) ĐANG CHẠY!")
    print("=" * 68)
    print(f"👉 1. Truy cập trên máy tính này : http://localhost:{PORT}")
    print(f"👉 2. Truy cập qua cùng mạng Wi-Fi: http://{lan_ip}:{PORT}")
    print("-" * 68)
    print("⏳ Đang khởi tạo đường truyền HTTPS công cộng trên mạng Internet...")
    sys.stdout.flush()

    ssh_cmd = [
        "ssh",
        "-o", "StrictHostKeyChecking=no",
        "-o", "ServerAliveInterval=30",
        "-o", "ExitOnForwardFailure=yes",
        "-R", f"80:localhost:{PORT}",
        "nokey@localhost.run"
    ]

    import time
    while True:
        try:
            proc = subprocess.Popen(
                ssh_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                text=True,
                encoding="utf-8",
                errors="replace"
            )
            printed_url = False
            for line in proc.stdout:
                match = re.search(r"(https://[a-zA-Z0-9.-]+\.lhr\.life)", line)
                if match and not printed_url:
                    public_url = match.group(1)
                    printed_url = True
                    print("\n" + "★" * 68)
                    print(f"✅ LINK INTERNET CÔNG CỘNG (Mở trên mọi điện thoại 4G/Wi-Fi):")
                    print(f"   🔗 {public_url}")
                    print(f"   📥 Tải trực tiếp APK: {public_url}/TroLyTuVanTHCS-Android.apk")
                    print("★" * 68 + "\n")
                    sys.stdout.flush()
            proc.wait()
            time.sleep(2)
        except KeyboardInterrupt:
            print("\nĐã dừng máy chủ Web App.")
            break
        except Exception as e:
            print(f"Đang kết nối lại đường truyền Internet ({e})...")
            time.sleep(5)


if __name__ == "__main__":
    main()
