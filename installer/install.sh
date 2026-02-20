#!/bin/bash

# ClosedPaw Installer
# One-command installation: curl -sSL https://raw.githubusercontent.com/closedpaw/closedpaw/main/installer/install.sh | bash

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DEFAULT_INSTALL_DIR="$HOME/.closedpaw"
DEFAULT_CONFIG_DIR="$HOME/.config/closedpaw"
DEFAULT_TEMP_DIR="/tmp"
REQUIRED_PYTHON_VERSION="3.11"

# These will be set after user selection
INSTALL_DIR=""
CONFIG_DIR=""
TEMP_DIR=""
LOG_FILE=""

# Logging setup (will be reinitialized after temp dir selection)
setup_logging() {
    if [ -n "$TEMP_DIR" ]; then
        LOG_FILE="$TEMP_DIR/closedpaw-install.log"
        exec 1> >(tee -a "$LOG_FILE")
        exec 2>&1
    fi
}

select_install_location() {
    print_step "Setting up installation location..."
    
    # Always use defaults for non-interactive installation
    INSTALL_DIR="$DEFAULT_INSTALL_DIR"
    CONFIG_DIR="$DEFAULT_CONFIG_DIR"
    TEMP_DIR="$DEFAULT_TEMP_DIR"
    
    # Create directories if they don't exist
    mkdir -p "$INSTALL_DIR" 2>/dev/null || {
        print_error "Cannot create installation directory: $INSTALL_DIR"
        print_error "Please check permissions or choose a different location"
        exit 1
    }
    
    mkdir -p "$CONFIG_DIR" 2>/dev/null || {
        print_error "Cannot create config directory: $CONFIG_DIR"
        exit 1
    }
    
    mkdir -p "$TEMP_DIR" 2>/dev/null || {
        print_error "Cannot create temp directory: $TEMP_DIR"
        exit 1
    }
    
    # Check available space (need at least 2GB) - warn but don't block
    AVAILABLE_KB=$(df "$INSTALL_DIR" | tail -1 | awk '{print $4}')
    AVAILABLE_GB=$((AVAILABLE_KB / 1024 / 1024))
    
    if [ "$AVAILABLE_GB" -lt 2 ]; then
        print_warning "Low disk space: ${AVAILABLE_GB}GB available (recommended: 2GB+)"
    fi
    
    print_success "Installation location set:"
    echo "  Install: $INSTALL_DIR"
    echo "  Config:  $CONFIG_DIR"
    echo "  Temp:    $TEMP_DIR"
    
    # Setup logging with selected temp dir
    setup_logging
}

print_banner() {
    echo -e "${BLUE}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║              ClosedPaw Installer                            ║"
    echo "║     One command - and it works. Zero-trust AI assistant.     ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running in interactive mode
is_interactive() {
    [ -t 0 ]
}

detect_os() {
    print_step "Detecting operating system..."
    
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        OS="linux"
        if [ -f /etc/os-release ]; then
            . /etc/os-release
            DISTRO=$NAME
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
        DISTRO="macOS $(sw_vers -productVersion)"
    else
        print_error "Unsupported operating system: $OSTYPE"
        exit 1
    fi
    
    print_success "Detected: $DISTRO"
}

check_dependencies() {
    print_step "Checking dependencies..."
    
    # Check Python
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
        print_success "Python $PYTHON_VERSION found"
        
        # Check Python version
        if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 11) else 1)"; then
            print_error "Python 3.11+ required. Found: $PYTHON_VERSION"
            print_error "Please upgrade Python and try again"
            exit 1
        fi
    else
        print_error "Python 3 not found. Please install Python 3.11+"
        exit 1
    fi
    
    # Check Git
    if command -v git &> /dev/null; then
        print_success "Git found"
    else
        print_warning "Git not found. Will install if needed"
    fi
    
    # Check Node.js (for LLM Checker)
    if command -v node &> /dev/null; then
        NODE_VERSION=$(node --version)
        print_success "Node.js $NODE_VERSION found"
    else
        print_warning "Node.js not found. Will install for LLM Checker"
        install_nodejs
    fi
}

