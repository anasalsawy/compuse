param(
    [string]$ProjectRoot = ""
)

$ErrorActionPreference = "Stop"

# Tasker uses the user's normal Python installation. This installer never
# creates, activates, or depends on a virtual environment.
$projectRoot = if ([string]::IsNullOrWhiteSpace($ProjectRoot)) {
    Split-Path -Parent $MyInvocation.MyCommand.Path
} else {
    $ProjectRoot
}
$projectRoot = (Resolve-Path $projectRoot).Path
Set-Location $projectRoot

# Keep an extracted installation upgradeable too. A Git checkout is pulled;
# an extracted folder receives a staged overlay from the public main archive.
$repo = "anasalsawy/compuse"
$archivePath = Join-Path ([IO.Path]::GetTempPath()) ("tasker-main-" + [guid]::NewGuid().ToString("N") + ".zip")
$extractPath = Join-Path ([IO.Path]::GetTempPath()) ("tasker-main-" + [guid]::NewGuid().ToString("N"))
try {
    if (Test-Path (Join-Path $projectRoot ".git")) {
        & git.exe -C $projectRoot pull --ff-only origin main
        if ($LASTEXITCODE -ne 0) {
            throw "Git update failed with exit code $LASTEXITCODE"
        }
    } else {
        $archiveUrl = "https://github.com/$repo/archive/refs/heads/main.zip"
        $curl = Get-Command curl.exe -ErrorAction SilentlyContinue
        if ($null -eq $curl) {
            Invoke-WebRequest -UseBasicParsing -Uri $archiveUrl -OutFile $archivePath
        } else {
            & $curl.Source --noproxy "*" --fail --location --connect-timeout 20 --max-time 180 $archiveUrl --output $archivePath
            if ($LASTEXITCODE -ne 0) {
                throw "GitHub source download failed with exit code $LASTEXITCODE"
            }
        }
        Expand-Archive -LiteralPath $archivePath -DestinationPath $extractPath -Force
        $sourceRoot = Get-ChildItem -LiteralPath $extractPath -Directory | Select-Object -First 1
        if ($null -eq $sourceRoot) {
            throw "GitHub source archive did not contain a project directory"
        }
        Get-ChildItem -LiteralPath $sourceRoot.FullName -Force | ForEach-Object {
            Copy-Item -LiteralPath $_.FullName -Destination $projectRoot -Recurse -Force
        }
        Write-Host "Updated Tasker source in place from GitHub main."
    }
} finally {
    Remove-Item -LiteralPath $archivePath -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $extractPath -Recurse -Force -ErrorAction SilentlyContinue
}

$python = (Get-Command python.exe -ErrorAction Stop).Source
Write-Host "Installing Tasker with: $python"

# --isolated prevents inherited proxy variables and pip user configuration
# from changing this install request.
& $python -m pip --isolated install --user -e ".[desktop]"
if ($LASTEXITCODE -ne 0) {
    throw "Tasker installation failed with exit code $LASTEXITCODE"
}

$scriptDir = (& $python -c "import sysconfig; print(sysconfig.get_path('scripts', scheme='nt_user'))").Trim()
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
$pathParts = @($userPath -split ';' | Where-Object { $_ })
if ($pathParts -notcontains $scriptDir) {
    [Environment]::SetEnvironmentVariable("Path", (($pathParts + $scriptDir) -join ';'), "User")
    Write-Host "Added Tasker command directory to your user PATH: $scriptDir"
}

$env:Path = (([Environment]::GetEnvironmentVariable("Path", "Process")) + ";" + $scriptDir)
Write-Host "Tasker installed. Close this PowerShell window and open a new one."
Write-Host "Then start it with: tasker --live --trace"
