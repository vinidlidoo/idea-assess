#!/bin/bash
# Claude Code hook for automatic linting and formatting
# This hook runs after Edit/Write operations from Claude Code

# Exit if no files provided as arguments
if [ $# -eq 0 ]; then
    exit 0
fi

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}🔧 Running linting hook on modified files...${NC}"

# Activate virtual environment if it exists
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
fi

# Track if any fixes were made
FIXES_MADE=false

# Process each file passed as argument
for file in "$@"; do
    # Only process Python files
    if [[ "$file" == *.py ]]; then
        echo -e "\n📝 Processing: $file"
        
        # Run ruff check with auto-fix
        if command -v ruff &> /dev/null; then
            echo "  Running ruff..."
            if ruff check "$file" --fix --quiet; then
                echo -e "  ${GREEN}✓ Ruff: No issues${NC}"
            else
                echo -e "  ${YELLOW}⚠ Ruff: Fixed some issues${NC}"
                FIXES_MADE=true
            fi
        fi
        
        # Run basedpyright for type checking (no auto-fix, just report)
        if command -v basedpyright &> /dev/null; then
            echo "  Running basedpyright..."
            OUTPUT=$(basedpyright "$file" 2>&1)
            ERROR_COUNT=$(echo "$OUTPUT" | grep -c "error:")
            WARNING_COUNT=$(echo "$OUTPUT" | grep -c "warning:")
            
            if [ "$ERROR_COUNT" -eq 0 ] && [ "$WARNING_COUNT" -eq 0 ]; then
                echo -e "  ${GREEN}✓ Basedpyright: No issues${NC}"
            else
                echo -e "  ${YELLOW}⚠ Basedpyright: $ERROR_COUNT errors, $WARNING_COUNT warnings${NC}"
                # Show first 3 errors/warnings for context
                echo "$OUTPUT" | grep -E "(error:|warning:)" | head -3 | sed 's/^/    /'
            fi
        fi
    fi
done

if [ "$FIXES_MADE" = true ]; then
    echo -e "\n${GREEN}✅ Linting complete - some issues were auto-fixed${NC}"
else
    echo -e "\n${GREEN}✅ Linting complete - no issues found${NC}"
fi