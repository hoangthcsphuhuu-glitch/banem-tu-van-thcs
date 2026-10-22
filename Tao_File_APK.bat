@echo off
chcp 65001 >nul
title Dong goi File APK Android - Ban Dong Hanh THCS
echo ==============================================================
echo   DONG GOI WEB APP THANH FILE APK CAI DAT ANDROID
echo ==============================================================
echo.
python "%~dp0build_apk.py"
echo.
echo File APK da san sang tai: %~dp0TroLyTuVanTHCS-Android.apk
pause
