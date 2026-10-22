@echo off
chcp 65001 >nul
title Ban Dong Hanh THCS - Web App (Tuoi 13, 14, 15)
echo ==============================================================
echo   KHOI DONG WEB APP: TRO LY TU VAN HOC SINH THCS (13-15 TUOI)
echo ==============================================================
echo.
echo Dang mo trinh duyet tai dia chi: http://localhost:3000
echo Nhan Ctrl + C de dung may chu.
echo.
start "" "http://localhost:3000"
python -m http.server 3000 --directory "%~dp0www"
pause
