@echo off
chcp 65001 >nul
echo ========================================
echo    KATANA SAMURAI v3.0 - INSTALLER
echo ========================================
echo.

REM Controllo se Python è installato
echo [INFO] Controllo installazione Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERRORE] Python non trovato!
    echo [INFO] Scaricando e installando Python...
    
    REM Download Python installer
    powershell -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe' -OutFile 'python_installer.exe'"
    
    REM Installa Python silenziosamente
    echo [INFO] Installazione Python in corso...
    python_installer.exe /quiet InstallAllUsers=1 PrependPath=1 Include_test=0
    
    REM Attendi completamento installazione
    timeout /t 30 /nobreak >nul
    
    REM Rimuovi installer
    del python_installer.exe
    
    REM Aggiorna PATH
    call refreshenv
    
    echo [OK] Python installato con successo!
) else (
    echo [OK] Python già installato
    python --version
)

echo.
echo [INFO] Controllo dipendenze Python...

REM Controlla se pip è disponibile
pip --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERRORE] pip non trovato!
    echo [INFO] Installazione pip...
    python -m ensurepip --upgrade
)

REM Controlla e installa requirements
echo [INFO] Installazione dipendenze...

REM Controlla pygame
python -c "import pygame" >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Installazione pygame...
    pip install pygame
) else (
    echo [OK] pygame già installato
)

REM Controlla tkinter (dovrebbe essere incluso con Python)
python -c "import tkinter" >nul 2>&1
if %errorlevel% neq 0 (
    echo [AVVISO] tkinter non trovato - potrebbe essere necessario reinstallare Python con tkinter
) else (
    echo [OK] tkinter disponibile
)

REM Controlla PIL/Pillow
python -c "import PIL" >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Installazione Pillow...
    pip install Pillow
) else (
    echo [OK] Pillow già installato
)

REM Controlla PyPDF2
python -c "import PyPDF2" >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Installazione PyPDF2...
    pip install PyPDF2
) else (
    echo [OK] PyPDF2 già installato
)

REM Controlla pdf2image
python -c "import pdf2image" >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Installazione pdf2image...
    pip install pdf2image
) else (
    echo [OK] pdf2image già installato
)

REM Controlla numpy
python -c "import numpy" >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Installazione numpy...
    pip install numpy
) else (
    echo [OK] numpy già installato
)

REM Controlla opencv
python -c "import cv2" >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Installazione opencv-python...
    pip install opencv-python
) else (
    echo [OK] opencv-python già installato
)

echo.
echo ========================================
echo   INSTALLAZIONE COMPLETATA!
echo ========================================
echo.
echo [INFO] Per avviare Katana Samurai:
echo python katana_gui.py
echo.
echo [INFO] Documentazione disponibile in:
echo - README.md
echo - DOCUMENTAZIONE_KATANA.md
echo.
pause