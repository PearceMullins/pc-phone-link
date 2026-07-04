$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

function Get-ProjectVersion {
    $pyproject = Join-Path $RepoRoot "pyproject.toml"
    $content = Get-Content $pyproject -Raw
    if ($content -match 'version\s*=\s*"([^"]+)"') {
        return $Matches[1]
    }
    throw "Could not read version from pyproject.toml"
}

$Version = Get-ProjectVersion
Write-Host "Building PC Phone Link release v$Version"

if (-not (Get-Command pyinstaller -ErrorAction SilentlyContinue)) {
    throw "PyInstaller is not installed. Run: pip install pyinstaller"
}

$BuildRoot = Join-Path $RepoRoot "build"
$DistRoot = Join-Path $RepoRoot "dist"
$ReleaseDir = Join-Path $DistRoot "PCPhoneLink"

if (Test-Path $ReleaseDir) {
    Remove-Item $ReleaseDir -Recurse -Force
}

Write-Host "Building host executable..."
pyinstaller --noconfirm --clean (Join-Path $PSScriptRoot "PCPhoneLinkHost.spec")

Write-Host "Building launcher executable..."
pyinstaller --noconfirm --clean (Join-Path $PSScriptRoot "PCPhoneLinkLauncher.spec")

New-Item -ItemType Directory -Force -Path $ReleaseDir | Out-Null
Copy-Item (Join-Path $DistRoot "PCPhoneLinkHost.exe") $ReleaseDir
Copy-Item (Join-Path $DistRoot "PCPhoneLinkLauncher.exe") $ReleaseDir

$ReadmePath = Join-Path $ReleaseDir "README.txt"
@(
    "PC Phone Link v$Version"
    ""
    "1. Run PCPhoneLinkLauncher.exe"
    "2. Open the launcher URL on your phone (printed in the console)"
    "3. Tap Start controls and approve pairing on the PC and phone"
    ""
    "Keep PCPhoneLinkHost.exe in the same folder as the launcher."
    "Documentation: https://github.com/PearceMullins/pc-phone-link"
) | Set-Content -Path $ReadmePath -Encoding UTF8

Write-Host "Release folder ready: $ReleaseDir"
