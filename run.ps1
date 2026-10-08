param(
    [string]$Provider = "all",
    [string]$ConfigPath = "config/config.yaml",
    [ValidateSet("collect", "collect-report", "test-connection")]
    [string]$Mode = "collect"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $ConfigPath)) {
    throw "Config file not found: $ConfigPath"
}

if (Get-Command uv -ErrorAction SilentlyContinue) {
    uv run vm-asset-inventory --config $ConfigPath --provider $Provider --mode $Mode
    exit $LASTEXITCODE
}

$venvPython = ".venv/Scripts/python.exe"
if (Test-Path $venvPython) {
    $srcPath = (Resolve-Path -LiteralPath "src").Path
    if ($env:PYTHONPATH) {
        $env:PYTHONPATH = "$srcPath;$env:PYTHONPATH"
    } else {
        $env:PYTHONPATH = $srcPath
    }
    & $venvPython -m vm_asset_inventory.cli --config $ConfigPath --provider $Provider --mode $Mode
    exit $LASTEXITCODE
}

$bundleCandidates = @(
    "output/offline_bundle_modular_v3/uv-bin/uv.exe",
    "output/offline_bundle_modular_v2/uv-bin/uv.exe",
    "output/offline_bundle_modular/uv-bin/uv.exe",
    "output/offline_bundle/uv-bin/uv.exe"
)

$localUv = $null
foreach ($candidate in $bundleCandidates) {
    if (Test-Path $candidate) {
        $localUv = Resolve-Path -LiteralPath $candidate
        break
    }
}

if ($localUv) {
    $bundleRoot = Split-Path -Path (Split-Path -Path $localUv -Parent) -Parent
    $bundleCache = Join-Path $bundleRoot "uv-cache"
    if (Test-Path $bundleCache) {
        $env:UV_CACHE_DIR = (Resolve-Path -LiteralPath $bundleCache).Path
    }
    & $localUv run --offline vm-asset-inventory --config $ConfigPath --provider $Provider --mode $Mode
    exit $LASTEXITCODE
}

throw "No runnable runtime found. Expected one of: uv on PATH, bundled uv.exe under output/offline_bundle*, or .venv/Scripts/python.exe"
