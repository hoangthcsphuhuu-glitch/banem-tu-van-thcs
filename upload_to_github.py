#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Công cụ tự động tải toàn bộ mã nguồn dự án Chatbot banem (THCS 13-15) lên GitHub
và kích hoạt GitHub Pages (chạy trực tiếp bằng Python, không cần cài đặt Git).
"""

import os
import sys
import time
import json
import base64
import webbrowser
import urllib.request
import urllib.parse
import urllib.error

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

WORKSPACE_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_NAME = "banem-tu-van-thcs"
REPO_DESC = "Chatbot banem - Trợ lý tư vấn tâm lý, kỹ năng sống và định hướng học sinh THCS (13, 14, 15 tuổi) kèm file APK Android"

# Official GitHub CLI OAuth Client ID for Device Flow
GITHUB_CLIENT_ID = "178c6fc778ccc68e1d6a"


def github_api(method, path, token, payload=None):
    url = f"https://api.github.com{path}"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "User-Agent": "banem-thcs-uploader",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, (json.loads(body) if body else {})
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        try:
            err_json = json.loads(err_body)
        except Exception:
            err_json = {"message": err_body}
        return e.code, err_json


def get_token_via_device_flow():
    req_data = urllib.parse.urlencode({
        "client_id": GITHUB_CLIENT_ID,
        "scope": "repo workflow"
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://github.com/login/device/code",
        data=req_data,
        headers={"Accept": "application/json", "User-Agent": "banem-thcs-uploader"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        info = json.loads(resp.read().decode("utf-8"))

    device_code = info["device_code"]
    user_code = info["user_code"]
    verification_uri = info["verification_uri"]
    interval = int(info.get("interval", 5))

    print("=" * 68)
    print("🔐 XÁC THỰC TÀI KHOẢN GITHUB ĐỂ TẢI MÃ NGUỒN LÊN:")
    print("=" * 68)
    print(f"👉 Bước 1: Mở trình duyệt tại địa chỉ: {verification_uri}")
    print(f"👉 Bước 2: Nhập mã xác thực gồm 8 ký tự sau:  {user_code}")
    print("👉 Bước 3: Bấm nút 'Authorize' (Cho phép) trên trang GitHub.")
    print("=" * 68)
    sys.stdout.flush()

    try:
        webbrowser.open(verification_uri)
    except Exception:
        pass

    while True:
        time.sleep(interval)
        poll_data = urllib.parse.urlencode({
            "client_id": GITHUB_CLIENT_ID,
            "device_code": device_code,
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code"
        }).encode("utf-8")
        poll_req = urllib.request.Request(
            "https://github.com/login/oauth/access_token",
            data=poll_data,
            headers={"Accept": "application/json", "User-Agent": "banem-thcs-uploader"},
            method="POST"
        )
        with urllib.request.urlopen(poll_req, timeout=20) as resp:
            res = json.loads(resp.read().decode("utf-8"))

        if "access_token" in res:
            print("\n✅ Đã xác thực GitHub thành công!")
            return res["access_token"]
        err = res.get("error")
        if err == "authorization_pending":
            continue
        elif err == "slow_down":
            interval += 5
        else:
            raise RuntimeError(f"Lỗi xác thực GitHub: {res}")


def collect_project_files():
    ignore_dirs = {".git", "node_modules", "__pycache__"}
    files_list = []
    for root, dirs, files in os.walk(WORKSPACE_DIR):
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        for fname in files:
            full_path = os.path.join(root, fname)
            rel_path = os.path.relpath(full_path, WORKSPACE_DIR).replace("\\", "/")
            files_list.append((rel_path, full_path))
    return files_list


def upload_repository(token):
    status, user_info = github_api("GET", "/user", token)
    if status != 200:
        raise RuntimeError(f"Không thể lấy thông tin tài khoản GitHub: {user_info}")

    owner = user_info["login"]
    print(f"👤 Tài khoản GitHub: {owner}")

    # Check if repo exists
    status, repo_info = github_api("GET", f"/repos/{owner}/{REPO_NAME}", token)
    if status == 404:
        print(f"📦 Đang khởi tạo kho chứa mới: {owner}/{REPO_NAME} ...")
        status, repo_info = github_api(
            "POST",
            "/user/repos",
            token,
            {
                "name": REPO_NAME,
                "description": REPO_DESC,
                "private": False,
                "auto_init": True,
            },
        )
        if status not in (200, 201):
            raise RuntimeError(f"Không thể tạo repository: {repo_info}")
        time.sleep(2)
    else:
        print(f"📦 Đã tìm thấy kho chứa: {owner}/{REPO_NAME}")

    # Get latest commit SHA on main (or default branch)
    default_branch = repo_info.get("default_branch", "main")
    status, ref_info = github_api("GET", f"/repos/{owner}/{REPO_NAME}/git/ref/heads/{default_branch}", token)
    if status != 200:
        # Repo might be completely empty, initialize README via Contents API
        github_api(
            "PUT",
            f"/repos/{owner}/{REPO_NAME}/contents/README.md",
            token,
            {
                "message": "Initial commit",
                "content": base64.b64encode(b"# banem THCS").decode("ascii"),
            },
        )
        time.sleep(1)
        status, ref_info = github_api("GET", f"/repos/{owner}/{REPO_NAME}/git/ref/heads/{default_branch}", token)

    base_commit_sha = ref_info["object"]["sha"]

    # Upload all project files as Git blobs
    files_to_upload = collect_project_files()
    tree_items = []
    print(f"🚀 Đang tải {len(files_to_upload)} tệp mã nguồn & APK lên GitHub...")

    for idx, (rel_path, full_path) in enumerate(files_to_upload, 1):
        with open(full_path, "rb") as f:
            raw_bytes = f.read()
        b64_content = base64.b64encode(raw_bytes).decode("ascii")
        st, blob_res = github_api(
            "POST",
            f"/repos/{owner}/{REPO_NAME}/git/blobs",
            token,
            {"content": b64_content, "encoding": "base64"},
        )
        if st not in (200, 201):
            raise RuntimeError(f"Lỗi tải file {rel_path}: {blob_res}")

        tree_items.append({
            "path": rel_path,
            "mode": "100644",
            "type": "blob",
            "sha": blob_res["sha"],
        })
        print(f"   [{idx}/{len(files_to_upload)}] Đã tải: {rel_path}")

    # Create Git Tree
    st, tree_res = github_api(
        "POST",
        f"/repos/{owner}/{REPO_NAME}/git/trees",
        token,
        {"base_tree": base_commit_sha, "tree": tree_items},
    )
    if st not in (200, 201):
        raise RuntimeError(f"Lỗi tạo Git Tree: {tree_res}")

    # Create Commit
    st, commit_res = github_api(
        "POST",
        f"/repos/{owner}/{REPO_NAME}/git/commits",
        token,
        {
            "message": "Update Chatbot banem - Trợ lý tư vấn học sinh THCS (13-15 tuổi) & Android APK",
            "tree": tree_res["sha"],
            "parents": [base_commit_sha],
        },
    )
    if st not in (200, 201):
        raise RuntimeError(f"Lỗi tạo Commit: {commit_res}")

    # Update branch reference
    st, _ = github_api(
        "PATCH",
        f"/repos/{owner}/{REPO_NAME}/git/refs/heads/{default_branch}",
        token,
        {"sha": commit_res["sha"], "force": True},
    )

    # Enable GitHub Pages from main branch root
    github_api(
        "POST",
        f"/repos/{owner}/{REPO_NAME}/pages",
        token,
        {"source": {"branch": default_branch, "path": "/"}},
    )

    repo_url = f"https://github.com/{owner}/{REPO_NAME}"
    pages_url = f"https://{owner}.github.io/{REPO_NAME}/www/"
    apk_url = f"https://{owner}.github.io/{REPO_NAME}/www/TroLyTuVanTHCS-Android.apk"

    print("\n" + "★" * 68)
    print("🎉 ĐÃ TẢI TOÀN BỘ MÃ NGUỒN LÊN GITHUB THÀNH CÔNG!")
    print(f"🔗 Kho mã nguồn GitHub : {repo_url}")
    print(f"🌐 Link Web App cố định: {pages_url}")
    print(f"📥 Link tải APK cố định: {apk_url}")
    print("★" * 68)


def main():
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if len(sys.argv) > 1 and sys.argv[1].strip():
        token = sys.argv[1].strip()
    if not token:
        token = get_token_via_device_flow()
    upload_repository(token)


if __name__ == "__main__":
    main()
