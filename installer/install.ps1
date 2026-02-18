# ClosedPaw Installer for Windows
# One-command installation: iwr -useb https://raw.githubusercontent.com/logansin/closedpaw/main/installer/install.ps1 | iex

param(
    [switch]$Silent,
    [string]$InstallDir = "",
    [string]$ConfigDir = "",
    [string]$TempDir = ""
)

$ErrorActionPreference = "Stop"

# Default Configuration
$DefaultInstallDir = "$env:USERPROFILE\.closedpaw"
$DefaultConfigDir = "$env:USERPROFILE\.config\closedpaw"
$DefaultTempDir = "$env:TEMP"
$RequiredPythonVersion = "3.11"

# These will be set after user selection
$script:InstallDir = $null
$script:ConfigDir = $null
$script:TempDir = $null
$script:LogFile = $null

function Write-Log {
    param($Message, $Level = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logEntry = "[$timestamp] [$Level] $Message"
    if ($script:LogFile) {
        Add-Content -Path $script:LogFile -Value $logEntry
    }
    
    switch ($Level) {
        "SUCCESS" { Write-Host $Message -ForegroundColor Green }
        "WARNING" { Write-Host $Message -ForegroundColor Yellow }
        "ERROR" { Write-Host $Message -ForegroundColor Red }
        "STEP" { Write-Host $Message -ForegroundColor Cyan }
        default { Write-Host $Message }
    }
}

function Select-InstallLocation {
    Write-Log "Setting up installation location..." "STEP"
    
    $script:InstallDir = $DefaultInstallDir
    $script:ConfigDir = $DefaultConfigDir
    $script:TempDir = $DefaultTempDir
    $script:LogFile = "$script:TempDir\securesphere-install.log"
    
    try {
        New-Item -ItemType Directory -Force -Path $script:InstallDir | Out-Null
        New-Item -ItemType Directory -Force -Path $script:ConfigDir | Out-Null
        New-Item -ItemType Directory -Force -Path $script:TempDir | Out-Null
    } catch {
        Write-Log "Failed to create directories: $_" "ERROR"
        exit 1
    }
    
    $drive = (Get-Item $script:InstallDir).PSDrive.Name
    $disk = Get-PSDrive -Name $drive
    $availableGB = [math]::Round($disk.Free / 1GB, 2)
    
    if ($availableGB -lt 2) {
        Write-Log "Low disk space: $availableGB GB available (recommended: 2GB+)" "WARNING"
    }
    
    Write-Log "Installation location set:" "SUCCESS"
    Write-Log "  Install: $($script:InstallDir)" "SUCCESS"
    Write-Log "  Config:  $($script:ConfigDir)" "SUCCESS"
    Write-Log "  Temp:    $($script:TempDir)" "SUCCESS"
}

function Print-Banner {
    Write-Host ""
    Write-Host "==============================================" -ForegroundColor Cyan
    Write-Host "        ClosedPaw Installer                  " -ForegroundColor Cyan
    Write-Host "   One command - and it works.               " -ForegroundColor Cyan
    Write-Host "==============================================" -ForegroundColor Cyan
    Write-Host "
}

function Test-Administrator {
    $currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
    return $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Get-OSInfo {
    Write-Log "Detecting Windows version..." "STEP"
    $osInfo = Get-CimInstance Win32_OperatingSystem
    Write-Log "Windows Version: $($osInfo.Caption)" "SUCCESS"
    Write-Log "Build: $($osInfo.BuildNumber)" "SUCCESS"
    return $osInfo
}

function Test-Dependencies {
    Write-Log "Checking dependencies..." "STEP"
    
    try {
        $pythonVersion = (python --version 2>&1).ToString()
        Write-Log "Python found: $pythonVersion" "SUCCESS"
        
        $versionMatch = $pythonVersion -match "Python (\d+)\.(\d+)"
        if ($versionMatch) {
            $major = [int]$matches[1]
            $minor = [int]$matches[2]
            
            if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 11)) {
                Write-Log ("Python 3.11+ required. Found: " + $major + "." + $minor) "ERROR"
                Write-Log "Please upgrade Python from https://python.org" "ERROR"
                exit 1
            }
        }
    } catch {
        Write-Log "Python not found. Please install Python 3.11+ from https://python.org" "ERROR"
        exit 1
    }
    
    try {
        $gitVersion = git --version
        Write-Log "Git found: $gitVersion" "SUCCESS"
    } catch {
        Write-Log "Git not found. Will install if needed" "WARNING"
    }
    
    try {
        $nodeVersion = node --version
        Write-Log "Node.js found: $nodeVersion" "SUCCESS"
    } catch {
        Write-Log "Node.js not found. Will install..." "WARNING"
        Install-NodeJS
    }
}

