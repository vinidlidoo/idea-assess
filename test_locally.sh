#!/bin/bash
# Comprehensive test script for the Business Idea Analyzer
# Compatible with older bash versions (3.x)
#
# Updated to use --prompt-variant flag with new prompt system:
#   "main" - active prompt from agents/{agent}/main.md
#   "v1", "v2", "v3" - historical versions from versions/{agent}/
#   "revision" - special workflow prompts

# Set up trap to handle Ctrl+C properly
cleanup() {
  echo ""
  echo "Test interrupted by user"
  # Kill any running python processes
  pkill -P $$ 2>/dev/null
  exit 130
}
trap cleanup INT TERM

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
# Reordered so each level starts with debug flag for better diagnostics
SCENARIO_NAMES=(
  "1_debug"
  "2_minimal"
  "3_alt_prompt"
  "4_review_debug"
  "5_review_basic"
  "6_review_multi"
  "7_websearch_debug"
  "8_with_websearch"
  "9_full_features"
)

SCENARIO_FLAGS=(
  "--no-websearch --debug"
  "--no-websearch"
  "--no-websearch --prompt-variant v2"
  "--no-websearch --debug --with-review --max-iterations 1"
  "--no-websearch --with-review --max-iterations 1"
  "--no-websearch --with-review --max-iterations 2"
  "--debug"                          # Default includes websearch with debug
  ""                                 # Default includes websearch
  "--with-review --max-iterations 3" # Full with websearch
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

  # Note: We no longer need TEST_HARNESS_RUN since we use a single setup_logging()
  # export TEST_HARNESS_RUN=1  # Removed - no longer needed with new logging

  echo ""
  echo "--------------------------------------"
  echo "Test: $scenario_name"
  echo "Idea: ${idea:0:40}..."
  echo "Flags: ${flags:-none}"
  echo "--------------------------------------"

  # Create log file for test output
  timestamp=$(date +%Y%m%d_%H%M%S)
  test_dir="logs/tests/${timestamp}_${scenario_name}_$(echo "$idea" | cut -d' ' -f1-3 | tr ' ' '_' | cut -c1-30)"
  mkdir -p "$test_dir"
  log_file="$test_dir/output.log"

  # Use 5 minute timeout for all tests
  local timeout_seconds=300

  # Run the analysis with timeout, showing output in real-time
  echo "Running test..."
  echo ""

  # Use tee to show output and save to log file simultaneously
  # Use --foreground with timeout to allow signal propagation
  if timeout --foreground $timeout_seconds python src/cli.py "$idea" $flags 2>&1 | tee "$log_file"; then
    # Check if analysis was successful (handles both regular and reviewer modes)
    if grep -q -E "(Analysis saved to:|Saved to:)" "$log_file"; then
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
      echo -e "${YELLOW}⏱️  TEST TIMEOUT${NC} (>${timeout_seconds}s)"
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
echo "TEST MODE SELECTION"
echo "======================================"
echo ""
echo "1) Run ALL scenarios"
echo "2) Select specific scenarios to run"
echo ""
echo -n "Enter choice (1 or 2): "
read -r test_mode

if [ "$test_mode" = "2" ]; then
  # Show available scenarios
  echo ""
  echo "Available scenarios:"
  echo "-------------------"
  for i in "${!SCENARIO_NAMES[@]}"; do
    echo "$((i + 1))) ${SCENARIO_NAMES[$i]} - ${SCENARIO_FLAGS[$i]:-default}"
  done
  echo ""
  echo "Enter scenario numbers to run (space-separated, e.g., '1 3 5'):"
  read -r selected_scenarios

  echo ""
  echo "======================================"
  echo "RUNNING SELECTED SCENARIOS"
  echo "======================================"

  # Run selected scenarios
  for num in $selected_scenarios; do
    idx=$((num - 1))
    if [ $idx -ge 0 ] && [ $idx -lt ${#SCENARIO_NAMES[@]} ]; then
      # Cycle through test ideas using modulo
      idea_idx=$((idx % ${#TEST_IDEAS[@]}))
      idea="${TEST_IDEAS[$idea_idx]}"
      run_test "$idea" "${SCENARIO_NAMES[$idx]}" "${SCENARIO_FLAGS[$idx]}"
    else
      echo "Invalid scenario number: $num (skipping)"
    fi
  done
else
  # Original behavior - run all with level prompts
  echo ""
  echo "======================================"
  echo "STARTING ALL TESTS"
  echo "======================================"
  echo ""
  echo "NOTE: You can skip any test level when prompted"
  echo ""

  # Level 1: Basic functionality tests (debug first for diagnostics)
  if ask_continue "LEVEL 1: Basic Functionality"; then
    for i in 0 1 2; do
      idea_idx=$((i % ${#TEST_IDEAS[@]}))
      run_test "${TEST_IDEAS[$idea_idx]}" "${SCENARIO_NAMES[$i]}" "${SCENARIO_FLAGS[$i]}"
    done
  fi

  # Level 2: Reviewer tests (debug first for diagnostics)
  if ask_continue "LEVEL 2: Reviewer Functionality"; then
    for i in 3 4 5; do
      idea_idx=$((i % ${#TEST_IDEAS[@]}))
      run_test "${TEST_IDEAS[$idea_idx]}" "${SCENARIO_NAMES[$i]}" "${SCENARIO_FLAGS[$i]}"
    done
  fi

  # Level 3: Full feature tests (optional - slower, debug first)
  echo ""
  echo "======================================"
  echo "LEVEL 3: Full Features (with WebSearch - SLOWER)"
  echo "======================================"
  echo "⚠️  WARNING: These tests use WebSearch and may take several minutes each"
  echo "Press ENTER to run these tests, or any other key + ENTER to skip:"
  read -r response
  if [ -z "$response" ]; then
    echo "Running full feature tests..."
    for i in 6 7 8; do
      idea_idx=$((i % ${#TEST_IDEAS[@]}))
      run_test "${TEST_IDEAS[$idea_idx]}" "${SCENARIO_NAMES[$i]}" "${SCENARIO_FLAGS[$i]}"
    done
  else
    echo "Skipping Level 3 tests..."
  fi
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
  IFS=';' read -ra RESULTS_ARRAY <<<"$test_results"
  for result_entry in "${RESULTS_ARRAY[@]}"; do
    if [ -n "$result_entry" ]; then
      IFS=':' read -r test_id result <<<"$result_entry"
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

echo ""
if [ $success_rate -eq 100 ]; then
  echo -e "${GREEN}✅ All tests passed!${NC}"
else
  echo -e "${RED}❌ Some tests failed. Check the logs${NC}"
fi

echo ""
echo "All test logs saved in: logs/tests/"
echo ""

# Exit with appropriate code
if [ $success_rate -eq 100 ]; then
  exit 0
else
  exit 1
fi