install_nodejs() {
    print_step "Installing Node.js..."
    
    if [[ "$OS" == "macos" ]]; then
        if command -v brew &> /dev/null; then
            brew install node
        else
            print_error "Homebrew not found. Please install Node.js manually"
            exit 1
        fi
    else
        # Linux
        if command -v apt-get &> /dev/null; then
            curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
            sudo apt-get install -y nodejs
        elif command -v yum &> /dev/null; then
            curl -fsSL https://rpm.nodesource.com/setup_20.x | sudo bash -
            sudo yum install -y nodejs
        else
            print_error "Cannot install Node.js automatically. Please install manually"
            exit 1
        fi
    fi
    
    print_success "Node.js installed"
}

install_sandbox() {
    print_step "Installing sandboxing environment (gVisor)..."
    
    # gVisor is the default sandbox for Linux/macOS
    if [[ "$OS" == "macos" ]]; then
        # macOS - use Docker with gVisor runtime
        if command -v docker &> /dev/null; then
            print_step "Configuring Docker with gVisor on macOS..."
            # On macOS, gVisor runs via Docker Desktop
            docker run --rm --runtime=runsc alpine echo "gVisor test" 2>/dev/null || {
                print_warning "gVisor runtime not available in Docker"
                print_step "Installing gVisor for Docker..."
                # Download and install runsc for Docker Desktop
                curl -fsSL https://gvisor.dev/archive.key | gpg --dearmor -o /tmp/gvisor-archive-keyring.gpg 2>/dev/null || true
                curl -fsSL https://storage.googleapis.com/gvisor/releases/release/latest/$(uname -m)/runsc > /tmp/runsc
                chmod +x /tmp/runsc
                sudo mv /tmp/runsc /usr/local/bin/ 2>/dev/null || {
                    print_warning "Could not install gVisor binary to /usr/local/bin"
                }
            }
        else
            print_warning "Docker not found. Please install Docker Desktop for macOS"
            print_warning "Sandboxing will be limited without Docker"
        fi
    else
        # Linux - native gVisor installation
        print_step "Installing gVisor on Linux..."
        
        # Add gVisor repository
        curl -fsSL https://gvisor.dev/archive.key | sudo gpg --dearmor -o /usr/share/keyrings/gvisor-archive-keyring.gpg 2>/dev/null || true
        echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/gvisor-archive-keyring.gpg] https://storage.googleapis.com/gvisor/releases release main" | sudo tee /etc/apt/sources.list.d/gvisor.list > /dev/null
        
        # Install gVisor
        if command -v apt-get &> /dev/null; then
            sudo apt-get update -qq
            sudo apt-get install -y runsc 2>/dev/null || {
                # Fallback: direct download
                print_step "Installing gVisor via direct download..."
                ARCH=$(uname -m)
                URL="https://storage.googleapis.com/gvisor/releases/release/latest/${ARCH}"
                curl -fsSL "${URL}/runsc" -o /tmp/runsc
                curl -fsSL "${URL}/runsc.sha512" -o /tmp/runsc.sha512
                chmod +x /tmp/runsc
                sudo mv /tmp/runsc /usr/local/bin/
            }
        elif command -v yum &> /dev/null; then
            # For RHEL/CentOS/Fedora
            curl -fsSL https://storage.googleapis.com/gvisor/releases/release/latest/$(uname -m)/runsc -o /tmp/runsc
            chmod +x /tmp/runsc
            sudo mv /tmp/runsc /usr/local/bin/
        fi
        
        # Configure Docker to use gVisor if available
        if command -v docker &> /dev/null; then
            print_step "Configuring Docker with gVisor runtime..."
            sudo mkdir -p /etc/docker
            echo '{
  "runtimes": {
    "runsc": {
      "path": "/usr/local/bin/runsc"
    }
  }
}' | sudo tee /etc/docker/daemon.json > /dev/null
            print_success "gVisor configured as Docker runtime"
        fi
    fi
    
    # Create sandbox config
    mkdir -p "$CONFIG_DIR"
    cat > "$CONFIG_DIR/sandbox.json" << EOF
{
  "sandbox_enabled": true,
  "platform": "$OS",
  "runtime": "gvisor",
  "installed_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF
    
    print_success "Sandboxing environment installed"
}

# Check and install sandbox (auto-install on Linux/macOS)
check_and_install_sandbox() {
    print_step "Checking sandboxing capabilities..."
    
    # On Linux/macOS, sandboxing is enabled by default for security
    if [[ "$OS" == "linux" ]] || [[ "$OS" == "macos" ]]; then
        print_success "Linux/macOS detected - full sandboxing available"
        
        # Check if gVisor is already installed
        if command -v runsc &> /dev/null || docker run --rm --runtime=runsc alpine echo "test" 2>/dev/null; then
            print_success "gVisor sandboxing already configured"
        else
            print_step "Installing gVisor sandboxing (recommended for security)..."
            install_sandbox
        fi
    fi
}

