# Work-CLI Windows Installer

$ErrorActionPreference = "Stop"

# Get Script Directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvDir = Join-Path $ScriptDir "venv"
$PythonScript = Join-Path $ScriptDir "src\Working_Code.py"
$RunnerScript = Join-Path $ScriptDir "scripts\working_runner.sh" # Not used on Windows directly but for reference

Write-Host "╔════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║      Working_Code Auto-Installer       ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════╝"
Write-Host ""

# 1. Check Python
Write-Host "🔍 Checking Python..." -ForegroundColor Yellow
if (-not (Get-Command "python" -ErrorAction SilentlyContinue)) {
    Write-Error "Python is not installed or not in PATH. Please install Python 3 from python.org or Microsoft Store."
    exit 1
}

# 2. Setup Venv
if (-not (Test-Path $VenvDir)) {
    Write-Host "📦 Creating Virtual Environment in $VenvDir..." -ForegroundColor Yellow
    python -m venv $VenvDir
} else {
    Write-Host "✅ Virtual Environment found." -ForegroundColor Green
}

# 3. Install Dependencies
Write-Host "⬇️  Installing/Updating Dependencies..." -ForegroundColor Yellow
$Pip = Join-Path $VenvDir "Scripts\pip.exe"
& $Pip install --upgrade pip --quiet
& $Pip install rich typer cryptography xhtml2pdf --quiet

# 4. Create Function/Alias in Profile
$ProfileDir = Split-Path $PROFILE -Parent
if (-not (Test-Path $ProfileDir)) {
    New-Item -ItemType Directory -Path $ProfileDir -Force | Out-Null
}
if (-not (Test-Path $PROFILE)) {
    New-Item -ItemType File -Path $PROFILE -Force | Out-Null
}

$FunctionDefinition = @"

# Work-CLI Alias
function work {
    & "$VenvDir\Scripts\python.exe" "$PythonScript" `$args
}
"@

# Check if already exists
$CurrentProfile = Get-Content $PROFILE -Raw -ErrorAction SilentlyContinue
if ($CurrentProfile -match "Work-CLI Alias") {
    Write-Host "⚠️  Alias 'work' seems to already exist in $PROFILE." -ForegroundColor Yellow
} else {
    Add-Content -Path $PROFILE -Value $FunctionDefinition
    Write-Host "✅ Added 'work' alias to your PowerShell profile." -ForegroundColor Green
}

# 5. Language Selection
Write-Host ""
Write-Host "Select Language:"
Write-Host "1. SPANISH (ES)"
Write-Host "2. ENGLISH (EN)"
Write-Host "3. FRENCH (FR)"
Write-Host "4. PORTUGUESE (PT)"
$LangOpt = Read-Host "Number [1-4]"

$PythonExe = Join-Path $VenvDir "Scripts\python.exe"
switch ($LangOpt) {
    "1" { & $PythonExe "$PythonScript" LANG-SET ES }
    "2" { & $PythonExe "$PythonScript" LANG-SET EN }
    "3" { & $PythonExe "$PythonScript" LANG-SET FR }
    "4" { & $PythonExe "$PythonScript" LANG-SET PT }
    Default { Write-Host "Defaulting to System/English." -ForegroundColor DarkGray }
}

# 6. User Registration & Security
Write-Host ""
Write-Host "👤 Creating Admin User..." -ForegroundColor Cyan
& $PythonExe "$PythonScript" REGISTER

Write-Host ""
Write-Host "🔐 Checking Encryption..." -ForegroundColor Cyan
& $PythonExe "$PythonScript" INIT-ENCRYPTION --check-first

Write-Host ""
Write-Host "🎉 Installation Complete!" -ForegroundColor Green
Write-Host "Type 'work' to start (you might need to restart your terminal or run '. `$PROFILE')."
