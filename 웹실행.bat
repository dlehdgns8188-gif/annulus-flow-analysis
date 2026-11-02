@echo off
setlocal
chcp 65001 >nul
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
pushd "%~dp0"
if errorlevel 1 goto error_pause
".venv\Scripts\python.exe" -m streamlit run "app.py" --server.address localhost
if errorlevel 1 goto error_pop
popd
exit /b 0
:error_pop
popd
:error_pause
echo ERROR: Web app could not start. Review the error above.
pause
exit /b 1