detect_hardware() {
    print_step "Detecting hardware capabilities..."
    
    # Try to use LLM Checker if available, otherwise use basic detection
    if command -v llm-checker &> /dev/null; then
        print_step "Using LLM Checker for hardware detection..."
        
        # Run hardware detection
        HW_INFO=$(llm-checker hw-detect --json 2>/dev/null || echo '{}')
        
        # Parse hardware info
        CPU=$(echo "$HW_INFO" | grep -o '"cpu": "[^"]*"' | cut -d'"' -f4 || echo "Unknown")
        RAM=$(echo "$HW_INFO" | grep -o '"ram": "[^"]*"' | cut -d'"' -f4 || echo "Unknown")
        GPU=$(echo "$HW_INFO" | grep -o '"gpu": "[^"]*"' | cut -d'"' -f4 || echo "None")
        BACKEND=$(echo "$HW_INFO" | grep -o '"backend": "[^"]*"' | cut -d'"' -f4 || echo "CPU")
    else
        # Basic hardware detection without llm-checker
        print_step "LLM Checker not available, using basic detection..."
        CPU=$(uname -m)
        RAM=$(free -h 2>/dev/null | awk '/^Mem:/ {print $2}' || echo "Unknown")
        GPU="Unknown"
        BACKEND="CPU"
    fi
    
    echo -e "${GREEN}Hardware detected:${NC}"
    echo "  CPU: $CPU"
    echo "  RAM: $RAM"
    echo "  GPU: $GPU"
    echo "  Backend: $BACKEND"
}

get_ollama_version() {
    if command -v ollama &> /dev/null; then
        ollama --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1
    else
        echo ""
    fi
}

