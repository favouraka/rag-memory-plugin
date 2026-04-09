#!/bin/bash
# Migration Script: Old Installation → New Venv Location
# Migrates from ~/.hermes-venv or user-space to ~/.rag-memory

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

OLD_VENV="$HOME/.hermes-venv"
NEW_VENV="$HOME/.rag-memory"
DATA_DIR="$HOME/.hermes/plugins/rag-memory"

# Functions
print_header() {
    echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║      RAG Memory Plugin - Migration to New Location         ║${NC}"
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

detect_old_installation() {
    FOUND_OLD=0
    INSTALLATION_TYPE="none"

    if [ -d "$OLD_VENV" ]; then
        FOUND_OLD=1
        INSTALLATION_TYPE="venv"
        print_warning "Old venv installation found: $OLD_VENV"
    fi

    if pip3 show rag-memory-plugin &>/dev/null; then
        FOUND_OLD=1
        INSTALLATION_TYPE="user-space"
        print_warning "User-space installation found"
        pip3 show rag-memory-plugin | grep Location | sed 's/Location: /  Location: /'
    fi

    if [ $FOUND_OLD -eq 0 ]; then
        print_success "No old installation found"
        print_info "You can proceed with fresh installation"
        return 1
    fi

    echo ""
    return 0
}

remove_old_installation() {
    print_info "Removing old installation..."

    # Deactivate if active
    deactivate 2>/dev/null || true

    if [ "$INSTALLATION_TYPE" = "venv" ] && [ -d "$OLD_VENV" ]; then
        print_info "Removing old venv: $OLD_VENV"
        rm -rf "$OLD_VENV"
        print_success "Old venv removed"
    fi

    if [ "$INSTALLATION_TYPE" = "user-space" ]; then
        print_info "Uninstalling user-space package..."
        pip3 uninstall -y rag-memory-plugin &>/dev/null || true
        print_success "Package uninstalled"
    fi

    # Clean up PATH
    for config in ~/.bashrc ~/.zshrc ~/.profile; do
        if [ -f "$config" ]; then
            if grep -q "hermes-venv" "$config" 2>/dev/null; then
                print_info "Cleaning up $config..."
                sed -i '/hermes-venv/d' "$config"
                print_success "Cleaned $config"
            fi
        fi
    done
}

backup_data() {
    if [ ! -d "$DATA_DIR" ]; then
        print_info "No data directory found, skipping backup"
        return 0
    fi

    print_info "Backing up data..."
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)

    if [ -f "$DATA_DIR/rag_core.db" ]; then
        cp "$DATA_DIR/rag_core.db" "$DATA_DIR/rag_core.db.backup.$TIMESTAMP"
        print_success "Database backed up"
    fi

    if [ -f "$DATA_DIR/config.yaml" ]; then
        cp "$DATA_DIR/config.yaml" "$DATA_DIR/config.yaml.backup.$TIMESTAMP"
        print_success "Configuration backed up"
    fi

    echo ""
}

run_new_installation() {
    print_info "Running new installation..."
    echo ""

    # Run install script
    if curl -sSL https://raw.githubusercontent.com/favouraka/rag-memory-plugin/main/install.sh | bash; then
        print_success "New installation completed"
        return 0
    else
        print_error "Installation failed"
        return 1
    fi
}

detect_shell_config() {
    if [ -n "$ZSH_VERSION" ]; then
        echo "$HOME/.zshrc"
    elif [ -n "$BASH_VERSION" ]; then
        echo "$HOME/.bashrc"
    else
        echo "$HOME/.profile"
    fi
}

show_activation_instructions() {
    PROFILE=$(detect_shell_config)

    echo ""
    echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║                   Migration Complete!                      ║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${GREEN}✅ Migration completed successfully!${NC}"
    echo ""
    echo -e "${CYAN}🚀 To start using rag-memory, run:${NC}"
    echo -e "   ${GREEN}source $PROFILE${NC}"
    echo ""
    echo "Or restart your terminal"
    echo ""
    echo -e "${CYAN}Verify installation:${NC}"
    echo -e "   ${GREEN}rag-memory --version${NC}"
    echo -e "   ${GREEN}rag-memory doctor${NC}"
    echo ""
}

# Main migration flow
main() {
    print_header

    # Detect old installation
    if ! detect_old_installation; then
        echo ""
        print_info "Running fresh installation..."
        run_new_installation
        show_activation_instructions
        exit 0
    fi

    # Confirm migration
    echo ""
    read -p "Proceed with migration? (y/N): " response
    response=$(echo "$response" | tr '[:upper:]' '[:lower:]')

    if [[ ! "$response" =~ ^yes|y$ ]]; then
        print_info "Migration cancelled"
        exit 0
    fi

    echo ""

    # Backup data
    backup_data

    # Remove old installation
    remove_old_installation

    # Run new installation
    if ! run_new_installation; then
        print_error "Migration failed"
        exit 1
    fi

    # Show activation instructions
    show_activation_instructions

    exit 0
}

# Run main function
main "$@"
