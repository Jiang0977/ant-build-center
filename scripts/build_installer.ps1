Param(
    [switch]$Clean,
    [string]$Python = "python"
)

Write-Host "[1/5] Ensuring Python and PyInstaller are available..."
try {
    & $Python -V | Out-Null
} catch {
    Write-Error "Python not found. Please install Python 3.8+ and retry."; exit 1
}

& $Python -m pip install --upgrade pip setuptools wheel --quiet
& $Python -m pip install pyinstaller --quiet

if ($LASTEXITCODE -ne 0) { Write-Error "Failed to install PyInstaller."; exit 1 }

if ($Clean) {
    Write-Host "[2/5] Cleaning previous build artifacts..."
    if (Test-Path build) { Remove-Item -Recurse -Force build }
    if (Test-Path dist) { Remove-Item -Recurse -Force dist }
}

Write-Host "[3/5] Building executables with PyInstaller..."
& pyinstaller main.spec --noconfirm
if ($LASTEXITCODE -ne 0) { Write-Error "PyInstaller build failed."; exit 1 }

Write-Host "[4/5] Copying runtime assets to dist..."
Copy-Item -Recurse -Force config dist/config
Copy-Item -Recurse -Force scripts dist/scripts

Write-Host "[5/5] Packaging zip (windows-dist.zip) - exe files only..."
if (Test-Path dist\windows-dist.zip) { Remove-Item dist\windows-dist.zip -Force }
Compress-Archive -Path dist\*.exe -DestinationPath dist\windows-dist.zip -Force

Write-Host "Done. Outputs:"
Get-ChildItem -File dist | Select-Object Name,Length

