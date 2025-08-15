#!/bin/bash
# Comprehensive test script for the Business Idea Analyzer
# Compatible with older bash versions (3.x)

echo "======================================"
echo "BUSINESS IDEA ANALYZER - COMPREHENSIVE TEST"
echo "Run this script locally to avoid timeouts:"
echo "  chmod +x test_locally.sh"
echo "  ./test_locally.sh"
echo "======================================"

# Activate virtual environment
source .venv/bin/activate

# Test configuration
TEST_IDEAS=(
    "AI-powered fitness app for seniors"
    "B2B marketplace for recycled materials"
    "Virtual interior design using AR"
)

# Test scenarios - using parallel arrays instead of associative array
SCENARIO_NAMES=(
    "1_minimal"
    "2_debug"
    "3_alt_prompt"
    "4_review_basic"
    "5_review_multi"
    "6_with_websearch"
    "7_full_debug"
    "8_full_features"
)

SCENARIO_FLAGS=(
    "--no-websearch"
    "--no-websearch --debug"
    "--no-websearch --prompt-version v2"
    "--no-websearch --with-review --max-iterations 1"
    "--no-websearch --with-review --max-iterations 2"
    ""  # Default includes websearch
    "--debug --with-review --max-iterations 2"
    "--with-review --max-iterations 3"  # Full with websearch
)

# Results tracking
total_tests=0
successful_tests=0
skipped_tests=0
test_results=""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to run a single test (simplified without interactive controls)
run_test() {
    local idea="$1"
    local scenario_name="$2"
    local flags="$3"
    local test_id="${scenario_name}_$(echo "$idea" | cut -d' ' -f1-3 | tr ' ' '_')"
    
    echo ""
    echo "--------------------------------------"
    echo "Test: $scenario_name"
    echo "Idea: ${idea:0:40}..."
    echo "Flags: ${flags:-none}"
    echo "--------------------------------------"
    
    # Create log file in project directory
    mkdir -p logs/test
    log_file="logs/test/${test_id}_$(date +%Y%m%d_%H%M%S).log"
    
    # Run the analysis with timeout, showing output in real-time
    echo "Running test..."
    echo ""
    
    # Use tee to show output and save to log file simultaneously
    if timeout 180 python src/cli.py "$idea" $flags 2>&1 | tee "$log_file"; then
        # Check if analysis was successful
        if grep -q "Analysis saved to:" "$log_file"; then
            echo ""
            echo -e "${GREEN}✅ TEST PASSED${NC}"
            test_results="${test_results}${test_id}:success;"
            ((successful_tests++))
        else
            echo ""
            echo -e "${RED}❌ TEST FAILED${NC} (no output file created)"
            test_results="${test_results}${test_id}:failed_no_output;"
        fi
    else
        exit_code=$?
        echo ""
        if [ $exit_code -eq 124 ]; then
            echo -e "${YELLOW}⏱️  TEST TIMEOUT${NC} (>180s)"
            test_results="${test_results}${test_id}:timeout;"
        else
            echo -e "${RED}❌ TEST FAILED${NC} (exit code: $exit_code)"
            test_results="${test_results}${test_id}:failed_error;"
        fi
    fi
    
    ((total_tests++))
}

# Function to ask user whether to continue
ask_continue() {
    local level_name="$1"
    echo ""
    echo "======================================"
    echo "$level_name"
    echo "======================================"
    echo "Press ENTER to run these tests, or 'S' + ENTER to skip this level:"
    read -r response
    if [[ "$response" == "s" ]] || [[ "$response" == "S" ]]; then
        echo "Skipping $level_name..."
        return 1
    fi
    return 0
}

# Main test execution
echo ""
echo "======================================"
echo "STARTING TESTS"
echo "======================================"
echo ""
echo "NOTE: You can skip any test level when prompted"
echo ""

