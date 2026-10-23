#Requires -Version 5.1
<#
.SYNOPSIS
  Install MiKTeX (user-level, no admin) from the Aliyun CTAN mirror and verify
  that XeLaTeX can compile a small ctex (Chinese) document.
.DESCRIPTION
  Steps: download installer (resumable) -> write setupwiz.opt -> unattended
  install into %LOCALAPPDATA%\Programs\MiKTeX -> configure mirror and
  AutoInstall -> compile a smoke test.
  ASCII-only by design: Windows PowerShell 5.1 reads BOM-less UTF-8 as ANSI.
.EXAMPLE
  powershell -ExecutionPolicy Bypass -File .\install-miktex.ps1
#>
[CmdletBinding()]
param(
  [string]$Version = '25.12',
  [string]$Mirror  = 'https://mirrors.aliyun.com/CTAN/systems/win32/miktex'
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

$installerUrl = "$Mirror/setup/windows-x64/basic-miktex-$Version-x64.exe"
$packageRepo  = "$Mirror/tm/packages/"
$work         = Join-Path $env:TEMP 'miktex-setup'
$installer    = Join-Path $work "basic-miktex-$Version-x64.exe"
$bin          = Join-Path $env:LOCALAPPDATA 'Programs\MiKTeX\miktex\bin\x64'

New-Item -ItemType Directory -Force -Path $work | Out-Null

function Write-Step([string]$msg) { Write-Host "[*] $msg" -ForegroundColor Cyan }
function Write-Ok([string]$msg)   { Write-Host "[ok] $msg" -ForegroundColor Green }

function Get-Installer {
  if ((Test-Path $installer) -and ((Get-Item $installer).Length -gt 100MB)) {
    Write-Ok "installer already present: $installer"
    return
  }
  Write-Step "downloading $installerUrl"
  $curl = Get-Command curl.exe -ErrorAction SilentlyContinue
  if ($curl) {
    & $curl.Source -L -C - --retry 10 --retry-delay 3 --connect-timeout 20 -o $installer $installerUrl
    if ($LASTEXITCODE -ne 0) { throw "curl failed with exit code $LASTEXITCODE" }
  } else {
    Invoke-WebRequest -Uri $installerUrl -OutFile $installer -UseBasicParsing
  }
  $len = (Get-Item $installer).Length
  if ($len -lt 100MB) { throw "download incomplete ($len bytes): $installer" }
  Unblock-File -Path $installer -ErrorAction SilentlyContinue
  Write-Ok ("downloaded {0:N0} bytes" -f $len)
}

function Install-MiKTeX {
  if (Test-Path (Join-Path $bin 'xelatex.exe')) {
    Write-Ok "MiKTeX already installed: $bin (skipping installer)"
    return
  }
  $optPath = Join-Path $work 'setupwiz.opt'
  $opt = @(
    '--private'
    '--unattended'
    '--auto-install=yes'
    '--package-set=basic'
    '--paper-size=A4'
    "--remote-package-repository=$packageRepo"
  )
  Set-Content -Path $optPath -Value $opt -Encoding ASCII
  Write-Step "installing MiKTeX $Version (user-level, unattended, ~2 min)"
  Push-Location $work
  try {
    & $installer --unattended
    if ($LASTEXITCODE -ne 0) { throw "installer failed with exit code $LASTEXITCODE" }
  } finally {
    Pop-Location
  }
  if (-not (Test-Path (Join-Path $bin 'xelatex.exe'))) {
    throw "installer finished but xelatex.exe is missing under $bin"
  }
  Write-Ok "installed: $bin"
}

function Set-MiKTeXConfig {
  Write-Step "configuring mirror + AutoInstall"
  & (Join-Path $bin 'initexmf.exe') '--set-config-value=[MPM]AutoInstall=1'
  if ($LASTEXITCODE -ne 0) { throw 'initexmf failed to set [MPM]AutoInstall' }
  & (Join-Path $bin 'mpm.exe') "--set-repository=$packageRepo"
  if ($LASTEXITCODE -ne 0) { throw 'mpm failed to set repository' }
  $auto = & (Join-Path $bin 'initexmf.exe') '--show-config-value=[MPM]AutoInstall'
  $repo = & (Join-Path $bin 'initexmf.exe') '--show-config-value=[MPM]RemoteRepository'
  Write-Host "    AutoInstall = $auto"
  Write-Host "    Repository  = $repo"
}

function Test-XeLaTeX {
  Write-Step "compiling smoke test (ctexart, Chinese text, formula)"
  $smoke = Join-Path $work 'smoke'
  New-Item -ItemType Directory -Force -Path $smoke | Out-Null
  # Chinese via code points: the script itself stays ASCII.
  $cn  = -join ([char]0x4E2D, [char]0x6587, [char]0x6D4B, [char]0x8BD5)
  $tex = '\documentclass[UTF8]{ctexart}' + "`r`n" +
         '\begin{document}' + "`r`n" +
         $cn + ' $E=mc^2$' + "`r`n" +
         '\end{document}' + "`r`n"
  $texPath = Join-Path $smoke 'smoke.tex'
  [IO.File]::WriteAllText($texPath, $tex, (New-Object System.Text.UTF8Encoding($false)))

  Push-Location $smoke
  try {
    & (Join-Path $bin 'latexmk.exe') -xelatex -interaction=nonstopmode -halt-on-error smoke.tex | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "smoke test failed (latexmk exit $LASTEXITCODE); see $smoke\smoke.log" }
  } finally {
    Pop-Location
  }
  $pdf = Join-Path $smoke 'smoke.pdf'
  if (-not (Test-Path $pdf)) { throw "smoke test failed: $pdf not produced" }
  Write-Ok "smoke test passed: $pdf"
}

$env:PATH = "$bin;$env:PATH"

Get-Installer
Install-MiKTeX
Set-MiKTeXConfig
Test-XeLaTeX

Write-Host ''
Write-Ok "MiKTeX $Version ready."
Write-Host "    bin:  $bin"
Write-Host "    next: open a NEW terminal (so PATH is refreshed), then run:"
Write-Host "          cd <paper folder>"
Write-Host "          latexmk -xelatex main"
Write-Host "    TeXworks: double-click main.tex (first line selects XeLaTeX automatically)."