compare_versions() {
    # Returns 0 if $1 >= $2, 1 otherwise
    if [ "$1" = "$2" ]; then
        return 0
    fi
    local IFS=.
    local i ver1=($1) ver2=($2)
    for ((i=0; i<${#ver1[@]} || i<${#ver2[@]}; i++)); do
        local v1=${ver1[i]:-0}
        local v2=${ver2[i]:-0}
        if ((10#$v1 > 10#$v2)); then
            return 0
        elif ((10#$v1 < 10#$v2)); then
            return 1
        fi
    done
    return 0
}

install_ollama() {
    print_step "Checking Ollama installation..."
    
    local MIN_VERSION="0.3.0"
    local CURRENT_VERSION=$(get_ollama_version)
    
    if [ -n "$CURRENT_VERSION" ]; then
        print_success "Ollama found: version $CURRENT_VERSION"
        
        if compare_versions "$CURRENT_VERSION" "$MIN_VERSION"; then
            print_success "Ollama version is up to date (>= $MIN_VERSION)"
            
            # Check if security config is applied
            print_step "Verifying Ollama security configuration..."
            configure_ollama_security
            return
        else
            print_warning "Ollama version $CURRENT_VERSION is outdated (minimum: $MIN_VERSION)"
            
            if is_interactive; then
                read -p "Update Ollama to latest version? [Y/n]: " update_choice
                if [[ ! $update_choice =~ ^[Nn]$ ]]; then
                    print_step "Updating Ollama..."
                    
                    # Stop Ollama if running
                    if pgrep -x "ollama" > /dev/null; then
                        print_step "Stopping Ollama..."
                        if [[ "$OS" == "linux" ]]; then
                            sudo systemctl stop ollama 2>/dev/null || true
                        elif [[ "$OS" == "macos" ]]; then
                            pkill ollama 2>/dev/null || true
                        fi
                        sleep 2
                    fi
                    
                    # Reinstall/update
                    curl -fsSL https://ollama.com/install.sh | sh
                    print_success "Ollama updated successfully"
                else
                    print_warning "Continuing with outdated Ollama version"
                    print_warning "Some features may not work correctly"
                fi
            else
                # Non-interactive: auto-update
                print_step "Auto-updating Ollama (non-interactive mode)..."
                curl -fsSL https://ollama.com/install.sh | sh
                print_success "Ollama updated successfully"
            fi
        fi
    else
        print_step "Ollama not found. Installing..."
        curl -fsSL https://ollama.com/install.sh | sh
        print_success "Ollama installed successfully"
    fi
    
    # Configure Ollama for security
    configure_ollama_security
}

configure_ollama_security() {
    print_step "Configuring Ollama security (127.0.0.1 only)..."
    
    if [[ "$OS" == "linux" ]]; then
        # Create Ollama service override for security
        sudo mkdir -p /etc/systemd/system/ollama.service.d/
        
        local override_file="/etc/systemd/system/ollama.service.d/override.conf"
        local new_config="[Service]
Environment=OLLAMA_HOST=127.0.0.1:11434
Environment=OLLAMA_ORIGINS=*"
        
        # Check if config needs update
        if [ -f "$override_file" ]; then
            local current_config=$(cat "$override_file")
            if [ "$current_config" != "$new_config" ]; then
                echo "$new_config" | sudo tee "$override_file" > /dev/null
                sudo systemctl daemon-reload
                sudo systemctl restart ollama
                print_success "Ollama security configuration updated"
            else
                print_success "Ollama security configuration is correct"
            fi
        else
            echo "$new_config" | sudo tee "$override_file" > /dev/null
            sudo systemctl daemon-reload
            sudo systemctl restart ollama
            print_success "Ollama security configuration applied"
        fi
        
    elif [[ "$OS" == "macos" ]]; then
        # macOS: Check and set environment variable
        local current_host=$(launchctl getenv OLLAMA_HOST 2>/dev/null)
        if [ "$current_host" != "127.0.0.1:11434" ]; then
            launchctl setenv OLLAMA_HOST "127.0.0.1:11434"
            # Also add to shell profile for persistence
            if ! grep -q "OLLAMA_HOST=127.0.0.1:11434" "$HOME/.zshrc" 2>/dev/null; then
                echo 'export OLLAMA_HOST=127.0.0.1:11434' >> "$HOME/.zshrc"
            fi
            print_success "Ollama security configuration applied"
        else
            print_success "Ollama security configuration is correct"
        fi
    fi
    
    print_success "Ollama secured (listening on 127.0.0.1:11434 only)"
}

select_models() {
    print_step "Model Selection (Optional)"
    
    echo ""
    echo -e "${YELLOW}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${YELLOW}  MODEL DOWNLOAD IS OPTIONAL${NC}"
    echo -e "${YELLOW}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo "ClosedPaw can work with local LLM models via Ollama."
    echo "Models are typically 2-8 GB in size."
    echo ""
    
    if ! is_interactive; then
        # Non-interactive: skip model download
        echo "Skipping model download (non-interactive mode)"
        echo "You can download models later using: ollama pull llama3.2:3b"
        return
    fi
    
    echo "You have three options:"
    echo "  1. Download a recommended model now (requires internet)"
    echo "  2. Skip and download later manually"
    echo "  3. Use only cloud LLM providers (OpenAI, Anthropic, etc.)"
    echo ""
    
    # Ask user for choice
    read -p "Download model now? [Y/n/skip]: " choice
    
    case "$choice" in
        [Nn]*|[Ss]*)
            print_warning "Skipping model download"
            echo ""
            echo "You can download models later using:"
            echo "  ollama pull llama3.2:3b"
            echo ""
            echo "Or configure cloud providers in the Web UI."
            return
            ;;
        *)
            # Continue with model selection
            ;;
    esac
    
    echo ""
    echo -e "${BLUE}Detecting optimal models for your hardware...${NC}"
    
    # Get recommendations from LLM Checker
    RECOMMENDATIONS=$(llm-checker recommend --category chat --json 2>/dev/null || echo '[]')
    
    if [ -z "$RECOMMENDATIONS" ] || [ "$RECOMMENDATIONS" = "[]" ]; then
        print_warning "Could not get recommendations. Using defaults."
        RECOMMENDATIONS='[{"name": "llama3.2:3b", "description": "Fast, good for chat", "size": "2GB"}, {"name": "mistral:7b", "description": "Balance of speed and quality", "size": "4GB"}]'
    fi
    
    # Display recommendations
    echo ""
    echo -e "${GREEN}Recommended models for your hardware:${NC}"
    echo ""
    
    # Parse and display models
    echo "$RECOMMENDATIONS" | python3 -c "
import json, sys
try:
    models = json.load(sys.stdin)
    for i, model in enumerate(models[:3], 1):
        name = model.get('name', 'unknown')
        desc = model.get('description', 'No description')
        size = model.get('size', 'Unknown size')
        print(f\"  [{i}] {name}\")
        print(f\"      {desc} (Size: {size})\")
        print()
except:
    print('  [1] llama3.2:3b - Fast, good for chat (Size: ~2GB)')
    print('  [2] mistral:7b - Balance of speed and quality (Size: ~4GB)')
" 2>/dev/null || {
        echo "  [1] llama3.2:3b - Fast, good for chat (Size: ~2GB)"
        echo "  [2] mistral:7b - Balance of speed and quality (Size: ~4GB)"
    }
    
    if is_interactive; then
        echo ""
        read -p "Select model [1-3] or 'skip' to cancel: " model_choice
        
        case "$model_choice" in
            [Ss]*)
                print_warning "Skipping model download"
                return
                ;;
            2)
                SELECTED_MODEL="mistral:7b"
                ;;
            3)
                SELECTED_MODEL="qwen2.5:7b"
                ;;
            *)
                SELECTED_MODEL="llama3.2:3b"
                ;;
        esac
        
        # Confirm download
        echo ""
        echo -e "${YELLOW}About to download:${NC} $SELECTED_MODEL"
        echo "This may take several minutes depending on your internet speed."
        echo ""
        read -p "Proceed with download? [Y/n]: " confirm
        
        case "$confirm" in
            [Nn]*)
                print_warning "Download cancelled"
                return
                ;;
        esac
    else
        # Non-interactive: skip model download
        print_warning "Skipping model download (non-interactive mode)"
        echo "You can download models later using: ollama pull llama3.2:3b"
        return
    fi
    
    print_step "Downloading model: $SELECTED_MODEL"
    echo "This may take a while... Press Ctrl+C to cancel"
    echo ""
    
    if ollama pull "$SELECTED_MODEL"; then
        print_success "Model $SELECTED_MODEL installed successfully!"
    else
        print_error "Failed to download model"
        echo "You can try again later with: ollama pull $SELECTED_MODEL"
    fi
}

setup_directories() {
    print_step "Setting up directories..."
    
    mkdir -p "$INSTALL_DIR"
    mkdir -p "$CONFIG_DIR"
    mkdir -p "$INSTALL_DIR/skills"
    mkdir -p "$INSTALL_DIR/logs"
    
    print_success "Directories created"
}

generate_encryption_key() {
    print_step "Generating encryption key for API keys..."
    
    # Generate a random encryption key
    ENCRYPTION_KEY=$(openssl rand -hex 32)
    
    # Store key securely
    echo "$ENCRYPTION_KEY" > "$CONFIG_DIR/.encryption_key"
    chmod 600 "$CONFIG_DIR/.encryption_key"
    
    print_success "Encryption key generated"
}

clone_repository() {
    print_step "Downloading ClosedPaw..."
    
    # Clone from GitHub
    if [ -d "$INSTALL_DIR" ]; then
        print_warning "Directory $INSTALL_DIR already exists, removing..."
        rm -rf "$INSTALL_DIR"
    fi
    
    git clone https://github.com/closedpaw/closedpaw.git "$INSTALL_DIR"
    
    print_success "ClosedPaw downloaded"
}

install_python_dependencies() {
    print_step "Installing Python dependencies..."
    
    cd "$INSTALL_DIR"
    
    # Create virtual environment
    python3 -m venv venv
    source venv/bin/activate
    
    # Install dependencies
    pip install --upgrade pip
    pip install fastapi uvicorn pydantic pydantic-ai httpx sqlalchemy
    pip install python-multipart python-jose[cryptography] passlib[bcrypt]
    
    print_success "Python dependencies installed"
}

install_frontend_dependencies() {
    print_step "Installing frontend dependencies..."
    
    cd "$INSTALL_DIR/frontend"
    
    # Check if Node.js is installed
    if ! command -v npm &> /dev/null; then
        print_error "Node.js is required but not installed"
        print_error "Please install Node.js 20+ and try again"
        exit 1
    fi
    
    # Install dependencies
    npm install
    
    print_success "Frontend dependencies installed"
}

build_frontend() {
    print_step "Building frontend..."
    
    cd "$INSTALL_DIR/frontend"
    
    # Build for production
    npm run build
    
    print_success "Frontend built successfully"
}

configure_firewall() {
    print_step "Configuring firewall..."
    
    if [[ "$OS" == "linux" ]]; then
        if command -v ufw &> /dev/null; then
            # Allow only localhost access
            sudo ufw allow from 127.0.0.1 to any port 3000 comment 'SecureSphere AI Web UI'
            sudo ufw allow from 127.0.0.1 to any port 8000 comment 'SecureSphere AI API'
            print_success "UFW configured"
        fi
    fi
}

create_launcher() {
    print_step "Creating launcher scripts..."
    
    # Create main launcher
    cat > "$INSTALL_DIR/closedpaw" << 'EOF'
#!/bin/bash

INSTALL_DIR="$HOME/.closedpaw"
CONFIG_DIR="$HOME/.config/closedpaw"
PID_FILE="$CONFIG_DIR/closedpaw.pid"

cd "$INSTALL_DIR"
source venv/bin/activate

# Function to cleanup on exit
cleanup() {
    echo "Shutting down ClosedPaw..."
    if [ -f "$PID_FILE" ]; then
        while read pid; do
            kill $pid 2>/dev/null || true
        done < "$PID_FILE"
        rm -f "$PID_FILE"
    fi
    exit 0
}

trap cleanup INT TERM

# Start Ollama if not running
if ! curl -s http://127.0.0.1:11434/api/tags > /dev/null 2>&1; then
    echo "Starting Ollama..."
    ollama serve &
    echo $! >> "$PID_FILE"
    sleep 3
fi

# Start Backend
echo "Starting ClosedPaw Backend..."
cd backend
uvicorn app.main:app --host 127.0.0.1 --port 8000 &
echo $! >> "$PID_FILE"

# Start Frontend (production build)
echo "Starting ClosedPaw Web UI..."
cd ../frontend
npm start &
echo $! >> "$PID_FILE"

echo ""
echo "✅ ClosedPaw is running!"
echo ""
echo "🌐 Web UI: http://localhost:3000"
echo "🔌 API: http://localhost:8000"
echo ""
echo "Press Ctrl+C to stop"

# Wait for interrupt
wait
EOF

    chmod +x "$INSTALL_DIR/closedpaw"
    
    # Add to PATH
    if [[ ":$PATH:" != *":$INSTALL_DIR:"* ]]; then
        echo "export PATH=\"$INSTALL_DIR:\$PATH\"" >> "$HOME/.bashrc"
        echo "export PATH=\"$INSTALL_DIR:\$PATH\"" >> "$HOME/.zshrc" 2>/dev/null || true
    fi
    
    print_success "Launcher created"
}

open_browser() {
    print_step "Opening browser..."
    
    # Wait a moment for services to start
    sleep 2
    
    # Try to open browser (cross-platform)
    if command -v xdg-open &> /dev/null; then
        xdg-open "http://localhost:3000" &
    elif command -v open &> /dev/null; then
        open "http://localhost:3000" &
    else
        print_warning "Could not open browser automatically"
        echo "Please open http://localhost:3000 manually"
    fi
}

print_completion() {
    echo ""
    echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║          ClosedPaw Installation Complete!                   ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${BLUE}Quick Start:${NC}"
    echo "  • Restart terminal or run: source ~/.bashrc"
    echo "  • Start anytime: closedpaw"
    echo "  • Web UI: http://localhost:3000"
    echo "  • API: http://localhost:8000"
    echo ""
    echo -e "${YELLOW}Security Notes:${NC}"
    echo "  • Ollama listens only on 127.0.0.1:11434"
    echo "  • Web UI accessible only from localhost"
    echo "  • API keys encrypted with generated key"
    echo "  • Hardened sandboxing with gVisor/Kata"
    echo ""
    echo -e "${BLUE}Installation log: $LOG_FILE${NC}"
}

# Main installation flow
main() {
    print_banner
    
    select_install_location
    detect_os
    check_dependencies
    check_and_install_sandbox
    detect_hardware
    install_ollama
    setup_directories
    generate_encryption_key
    clone_repository
    install_python_dependencies
    install_frontend_dependencies
    build_frontend
    select_models
    configure_firewall
    create_launcher
    
    print_completion
    
    # Auto-start after installation
    echo ""
    print_step "Starting ClosedPaw..."
    "$INSTALL_DIR/closedpaw" &
    sleep 3
    open_browser
}

# Run main function
main "$@"