@echo off
:: Install Python packages (assuming you have Python and pip installed)
pip install Flask requests git cryptography

:: Clone the repository to the Downloads folder
cd %USERPROFILE%\Downloads
git clone https://github.com/Erfinden/bunkermessungai.local

:: Define the path to the cam.py script
set SCRIPT_PATH=%USERPROFILE%\Downloads\bunkermessungai.local\cam.py

:: Create a scheduled task to run cam.py on startup
schtasks /create /tn "RunCamScript" /tr "python %SCRIPT_PATH%" /sc onstart /ru "System"

echo Installation completed successfully.