function Install-NodeJS {
    Write-Log "Installing Node.js..." "STEP"
    
    try {
        $nodeUrl = "https://nodejs.org/dist/v20.11.0/node-v20.11.0-x64.msi"
        $nodeInstaller = "$env:TEMP\nodejs.msi"
        
        Invoke-WebRequest -Uri $nodeUrl -OutFile $nodeInstaller
        Start-Process -FilePath "msiexec.exe" -ArgumentList "/i", $nodeInstaller, "/quiet", "/norestart" -Wait
        
        $env:Path = [System.Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + [System.Environment]::GetEnvironmentVariable('Path', 'User')
        
        Write-Log "Node.js installed successfully" "SUCCESS"
    } catch {
        Write-Log "Failed to install Node.js automatically" "ERROR"
        Write-Log "Please install manually from https://nodejs.org" "ERROR"
        exit 1
    }
}

function Get-OllamaPath {
    # Check if ollama is in PATH
    $ollamaInPath = Get-Command ollama -ErrorAction SilentlyContinue
    if ($ollamaInPath) {
        return $ollamaInPath.Source
    }
    
    # Check common installation locations
    $possiblePaths = @(
        "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe",
        "$env:ProgramFiles\Ollama\ollama.exe",
        "$env:ProgramFiles(x86)\Ollama\ollama.exe",
        "$env:USERPROFILE\AppData\Local\Programs\Ollama\ollama.exe"
    )
    
    foreach ($path in $possiblePaths) {
        if (Test-Path $path) {
            return $path
        }
    }
    
    return $null
}

function Get-OllamaVersion {
    $ollamaPath = Get-OllamaPath
    if ($ollamaPath) {
        try {
            $versionOutput = & $ollamaPath --version 2>$null
            if ($versionOutput -match '(\d+\.\d+\.\d+)') {
                return $matches[1]
            }
        } catch {
            return $null
        }
    }
    return $null
}

function Compare-Versions($version1, $version2) {
    $v1 = [version]$version1
    $v2 = [version]$version2
    return $v1 -ge $v2
}

function Install-Ollama {
    Write-Log "Checking Ollama installation..." "STEP"
    
    $minVersion = "0.3.0"
    $currentVersion = Get-OllamaVersion
    
    if ($currentVersion) {
        Write-Log "Ollama found: version $currentVersion" "SUCCESS"
        
        if (Compare-Versions $currentVersion $minVersion) {
            Write-Log "Ollama version is up to date" "SUCCESS"
            Configure-OllamaSecurity
            return
        } else {
            Write-Log "Ollama version $currentVersion is outdated" "WARNING"
            
            $isInteractive = [Environment]::UserInteractive -and ([Environment]::GetCommandLineArgs() -notcontains '-NonInteractive')
            
            if ($isInteractive -and -not $Silent) {
                $updateChoice = Read-Host "Update Ollama to latest version? [Y/n]"
                
                if ($updateChoice -notmatch "^[Nn]") {
                    Update-Ollama
                } else {
                    Write-Log "Continuing with outdated Ollama version" "WARNING"
                }
            } else {
                Write-Log "Auto-updating Ollama (non-interactive mode)..." "STEP"
                Update-Ollama
            }
        }
    } else {
        Write-Log "Ollama not found. Installing..." "STEP"
        Install-OllamaInstaller
    }
    
    Configure-OllamaSecurity
}

function Update-Ollama {
    $ollamaProcess = Get-Process -Name "ollama" -ErrorAction SilentlyContinue
    if ($ollamaProcess) {
        Write-Log "Stopping Ollama..." "STEP"
        Stop-Process -Name "ollama" -Force
        Start-Sleep -Seconds 2
    }
    Install-OllamaInstaller
    Write-Log "Ollama updated successfully" "SUCCESS"
}

function Install-OllamaInstaller {
    try {
        $ollamaUrl = "https://ollama.com/download/OllamaSetup.exe"
        $ollamaInstaller = "$env:TEMP\OllamaSetup.exe"
        
        Write-Log "Downloading Ollama..." "STEP"
        Invoke-WebRequest -Uri $ollamaUrl -OutFile $ollamaInstaller
        
        Write-Log "Installing Ollama..." "STEP"
        Start-Process -FilePath $ollamaInstaller -ArgumentList "/S" -Wait
        
        Remove-Item $ollamaInstaller -ErrorAction SilentlyContinue
    } catch {
        Write-Log "Failed to install Ollama: $_" "ERROR"
        exit 1
    }
}

function Configure-OllamaSecurity {
    Write-Log "Configuring Ollama security..." "STEP"
    
    $currentHost = [System.Environment]::GetEnvironmentVariable("OLLAMA_HOST", "User")
    $currentOrigins = [System.Environment]::GetEnvironmentVariable("OLLAMA_ORIGINS", "User")
    
    $needsUpdate = $false
    
    if ($currentHost -ne "127.0.0.1:11434") {
        [System.Environment]::SetEnvironmentVariable("OLLAMA_HOST", "127.0.0.1:11434", "User")
        $needsUpdate = $true
    }
    
    if ($currentOrigins -ne "*") {
        [System.Environment]::SetEnvironmentVariable("OLLAMA_ORIGINS", "*", "User")
        $needsUpdate = $true
    }
    
    if ($needsUpdate) {
        Write-Log "Ollama security configuration applied" "SUCCESS"
    } else {
        Write-Log "Ollama security configuration is correct" "SUCCESS"
    }
}

function Select-Models {
    Write-Log "Model Selection (Optional)" "STEP"
    
    Write-Host ""
    Write-Host "==============================================" -ForegroundColor Yellow
    Write-Host "  MODEL DOWNLOAD IS OPTIONAL" -ForegroundColor Yellow
    Write-Host "==============================================" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "ClosedPaw can work with local LLM models via Ollama."
    Write-Host "Models are typically 2-8 GB in size."
    Write-Host ""
    
    $isInteractive = [Environment]::UserInteractive -and ([Environment]::GetCommandLineArgs() -notcontains '-NonInteractive')
    
    if (-not $isInteractive -or $Silent) {
        Write-Log "Skipping model download (non-interactive mode)" "WARNING"
        Write-Host "You can download models later using: ollama pull llama3.2:3b"
        return
    }
    
    Write-Host "You have three options:"
    Write-Host "  1. Download a recommended model now (requires internet)"
    Write-Host "  2. Skip and download later manually"
    Write-Host "  3. Use only cloud LLM providers (OpenAI, Anthropic, etc.)"
    Write-Host ""
    
    $choice = Read-Host "Download model now? [Y/n/skip]"
    
    if ($choice -match "^[Nn]|^[Ss]") {
        Write-Log "Skipping model download" "WARNING"
        Write-Host ""
        Write-Host "You can download models later using:"
        Write-Host "  ollama pull llama3.2:3b"
        return
    }
    
    Write-Host ""
    Write-Log "Recommended models:" "STEP"
    Write-Host ""
    Write-Host "  [1] llama3.2:3b - Fast, good for chat (Size: ~2GB)"
    Write-Host "  [2] mistral:7b - Balance of speed and quality (Size: ~4GB)"
    Write-Host "  [3] qwen2.5:7b - Excellent for code (Size: ~4GB)"
    Write-Host ""
    
    $modelChoice = Read-Host "Select model [1-3] or 'skip' to cancel"
    
    if ($modelChoice -eq "skip") {
        Write-Log "Skipping model download" "WARNING"
        return
    }
    
    switch ($modelChoice) {
        "2" { $selectedModel = "mistral:7b" }
        "3" { $selectedModel = "qwen2.5:7b" }
        default { $selectedModel = "llama3.2:3b" }
    }
    
    Write-Host ""
    Write-Host "About to download: $selectedModel" -ForegroundColor Yellow
    Write-Host "This may take several minutes depending on your internet speed."
    Write-Host ""
    
    $confirm = Read-Host "Proceed with download? [Y/n]"
    
    if ($confirm -match "^[Nn]") {
        Write-Log "Download cancelled" "WARNING"
        return
    }
    
    Write-Log "Downloading model: $selectedModel" "STEP"
    Write-Host "This may take a while... Press Ctrl+C to cancel"
    Write-Host ""
    
    try {
        $ollamaPath = Get-OllamaPath
        if (-not $ollamaPath) {
            Write-Log "Ollama not found. Cannot download model." "ERROR"
            return
        }
        
        $ollamaProcess = Get-Process -Name "ollama" -ErrorAction SilentlyContinue
        if (-not $ollamaProcess) {
            Start-Process -FilePath $ollamaPath -ArgumentList "serve" -WindowStyle Hidden
            Start-Sleep -Seconds 3
        }
        
        & $ollamaPath pull $selectedModel
        
        Write-Log "Model $selectedModel installed successfully!" "SUCCESS"
    } catch {
        Write-Log "Failed to download model: $_" "ERROR"
        Write-Host "You can try again later with: ollama pull $selectedModel"
    }
}

function Initialize-Directories {
    Write-Log "Setting up directories..." "STEP"
    
    New-Item -ItemType Directory -Force -Path $script:InstallDir | Out-Null
    New-Item -ItemType Directory -Force -Path $script:ConfigDir | Out-Null
    New-Item -ItemType Directory -Force -Path "$script:InstallDir\skills" | Out-Null
    New-Item -ItemType Directory -Force -Path "$script:InstallDir\logs" | Out-Null
    
    Write-Log "Directories created" "SUCCESS"
}

function Clone-Repository {
    Write-Log "Downloading ClosedPaw..." "STEP"
    
    if (Test-Path $script:InstallDir) {
        $contents = Get-ChildItem $script:InstallDir
        if ($contents) {
            Write-Log "Directory exists, removing..." "WARNING"
            Remove-Item -Path $script:InstallDir -Recurse -Force
        }
    }
    
    git clone https://github.com/logansin/closedpaw.git $script:InstallDir
    
    Write-Log "ClosedPaw downloaded" "SUCCESS"
}

function New-EncryptionKey {
    Write-Log "Generating encryption key..." "STEP"
    
    $encryptionKey = -join ((1..64) | ForEach-Object { '{0:X2}' -f (Get-Random -Maximum 256) })
    $keyFile = "$script:ConfigDir\.encryption_key"
    $encryptionKey | Out-File -FilePath $keyFile -Encoding UTF8
    
    $acl = Get-Acl $keyFile
    $acl.SetAccessRuleProtection($true, $false)
    
    $currentUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
    $accessRule = New-Object System.Security.AccessControl.FileSystemAccessRule($currentUser, "Read,Write", "Allow")
    $acl.SetAccessRule($accessRule)
    Set-Acl $keyFile $acl
    
    Write-Log "Encryption key generated and secured" "SUCCESS"
}

function Install-PythonDependencies {
    Write-Log "Installing Python dependencies..." "STEP"
    
    Set-Location $script:InstallDir
    
    python -m venv venv
    & ".\venv\Scripts\Activate.ps1"
    
    python -m pip install --upgrade pip
    
    $packages = @("fastapi", "uvicorn[standard]", "pydantic", "pydantic-ai", "httpx", "sqlalchemy", "python-multipart", "python-jose[cryptography]", "passlib[bcrypt]", "cryptography", "pynacl")
    
    foreach ($package in $packages) {
        Write-Log "Installing $package..." "STEP"
        pip install $package
    }
    
    Write-Log "Python dependencies installed" "SUCCESS"
}

function Install-FrontendDependencies {
    Write-Log "Installing frontend dependencies..." "STEP"
    
    Set-Location "$script:InstallDir\frontend"
    
    if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
        Write-Log "Node.js is required but not installed" "ERROR"
        exit 1
    }
    
    npm install
    
    Write-Log "Frontend dependencies installed" "SUCCESS"
}

