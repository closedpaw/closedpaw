# ClosedPaw Installer for Windows
# Usage: iwr -useb https://raw.githubusercontent.com/logansin/closedpaw/main/installer/install.ps1 | iex
#        & ([scriptblock]::Create((iwr -useb https://raw.githubusercontent.com/logansin/closedpaw/main/installer/install.ps1))) -Tag beta -DryRun

param(
    [string]$Tag = "latest",
    [ValidateSet("npm", "git")]
    [string]$InstallMethod = "npm",
    [string]$GitDir,
    [switch]$NoOnboard,
    [switch]$NoGitUpdate,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "  ClosedPaw Installer" -ForegroundColor Cyan
Write-Host "  Zero-Trust AI Assistant" -ForegroundColor Gray
Write-Host ""

# Check PowerShell version
if ($PSVersionTable.PSVersion.Major -lt 5) {
    Write-Host "Error: PowerShell 5+ required" -ForegroundColor Red
    exit 1
}

Write-Host "[OK] Windows detected" -ForegroundColor Green

# Environment variable overrides
if (-not $PSBoundParameters.ContainsKey("InstallMethod")) {
    if (-not [string]::IsNullOrWhiteSpace($env:CLOSEDPAW_INSTALL_METHOD)) {
        $InstallMethod = $env:CLOSEDPAW_INSTALL_METHOD
    }
}
if (-not $PSBoundParameters.ContainsKey("GitDir")) {
    if (-not [string]::IsNullOrWhiteSpace($env:CLOSEDPAW_GIT_DIR)) {
        $GitDir = $env:CLOSEDPAW_GIT_DIR
    }
}
if (-not $PSBoundParameters.ContainsKey("NoOnboard")) {
    if ($env:CLOSEDPAW_NO_ONBOARD -eq "1") {
        $NoOnboard = $true
    }
}
if (-not $PSBoundParameters.ContainsKey("NoGitUpdate")) {
    if ($env:CLOSEDPAW_GIT_UPDATE -eq "0") {
        $NoGitUpdate = $true
    }
}
if (-not $PSBoundParameters.ContainsKey("DryRun")) {
    if ($env:CLOSEDPAW_DRY_RUN -eq "1") {
        $DryRun = $true
    }
}

if ([string]::IsNullOrWhiteSpace($GitDir)) {
    $userHome = [Environment]::GetFolderPath("UserProfile")
    $GitDir = (Join-Path $userHome ".closedpaw")
}

# Check for Python 3.11+
function Check-Python {
    $pythonCommands = @("python", "python3", "py")
    foreach ($cmd in $pythonCommands) {
        try {
            $version = & $cmd --version 2>&1
            if ($version -match "Python (\d+)\.(\d+)") {
                $major = [int]$matches[1]
                $minor = [int]$matches[2]
                if ($major -gt 3 -or ($major -eq 3 -and $minor -ge 11)) {
                    Write-Host "[OK] Python $major.$minor found ($cmd)" -ForegroundColor Green
                    return $cmd
                }
            }
        } catch {}
    }
    Write-Host "[!] Python 3.11+ not found" -ForegroundColor Yellow
    return $null
}

# Install Python
function Install-Python {
    Write-Host "[*] Installing Python 3.12..." -ForegroundColor Yellow

    # Try winget first
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        Write-Host "  Using winget..." -ForegroundColor Gray
        winget install Python.Python.3.12 --accept-package-agreements --accept-source-agreements
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
        Write-Host "[OK] Python installed via winget" -ForegroundColor Green
        return
    }

    # Try Chocolatey
    if (Get-Command choco -ErrorAction SilentlyContinue) {
        Write-Host "  Using Chocolatey..." -ForegroundColor Gray
        choco install python312 -y
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
        Write-Host "[OK] Python installed via Chocolatey" -ForegroundColor Green
        return
    }

    # Try Scoop
    if (Get-Command scoop -ErrorAction SilentlyContinue) {
        Write-Host "  Using Scoop..." -ForegroundColor Gray
        scoop install python
        Write-Host "[OK] Python installed via Scoop" -ForegroundColor Green
        return
    }

    # Manual download fallback
    Write-Host ""
    Write-Host "Error: Could not find a package manager (winget, choco, or scoop)" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please install Python 3.11+ manually:" -ForegroundColor Yellow
    Write-Host "  https://python.org/downloads/" -ForegroundColor Cyan
    Write-Host ""
    exit 1
}

