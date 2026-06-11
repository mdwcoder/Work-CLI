$ErrorActionPreference = "Stop"

$Installer = Join-Path $PSScriptRoot "install.ps1"
& $Installer @args
