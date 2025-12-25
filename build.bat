@echo off
echo Building Gemini Desktop Tool...
pyinstaller --onefile --windowed --name "GeminiTool" --icon=NONE main.py
echo.
echo Build complete! The executable is in the 'dist' folder.
pause
