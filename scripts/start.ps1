# PowerShell startup script for memory-mesh (Windows)
# Usage: .\scripts\start.ps1           # local only
#        .\scripts\start.ps1 --chatgpt  # with ngrok

if (-not (Get-Command memory-mesh -ErrorAction SilentlyContinue)) {
    pip install -e .
}

$LocalIP = (Test-Connection -ComputerName (hostname) -Count 1).IPV4Address.IPAddressToString
Write-Host "Local:     http://${LocalIP}:8765"
Write-Host "mDNS:      http://memory-mesh.local:8765"

try {
    $TsIP = (tailscale ip -4 2>$null).Trim()
    if ($TsIP) { Write-Host "Tailscale: http://${TsIP}:8765" }
} catch {}

if ($args[0] -eq "--chatgpt") {
    memory-mesh chatgpt @($args | Select-Object -Skip 1)
} else {
    memory-mesh serve
}
