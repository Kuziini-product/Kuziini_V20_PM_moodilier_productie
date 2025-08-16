@echo off
setlocal
cd /d "%~dp0"

REM ==== setari ====
set "PORT=8501"
set "ADDR=localhost"

REM ==== alege Python (py -3 daca exista, altfel python) ====
where py >nul 2>&1 && (set "PY=py -3") || (set "PY=python")

REM ==== depedente (idempotent) ====
%PY% -m pip install -r requirements.txt

REM ==== elibereaza portul 8501 fara PowerShell ====
for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":%PORT% " ^| findstr LISTENING') do (
  taskkill /PID %%P /F >nul 2>&1
)

REM ==== porneste Streamlit in fereastra proprie ====
start "Kuziini Planner" %PY% -m streamlit run "streamlit_app.py" --server.address %ADDR% --server.port %PORT% --server.headless=false

REM ==== deschide automat browserul (cu asteptare simpla) ====
where curl >nul 2>&1
if errorlevel 1 (
  timeout /t 3 >nul
  start "" "http://%ADDR%:%PORT%"
) else (
  set /a tries=0
  :wait
  set /a tries+=1
  curl --max-time 2 -s -o NUL "http://%ADDR%:%PORT%/_stcore/health"
  if errorlevel 1 (
     if %tries% LSS 30 (timeout /t 1 >nul & goto wait)
  )
  start "" "http://%ADDR%:%PORT%"
)

endlocal
