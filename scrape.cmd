@echo off
setlocal
pushd "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Python environment missing. Run: uv sync --frozen
  popd
  exit /b 2
)
".venv\Scripts\python.exe" -m super_scraper %*
set "scraper_exit=%errorlevel%"
popd
exit /b %scraper_exit%
