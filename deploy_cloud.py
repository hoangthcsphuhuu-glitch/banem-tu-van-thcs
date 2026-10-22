#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Triển khai Web App Trợ Lý Tư Vấn Học Sinh THCS Phú Hữu lên Cloud Hosting cố định 24/7 (Surge.sh)
"""
import os
import sys
import subprocess

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

WORKSPACE_DIR = os.path.dirname(os.path.abspath(__file__))
WWW_DIR = os.path.join(WORKSPACE_DIR, "www")
DOMAIN = "tu-van-thcs-phu-huu.surge.sh"

# Tạo file CNAME và 200.html (hỗ trợ SPA/PWA trên Surge)
with open(os.path.join(WWW_DIR, "CNAME"), "w", encoding="utf-8") as f:
    f.write(DOMAIN + "\n")

print(f"Đang chuẩn bị triển khai lên tên miền cố định: https://{DOMAIN} ...")
