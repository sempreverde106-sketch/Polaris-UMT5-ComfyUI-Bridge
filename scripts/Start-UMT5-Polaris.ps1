param(
    [Parameter(Mandatory=$true)]
    [string]$ServerExe,

    [Parameter(Mandatory=$true)]
    [string]$ModelPath,

    [string]$Device = "Vulkan1",
    [int]$GpuLayers = 12,
    [int]$Port = 8089
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $ServerExe -PathType Leaf)) {
    throw "llama-server.exe not found: $ServerExe"
}

if (-not (Test-Path -LiteralPath $ModelPath -PathType Leaf)) {
    throw "UMT5 GGUF model not found: $ModelPath"
}

Write-Host "=== Polaris UMT5 Server ===" -ForegroundColor Cyan
Write-Host "Device: $Device"
Write-Host "GPU layers: $GpuLayers"
Write-Host "Port: $Port"

& $ServerExe --device $Device -m $ModelPath -ngl $GpuLayers -c 512 -b 256 -ub 256 -fit off --embedding --pooling none --cache-ram 0 --parallel 1 --host 127.0.0.1 --port $Port

exit $LASTEXITCODE