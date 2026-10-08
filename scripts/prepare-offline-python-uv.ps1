param(
    [string]$ProxyUrl = "",
    [string]$ProxyConfigPath = "shared_proxy\proxy.yaml",
    [string]$ProxyFeature = "offline_download",

    [string]$PythonVersion = "3.12.10",
    [string]$BundleDir = "output/offline_bundle"
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonRoot = Split-Path -Parent $projectRoot
$proxyModulePath = Join-Path $pythonRoot "shared_proxy\scripts\ProxyConfig.psm1"
if (-not (Test-Path $proxyModulePath)) {
    throw "Shared proxy module not found: $proxyModulePath"
}
Import-Module $proxyModulePath -Force

$proxyYamlAbsolute = $ProxyConfigPath
if (-not [System.IO.Path]::IsPathRooted($proxyYamlAbsolute)) {
    $candidateFromProject = Join-Path $projectRoot $ProxyConfigPath
    if (Test-Path $candidateFromProject) {
        $proxyYamlAbsolute = $candidateFromProject
    } else {
        $proxyYamlAbsolute = Join-Path $pythonRoot $ProxyConfigPath
    }
}

$resolvedProxy = @{
    http = ""
    https = ""
    no_proxy = ""
}

if ($ProxyUrl) {
    $resolvedProxy.http = $ProxyUrl
    $resolvedProxy.https = $ProxyUrl
} else {
    $resolvedProxy = Get-ProxySettingsForFeature -YamlPath $proxyYamlAbsolute -Feature $ProxyFeature
}

if (-not $resolvedProxy.http -or -not $resolvedProxy.https) {
    throw "Proxy URL is empty. Provide -ProxyUrl or configure proxy profile in $ProxyConfigPath"
}

# Proxy is injected from external config/parameters, not hardcoded in source code.
$env:HTTP_PROXY = $resolvedProxy.http
$env:HTTPS_PROXY = $resolvedProxy.https
if ($resolvedProxy.no_proxy) {
    $env:NO_PROXY = $resolvedProxy.no_proxy
} elseif (-not $env:NO_PROXY) {
    $env:NO_PROXY = "localhost,127.0.0.1"
}

$bundlePath = Resolve-Path -LiteralPath "." | ForEach-Object { Join-Path $_ $BundleDir }
New-Item -ItemType Directory -Path $bundlePath -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $bundlePath "wheelhouse") -Force | Out-Null

$pythonEmbedZip = "python-$PythonVersion-embed-amd64.zip"
$pythonEmbedUrl = "https://www.python.org/ftp/python/$PythonVersion/$pythonEmbedZip"
$pythonEmbedOut = Join-Path $bundlePath $pythonEmbedZip

Write-Host "Downloading Python embeddable package via proxy..."
Invoke-WebRequest -Uri $pythonEmbedUrl -OutFile $pythonEmbedOut -UseBasicParsing -Proxy $resolvedProxy.https

$uvZip = Join-Path $bundlePath "uv-windows-x86_64.zip"
$uvUrl = "https://github.com/astral-sh/uv/releases/latest/download/uv-x86_64-pc-windows-msvc.zip"

Write-Host "Downloading uv binary via proxy..."
Invoke-WebRequest -Uri $uvUrl -OutFile $uvZip -UseBasicParsing -Proxy $resolvedProxy.https

$uvExtractDir = Join-Path $bundlePath "uv-bin"
New-Item -ItemType Directory -Path $uvExtractDir -Force | Out-Null
Expand-Archive -Path $uvZip -DestinationPath $uvExtractDir -Force

$uvExe = Get-ChildItem -Path $uvExtractDir -Filter "uv.exe" -Recurse | Select-Object -First 1
if (-not $uvExe) {
    throw "uv.exe not found after extraction"
}

Write-Host "Exporting requirements from project context..."
$requirementsFile = Join-Path $bundlePath "requirements.lock.txt"
& $uvExe.FullName export --format requirements-txt -o $requirementsFile
if ($LASTEXITCODE -ne 0) {
    throw "uv export failed with exit code $LASTEXITCODE"
}

# Remove editable local project line for offline wheel download.
$filteredRequirements = Get-Content -Path $requirementsFile | Where-Object { $_ -notmatch '^-e\s+\.$' }
Set-Content -Path $requirementsFile -Value $filteredRequirements -Encoding UTF8

Write-Host "Priming dependency cache via uv sync..."
& $uvExe.FullName sync --frozen
if ($LASTEXITCODE -ne 0) {
    throw "uv sync failed with exit code $LASTEXITCODE"
}

Write-Host "Copying uv cache for offline restore..."
$uvCacheDir = (& $uvExe.FullName cache dir).Trim()
if (-not $uvCacheDir -or -not (Test-Path $uvCacheDir)) {
    throw "uv cache directory not found"
}

$offlineCacheDir = Join-Path $bundlePath "uv-cache"
if (Test-Path $offlineCacheDir) {
    Remove-Item -Path $offlineCacheDir -Recurse -Force
}
Copy-Item -Path $uvCacheDir -Destination $offlineCacheDir -Recurse -Force

Write-Host "Offline bundle prepared at: $bundlePath"
