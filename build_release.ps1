$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$venv = Join-Path $root '.venv-build'
$python = Join-Path $venv 'Scripts\python.exe'
$pyinstaller = Join-Path $venv 'Scripts\pyinstaller.exe'
$output = Join-Path $root 'release-output'

if (-not (Test-Path $python)) {
    python -m venv $venv
}

& $python -m pip install --disable-pip-version-check -r (Join-Path $root 'requirements-build.txt')

New-Item -ItemType Directory -Force $output | Out-Null

Push-Location (Join-Path $root 'app')
try {
    & $pyinstaller --noconfirm --clean `
        --distpath (Join-Path $output 'dist') `
        --workpath (Join-Path $output 'build-demo') `
        'TKM-demo.spec'
    & $pyinstaller --noconfirm --clean `
        --distpath (Join-Path $output 'dist') `
        --workpath (Join-Path $output 'build-full') `
        'TKM-full.spec'
}
finally {
    Pop-Location
}

Write-Host "Release build completed: $output"
