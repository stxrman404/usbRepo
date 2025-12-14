# StarSearch Firewall Configuration Script
# Opens port 8888 in Windows Firewall for StarSearch
# Run as Administrator

Write-Host "StarSearch Firewall Configuration" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "ERROR: This script must be run as Administrator!" -ForegroundColor Red
    Write-Host "Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Press any key to exit..."
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    exit 1
}

$port = 8888
$ruleName = "StarSearch Port $port"

Write-Host "Configuring Windows Firewall for port $port..." -ForegroundColor Yellow
Write-Host ""

# Remove existing rule if it exists
$existingRule = Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue
if ($existingRule) {
    Write-Host "Removing existing rule..." -ForegroundColor Yellow
    Remove-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue
}

# Create inbound rule
Write-Host "Creating inbound firewall rule..." -ForegroundColor Yellow
New-NetFirewallRule -DisplayName $ruleName `
    -Direction Inbound `
    -LocalPort $port `
    -Protocol TCP `
    -Action Allow `
    -Description "StarSearch Server/Client Communication Port" | Out-Null

if ($?) {
    Write-Host "✓ Inbound rule created successfully!" -ForegroundColor Green
} else {
    Write-Host "✗ Failed to create inbound rule" -ForegroundColor Red
    exit 1
}

# Create outbound rule (usually not needed, but ensures connectivity)
Write-Host "Creating outbound firewall rule..." -ForegroundColor Yellow
New-NetFirewallRule -DisplayName "$ruleName (Outbound)" `
    -Direction Outbound `
    -LocalPort $port `
    -Protocol TCP `
    -Action Allow `
    -Description "StarSearch Server/Client Communication Port (Outbound)" | Out-Null

if ($?) {
    Write-Host "✓ Outbound rule created successfully!" -ForegroundColor Green
} else {
    Write-Host "⚠ Outbound rule creation failed (may not be necessary)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Firewall configuration complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Port $port is now open for StarSearch." -ForegroundColor Cyan
Write-Host ""
Write-Host "Press any key to exit..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

