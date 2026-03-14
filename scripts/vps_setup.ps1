# ============================================
# MapleBot VPS Setup Script
# Run this in PowerShell on the VPS (173.212.200.125)
# ============================================

Write-Host "=== MapleBot VPS Setup ===" -ForegroundColor Cyan

# 1. Install DirectX Runtime (fixes error -2147467259)
Write-Host "`n[1/4] Installing DirectX Runtime..." -ForegroundColor Yellow
$dxPath = "$env:TEMP\dxwebsetup.exe"
Invoke-WebRequest -Uri "https://download.microsoft.com/download/1/7/1/1718CCC4-6315-4D8E-9543-8E28A4E18C4C/dxwebsetup.exe" -OutFile $dxPath
Start-Process $dxPath -ArgumentList "/Q" -Wait
Write-Host "  DirectX installed!" -ForegroundColor Green

# 2. Install Desktop Experience (GPU emulation for Server)
Write-Host "`n[2/4] Installing Desktop Experience..." -ForegroundColor Yellow
try {
    Install-WindowsFeature Desktop-Experience -ErrorAction SilentlyContinue
    Install-WindowsFeature Server-Media-Foundation -ErrorAction SilentlyContinue
    Write-Host "  Desktop features installed!" -ForegroundColor Green
} catch {
    Write-Host "  Skipped (may not be Windows Server)" -ForegroundColor DarkYellow
}

# 3. Clone MapleBot repo
Write-Host "`n[3/4] Cloning MapleBot..." -ForegroundColor Yellow
if (Test-Path "c:\MapleBot") {
    Write-Host "  c:\MapleBot already exists, pulling latest..." -ForegroundColor DarkYellow
    Set-Location "c:\MapleBot"
    git pull
} else {
    git clone https://github.com/lacp90/MapleBot.git c:\MapleBot
    Set-Location "c:\MapleBot"
}
Write-Host "  MapleBot cloned!" -ForegroundColor Green

# 4. Install Python dependencies
Write-Host "`n[4/4] Installing Python packages..." -ForegroundColor Yellow
pip install pyautogui opencv-python numpy pywin32 pyyaml requests Pillow
Write-Host "  Dependencies installed!" -ForegroundColor Green

Write-Host "`n=== SETUP COMPLETE ===" -ForegroundColor Cyan
Write-Host "Next steps:" -ForegroundColor White
Write-Host "  1. Install MapleRoyals and try launching it again" -ForegroundColor White
Write-Host "  2. If DirectX error persists, try: dxwnd (DirectX wrapper)" -ForegroundColor White
Write-Host "  3. Once game runs: cd c:\MapleBot; python main.py" -ForegroundColor White