# Check for Node.js
function Check-Node {
    try {
        $nodeVersion = (node -v 2>$null)
        if ($nodeVersion) {
            $version = [int]($nodeVersion -replace 'v(\d+)\..*', '$1')
            if ($version -ge 18) {
                Write-Host "[OK] Node.js $nodeVersion found" -ForegroundColor Green
                return $true
            } else {
                Write-Host "[!] Node.js $nodeVersion found, but v18+ required" -ForegroundColor Yellow
                return $false
            }
        }
    } catch {
        Write-Host "[!] Node.js not found" -ForegroundColor Yellow
        return $false
    }
    return $false
}

# Install Node.js
function Install-Node {
    Write-Host "[*] Installing Node.js..." -ForegroundColor Yellow

    # Try winget first
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        Write-Host "  Using winget..." -ForegroundColor Gray
        winget install OpenJS.NodeJS.LTS --accept-package-agreements --accept-source-agreements
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
        Write-Host "[OK] Node.js installed via winget" -ForegroundColor Green
        return
    }

    # Try Chocolatey
    if (Get-Command choco -ErrorAction SilentlyContinue) {
        Write-Host "  Using Chocolatey..." -ForegroundColor Gray
        choco install nodejs-lts -y
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
        Write-Host "[OK] Node.js installed via Chocolatey" -ForegroundColor Green
        return
    }

    # Try Scoop
    if (Get-Command scoop -ErrorAction SilentlyContinue) {
        Write-Host "  Using Scoop..." -ForegroundColor Gray
        scoop install nodejs-lts
        Write-Host "[OK] Node.js installed via Scoop" -ForegroundColor Green
        return
    }

    Write-Host ""
    Write-Host "Error: Could not find a package manager" -ForegroundColor Red
    Write-Host "Please install Node.js 18+ manually: https://nodejs.org" -ForegroundColor Yellow
    exit 1
}

# Check for Git
function Check-Git {
    try {
        $null = Get-Command git -ErrorAction Stop
        Write-Host "[OK] Git found" -ForegroundColor Green
        return $true
    } catch {
        Write-Host "[!] Git not found" -ForegroundColor Yellow
        return $false
    }
}

# Check for Ollama
function Check-Ollama {
    $ollamaPaths = @(
        "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe",
        "$env:ProgramFiles\Ollama\ollama.exe"
    )
    
    foreach ($path in $ollamaPaths) {
        if (Test-Path $path) {
            Write-Host "[OK] Ollama found" -ForegroundColor Green
            return $true
        }
    }
    
    try {
        $null = Get-Command ollama -ErrorAction Stop
        Write-Host "[OK] Ollama found" -ForegroundColor Green
        return $true
    } catch {}
    
    Write-Host "[!] Ollama not found (optional, for local LLM)" -ForegroundColor Yellow
    return $false
}

# Check sandbox capability on Windows
function Check-SandboxCapability {
    Write-Host "[*] Checking sandboxing capability..." -ForegroundColor Yellow
    
    # Check for WSL2 (can run Linux containers)
    $wslInstalled = $false
    try {
        $wslCheck = wsl --status 2>&1
        if ($wslCheck -notmatch "is not installed") {
            $wslInstalled = $true
        }
    } catch {}
    
    # Check for Docker Desktop
    $dockerInstalled = $false
    try {
        $null = Get-Command docker -ErrorAction Stop
        $dockerCheck = docker version 2>&1
        if ($LASTEXITCODE -eq 0) {
            $dockerInstalled = $true
        }
    } catch {}
    
    # Check Windows version (Windows 10 Pro/Enterprise or Windows 11 needed for Hyper-V)
    $osInfo = Get-CimInstance Win32_OperatingSystem
    $isProOrEnterprise = $osInfo.Caption -match "Pro|Enterprise|Education"
    $isWin11 = [System.Environment]::OSVersion.Version.Build -ge 22000
    
    if ($wslInstalled -or ($dockerInstalled -and ($isProOrEnterprise -or $isWin11))) {
        Write-Host "[OK] Sandboxing available (WSL2/Docker detected)" -ForegroundColor Green
        return $true
    }
    
    Write-Host "[!] Limited sandboxing on Windows" -ForegroundColor Yellow
    Write-Host "    For full sandboxing (gVisor/Kata), use Linux or macOS" -ForegroundColor Gray
    Write-Host "    Or install WSL2: wsl --install" -ForegroundColor Gray
    return $false
}

