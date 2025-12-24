@echo off
echo ========================================
echo    Medical PDF Signer - Frontend
echo ========================================
echo.

cd /d "%~dp0frontend"

if not exist "node_modules" (
    echo Installing dependencies...
    npm install
)

echo.
echo Starting React development server on http://localhost:3000
echo.
npm start
