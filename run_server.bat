@echo off
REM ======================================================
REM  Launch MTK Analysis Web Viewer
REM ======================================================
REM --- Navigate to the web viewer folder ---
cd /d "C:\MTK\python\MTK_Analysis\web_viewer"
REM --- Activate the MTK virtual environment ---
call "C:\MTK\python_pilot\.venv\Scripts\activate.bat"
REM --- Start Flask app in the background ---
start "Flask Server" cmd /k "python app.py"
REM --- Wait 3 seconds for the server to start ---
timeout /t 3 >nul
REM --- Open the web browser automatically ---
start "" "http://127.0.0.1:5000"
REM --- Keep the main window open for diagnostics ---
echo.
echo Flask web viewer launched successfully!
echo.
pause