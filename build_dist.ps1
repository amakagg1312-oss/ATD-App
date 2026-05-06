<#
.SYNOPSIS
    Build a distributable ZIP of the NBA 2K26 Generator app.
    Run from the project root: .\build_dist.ps1
#>

$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot
$BuildDir = Join-Path $ProjectRoot "dist"
$FrontendDir = Join-Path $ProjectRoot "frontend"

# Python embeddable config
$PythonVersion = "3.13.4"
$PythonZipName = "python-$PythonVersion-embed-amd64.zip"
$PythonUrl = "https://www.python.org/ftp/python/$PythonVersion/$PythonZipName"
$PythonDownload = Join-Path $BuildDir $PythonZipName
$PythonExtract = Join-Path $BuildDir "python-embed"

# Clean previous build
if (Test-Path $BuildDir) {
    Write-Host "Cleaning previous build..."
    Remove-Item $BuildDir -Recurse -Force
}
New-Item -ItemType Directory -Path $BuildDir | Out-Null

# ── Step 1: Download Python embeddable ──
Write-Host "Downloading Python $PythonVersion embeddable..."
if (-not (Test-Path $PythonDownload)) {
    Invoke-WebRequest -Uri $PythonUrl -OutFile $PythonDownload -UseBasicParsing
}
Write-Host "Extracting Python embeddable..."
New-Item -ItemType Directory -Path $PythonExtract -Force | Out-Null
Expand-Archive -Path $PythonDownload -DestinationPath $PythonExtract -Force

# ── Step 1b: Enable site-packages and install pip + openpyxl ──
Write-Host "Enabling site-packages in embedded Python..."
$PthFile = Get-ChildItem -Path $PythonExtract -Filter "python*._pth" | Select-Object -First 1
if ($PthFile) {
    $content = Get-Content $PthFile.FullName -Raw
    $content = $content -replace '#import site', 'import site'
    Set-Content -Path $PthFile.FullName -Value $content -NoNewline
}
$GetPipPath = Join-Path $BuildDir "get-pip.py"
Write-Host "Downloading get-pip.py..."
Invoke-WebRequest -Uri "https://bootstrap.pypa.io/get-pip.py" -OutFile $GetPipPath -UseBasicParsing
$EmbedPython = Join-Path $PythonExtract "python.exe"
Write-Host "Installing pip..."
& $EmbedPython $GetPipPath --no-warn-script-location 2>&1 | Out-Null
Write-Host "Installing openpyxl, numpy, pandas, scikit-learn, joblib..."
& $EmbedPython -m pip install openpyxl numpy pandas scikit-learn joblib --no-warn-script-location 2>&1 | Write-Host

# ── Step 2: Package Electron app ──
Write-Host "Packaging Electron app..."
Push-Location $FrontendDir
try {
    npx @electron/packager . "NBA2K26-Generator" `
        --platform=win32 `
        --arch=x64 `
        --out="$BuildDir" `
        --overwrite `
        --ignore="node_modules/@electron/packager" `
        --ignore="node_modules/electron$" `
        --asar=false
} finally {
    Pop-Location
}

# Find the packaged app folder
$AppFolder = Get-ChildItem -Path $BuildDir -Directory -Filter "NBA2K26-Generator-win32-x64" | Select-Object -First 1
if (-not $AppFolder) {
    Write-Error "Electron packager output not found!"
    exit 1
}
$AppPath = $AppFolder.FullName
$ResourcesPath = Join-Path $AppPath "resources"

# ── Step 3: Copy Python embeddable into resources/python ──
Write-Host "Copying Python runtime..."
$PythonDest = Join-Path $ResourcesPath "python"
Copy-Item -Path $PythonExtract -Destination $PythonDest -Recurse

# ── Step 4: Copy data folders into resources/data ──
Write-Host "Copying data files..."
$DataDest = Join-Path $ResourcesPath "data"
New-Item -ItemType Directory -Path $DataDest | Out-Null

$DataFolders = @(
    "nba2k26_generator",
    "Playbook",
    "Generator Database",
    "NBA Site data",
    "Player Roles",
    "Badges",
    "Player Photos"
)

foreach ($folder in $DataFolders) {
    $src = Join-Path $ProjectRoot $folder
    if (Test-Path $src) {
        Write-Host "  Copying $folder..."
        Copy-Item -Path $src -Destination (Join-Path $DataDest $folder) -Recurse
    } else {
        Write-Warning "  Folder not found: $folder (skipping)"
    }
}

# ── Step 5: Clean up unnecessary files from data ──
# Remove Python cache files
Get-ChildItem -Path $DataDest -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

# ── Step 5b: Add ../data to Python's _pth so python -m can find nba2k26_generator ──
$DestPthFile = Get-ChildItem -Path $PythonDest -Filter "python*._pth" | Select-Object -First 1
if ($DestPthFile) {
    $lines = Get-Content $DestPthFile.FullName
    $newLines = @()
    foreach ($line in $lines) {
        if ($line.Trim() -eq ".") {
            $newLines += "../data"
        }
        $newLines += $line
    }
    $newContent = ($newLines -join "`n") + "`n"
    [System.IO.File]::WriteAllText($DestPthFile.FullName, $newContent, [System.Text.Encoding]::ASCII)
}

# ── Step 6: Rename the exe ──
$OldExe = Join-Path $AppPath "NBA2K26-Generator.exe"
$NewExe = Join-Path $AppPath "NBA 2K26 Generator.exe"
if (Test-Path $OldExe) {
    Rename-Item -Path $OldExe -NewName "NBA 2K26 Generator.exe"
}

# ── Step 7: Create final ZIP ──
$ZipPath = Join-Path $ProjectRoot "NBA2K26-Generator.zip"
if (Test-Path $ZipPath) {
    Remove-Item $ZipPath -Force
}
Write-Host "Creating ZIP archive..."
Compress-Archive -Path $AppPath -DestinationPath $ZipPath -CompressionLevel Optimal

$ZipSize = [math]::Round((Get-Item $ZipPath).Length / 1MB, 1)
Write-Host ""
Write-Host "Build complete!" -ForegroundColor Green
Write-Host "  ZIP: $ZipPath ($ZipSize MB)"
Write-Host "  Your friend can extract and run 'NBA 2K26 Generator.exe'"
