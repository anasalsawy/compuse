$ErrorActionPreference = "Stop"

# Tasker uses the user's normal Python installation. This installer never
# creates, activates, or depends on a virtual environment.
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

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