function Build-Frontend {
    Write-Log "Building frontend..." "STEP"
    
    Set-Location "$script:InstallDir\frontend"
    npm run build
    
    Write-Log "Frontend built successfully" "SUCCESS"
}

function New-LauncherScript {
    Write-Log "Creating launcher script..." "STEP"
    
    $ollamaPath = Get-OllamaPath
    if (-not $ollamaPath) {
        $ollamaPath = "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe"
    }
    
    $launcherContent = @"
# ClosedPaw Launcher
`$INSTALL_DIR = `"$env:USERPROFILE\.closedpaw`"
Set-Location `$INSTALL_DIR
& `".\venv\Scripts\Activate.ps1`"

`$ollamaRunning = Test-NetConnection -ComputerName 127.0.0.1 -Port 11434 -WarningAction SilentlyContinue
if (-not `$ollamaRunning.TcpTestSucceeded) {
    Write-Host `"Starting Ollama...`"
    Start-Process -FilePath `"$ollamaPath`" -ArgumentList `"serve`" -WindowStyle Hidden
    Start-Sleep -Seconds 3
}

Write-Host `"Starting SecureSphere AI backend...`"
Start-Process powershell -ArgumentList `"-Command`", `"cd '$env:USERPROFILE\.securesphere-ai\backend'; ..\venv\Scripts\uvicorn app.main:app --host 127.0.0.1 --port 8000`" -WindowStyle Normal

Write-Host `"Starting Web UI...`"
Start-Process powershell -ArgumentList `"-Command`", `"cd '$env:USERPROFILE\.securesphere-ai\frontend'; npm run dev`" -WindowStyle Normal

Write-Host "ClosedPaw is running!"
Write-Host `"Web UI: http://localhost:3000`"
Write-Host `"API: http://localhost:8000`"
"@
    
    $launcherPath = $script:InstallDir + "\closedpaw.ps1"
    $launcherContent | Out-File -FilePath $launcherPath -Encoding UTF8
    
    $batchContent = "@echo off`npowershell -ExecutionPolicy Bypass -File `"%USERPROFILE%\.closedpaw\closedpaw.ps1`""
    $batchPath = $script:InstallDir + "\closedpaw.bat"
    $batchContent | Out-File -FilePath $batchPath -Encoding ASCII
    
    $currentPath = [System.Environment]::GetEnvironmentVariable('Path', 'User')
    if ($currentPath -notlike "*" + $script:InstallDir + "*") {
        [System.Environment]::SetEnvironmentVariable('Path', $currentPath + ";" + $script:InstallDir, 'User')
    }
    
    Write-Log "Launcher created" "SUCCESS"
}

function Write-CompletionMessage {
    Write-Host ""
    Write-Host "==============================================" -ForegroundColor Green
    Write-Host "   ClosedPaw Installation Complete!          " -ForegroundColor Green
    Write-Host "==============================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Quick Start:" -ForegroundColor Cyan
    Write-Host "  - Restart PowerShell session"
    Write-Host "  - Start anytime: closedpaw.bat"
    Write-Host "  - Web UI: http://localhost:3000"
    Write-Host "  - API: http://localhost:8000"
    Write-Host ""
    Write-Host "Installation log: $script:LogFile" -ForegroundColor Cyan
}

function Open-Browser {
    Write-Log "Opening browser..." "STEP"
    Start-Sleep -Seconds 2
    
    try {
        Start-Process "http://localhost:3000"
    } catch {
        Write-Log "Could not open browser automatically" "WARNING"
        Write-Host "Please open http://localhost:3000 manually"
    }
}

function Main {
    Print-Banner
    
    Write-Host "Installing ClosedPaw on your system..." -ForegroundColor Yellow
    
    Select-InstallLocation
    Get-OSInfo
    Test-Dependencies
    Install-Ollama
    Initialize-Directories
    New-EncryptionKey
    Clone-Repository
    Install-PythonDependencies
    Install-FrontendDependencies
    Build-Frontend
    Select-Models
    New-LauncherScript
    
    Write-CompletionMessage
    
    Write-Host ""
    Write-Log "Starting ClosedPaw..." "STEP"
    Start-Process -FilePath "$script:InstallDir\closedpaw.bat" -WindowStyle Normal
    Start-Sleep -Seconds 3
    Open-Browser
}

Main
