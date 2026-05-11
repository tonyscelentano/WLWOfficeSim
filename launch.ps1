param(
    [switch]$Hidden
)

# OfficeSim Quick Launch Script
# Starts the backend server and opens the game in your browser.

$PORT = 8000
$URL = "http://127.0.0.1:$PORT"

Write-Host "Launching OfficeSim..." -ForegroundColor Cyan

# Check for virtual environment
if (-not (Test-Path ".venv")) {
    Write-Host "Error: .venv not found in the root directory." -ForegroundColor Red
    Write-Host "Please ensure your virtual environment is set up before running this script." -ForegroundColor Yellow
    exit 1
}

# Determine the best shell to use (PowerShell 7 'pwsh' preferred)
$shell = if (Get-Command pwsh -ErrorAction SilentlyContinue) { "pwsh" } else { "powershell" }

# Start the server in a new window so logs remain visible and can be interrupted independently
Write-Host "Starting server..." -ForegroundColor Gray
$serverCommand = "cd '$PSScriptRoot'; `$Host.UI.RawUI.WindowTitle = 'OfficeSim Server'; . .\.venv\Scripts\Activate.ps1; `$env:PYTHONPATH='src'; python src/web/server.py"
if ($Hidden) {
    Start-Process $shell -WindowStyle Hidden -ArgumentList "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", $serverCommand
} else {
    Start-Process $shell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-Command", $serverCommand
}

# Brief pause to allow the server to bind to the port
Write-Host "Waiting for server to initialize..." -ForegroundColor Gray
Start-Sleep -Seconds 2

# Open the default browser
Write-Host "Opening browser to $URL" -ForegroundColor Green
Start-Process $URL

if ($Hidden) {
    Write-Host "Done. Use 'Stop OfficeSim Server.bat' when you're finished playing." -ForegroundColor Cyan
} else {
    Write-Host "Done. Close the server window when you're finished playing." -ForegroundColor Cyan
}