# Ask user about sandbox installation
function Prompt-SandboxInstall {
    param([bool]$IsAvailable)
    
    if (-not $IsAvailable) {
        Write-Host ""
        Write-Host "[!] Sandboxing requires WSL2 or Docker Desktop" -ForegroundColor Yellow
        Write-Host "    Install WSL2 for Linux container support:" -ForegroundColor Gray
        Write-Host "    wsl --install" -ForegroundColor Cyan
        Write-Host ""
        return $false
    }
    
    Write-Host ""
    Write-Host "[*] Sandboxing protects against malicious code execution" -ForegroundColor Cyan
    $choice = Read-Host "Install sandboxed environment? [Y/n]"
    
    if ($choice -match "^[Nn]") {
        Write-Host "[!] Skipping sandbox installation" -ForegroundColor Yellow
        Write-Host "    Note: Code will run without isolation" -ForegroundColor Gray
        return $false
    }
    
    return $true
}

# Install sandboxing components
function Install-Sandbox {
    Write-Host "[*] Setting up sandboxing..." -ForegroundColor Yellow
    
    # Check if running in WSL
    $inWSL = $false
    try {
        $wslCheck = wsl -l -v 2>&1
        if ($wslCheck -match "Running") {
            $inWSL = $true
        }
    } catch {}
    
    if ($inWSL) {
        Write-Host "  Configuring WSL2 for gVisor..." -ForegroundColor Gray
        # gVisor can be installed in WSL2
        wsl -d Ubuntu -e bash -c "curl -fsSL https://gvisor.dev/archive.key | sudo gpg --dearmor -o /usr/share/keyrings/gvisor-archive-keyring.gpg && echo 'deb [arch=amd64 signed-by=/usr/share/keyrings/gvisor-archive-keyring.gpg] https://storage.googleapis.com/gvisor/releases release main' | sudo tee /etc/apt/sources.list.d/gvisor.list && sudo apt-get update && sudo apt-get install -y runsc"
        Write-Host "[OK] gVisor installed in WSL2" -ForegroundColor Green
    } else {
        Write-Host "  Docker Desktop detected, configuring..." -ForegroundColor Gray
        Write-Host "  Note: Full gVisor/Kata requires Linux" -ForegroundColor Gray
        Write-Host "  Docker will provide basic container isolation" -ForegroundColor Gray
    }
    
    # Create config marker
    $configDir = "$env:USERPROFILE\.config\closedpaw"
    if (-not (Test-Path $configDir)) {
        New-Item -ItemType Directory -Force -Path $configDir | Out-Null
    }
    @{ sandbox_enabled = $true; platform = "windows"; wsl_available = $inWSL } | ConvertTo-Json | Out-File "$configDir\sandbox.json"
    
    Write-Host "[OK] Sandboxing configured" -ForegroundColor Green
}

# Install Ollama
function Install-Ollama {
    Write-Host "[*] Installing Ollama..." -ForegroundColor Yellow
    
    $ollamaUrl = "https://ollama.com/download/OllamaSetup.exe"
    $installer = "$env:TEMP\OllamaSetup.exe"
    
    try {
        Invoke-WebRequest -Uri $ollamaUrl -OutFile $installer -UseBasicParsing
        Start-Process -FilePath $installer -ArgumentList "/S" -Wait
        Remove-Item $installer -ErrorAction SilentlyContinue
        Write-Host "[OK] Ollama installed" -ForegroundColor Green
        
        # Configure security
        [System.Environment]::SetEnvironmentVariable("OLLAMA_HOST", "127.0.0.1:11434", "User")
        [System.Environment]::SetEnvironmentVariable("OLLAMA_ORIGINS", "*", "User")
    } catch {
        Write-Host "[!] Failed to install Ollama: $_" -ForegroundColor Yellow
        Write-Host "    Install manually from: https://ollama.com" -ForegroundColor Gray
    }
}

