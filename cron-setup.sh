#!/bin/bash
# Journal Automation Cron Setup Script
# This script sets up a cron job to automatically run journal generation daily

set -e  # Exit on error

# Configuration
CRON_SCHEDULE="25 11 * * *"  # Run at 11:25 AM daily
JOURNAL_COMMAND="journal run --date \$(date +\%Y-\%m-\%d)"
LOG_FILE="$HOME/.local/share/journal-automation/logs/journal.log"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROMPTS_DIR="$SCRIPT_DIR/prompts"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_info() {
    echo -e "${YELLOW}ℹ${NC} $1"
}

# Check prerequisites (no root required)
check_root() {
    # No root required - logs are in user directory
    true
}

# Verify prerequisites
check_prerequisites() {
    echo "Checking prerequisites..."

    # Check if journal command exists
    if ! command -v journal &> /dev/null; then
        print_error "'journal' command not found. Please install it first."
        exit 1
    fi
    print_success "journal command found"

    # Check if prompts directory exists
    if [ ! -d "$PROMPTS_DIR" ]; then
        print_error "Prompts directory not found: $PROMPTS_DIR"
        exit 1
    fi
    print_success "Prompts directory found"

    # Check if prompt files exist
    local required_prompts=("summary.txt" "project_section.txt" "fact_checking.txt" "quality_assurance.txt" "orchestration.txt")
    for prompt in "${required_prompts[@]}"; do
        if [ ! -f "$PROMPTS_DIR/$prompt" ]; then
            print_error "Required prompt file not found: $prompt"
            exit 1
        fi
    done
    print_success "All required prompt files found"

    # Check if date command works
    if ! date +%Y-%m-%d &> /dev/null; then
        print_error "date command failed"
        exit 1
    fi
    print_success "date command works"
}

# Create log file directory if needed
setup_logging() {
    echo "Setting up logging..."

    # Create log directory if it doesn't exist
    LOG_DIR=$(dirname "$LOG_FILE")
    if [ ! -d "$LOG_DIR" ]; then
        print_info "Creating log directory: $LOG_DIR"
        mkdir -p "$LOG_DIR"
        print_success "Log directory created"
    else
        print_success "Log directory already exists"
    fi

    # Create log file if it doesn't exist
    if [ ! -f "$LOG_FILE" ]; then
        print_info "Creating log file: $LOG_FILE"
        touch "$LOG_FILE"
        print_success "Log file created"
    else
        print_success "Log file already exists"
    fi

    # Test write access
    if ! touch "$LOG_FILE" 2>/dev/null; then
        print_error "Cannot write to log file. Check permissions."
        exit 1
    fi
    print_success "Log file is writable"
}

# Create the cron job
setup_cron() {
    echo "Setting up cron job..."

    # Create temporary crontab
    local temp_crontab=$(mktemp)

    # Get current crontab
    crontab -l > "$temp_crontab" 2>/dev/null || true

    # Remove existing journal automation cron job if present
    sed -i '/journal run --date/d' "$temp_crontab"

    # Add new cron job
    echo "$CRON_SCHEDULE $JOURNAL_COMMAND >> $LOG_FILE 2>&1" >> "$temp_crontab"

    # Install new crontab
    if crontab "$temp_crontab"; then
        print_success "Cron job installed successfully"
    else
        print_error "Failed to install cron job"
        rm "$temp_crontab"
        exit 1
    fi

    # Clean up
    rm "$temp_crontab"
}

# Verify cron job
verify_cron() {
    echo "Verifying cron job..."

    if crontab -l | grep -q "journal run --date"; then
        print_success "Cron job is active"
        echo ""
        echo "Current cron job:"
        crontab -l | grep "journal run --date"
    else
        print_error "Cron job not found in crontab"
        exit 1
    fi
}

# Display summary
display_summary() {
    echo ""
    echo "================================================================"
    echo "Cron Setup Complete!"
    echo "================================================================"
    echo ""
    echo "Schedule: $CRON_SCHEDULE (11:25 AM daily)"
    echo "Command:  $JOURNAL_COMMAND"
    echo "Logs:     $LOG_FILE"
    echo ""
    echo "To view logs:"
    echo "  tail -f $LOG_FILE"
    echo "  ls -lh $LOG_DIR/"
    echo ""
    echo "To test manually:"
    echo "  journal run --date \$(date +%Y-%m-%d)"
    echo ""
    echo "To edit cron job:"
    echo "  crontab -e"
    echo ""
    echo "To remove cron job:"
    echo "  crontab -l | grep -v 'journal run --date' | crontab -"
    echo ""
}

# Main execution
main() {
    echo "================================================================"
    echo "Journal Automation Cron Setup"
    echo "================================================================"
    echo ""

    check_root
    check_prerequisites
    setup_logging
    setup_cron
    verify_cron
    display_summary
}

# Run main function
main "$@"
