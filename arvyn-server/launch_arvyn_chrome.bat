@echo off
echo Starting ISOLATED Chrome instance for Arvyn...
echo This ensures Port 9222 is available even if other Chromes are open.
start "" "chrome.exe" --remote-debugging-port=9222 --user-data-dir="%TEMP%\arvyn-debug-profile" --no-first-run --no-default-browser-check
echo Chrome launched. Please verify a new window appeared.
pause
