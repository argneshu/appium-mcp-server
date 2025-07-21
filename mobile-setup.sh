#!/bin/bash

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Create the mobile function
mobile() {
    local MODEL="gemini"
    local INTERACTIVE=false
    local PROMPT=""
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --claude)
                MODEL="claude"
                shift
                ;;
            --gemini)
                MODEL="gemini"
                shift
                ;;
            -i|--interactive)
                INTERACTIVE=true
                shift
                ;;
            -h|--help)
                echo "Mobile Automation Agent"
                echo ""
                echo "Usage:"
                echo "  mobile \"Launch Settings\"                     - Single command (default: gemini)"
                echo "  mobile --claude \"Open Instagram\"             - Single command with Claude"
                echo "  mobile --gemini \"Calculate 15 + 25\"          - Single command with Gemini"
                echo "  mobile -i                                    - Interactive mode"
                echo "  mobile --claude -i                           - Interactive mode with Claude"
                echo ""
                echo "Flags:"
                echo "  --claude     Use Claude model"
                echo "  --gemini     Use Gemini model (default)"
                echo "  -i           Interactive mode"
                echo "  -h           Show this help"
                return 0
                ;;
            *)
                # Collect remaining arguments as prompt
                PROMPT="$*"
                break
                ;;
        esac
    done
    
    # Execute based on mode
    if [ "$INTERACTIVE" = true ]; then
        echo "Starting interactive mobile automation with $MODEL..."
        (cd "$SCRIPT_DIR" && python run_agent.py --model "$MODEL" --interactive)
    elif [ -n "$PROMPT" ]; then
        (cd "$SCRIPT_DIR" && python run_agent.py --model "$MODEL" --prompt "$PROMPT")
    else
        echo "Starting interactive mobile automation with $MODEL..."
        (cd "$SCRIPT_DIR" && python run_agent.py --model "$MODEL" --interactive)
    fi
}

echo "Mobile automation function loaded!"
echo "Usage: mobile \"Launch Settings on iPhone\""
echo "       mobile -i"
echo "       mobile --claude \"Open Instagram\""
echo ""
echo "To make this permanent, add this to your ~/.bashrc or ~/.zshrc:"
echo "source \"$SCRIPT_DIR/mobile-setup.sh\""
