@echo off
setlocal
chcp 65001 >nul
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
pushd "%~dp0"
if errorlevel 1 goto directory_error
if not exist ".venv\Scripts\python.exe" goto python_missing
if not exist "main.py" goto main_missing
".venv\Scripts\python.exe" "main.py"
if errorlevel 1 goto program_error
popd
exit /b 0

:python_missing
echo ERROR: .venv\Scripts\python.exe was not found in the project folder.
goto error_pause

:main_missing
echo ERROR: main.py was not found in the project folder.
goto error_pause

:program_error
echo ERROR: The program stopped unexpectedly. Review the error message above.
goto error_pause

:directory_error
echo ERROR: The project folder could not be opened.
pause
exit /b 1

:error_pause
pause
popd
exit /b 1
