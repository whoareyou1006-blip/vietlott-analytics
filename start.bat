@echo off
chcp 65001 >nul
title Vietlott 6/55 Analytics
setlocal

rem --- Chon Python: uu tien runtime portable, neu khong co thi dung python he thong ---
if exist "%~dp0runtime\python\python.exe" (
    set "PY=%~dp0runtime\python\python.exe"
) else (
    set "PY=python"
)

echo ============================================
echo   Vietlott Power 6/55 - Analytics & Du doan
echo ============================================
echo.
echo  [1] Khoi dong app (mo trinh duyet)
echo  [2] Cap nhat du lieu tu 4 nguon
echo  [3] Chay du doan + kiem chung (console)
echo  [4] Thoat
echo.
set /p choice="Chon (1-4): "

if "%choice%"=="1" goto start
if "%choice%"=="2" goto update
if "%choice%"=="3" goto predict
if "%choice%"=="4" exit
goto :eof

:start
start "" http://localhost:8000
"%PY%" "%~dp0app\server.py" 8000
goto :eof

:update
"%PY%" "%~dp0scripts\fetch_data.py"
"%PY%" "%~dp0scripts\build_db.py"
echo.
echo Da cap nhat xong. Nhan phim bat ky de thoat.
pause >nul
goto :eof

:predict
"%PY%" "%~dp0scripts\predict.py"
echo.
pause
goto :eof