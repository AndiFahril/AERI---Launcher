param(
    [Parameter(Mandatory = $true)]
    [string]$Version
)

$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$ReleaseRoot = Join-Path $ProjectRoot 'release'
$PackageRoot = Join-Path $ReleaseRoot 'AERI'
$Archive = Join-Path $ReleaseRoot 'AERI-Windows.zip'

if (Test-Path -LiteralPath $PackageRoot) {
    Remove-Item -LiteralPath $PackageRoot -Recurse -Force
}
if (Test-Path -LiteralPath $Archive) {
    Remove-Item -LiteralPath $Archive -Force
}

New-Item -ItemType Directory -Path $PackageRoot -Force | Out-Null
Copy-Item (Join-Path $ProjectRoot 'dist\AERI.exe') $PackageRoot
Copy-Item (Join-Path $ProjectRoot 'PASANG.cmd') $PackageRoot
Copy-Item (Join-Path $ProjectRoot 'README.md') $PackageRoot
Copy-Item (Join-Path $ProjectRoot 'LICENSE') $PackageRoot
Copy-Item (Join-Path $ProjectRoot 'apps.json') $PackageRoot
Copy-Item (Join-Path $ProjectRoot 'settings.json') $PackageRoot
Copy-Item (Join-Path $ProjectRoot 'icons') $PackageRoot -Recurse

@"
# AERI $Version

Terima kasih telah mengunduh AERI. Jalankan `PASANG.cmd` untuk memasang shortcut desktop,
atau jalankan `AERI.exe` langsung untuk mode portable.
"@ | Set-Content -LiteralPath (Join-Path $PackageRoot 'START-HERE.md') -Encoding utf8

Compress-Archive -Path $PackageRoot -DestinationPath $Archive -CompressionLevel Optimal
Write-Output "Release archive created: $Archive"
