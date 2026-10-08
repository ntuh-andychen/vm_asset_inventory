param(
    [string]$BundleDir = "output/offline_bundle",
    [string]$InstallDir = "runtime/python-embed"
)

$ErrorActionPreference = "Stop"

$root = Resolve-Path -LiteralPath "."
$bundlePath = Join-Path $root $BundleDir
$installPath = Join-Path $root $InstallDir

if (-not (Test-Path $bundlePath)) {
    throw "Bundle path not found: $bundlePath"
}

New-Item -ItemType Directory -Path $installPath -Force | Out-Null

$embedZip = Get-ChildItem -Path $bundlePath -Filter "python-*-embed-amd64.zip" | Select-Object -First 1
if (-not $embedZip) {
    throw "Python embeddable zip not found in bundle"
}

Write-Host "Extracting Python embeddable..."
Expand-Archive -Path $embedZip.FullName -DestinationPath $installPath -Force

$pth = Get-ChildItem -Path $installPath -Filter "python*._pth" | Select-Object -First 1
if ($pth) {
    $text = Get-Content -Path $pth.FullName -Raw
    $text = $text -replace "#import site", "import site"
    Set-Content -Path $pth.FullName -Value $text -Encoding UTF8
}

$uvExe = Get-ChildItem -Path (Join-Path $bundlePath "uv-bin") -Filter "uv.exe" -Recurse | Select-Object -First 1
if (-not $uvExe) {
    throw "uv.exe not found in bundle"
}

$pythonExe = Get-ChildItem -Path $installPath -Filter "python.exe" | Select-Object -First 1
if (-not $pythonExe) {
    throw "python.exe not found after extraction"
}

$uvCache = Join-Path $bundlePath "uv-cache"
if (-not (Test-Path $uvCache)) {
    throw "uv-cache not found in bundle"
}

$env:UV_CACHE_DIR = $uvCache

Write-Host "Restoring project environment from local uv cache in offline mode..."
& $uvExe.FullName sync --frozen --offline --python $pythonExe.FullName
if ($LASTEXITCODE -ne 0) {
    throw "offline uv sync failed with exit code $LASTEXITCODE"
}

Write-Host "Offline smoke test..."
& $uvExe.FullName run --offline -- python -c "import requests, yaml, tenacity; print('offline-smoke-ok')"

Write-Host "Offline install completed. Python: $($pythonExe.FullName)"
