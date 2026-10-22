#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Trình đóng gói tự động Web App (www/) thành file cài đặt Android (.apk)
Dành cho dự án: Bạn Đồng Hành THCS - Trợ Lý Tư Vấn Học Sinh (13, 14, 15 tuổi)
"""

import os
import sys
import zlib
import struct
import hashlib
import base64
import zipfile
import datetime

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

WORKSPACE_DIR = os.path.dirname(os.path.abspath(__file__))
WWW_DIR = os.path.join(WORKSPACE_DIR, "www")
APK_OUTPUT_PATH = os.path.join(WORKSPACE_DIR, "TroLyTuVanTHCS-Android.apk")


# ============================================================================
# 1. TẠO ICON PNG CHUẨN CHO WEB APP (PWA) & ANDROID APK
# ============================================================================
def create_app_icon_png(width, height):
    """Tạo file ảnh PNG (RGBA) có biểu tượng đám mây Mây & trái tim trên nền Gradient Tím - Hồng."""
    raw_rows = bytearray()
    cx, cy = width / 2.0, height / 2.0
    radius = width * 0.45

    for y in range(height):
        raw_rows.append(0)  # Filter type 0 (None)
        ny = y / float(height)
        for x in range(width):
            nx = x / float(width)
            # Rounded square mask
            dx = max(abs(x - cx) - (width * 0.28), 0.0)
            dy = max(abs(y - cy) - (height * 0.28), 0.0)
            dist_corner = (dx * dx + dy * dy) ** 0.5
            corner_r = width * 0.22

            if dist_corner > corner_r:
                raw_rows.extend((0, 0, 0, 0))
                continue

            # Background gradient (#4F46E5 -> #7C3AED -> #EC4899)
            t = (nx + ny) * 0.5
            r = int(79 + (236 - 79) * t)
            g = int(70 + (72 - 70) * t)
            b = int(229 + (153 - 229) * t)

            # Cloud body in center
            c1 = ((nx - 0.50) ** 2) / (0.24 ** 2) + ((ny - 0.50) ** 2) / (0.17 ** 2)
            c2 = ((nx - 0.36) ** 2) / (0.14 ** 2) + ((ny - 0.53) ** 2) / (0.12 ** 2)
            c3 = ((nx - 0.64) ** 2) / (0.14 ** 2) + ((ny - 0.53) ** 2) / (0.12 ** 2)
            c4 = ((nx - 0.48) ** 2) / (0.16 ** 2) + ((ny - 0.40) ** 2) / (0.13 ** 2)

            if min(c1, c2, c3, c4) <= 1.0:
                r, g, b = 255, 255, 255
                # Cute eyes & smile on cloud
                eye_l = (nx - 0.41) ** 2 + (ny - 0.48) ** 2
                eye_r = (nx - 0.59) ** 2 + (ny - 0.48) ** 2
                smile = abs(((nx - 0.50) ** 2) / (0.07 ** 2) + ((ny - 0.52) ** 2) / (0.05 ** 2) - 1.0)
                if eye_l < 0.0007 or eye_r < 0.0007 or (ny > 0.53 and smile < 0.28 and abs(nx - 0.50) < 0.065):
                    r, g, b = 79, 70, 229

            raw_rows.extend((r, g, b, 255))

    def png_chunk(chunk_type, data):
        crc = zlib.crc32(chunk_type + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + chunk_type + data + struct.pack(">I", crc)

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    idat = zlib.compress(bytes(raw_rows), 9)
    return (
        b"\x89PNG\r\n\x1a\n"
        + png_chunk(b"IHDR", ihdr)
        + png_chunk(b"IDAT", idat)
        + png_chunk(b"IEND", b"")
    )


# ============================================================================
# 2. TẠO ANDROID BINARY XML (AndroidManifest.xml) CHUẨN AXML
# ============================================================================
def build_binary_android_manifest():
    """
    Biên dịch AndroidManifest.xml sang định dạng nhị phân AXML (RES_XML_TYPE = 0x0003)
    Khai báo quyền INTERNET, usesCleartextTraffic, và MainActivity khởi chạy WebView.
    """
    # Danh sách chuỗi có gắn Resource ID hệ thống Android (phải đứng đầu String Pool)
    attr_strings = [
        ("theme", 0x01010000),
        ("label", 0x01010001),
        ("name", 0x01010003),
        ("exported", 0x01010010),
        ("configChanges", 0x0101001F),
        ("minSdkVersion", 0x0101020C),
        ("versionCode", 0x0101021B),
        ("versionName", 0x0101021C),
        ("targetSdkVersion", 0x01010270),
        ("usesCleartextTraffic", 0x010104EC),
    ]

    other_strings = [
        "android",
        "http://schemas.android.com/apk/res/android",
        "manifest",
        "package",
        "vn.edu.thcs.trolytuvan",
        "1.0.0",
        "uses-sdk",
        "uses-permission",
        "android.permission.INTERNET",
        "application",
        "banem - Tư Vấn THCS (13-15)",
        "activity",
        "vn.edu.thcs.trolytuvan.MainActivity",
        "intent-filter",
        "action",
        "android.intent.action.MAIN",
        "category",
        "android.intent.category.LAUNCHER",
    ]

    all_strings = [s[0] for s in attr_strings] + other_strings
    str_index = {s: i for i, s in enumerate(all_strings)}

    # Build String Pool Chunk (UTF-16LE)
    encoded_strings = []
    for s in all_strings:
        u16 = s.encode("utf-16le")
        char_len = len(s)
        encoded_strings.append(struct.pack("<H", char_len) + u16 + b"\x00\x00")

    offsets = []
    cur_offset = 0
    for es in encoded_strings:
        offsets.append(cur_offset)
        cur_offset += len(es)

    strings_blob = b"".join(encoded_strings)
    while len(strings_blob) % 4 != 0:
        strings_blob += b"\x00"

    string_count = len(all_strings)
    header_size = 28
    strings_start = header_size + 4 * string_count
    chunk_size = strings_start + len(strings_blob)

    string_pool_chunk = (
        struct.pack(
            "<HHIIIIII",
            0x0001,  # RES_STRING_POOL_TYPE
            header_size,
            chunk_size,
            string_count,
            0,  # styleCount
            0,  # flags (UTF-16)
            strings_start,
            0,  # stylesStart
        )
        + b"".join(struct.pack("<I", off) for off in offsets)
        + strings_blob
    )

    # Build Resource ID Map Chunk (0x0180)
    res_ids = [s[1] for s in attr_strings]
    res_map_size = 8 + 4 * len(res_ids)
    res_map_chunk = struct.pack("<HHI", 0x0180, 8, res_map_size) + b"".join(
        struct.pack("<I", rid) for rid in res_ids
    )

    NS_URI = str_index["http://schemas.android.com/apk/res/android"]
    NS_PREFIX = str_index["android"]
    NO_INDEX = 0xFFFFFFFF

    def make_ns_chunk(is_start, line):
        ctype = 0x0100 if is_start else 0x0101
        return struct.pack("<HHIIIII", ctype, 16, 24, line, NO_INDEX, NS_PREFIX, NS_URI)

    def make_attr(ns_idx, name_str, raw_str, data_type, data_val):
        name_idx = str_index[name_str]
        raw_idx = str_index[raw_str] if raw_str is not None else NO_INDEX
        return struct.pack("<IIIHBBI", ns_idx, name_idx, raw_idx, 8, 0, data_type, data_val)

    def make_start_element(tag_name, line, attrs):
        attr_blob = b"".join(attrs)
        size = 36 + len(attr_blob)
        return (
            struct.pack(
                "<HHIIIIIHHHHHH",
                0x0102,  # RES_XML_START_ELEMENT_TYPE
                16,
                size,
                line,
                NO_INDEX,
                NO_INDEX,
                str_index[tag_name],
                0x0014,  # attributeStart
                0x0014,  # attributeSize (20 bytes)
                len(attrs),
                0,
                0,
                0,
            )
            + attr_blob
        )

    def make_end_element(tag_name, line):
        return struct.pack(
            "<HHIIIII",
            0x0103,  # RES_XML_END_ELEMENT_TYPE
            16,
            24,
            line,
            NO_INDEX,
            NO_INDEX,
            str_index[tag_name],
        )

    TYPE_STRING = 0x03
    TYPE_INT_DEC = 0x10
    TYPE_INT_HEX = 0x11
    TYPE_INT_BOOL = 0x12
    TYPE_REFERENCE = 0x01

    xml_nodes = [
        make_ns_chunk(True, 2),
        # <manifest>
        make_start_element(
            "manifest",
            2,
            [
                make_attr(NS_URI, "versionCode", None, TYPE_INT_DEC, 1),
                make_attr(NS_URI, "versionName", "1.0.0", TYPE_STRING, str_index["1.0.0"]),
                make_attr(NO_INDEX, "package", "vn.edu.thcs.trolytuvan", TYPE_STRING, str_index["vn.edu.thcs.trolytuvan"]),
            ],
        ),
        # <uses-sdk android:minSdkVersion="21" android:targetSdkVersion="29" />
        make_start_element(
            "uses-sdk",
            4,
            [
                make_attr(NS_URI, "minSdkVersion", None, TYPE_INT_DEC, 21),
                make_attr(NS_URI, "targetSdkVersion", None, TYPE_INT_DEC, 29),
            ],
        ),
        make_end_element("uses-sdk", 4),
        # <uses-permission android:name="android.permission.INTERNET" />
        make_start_element(
            "uses-permission",
            5,
            [
                make_attr(NS_URI, "name", "android.permission.INTERNET", TYPE_STRING, str_index["android.permission.INTERNET"]),
            ],
        ),
        make_end_element("uses-permission", 5),
        # <application>
        make_start_element(
            "application",
            6,
            [
                make_attr(NS_URI, "theme", None, TYPE_REFERENCE, 0x0103012B),  # Theme.DeviceDefault.NoActionBar
                make_attr(NS_URI, "label", "banem - Tư Vấn THCS (13-15)", TYPE_STRING, str_index["banem - Tư Vấn THCS (13-15)"]),
                make_attr(NS_URI, "usesCleartextTraffic", None, TYPE_INT_BOOL, 0xFFFFFFFF),
            ],
        ),
        # <activity>
        make_start_element(
            "activity",
            7,
            [
                make_attr(NS_URI, "name", "vn.edu.thcs.trolytuvan.MainActivity", TYPE_STRING, str_index["vn.edu.thcs.trolytuvan.MainActivity"]),
                make_attr(NS_URI, "exported", None, TYPE_INT_BOOL, 0xFFFFFFFF),
                make_attr(NS_URI, "configChanges", None, TYPE_INT_HEX, 0x000004A0),
            ],
        ),
        # <intent-filter>
        make_start_element("intent-filter", 8, []),
        make_start_element(
            "action",
            9,
            [make_attr(NS_URI, "name", "android.intent.action.MAIN", TYPE_STRING, str_index["android.intent.action.MAIN"])],
        ),
        make_end_element("action", 9),
        make_start_element(
            "category",
            10,
            [make_attr(NS_URI, "name", "android.intent.category.LAUNCHER", TYPE_STRING, str_index["android.intent.category.LAUNCHER"])],
        ),
        make_end_element("category", 10),
        make_end_element("intent-filter", 11),
        make_end_element("activity", 12),
        make_end_element("application", 13),
        make_end_element("manifest", 14),
        make_ns_chunk(False, 14),
    ]

    body = string_pool_chunk + res_map_chunk + b"".join(xml_nodes)
    total_size = 8 + len(body)
    return struct.pack("<HHI", 0x0003, 8, total_size) + body


# ============================================================================
# 3. TẠO DALVIK EXECUTABLE (classes.dex) KHỞI CHẠY WEBVIEW TOÀN MÀN HÌNH
# ============================================================================
def build_webview_classes_dex():
    """
    Tạo file classes.dex hợp lệ chứa class vn.edu.thcs.trolytuvan.MainActivity
    kế thừa android.app.Activity, khởi tạo WebView, bật JavaScript + DOMStorage
    và nạp file:///android_asset/www/index.html.
    """
    strings = [
        "<init>",                                   # 0
        "Landroid/app/Activity;",                   # 1
        "Landroid/os/Bundle;",                      # 2
        "Landroid/view/View;",                      # 3
        "Landroid/webkit/WebChromeClient;",         # 4
        "Landroid/webkit/WebSettings;",             # 5
        "Landroid/webkit/WebView;",                 # 6
        "Landroid/webkit/WebViewClient;",           # 7
        " Landroid/content/Context;",               # placeholder sorted
    ]
    # All strings in a DEX file MUST be sorted lexicographically by UTF-16 code units!
    dex_strings = sorted([
        "<init>",
        "L",
        "Landroid/app/Activity;",
        "Landroid/content/Context;",
        "Landroid/os/Bundle;",
        "Landroid/view/View;",
        "Landroid/webkit/WebChromeClient;",
        "Landroid/webkit/WebSettings;",
        "Landroid/webkit/WebView;",
        "Landroid/webkit/WebViewClient;",
        "Ljava/lang/String;",
        "Lvn/edu/thcs/trolytuvan/MainActivity;",
        "MainActivity.java",
        "V",
        "VL",
        "VZ",
        "Z",
        "file:///android_asset/www/index.html",
        "getSettings",
        "loadUrl",
        "onBackPressed",
        "onCreate",
        "setAllowFileAccess",
        "setContentView",
        "setDomStorageEnabled",
        "setJavaScriptEnabled",
        "setWebChromeClient",
        "setWebViewClient",
    ])
    s_idx = {s: i for i, s in enumerate(dex_strings)}

    # Types (sorted by string_idx)
    type_names = sorted(
        [
            "Landroid/app/Activity;",
            "Landroid/content/Context;",
            "Landroid/os/Bundle;",
            "Landroid/view/View;",
            "Landroid/webkit/WebChromeClient;",
            "Landroid/webkit/WebSettings;",
            "Landroid/webkit/WebView;",
            "Landroid/webkit/WebViewClient;",
            "Ljava/lang/String;",
            "Lvn/edu/thcs/trolytuvan/MainActivity;",
            "V",
            "Z",
        ],
        key=lambda x: s_idx[x],
    )
    t_idx = {t: i for i, t in enumerate(type_names)}

    # Protos: (shorty_str, return_type_str, param_type_list)
    proto_defs = [
        ("L", "Landroid/webkit/WebSettings;", []),
        ("V", "V", []),
        ("VL", "V", ["Landroid/content/Context;"]),
        ("VL", "V", ["Landroid/os/Bundle;"]),
        ("VL", "V", ["Landroid/view/View;"]),
        ("VL", "V", ["Landroid/webkit/WebChromeClient;"]),
        ("VL", "V", ["Landroid/webkit/WebViewClient;"]),
        ("VL", "V", ["Ljava/lang/String;"]),
        ("VZ", "V", ["Z"]),
    ]
    # Sort protos by return_type then params
    proto_defs.sort(key=lambda p: (t_idx[p[1]], [t_idx[x] for x in p[2]]))
    p_idx = {(p[1], tuple(p[2])): i for i, p in enumerate(proto_defs)}

    # Methods: (class_type, return_type, params_tuple, method_name)
    method_defs = [
        ("Landroid/app/Activity;", "V", (), "<init>"),
        ("Landroid/app/Activity;", "V", ("Landroid/os/Bundle;",), "onCreate"),
        ("Landroid/app/Activity;", "V", ("Landroid/view/View;",), "setContentView"),
        ("Landroid/webkit/WebChromeClient;", "V", (), "<init>"),
        ("Landroid/webkit/WebSettings;", "V", ("Z",), "setAllowFileAccess"),
        ("Landroid/webkit/WebSettings;", "V", ("Z",), "setDomStorageEnabled"),
        ("Landroid/webkit/WebSettings;", "V", ("Z",), "setJavaScriptEnabled"),
        ("Landroid/webkit/WebView;", "V", ("Landroid/content/Context;",), "<init>"),
        ("Landroid/webkit/WebView;", "Landroid/webkit/WebSettings;", (), "getSettings"),
        ("Landroid/webkit/WebView;", "V", ("Ljava/lang/String;",), "loadUrl"),
        ("Landroid/webkit/WebView;", "V", ("Landroid/webkit/WebChromeClient;",), "setWebChromeClient"),
        ("Landroid/webkit/WebView;", "V", ("Landroid/webkit/WebViewClient;",), "setWebViewClient"),
        ("Landroid/webkit/WebViewClient;", "V", (), "<init>"),
        ("Lvn/edu/thcs/trolytuvan/MainActivity;", "V", (), "<init>"),
        ("Lvn/edu/thcs/trolytuvan/MainActivity;", "V", ("Landroid/os/Bundle;",), "onCreate"),
    ]
    method_defs.sort(key=lambda m: (t_idx[m[0]], s_idx[m[3]], p_idx[(m[1], m[2])]))
    m_idx = {(m[0], m[3], m[2]): i for i, m in enumerate(method_defs)}

    def uleb128(val):
        out = bytearray()
        while True:
            byte = val & 0x7F
            val >>= 7
            if val != 0:
                byte |= 0x80
                out.append(byte)
            else:
                out.append(byte)
                break
        return bytes(out)

    # Layout fixed header & index tables
    # Header: 0x70 (112 bytes)
    # string_ids: 28 * 4 = 112 bytes
    # type_ids: 12 * 4 = 48 bytes
    # proto_ids: 9 * 12 = 108 bytes
    # method_ids: 15 * 8 = 120 bytes
    # class_defs: 1 * 32 = 32 bytes
    # Total index section = 112 + 112 + 48 + 108 + 120 + 32 = 532 (0x214)

    data_start = 0x214
    data_buf = bytearray()

    def align4():
        while (data_start + len(data_buf)) % 4 != 0:
            data_buf.append(0)

    # 1. Type lists for protos that have parameters
    type_list_offsets = {}
    for i, p in enumerate(proto_defs):
        params = p[2]
        if not params:
            type_list_offsets[i] = 0
        else:
            align4()
            type_list_offsets[i] = data_start + len(data_buf)
            data_buf.extend(struct.pack("<I", len(params)))
            for pt in params:
                data_buf.extend(struct.pack("<H", t_idx[pt]))

    # 2. Code item for <init>()V of MainActivity
    # registers_size=1, ins_size=1, outs_size=1, tries_size=0
    # insns: invoke-direct {v0}, Landroid/app/Activity;-><init>()V (70 10 mmmm 00 00)
    #        return-void (0e 00)
    align4()
    init_code_off = data_start + len(data_buf)
    m_act_init = m_idx[("Landroid/app/Activity;", "<init>", ())]
    init_insns = struct.pack("<HHHH", 0x1070, m_act_init, 0x0000, 0x000E)
    data_buf.extend(struct.pack("<HHHHII", 1, 1, 1, 0, 0, len(init_insns) // 2) + init_insns)

    # 3. Code item for onCreate(Bundle)V of MainActivity
    # registers_size=5 (v0, v1, v2: locals; v3=this, v4=savedInstanceState)
    # ins_size=2, outs_size=2
    align4()
    oncreate_code_off = data_start + len(data_buf)

    m_super_oncreate = m_idx[("Landroid/app/Activity;", "onCreate", ("Landroid/os/Bundle;",))]
    m_wv_init = m_idx[("Landroid/webkit/WebView;", "<init>", ("Landroid/content/Context;",))]
    m_wv_settings = m_idx[("Landroid/webkit/WebView;", "getSettings", ())]
    m_ws_js = m_idx[("Landroid/webkit/WebSettings;", "setJavaScriptEnabled", ("Z",))]
    m_ws_dom = m_idx[("Landroid/webkit/WebSettings;", "setDomStorageEnabled", ("Z",))]
    m_ws_file = m_idx[("Landroid/webkit/WebSettings;", "setAllowFileAccess", ("Z",))]
    m_wvc_init = m_idx[("Landroid/webkit/WebViewClient;", "<init>", ())]
    m_wv_setwvc = m_idx[("Landroid/webkit/WebView;", "setWebViewClient", ("Landroid/webkit/WebViewClient;",))]
    m_wcc_init = m_idx[("Landroid/webkit/WebChromeClient;", "<init>", ())]
    m_wv_setwcc = m_idx[("Landroid/webkit/WebView;", "setWebChromeClient", ("Landroid/webkit/WebChromeClient;",))]
    m_set_content = m_idx[("Landroid/app/Activity;", "setContentView", ("Landroid/view/View;",))]
    m_wv_load = m_idx[("Landroid/webkit/WebView;", "loadUrl", ("Ljava/lang/String;",))]

    t_wv = t_idx["Landroid/webkit/WebView;"]
    t_wvc = t_idx["Landroid/webkit/WebViewClient;"]
    t_wcc = t_idx["Landroid/webkit/WebChromeClient;"]
    s_url = s_idx["file:///android_asset/www/index.html"]

    insns = bytearray()
    # invoke-super {v3, v4}, Activity.onCreate(Bundle)
    insns.extend(struct.pack("<HHH", 0x206F, m_super_oncreate, 0x0043))
    # new-instance v0, WebView
    insns.extend(struct.pack("<HH", 0x0022, t_wv))
    # invoke-direct {v0, v3}, WebView.<init>(Context)
    insns.extend(struct.pack("<HHH", 0x2070, m_wv_init, 0x0030))
    # invoke-virtual {v0}, WebView.getSettings()
    insns.extend(struct.pack("<HHH", 0x106E, m_wv_settings, 0x0000))
    # move-result-object v1
    insns.extend(struct.pack("<H", 0x010C))
    # const/4 v2, #1
    insns.extend(struct.pack("<H", 0x1212))
    # invoke-virtual {v1, v2}, WebSettings.setJavaScriptEnabled(true)
    insns.extend(struct.pack("<HHH", 0x206E, m_ws_js, 0x0021))
    # invoke-virtual {v1, v2}, WebSettings.setDomStorageEnabled(true)
    insns.extend(struct.pack("<HHH", 0x206E, m_ws_dom, 0x0021))
    # invoke-virtual {v1, v2}, WebSettings.setAllowFileAccess(true)
    insns.extend(struct.pack("<HHH", 0x206E, m_ws_file, 0x0021))
    # new-instance v1, WebViewClient
    insns.extend(struct.pack("<HH", 0x0122, t_wvc))
    # invoke-direct {v1}, WebViewClient.<init>()
    insns.extend(struct.pack("<HHH", 0x1070, m_wvc_init, 0x0001))
    # invoke-virtual {v0, v1}, WebView.setWebViewClient(v1)
    insns.extend(struct.pack("<HHH", 0x206E, m_wv_setwvc, 0x0010))
    # new-instance v1, WebChromeClient
    insns.extend(struct.pack("<HH", 0x0122, t_wcc))
    # invoke-direct {v1}, WebChromeClient.<init>()
    insns.extend(struct.pack("<HHH", 0x1070, m_wcc_init, 0x0001))
    # invoke-virtual {v0, v1}, WebView.setWebChromeClient(v1)
    insns.extend(struct.pack("<HHH", 0x206E, m_wv_setwcc, 0x0010))
    # invoke-virtual {v3, v0}, Activity.setContentView(v0)
    insns.extend(struct.pack("<HHH", 0x206E, m_set_content, 0x0003))
    # const-string v1, "file:///android_asset/www/index.html"
    insns.extend(struct.pack("<HH", 0x011A, s_url))
    # invoke-virtual {v0, v1}, WebView.loadUrl(v1)
    insns.extend(struct.pack("<HHH", 0x206E, m_wv_load, 0x0010))
    # return-void
    insns.extend(struct.pack("<H", 0x000E))

    data_buf.extend(struct.pack("<HHHHII", 5, 2, 2, 0, 0, len(insns) // 2) + insns)

    # 4. String data items
    string_data_offsets = []
    for s in dex_strings:
        string_data_offsets.append(data_start + len(data_buf))
        utf8 = s.encode("utf-8")
        data_buf.extend(uleb128(len(s)) + utf8 + b"\x00")

    # 5. Class data item for MainActivity
    class_data_off = data_start + len(data_buf)
    m_main_init = m_idx[("Lvn/edu/thcs/trolytuvan/MainActivity;", "<init>", ())]
    m_main_oncreate = m_idx[("Lvn/edu/thcs/trolytuvan/MainActivity;", "onCreate", ("Landroid/os/Bundle;",))]

    class_data = (
        uleb128(0)  # static_fields_size
        + uleb128(0)  # instance_fields_size
        + uleb128(1)  # direct_methods_size (<init>)
        + uleb128(1)  # virtual_methods_size (onCreate)
        # direct method: <init> (PUBLIC | CONSTRUCTOR = 0x10001)
        + uleb128(m_main_init)
        + uleb128(0x10001)
        + uleb128(init_code_off)
        # virtual method: onCreate (PROTECTED = 0x0004)
        + uleb128(m_main_oncreate)
        + uleb128(0x0004)
        + uleb128(oncreate_code_off)
    )
    data_buf.extend(class_data)

    # 6. Map list at the end of data section
    align4()
    map_off = data_start + len(data_buf)
    num_type_lists = sum(1 for p in proto_defs if p[2])
    map_items = [
        (0x0000, 1, 0x0000),                        # TYPE_HEADER_ITEM
        (0x0001, len(dex_strings), 0x0070),         # TYPE_STRING_ID_ITEM
        (0x0002, len(type_names), 0x00E0),          # TYPE_TYPE_ID_ITEM
        (0x0003, len(proto_defs), 0x0110),          # TYPE_PROTO_ID_ITEM
        (0x0005, len(method_defs), 0x017C),         # TYPE_METHOD_ID_ITEM
        (0x0006, 1, 0x01F4),                        # TYPE_CLASS_DEF_ITEM
        (0x1001, num_type_lists, data_start),       # TYPE_TYPE_LIST
        (0x2001, 2, init_code_off),                 # TYPE_CODE_ITEM
        (0x2002, len(dex_strings), string_data_offsets[0]),  # TYPE_STRING_DATA_ITEM
        (0x2000, 1, class_data_off),                # TYPE_CLASS_DATA_ITEM
        (0x1000, 1, map_off),                       # TYPE_MAP_LIST
    ]
    data_buf.extend(struct.pack("<I", len(map_items)))
    for mtype, msize, moff in map_items:
        data_buf.extend(struct.pack("<HHII", mtype, 0, msize, moff))

    # Build index tables
    string_ids_bin = b"".join(struct.pack("<I", off) for off in string_data_offsets)
    type_ids_bin = b"".join(struct.pack("<I", s_idx[t]) for t in type_names)
    proto_ids_bin = b"".join(
        struct.pack("<III", s_idx[p[0]], t_idx[p[1]], type_list_offsets[i])
        for i, p in enumerate(proto_defs)
    )
    method_ids_bin = b"".join(
        struct.pack("<HHI", t_idx[m[0]], p_idx[(m[1], m[2])], s_idx[m[3]])
        for m in method_defs
    )
    class_defs_bin = struct.pack(
        "<IIIIIIII",
        t_idx["Lvn/edu/thcs/trolytuvan/MainActivity;"],  # class_idx
        0x0001,  # PUBLIC
        t_idx["Landroid/app/Activity;"],  # superclass_idx
        0,  # interfaces_off
        s_idx["MainActivity.java"],  # source_file_idx
        0,  # annotations_off
        class_data_off,  # class_data_off
        0,  # static_values_off
    )

    file_size = data_start + len(data_buf)
    data_size = len(data_buf)

    header_after_sig = struct.pack(
        "<IIIIIIIIIIIIIIIIIIII",
        file_size,
        0x70,  # header_size
        0x12345678,  # endian_tag
        0,  # link_size
        0,  # link_off
        map_off,
        len(dex_strings),
        0x0070,  # string_ids_off
        len(type_names),
        0x00E0,  # type_ids_off
        len(proto_defs),
        0x0110,  # proto_ids_off
        0,  # field_ids_size
        0,  # field_ids_off
        len(method_defs),
        0x017C,  # method_ids_off
        1,  # class_defs_size
        0x01F4,  # class_defs_off
        data_size,
        data_start,
    )

    body_after_sig = (
        header_after_sig
        + string_ids_bin
        + type_ids_bin
        + proto_ids_bin
        + method_ids_bin
        + class_defs_bin
        + bytes(data_buf)
    )

    sha1_sig = hashlib.sha1(body_after_sig).digest()
    adler_val = zlib.adler32(sha1_sig + body_after_sig) & 0xFFFFFFFF

    return b"dex\n035\x00" + struct.pack("<I", adler_val) + sha1_sig + body_after_sig


# ============================================================================
# 4. KÝ SỐ APK (APK SIGNATURE SCHEME V1 + V2 RSA-2048 CHUẨN ANDROID 7 -> 15)
# ============================================================================
def generate_rsa_keypair_and_cert():
    """
    Tạo khóa RSA-2048 và Chứng chỉ số X.509 DER (Android Debug Certificate)
    bằng toán học số nguyên lớn tích hợp sẵn trong Python.
    """
    # Cố định 2 số nguyên tố 1024-bit chuẩn để tạo khóa nhanh tức thì & nhất quán
    # (Tạo bằng Miller-Rabin deterministic seed cho khóa Debug của dự án)
    def is_probable_prime(n):
        if n % 2 == 0:
            return False
        d = n - 1
        r = 0
        while d % 2 == 0:
            d //= 2
            r += 1
        for a in (2, 3, 5, 7, 11, 13, 17, 19, 23):
            x = pow(a, d, n)
            if x == 1 or x == n - 1:
                continue
            for _ in range(r - 1):
                x = pow(x, 2, n)
                if x == n - 1:
                    break
            else:
                return False
        return True

    def find_prime(seed_str):
        h = hashlib.sha512(seed_str.encode()).digest() + hashlib.sha512((seed_str + "_2").encode()).digest()
        val = int.from_bytes(h, "big") | (1 << 1023) | 1
        while not is_probable_prime(val):
            val += 2
        return val

    p = find_prime("THCS_COUNSELOR_ANDROID_PRIME_P_2026")
    q = find_prime("THCS_COUNSELOR_ANDROID_PRIME_Q_2026")
    n = p * q
    e = 65537
    phi = (p - 1) * (q - 1)
    d = pow(e, -1, phi)

    return n, e, d


def asn1_len(length):
    if length < 0x80:
        return bytes([length])
    lb = length.to_bytes((length.bit_length() + 7) // 8, "big")
    return bytes([0x80 | len(lb)]) + lb


def asn1_node(tag, content):
    return bytes([tag]) + asn1_len(len(content)) + content


def asn1_int(val):
    if val == 0:
        b = b"\x00"
    else:
        b = val.to_bytes((val.bit_length() + 7) // 8, "big")
        if b[0] & 0x80:
            b = b"\x00" + b
    return asn1_node(0x02, b)


def asn1_seq(items):
    return asn1_node(0x30, b"".join(items))


def asn1_set(items):
    return asn1_node(0x31, b"".join(items))


def rsa_pkcs1_sha256_sign(message_bytes, n, d):
    digest = hashlib.sha256(message_bytes).digest()
    # DigestInfo cho SHA-256 (RFC 3447)
    digest_info_prefix = bytes.fromhex("3031300d060960864801650304020105000420")
    t = digest_info_prefix + digest
    k = 256  # 2048 bits
    ps_len = k - len(t) - 3
    em = b"\x00\x01" + (b"\xff" * ps_len) + b"\x00" + t
    m_int = int.from_bytes(em, "big")
    s_int = pow(m_int, d, n)
    return s_int.to_bytes(k, "big")


def build_x509_and_spki(n, e, d):
    # SubjectPublicKeyInfo (SPKI)
    rsa_pub_key = asn1_seq([asn1_int(n), asn1_int(e)])
    bit_string = asn1_node(0x03, b"\x00" + rsa_pub_key)
    alg_rsa = bytes.fromhex("300d06092a864886f70d0101010500")  # rsaEncryption OID
    spki = asn1_seq([alg_rsa, bit_string])

    # X.509 v3 TBSCertificate
    version_v3 = asn1_node(0xA0, asn1_int(2))
    serial = asn1_int(20261021)
    sig_alg_sha256_rsa = bytes.fromhex("300d06092a864886f70d01010b0500")  # sha256WithRSAEncryption

    # RDN: CN=TroLyTHCS
    oid_cn = bytes.fromhex("0603550403")
    val_cn = asn1_node(0x0C, b"TroLyTuVanTHCS")
    name_dn = asn1_seq([asn1_set([asn1_seq([oid_cn, val_cn])])])

    t_start = asn1_node(0x17, b"240101000000Z")
    t_end = asn1_node(0x17, b"491231235959Z")
    validity = asn1_seq([t_start, t_end])

    tbs_cert = asn1_seq([
        version_v3,
        serial,
        sig_alg_sha256_rsa,
        name_dn,
        validity,
        name_dn,
        spki,
    ])

    cert_sig = rsa_pkcs1_sha256_sign(tbs_cert, n, d)
    x509_der = asn1_seq([
        tbs_cert,
        sig_alg_sha256_rsa,
        asn1_node(0x03, b"\x00" + cert_sig),
    ])

    return x509_der, spki, name_dn, serial


def build_pkcs7_cert_rsa(cert_sf_bytes, x509_der, name_dn, serial, n, d):
    """Tạo file META-INF/CERT.RSA (PKCS#7 SignedData) cho APK Signature v1."""
    sig_bytes = rsa_pkcs1_sha256_sign(cert_sf_bytes, n, d)
    oid_data = bytes.fromhex("06092a864886f70d010701")
    oid_signed_data = bytes.fromhex("06092a864886f70d010702")
    alg_sha256 = bytes.fromhex("300d06096086480165030402010500")
    alg_rsa = bytes.fromhex("300d06092a864886f70d0101010500")

    issuer_and_serial = asn1_seq([name_dn, serial])
    signer_info = asn1_seq([
        asn1_int(1),
        issuer_and_serial,
        alg_sha256,
        alg_rsa,
        asn1_node(0x04, sig_bytes),
    ])

    signed_data = asn1_seq([
        asn1_int(1),
        asn1_set([alg_sha256]),
        asn1_seq([oid_data]),
        asn1_node(0xA0, x509_der),
        asn1_set([signer_info]),
    ])

    return asn1_seq([oid_signed_data, asn1_node(0xA0, signed_data)])


def compute_apk_v2_chunk_digest(sections):
    """Tính SHA-256 merkle-tree digest theo chuẩn APK Signature Scheme v2."""
    CHUNK_SIZE = 1024 * 1024
    chunk_digests = []
    for sec in sections:
        pos = 0
        sec_len = len(sec)
        while pos < sec_len:
            chunk = sec[pos : pos + CHUNK_SIZE]
            pos += CHUNK_SIZE
            h = hashlib.sha256()
            h.update(b"\xa5")
            h.update(struct.pack("<I", len(chunk)))
            h.update(chunk)
            chunk_digests.append(h.digest())

    top = hashlib.sha256()
    top.update(b"\x5a")
    top.update(struct.pack("<I", len(chunk_digests)))
    for cd in chunk_digests:
        top.update(cd)
    return top.digest()


def inject_apk_v2_signature_block(zip_bytes, x509_der, spki_der, n, d):
    """Chèn APK Signing Block v2 (ID 0x7109871a) vào trước Central Directory của file APK."""
    # Tìm End of Central Directory (EOCD: 0x06054b50)
    eocd_pos = zip_bytes.rfind(b"PK\x05\x06")
    if eocd_pos < 0:
        raise ValueError("Invalid ZIP structure")

    cd_size = struct.unpack("<I", zip_bytes[eocd_pos + 12 : eocd_pos + 16])[0]
    cd_offset = struct.unpack("<I", zip_bytes[eocd_pos + 16 : eocd_pos + 20])[0]

    before_cd = zip_bytes[:cd_offset]
    central_dir = zip_bytes[cd_offset:eocd_pos]
    eocd = bytearray(zip_bytes[eocd_pos:])

    def lp_slice(b):
        return struct.pack("<I", len(b)) + b

    # Để tính digest chính xác, EOCD trong quá trình hash phải chứa offset của Central Directory SAU khi chèn khối v2
    # Nhưng kích thước khối v2 là cố định với RSA-2048, nên ta tạo nháp 1 lần để lấy đúng độ dài khối v2
    def build_sig_block_for_eocd(test_eocd):
        top_digest = compute_apk_v2_chunk_digest([before_cd, central_dir, bytes(test_eocd)])
        # signature algorithm 0x0103 = RSA_PKCS1_V1_5_WITH_SHA256
        digest_entry = lp_slice(struct.pack("<I", 0x0103) + lp_slice(top_digest))
        digests_seq = lp_slice(digest_entry)
        certs_seq = lp_slice(lp_slice(x509_der))
        additional_attrs = lp_slice(b"")
        signed_data = digests_seq + certs_seq + additional_attrs

        sig_bytes = rsa_pkcs1_sha256_sign(signed_data, n, d)
        sig_entry = lp_slice(struct.pack("<I", 0x0103) + lp_slice(sig_bytes))
        signatures_seq = lp_slice(sig_entry)

        signer = lp_slice(lp_slice(signed_data) + signatures_seq + lp_slice(spki_der))
        signers_list = lp_slice(signer)

        pair_payload = struct.pack("<I", 0x7109871A) + signers_list
        pair = struct.pack("<Q", len(pair_payload)) + pair_payload

        # Padding pair (ID 0x42726577) để tổng kích thước APK Signing Block chia hết cho 4096 bytes
        base_block_len = 8 + len(pair) + 8 + 16
        rem = base_block_len % 4096
        if rem != 0:
            pad_total = (4096 - rem) if (4096 - rem) >= 12 else (4096 - rem + 4096)
            pad_payload = struct.pack("<I", 0x42726577) + (b"\x00" * (pad_total - 12))
            pad_pair = struct.pack("<Q", len(pad_payload)) + pad_payload
            pairs_blob = pair + pad_pair
        else:
            pairs_blob = pair

        size_of_block = len(pairs_blob) + 8 + 16
        return (
            struct.pack("<Q", size_of_block)
            + pairs_blob
            + struct.pack("<Q", size_of_block)
            + b"APK Sig Block 42"
        )

    dummy_block = build_sig_block_for_eocd(eocd)
    new_cd_offset = cd_offset + len(dummy_block)
    eocd[16:20] = struct.pack("<I", new_cd_offset)
    final_sig_block = build_sig_block_for_eocd(eocd)

    return before_cd + final_sig_block + central_dir + bytes(eocd)


# ============================================================================
# 5. ĐÓNG GÓI TOÀN BỘ DỰ ÁN THÀNH FILE APK HOÀN CHỈNH
# ============================================================================
def build_complete_apk():
    print("1/4: Đang tạo bộ Icon PNG chuẩn cho Web App (PWA) & Android...")
    assets_dir = os.path.join(WWW_DIR, "assets")
    os.makedirs(assets_dir, exist_ok=True)

    icon_192 = create_app_icon_png(192, 192)
    icon_512 = create_app_icon_png(512, 512)
    with open(os.path.join(assets_dir, "icon-192.png"), "wb") as f:
        f.write(icon_192)
    with open(os.path.join(assets_dir, "icon-512.png"), "wb") as f:
        f.write(icon_512)

    print("2/4: Đang biên dịch AndroidManifest.xml (AXML) và mã máy Dalvik (classes.dex)...")
    manifest_axml = build_binary_android_manifest()
    classes_dex = build_webview_classes_dex()

    # Collect all files to put into APK
    apk_entries = {
        "AndroidManifest.xml": manifest_axml,
        "classes.dex": classes_dex,
    }

    for root, _, files in os.walk(WWW_DIR):
        for fname in files:
            if fname.endswith(".apk"):
                continue
            full_path = os.path.join(root, fname)
            rel_path = os.path.relpath(full_path, WWW_DIR).replace("\\", "/")
            zip_entry_name = f"assets/www/{rel_path}"
            with open(full_path, "rb") as f:
                apk_entries[zip_entry_name] = f.read()

    print("3/4: Đang tạo chữ ký số bảo mật RSA-2048 (APK Signature v1 & v2)...")
    n, e, d = generate_rsa_keypair_and_cert()
    x509_der, spki_der, name_dn, serial = build_x509_and_spki(n, e, d)

    # Tạo META-INF/MANIFEST.MF và META-INF/CERT.SF
    manifest_mf_lines = [
        "Manifest-Version: 1.0",
        "Created-By: 1.0 (TroLyTuVanTHCS Builder)",
        "",
    ]
    sf_entries = []

    for entry_name in sorted(apk_entries.keys()):
        data = apk_entries[entry_name]
        sha256_b64 = base64.b64encode(hashlib.sha256(data).digest()).decode("ascii")
        entry_block = f"Name: {entry_name}\r\nSHA-256-Digest: {sha256_b64}\r\n\r\n"
        manifest_mf_lines.append(entry_block.rstrip("\r\n"))
        manifest_mf_lines.append("")

        sf_digest_b64 = base64.b64encode(hashlib.sha256(entry_block.encode("utf-8")).digest()).decode("ascii")
        sf_entries.append(f"Name: {entry_name}\r\nSHA-256-Digest: {sf_digest_b64}\r\n")

    manifest_mf_bytes = "\r\n".join(manifest_mf_lines).encode("utf-8")
    main_manifest_sha256 = base64.b64encode(hashlib.sha256(manifest_mf_bytes).digest()).decode("ascii")

    cert_sf_header = (
        "Signature-Version: 1.0\r\n"
        "Created-By: 1.0 (TroLyTuVanTHCS Builder)\r\n"
        f"SHA-256-Digest-Manifest: {main_manifest_sha256}\r\n"
        "X-Android-APK-Signed: 2\r\n\r\n"
    )
    cert_sf_bytes = (cert_sf_header + "\r\n".join(sf_entries)).encode("utf-8")
    cert_rsa_bytes = build_pkcs7_cert_rsa(cert_sf_bytes, x509_der, name_dn, serial, n, d)

    apk_entries["META-INF/MANIFEST.MF"] = manifest_mf_bytes
    apk_entries["META-INF/CERT.SF"] = cert_sf_bytes
    apk_entries["META-INF/CERT.RSA"] = cert_rsa_bytes

    print("4/4: Đang đóng gói và nhúng khối APK Signing Block v2...")
    import io
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for entry_name in sorted(apk_entries.keys()):
            info = zipfile.ZipInfo(entry_name, date_time=(2026, 1, 1, 0, 0, 0))
            info.external_attr = 0o644 << 16
            # Không nén các file ảnh PNG để tối ưu tốc độ đọc trên Android
            if entry_name.endswith(".png"):
                info.compress_type = zipfile.ZIP_STORED
            else:
                info.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(info, apk_entries[entry_name])

    signed_v2_apk = inject_apk_v2_signature_block(zip_buffer.getvalue(), x509_der, spki_der, n, d)

    with open(APK_OUTPUT_PATH, "wb") as f:
        f.write(signed_v2_apk)

    # Copy 1 bản vào www/ để người dùng mở Web App cũng có nút tải trực tiếp file APK về điện thoại!
    www_apk_path = os.path.join(WWW_DIR, "TroLyTuVanTHCS-Android.apk")
    with open(www_apk_path, "wb") as f:
        f.write(signed_v2_apk)

    size_kb = len(signed_v2_apk) / 1024.0
    print(f"HOÀN TẤT! Đã tạo file APK thành công: {APK_OUTPUT_PATH} ({size_kb:.1f} KB)")


if __name__ == "__main__":
    build_complete_apk()
