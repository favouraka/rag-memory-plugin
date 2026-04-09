#!/bin/bash
# RAG Memory Plugin Installation Script
# Uses virtual environment at ~/.rag-memory for consistent behavior

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Virtual environment location
VENV_PATH="$HOME/.rag-memory"

# Functions
print_header() {
    echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║       RAG Memory Plugin - Installation                    ║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${CYAN}→ $1${NC}"
}

detect_shell_config() {
    # Detect user's shell and return appropriate config file
    if [ -n "$ZSH_VERSION" ]; then
        echo "$HOME/.zshrc"
    elif [ -n "$BASH_VERSION" ]; then
        echo "$HOME/.bashrc"
    else
        echo "$HOME/.profile"
    fi
}

check_python_version() {
    print_info "Checking Python version..."

    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed"
        echo "  Please install Python 3.10 or higher"
        exit 1
    fi

    PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

    if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 10 ]); then
        print_error "Python $PYTHON_VERSION is too old"
        echo "  Required: Python 3.10 or higher"
        exit 1
    fi

    print_success "Python $PYTHON_VERSION detected"
    echo ""
}

check_pip() {
    print_info "Checking pip..."

    if ! command -v pip3 &> /dev/null; then
        print_error "pip3 is not installed"
        echo "  Install with: sudo apt install python3-pip"
        exit 1
    fi

    print_success "pip3 is available"
    echo ""
}

backup_existing_installation() {
    # Check if ~/.rag-memory already exists (not as venv)
    if [ -d "$VENV_PATH" ] && [ ! -f "$VENV_PATH/pyvenv.cfg" ]; then
        print_warning "$VENV_PATH already exists and is not a virtual environment"
        print_info "Backing up to $VENV_PATH.backup.$(date +%s)"
        mv "$VENV_PATH" "$VENV_PATH.backup.$(date +%s)"
    fi
}

create_virtual_environment() {
    print_info "Creating virtual environment at $VENV_PATH..."

    # Backup if exists
    backup_existing_installation

    # Check if venv already exists
    if [ -f "$VENV_PATH/pyvenv.cfg" ]; then
        print_warning "Virtual environment already exists at $VENV_PATH"

        # Ask if they want to recreate
        if [ -t 0 ]; then
            read -p "Recreate virtual environment? (y/N): " response
            response=$(echo "$response" | tr '[:upper:]' '[:lower:]')
            if [[ "$response" =~ ^yes|y$ ]]; then
                print_info "Removing old virtual environment..."
                rm -rf "$VENV_PATH"
            else
                print_info "Using existing virtual environment"
                return 0
            fi
        else
            # Non-interactive mode, use existing
            print_info "Using existing virtual environment"
            return 0
        fi
    fi

    # Create new venv
    python3 -m venv "$VENV_PATH"
    print_success "Virtual environment created"
}

install_package() {
    print_info "Installing rag-memory-plugin..."

    # Activate venv
    source "$VENV_PATH/bin/activate"

    # Install from GitHub
    if pip install 'git+https://github.com/favouraka/rag-memory-plugin.git#egg=rag-memory-plugin[neural]'; then
        print_success "Package installed successfully"
        deactivate
        return 0
    else
        deactivate
        return 1
    fi
}

add_to_path() {
    PROFILE=$(detect_shell_config)

    print_info "Adding rag-memory to PATH in $PROFILE"

    # Check if already in PATH
    if grep -q "$VENV_PATH/bin" "$PROFILE" 2>/dev/null; then
        print_success "Already in PATH"
        return 0
    fi

    # Add to profile
    echo "" >> "$PROFILE"
    echo "# RAG Memory Plugin" >> "$PROFILE"
    echo "export PATH=\"$VENV_PATH/bin:\$PATH\"" >> "$PROFILE"

    print_success "Added to $PROFILE"
    echo ""
}

show_activation_instructions() {
    PROFILE=$(detect_shell_config)

    echo ""
    echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║                   Installation Complete!                   ║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${GREEN}✅ Installation complete!${NC}"
    echo ""
    echo -e "${CYAN}🚀 To start using rag-memory immediately, run:${NC}"
    echo -e "   ${GREEN}source $PROFILE${NC}"
    echo ""
    echo "Or restart your terminal"
    echo ""
    echo -e "${CYAN}Next steps:${NC}"
    echo ""
    echo "  1. Run setup wizard:"
    echo -e "     ${GREEN}rag-memory setup${NC}"
    echo ""
    echo "  2. Check installation:"
    echo -e "     ${GREEN}rag-memory doctor${NC}"
    echo ""
    echo "  3. Search memory:"
    echo -e "     ${GREEN}rag-memory search \"your query\"${NC}"
    echo ""
    echo -e "${CYAN}Documentation: https://github.com/favouraka/rag-memory-plugin${NC}"
    echo ""
}

# Main installation flow
main() {
    print_header

    # Check prerequisites
    check_python_version
    check_pip

    # Create venv
    create_virtual_environment

    # Install package
    if ! install_package; then
        print_error "Package installation failed"
        exit 1
    fi

    # Add to PATH
    add_to_path

    # Show next steps
    show_activation_instructions

    exit 0
}

# Run main function
main "$@"
