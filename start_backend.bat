@echo off
echo ========================================
echo    Medical PDF Signer - Backend
echo ========================================
echo.

cd /d "%~dp0backend"

if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo Installing dependencies...
pip install -r requirements.txt

echo.
echo Starting Flask server on http://localhost:5000
echo.
echo Default Admin: admin@example.com / admin123
echo.
python app.py
