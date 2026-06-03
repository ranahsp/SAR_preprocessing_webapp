@echo off
cd /d "%~dp0"
echo Starting Sentinel-1 Streamlit app from %CD%
echo.
python -m streamlit run app.py --server.port 8501
echo.
echo Streamlit stopped. If there is an error above, copy it and send it here.
pause
