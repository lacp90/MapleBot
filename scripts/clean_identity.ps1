# ============================================
# MapleBot - Clean Identity Reset Script
# Run as Administrator!
# ============================================

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  MapleBot Identity Reset" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# --- Step 1: Generate random MAC address ---
# First byte must be even (unicast) and locally administered (bit 1 of first byte = 1)
# So we use 02 as the first byte (locally administered, unicast)
$newMac = "02"
for ($i = 0; $i -lt 5; $i++) {
    $newMac += "-" + ("{0:X2}" -f (Get-Random -Minimum 0 -Maximum 255))
}
$newMacNoDash = $newMac -replace "-", ""

Write-Host "[1/6] MAC Address Change" -ForegroundColor Yellow
Write-Host "  Current MAC: 04-0E-3C-3A-55-B3"
Write-Host "  New MAC:     $newMac" -ForegroundColor Green

# Get the adapter
$adapter = Get-NetAdapter -Name "Ethernet" -ErrorAction SilentlyContinue
if (-not $adapter) {
    Write-Host "  ERROR: Ethernet adapter not found!" -ForegroundColor Red
    exit 1
}

# Disable the adapter first
Write-Host "  Disabling adapter..." -ForegroundColor Gray
Disable-NetAdapter -Name "Ethernet" -Confirm:$false

# Set the new MAC via registry
$adapterGuid = (Get-NetAdapter -Name "Ethernet").InterfaceGuid
$regPath = "HKLM:\SYSTEM\CurrentControlSet\Control\Class\{4d36e972-e325-11ce-bfc1-08002be10318}"
$found = $false

Get-ChildItem $regPath | ForEach-Object {
    $props = Get-ItemProperty $_.PSPath -ErrorAction SilentlyContinue
    if ($props.NetCfgInstanceId -eq $adapterGuid) {
        Set-ItemProperty $_.PSPath -Name "NetworkAddress" -Value $newMacNoDash
        $found = $true
        Write-Host "  Registry updated!" -ForegroundColor Green
    }
}

if (-not $found) {
    Write-Host "  WARNING: Registry entry not found, trying alternative method..." -ForegroundColor Yellow
    # Alternative: try via Set-NetAdapter (some drivers support it)
    Get-ChildItem $regPath | ForEach-Object {
        $props = Get-ItemProperty $_.PSPath -ErrorAction SilentlyContinue
        if ($props.DriverDesc -like "*Realtek*Gaming*") {
            Set-ItemProperty $_.PSPath -Name "NetworkAddress" -Value $newMacNoDash
            Write-Host "  Registry updated via driver match!" -ForegroundColor Green
            $found = $true
        }
    }
}

# Re-enable the adapter
Write-Host "  Re-enabling adapter..." -ForegroundColor Gray
Enable-NetAdapter -Name "Ethernet" -Confirm:$false
Start-Sleep -Seconds 3

# Verify
$verifyMac = (Get-NetAdapter -Name "Ethernet").MacAddress
Write-Host "  Verified MAC: $verifyMac" -ForegroundColor Green
Write-Host ""

# --- Step 2: Flush DNS ---
Write-Host "[2/6] Flushing DNS Cache" -ForegroundColor Yellow
ipconfig /flushdns | Out-Null
Write-Host "  DNS cache cleared!" -ForegroundColor Green
Write-Host ""

# --- Step 3: Reset Winsock ---
Write-Host "[3/6] Resetting Winsock Catalog" -ForegroundColor Yellow
netsh winsock reset | Out-Null
Write-Host "  Winsock reset!" -ForegroundColor Green
Write-Host ""

# --- Step 4: Reset TCP/IP stack ---
Write-Host "[4/6] Resetting TCP/IP Stack" -ForegroundColor Yellow
netsh int ip reset | Out-Null
Write-Host "  TCP/IP stack reset!" -ForegroundColor Green
Write-Host ""

# --- Step 5: Clear ARP cache ---
Write-Host "[5/6] Clearing ARP Cache" -ForegroundColor Yellow
arp -d * 2>$null
netsh interface ip delete arpcache 2>$null
Write-Host "  ARP cache cleared!" -ForegroundColor Green
Write-Host ""

# --- Step 6: Clear MapleStory traces ---
Write-Host "[6/6] Cleaning MapleStory Traces" -ForegroundColor Yellow

# Delete MapleStory registry entries that might store HWID
$msRegPaths = @(
    "HKCU:\Software\Wizet",
    "HKCU:\Software\Nexon",
    "HKLM:\SOFTWARE\Wizet",
    "HKLM:\SOFTWARE\Nexon",
    "HKLM:\SOFTWARE\WOW6432Node\Wizet",
    "HKLM:\SOFTWARE\WOW6432Node\Nexon"
)

foreach ($path in $msRegPaths) {
    if (Test-Path $path) {
        Remove-Item $path -Recurse -Force -ErrorAction SilentlyContinue
        Write-Host "  Removed registry: $path" -ForegroundColor Green
    } else {
        Write-Host "  Not found (clean): $path" -ForegroundColor Gray
    }
}

# Clean temp files that MapleStory might leave
$tempPaths = @(
    "$env:TEMP\MapleStory*",
    "$env:TEMP\Nexon*",
    "$env:TEMP\Wizet*",
    "$env:LOCALAPPDATA\Nexon*",
    "$env:LOCALAPPDATA\Wizet*"
)

foreach ($path in $tempPaths) {
    $items = Get-Item $path -ErrorAction SilentlyContinue
    if ($items) {
        Remove-Item $path -Recurse -Force -ErrorAction SilentlyContinue
        Write-Host "  Cleaned: $path" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Identity Reset Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  New MAC: $newMac" -ForegroundColor Green
Write-Host ""
Write-Host "  NEXT STEPS:" -ForegroundColor Yellow
Write-Host "  1. Connect Surfshark VPN (for new IP)" -ForegroundColor White
Write-Host "  2. Create a new MapleRoyals account" -ForegroundColor White
Write-Host "  3. Launch MapleRoyals and log in" -ForegroundColor White
Write-Host ""
Write-Host "  NOTE: A reboot is recommended for" -ForegroundColor Yellow
Write-Host "  the cleanest reset, but you can try" -ForegroundColor Yellow
Write-Host "  without rebooting first." -ForegroundColor Yellow
Write-Host ""