# Level 1: Basic functionality tests
if ask_continue "LEVEL 1: Basic Functionality"; then
    run_test "${TEST_IDEAS[0]}" "${SCENARIO_NAMES[0]}" "${SCENARIO_FLAGS[0]}"
    run_test "${TEST_IDEAS[0]}" "${SCENARIO_NAMES[1]}" "${SCENARIO_FLAGS[1]}"
    run_test "${TEST_IDEAS[1]}" "${SCENARIO_NAMES[2]}" "${SCENARIO_FLAGS[2]}"
fi

# Level 2: Reviewer tests
if ask_continue "LEVEL 2: Reviewer Functionality"; then
    run_test "${TEST_IDEAS[1]}" "${SCENARIO_NAMES[3]}" "${SCENARIO_FLAGS[3]}"
    run_test "${TEST_IDEAS[2]}" "${SCENARIO_NAMES[4]}" "${SCENARIO_FLAGS[4]}"
fi

# Level 3: Full feature tests (optional - slower)
echo ""
echo "======================================"
echo "LEVEL 3: Full Features (with WebSearch - SLOWER)"
echo "======================================"
echo "⚠️  WARNING: These tests use WebSearch and may take several minutes each"
echo "Press ENTER to run these tests, or any other key + ENTER to skip:"
read -r response
if [ -z "$response" ]; then
    echo "Running full feature tests..."
    run_test "${TEST_IDEAS[0]}" "${SCENARIO_NAMES[5]}" "${SCENARIO_FLAGS[5]}"
    run_test "${TEST_IDEAS[1]}" "${SCENARIO_NAMES[6]}" "${SCENARIO_FLAGS[6]}"
    run_test "${TEST_IDEAS[2]}" "${SCENARIO_NAMES[7]}" "${SCENARIO_FLAGS[7]}"
else
    echo "Skipping Level 3 tests..."
fi

# Summary Report
echo ""
echo "======================================"
echo "TEST SUMMARY REPORT"
echo "======================================"

echo -e "${GREEN}✅ Successful:${NC} $successful_tests/$total_tests"
echo -e "${RED}❌ Failed:${NC} $((total_tests - successful_tests))/$total_tests"
echo ""

# Detailed results - parse the results string
if [ -n "$test_results" ]; then
    echo "Detailed Results:"
    echo "-----------------"
    IFS=';' read -ra RESULTS_ARRAY <<< "$test_results"
    for result_entry in "${RESULTS_ARRAY[@]}"; do
        if [ -n "$result_entry" ]; then
            IFS=':' read -r test_id result <<< "$result_entry"
            case $result in
                success)
                    echo -e "  ${GREEN}✅${NC} $test_id"
                    ;;
                timeout)
                    echo -e "  ${YELLOW}⏱️${NC} $test_id (timeout)"
                    ;;
                *)
                    echo -e "  ${RED}❌${NC} $test_id ($result)"
                    ;;
            esac
        fi
    done
fi

# Success rate
if [ $total_tests -gt 0 ]; then
    success_rate=$((successful_tests * 100 / total_tests))
else
    success_rate=0
fi

echo ""
echo "Success Rate: ${success_rate}%"

# Recommendations
echo ""
echo "======================================"
echo "RECOMMENDATIONS"
echo "======================================"

if [ $success_rate -eq 100 ]; then
    echo -e "${GREEN}🎉 All tests passed! System is fully functional.${NC}"
elif [ $success_rate -ge 80 ]; then
    echo -e "${GREEN}✅ System is mostly functional.${NC}"
    echo "Review failed tests in logs/test/"
elif [ $success_rate -ge 50 ]; then
    echo -e "${YELLOW}⚠️  System has some issues.${NC}"
    echo "Check logs: ls -la logs/test/"
else
    echo -e "${RED}❌ System has significant issues.${NC}"
    echo "Debug with: grep -i error logs/test/*.log"
fi

echo ""
echo "All test logs saved in: logs/test/"
echo ""

# Exit with appropriate code
if [ $success_rate -eq 100 ]; then
    exit 0
else
    exit 1
fi