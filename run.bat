@echo off
title ScreenBridge
echo ====================================================
echo        ScreenBridge v2 - Baslatiliyor...
echo ====================================================
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [HATA] Python bulunamadi! Lutfen Python 3.10+ kurun ve PATH'e ekleyin.
    pause
    exit /b 1
)

echo [1/2] Bagimliliklar kontrol ediliyor...
pip install -r requirements.txt

echo.
echo [2/2] ScreenBridge sunucusu baslatiliyor...
echo Tarayicinizda acin: http://localhost:8000
echo.
python backend/main.py

pause