# Check for existing ClosedPaw installation
function Check-ExistingClosedPaw {
    try {
        $null = Get-Command closedpaw -ErrorAction Stop
        Write-Host "[*] Existing ClosedPaw installation detected" -ForegroundColor Yellow
        return $true
    } catch {
        return $false
    }
}

# Ensure closedpaw is on PATH
function Ensure-ClosedPawOnPath {
    if (Get-Command closedpaw -ErrorAction SilentlyContinue) {
        return $true
    }

    $npmPrefix = $null
    try {
        $npmPrefix = (npm config get prefix 2>$null).Trim()
    } catch {}

    if (-not [string]::IsNullOrWhiteSpace($npmPrefix)) {
        $npmBin = Join-Path $npmPrefix "bin"
        $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
        if (-not ($userPath -split ";" | Where-Object { $_ -ieq $npmBin })) {
            [Environment]::SetEnvironmentVariable("Path", "$userPath;$npmBin", "User")
            $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
            Write-Host "[!] Added $npmBin to user PATH" -ForegroundColor Yellow
        }
        if (Test-Path (Join-Path $npmBin "closedpaw.cmd")) {
            return $true
        }
    }

    Write-Host "[!] closedpaw is not on PATH yet. Restart PowerShell." -ForegroundColor Yellow
    return $false
}

# Install ClosedPaw via npm
function Install-ClosedPaw {
    if ([string]::IsNullOrWhiteSpace($Tag)) {
        $Tag = "latest"
    }
    
    $packageName = "closedpaw"
    Write-Host "[*] Installing ClosedPaw ($packageName@$Tag)..." -ForegroundColor Yellow
    
    # Silence npm output
    $env:NPM_CONFIG_LOGLEVEL = "error"
    $env:NPM_CONFIG_UPDATE_NOTIFIER = "false"
    $env:NPM_CONFIG_FUND = "false"
    $env:NPM_CONFIG_AUDIT = "false"
    
    try {
        if ($DryRun) {
            Write-Host "  [DRY RUN] Would run: npm install -g $packageName@$Tag" -ForegroundColor Gray
        } else {
            $npmOutput = npm install -g "$packageName@$Tag" 2>&1
            if ($LASTEXITCODE -ne 0) {
                Write-Host "[!] npm install failed" -ForegroundColor Red
                $npmOutput | ForEach-Object { Write-Host $_ }
                exit 1
            }
        }
    } finally {
        $env:NPM_CONFIG_LOGLEVEL = $null
        $env:NPM_CONFIG_UPDATE_NOTIFIER = $null
        $env:NPM_CONFIG_FUND = $null
        $env:NPM_CONFIG_AUDIT = $null
    }
    
    Write-Host "[OK] ClosedPaw installed" -ForegroundColor Green
}

# Install from GitHub
function Install-ClosedPawFromGit {
    param(
        [string]$RepoDir,
        [switch]$SkipUpdate
    )
    
    $repoUrl = "https://github.com/logansin/closedpaw.git"
    Write-Host "[*] Installing ClosedPaw from GitHub ($repoUrl)..." -ForegroundColor Yellow

    if (-not $SkipUpdate) {
        if (-not (Test-Path $RepoDir)) {
            git clone $repoUrl $RepoDir
        } else {
            if (-not (git -C $RepoDir status --porcelain 2>$null)) {
                git -C $RepoDir pull --rebase 2>$null
            } else {
                Write-Host "[!] Repo is dirty; skipping git pull" -ForegroundColor Yellow
            }
        }
    }

    # Install backend dependencies
    Write-Host "[*] Setting up Python environment..." -ForegroundColor Yellow
    Push-Location "$RepoDir\backend"
    & python -m venv venv
    & ".\venv\Scripts\pip.exe" install --upgrade pip | Out-Null
    & ".\venv\Scripts\pip.exe" install fastapi uvicorn pydantic httpx sqlalchemy python-multipart python-jose passlib | Out-Null
    Pop-Location

    # Install frontend dependencies
    Write-Host "[*] Installing frontend dependencies..." -ForegroundColor Yellow
    Push-Location "$RepoDir\frontend"
    npm install --legacy-peer-deps 2>$null
    Pop-Location

    # Create wrapper script
    $binDir = Join-Path $env:USERPROFILE ".local\bin"
    if (-not (Test-Path $binDir)) {
        New-Item -ItemType Directory -Force -Path $binDir | Out-Null
    }
    
    $cmdPath = Join-Path $binDir "closedpaw.cmd"
    $cmdContents = "@echo off`r`nnode ""$RepoDir\bin\closedpaw.js"" %*`r`n"
    Set-Content -Path $cmdPath -Value $cmdContents -NoNewline

    # Add to PATH
    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    if (-not ($userPath -split ";" | Where-Object { $_ -ieq $binDir })) {
        [Environment]::SetEnvironmentVariable("Path", "$userPath;$binDir", "User")
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
        Write-Host "[!] Added $binDir to user PATH" -ForegroundColor Yellow
    }

    Write-Host "[OK] ClosedPaw installed to $cmdPath" -ForegroundColor Green
}

