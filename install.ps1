$repo = "rynfrfr/DownloadMate"
$exeName = "DownloadMate.exe"
$installDir = "$env:LOCALAPPDATA\DownloadMate"

Write-Host "Downloading $exeName from $repo..." -ForegroundColor Cyan

$release = Invoke-RestMethod "https://api.github.com/repos/$repo/releases/latest"
$asset = $release.assets | Where-Object { $_.name -eq $exeName }
if (-not $asset) {
    Write-Host "Could not find $exeName in the latest release." -ForegroundColor Red
    exit 1
}

New-Item -ItemType Directory -Force -Path $installDir | Out-Null
$outPath = "$installDir\$exeName"

Write-Host "Downloading $($asset.name)..." -ForegroundColor Gray
Invoke-WebRequest -Uri $asset.browser_download_url -OutFile $outPath

[Environment]::SetEnvironmentVariable(
    "Path",
    [Environment]::GetEnvironmentVariable("Path", "User") + ";$installDir",
    "User"
)

$shortcutDir = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs"
$shortcut = "$shortcutDir\DownloadMate.lnk"
if (-not (Test-Path $shortcut)) {
    $shell = New-Object -ComObject WScript.Shell
    $link = $shell.CreateShortcut($shortcut)
    $link.TargetPath = $outPath
    $link.WorkingDirectory = $installDir
    $link.Description = "Automatically organize your Downloads folder"
    $link.Save()
    Write-Host "Created Start Menu shortcut." -ForegroundColor Green
}

Write-Host ""
Write-Host "DownloadMate installed to $installDir" -ForegroundColor Green
Write-Host "Added to PATH (log out/in or restart to take effect)." -ForegroundColor Yellow
Write-Host "Run 'DownloadMate' to start." -ForegroundColor Cyan