# Create directories
function Initialize-Directories {
    $dirs = @(
        $GitDir,
        "$env:USERPROFILE\.config\closedpaw"
    )
    
    foreach ($dir in $dirs) {
        if (-not (Test-Path $dir)) {
            New-Item -ItemType Directory -Force -Path $dir | Out-Null
        }
    }
    Write-Host "[OK] Directories created" -ForegroundColor Green
}

# Print success message
function Print-Success {
    Write-Host ""
    Write-Host "==============================================" -ForegroundColor Green
    Write-Host "  ClosedPaw Installation Complete!" -ForegroundColor Green
    Write-Host "==============================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Quick Start:" -ForegroundColor Cyan
    Write-Host "  closedpaw start     " -NoNewline; Write-Host "# Start the assistant" -ForegroundColor Gray
    Write-Host "  closedpaw chat ""Hi""" -NoNewline; Write-Host " # Quick chat" -ForegroundColor Gray
    Write-Host "  closedpaw doctor    " -NoNewline; Write-Host "# Run diagnostics" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Web UI: " -NoNewline; Write-Host "http://localhost:3000" -ForegroundColor Cyan
    Write-Host "API:    " -NoNewline; Write-Host "http://localhost:8000" -ForegroundColor Cyan
    Write-Host ""
}

# Main installation flow
function Main {
    # Check dependencies
    $python = Check-Python
    if (-not $python) {
        Install-Python
        $python = Check-Python
        if (-not $python) {
            Write-Host "[!] Python installation failed. Please install manually." -ForegroundColor Red
            exit 1
        }
    }

    $nodeOk = Check-Node
    if (-not $nodeOk) {
        Install-Node
        $nodeOk = Check-Node
        if (-not $nodeOk) {
            Write-Host "[!] Node.js installation failed. Please install manually." -ForegroundColor Red
            exit 1
        }
    }

    if ($InstallMethod -eq "git") {
        if (-not (Check-Git)) {
            Write-Host "[!] Git is required for git install method" -ForegroundColor Red
            Write-Host "    Install from: https://git-scm.com" -ForegroundColor Yellow
            exit 1
        }
    }

    # Check Ollama (optional)
    $ollama = Check-Ollama
    if (-not $ollama) {
        Write-Host "[*] Ollama is optional but recommended for local LLM" -ForegroundColor Yellow
        $install = Read-Host "Install Ollama? [Y/n]"
        if ($install -notmatch "^[Nn]") {
            Install-Ollama
        }
    }

    # Check sandbox capability and prompt for installation
    $sandboxAvailable = Check-SandboxCapability
    $installSandbox = Prompt-SandboxInstall -IsAvailable $sandboxAvailable
    if ($installSandbox) {
        Install-Sandbox
    }

    # Initialize directories
    Initialize-Directories

    # Install ClosedPaw
    if ($DryRun) {
        Write-Host "[DRY RUN] Would install ClosedPaw via $InstallMethod" -ForegroundColor Yellow
    } else {
        if ($InstallMethod -eq "npm") {
            Install-ClosedPaw
        } else {
            Install-ClosedPawFromGit -RepoDir $GitDir -SkipUpdate:$NoGitUpdate
        }
    }

    # Ensure on PATH
    Ensure-ClosedPawOnPath

    # Success
    Print-Success
}

# Run main
Main
