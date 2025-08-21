#!/bin/bash
# Comprehensive test script for the Business Idea Analyzer
# Compatible with older bash versions (3.x)
#
# Updated to use --analyst-prompt and --reviewer-prompt flags:
#   These flags directly set the system_prompt in agent configs
#   Default is "system.md" as configured in BaseAgentConfig

# Set up trap to handle Ctrl+C properly
cleanup() {
  echo ""
  echo "Test interrupted by user"
  # Kill any child processes including timeout and python
  jobs -p | xargs -r kill 2>/dev/null
  pkill -P $$ 2>/dev/null
  # Kill any python processes that might be hanging
  pkill -f "python -m src.cli" 2>/dev/null
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
  "--no-websearch --analyst-prompt experimental/analyst/concise.md"
  "--no-websearch --debug --with-review --max-iterations 2"
  "--no-websearch --with-review --max-iterations 2"
  "--no-websearch --with-review" #use Default max-iterations
  "--debug"                      # Default includes websearch with debug
  ""                             # Default includes websearch
  "--with-review"                # Full with websearch
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

  # No need to create log file - run_analytics handles logging

  # Use 5 minute timeout for all tests
  local timeout_seconds=600

  # Run the analysis with timeout, showing output in real-time
  echo "Running test..."
  echo ""

  # Run the analysis with timeout (run_analytics handles logging)
  # Create a temp file to capture output since we need to handle interrupts properly
  local temp_output=$(mktemp)

  # Run in background to allow better interrupt handling
  timeout $timeout_seconds python -m src.cli "$idea" $flags >"$temp_output" 2>&1 &
  local pid=$!

  # Wait for the process and show output in real-time
  while kill -0 $pid 2>/dev/null; do
    if [ -s "$temp_output" ]; then
      cat "$temp_output"
      >"$temp_output" # Clear the file after displaying
    fi
    sleep 0.1
  done

  # Get any remaining output and exit code
  wait $pid
  exit_code=$?

  # Display any remaining output
  if [ -s "$temp_output" ]; then
    cat "$temp_output"
  fi

  # Save output for checking success
  output=$(cat "$temp_output")
  rm -f "$temp_output"

  if [ $exit_code -eq 0 ]; then
    # Check if analysis was successful (handles both regular and reviewer modes)
    if echo "$output" | grep -q -E "(Analysis saved to:|Analysis completed)"; then
      echo ""
      echo -e "${GREEN}✅ TEST PASSED${NC}"
      test_results="${test_results}${test_id}:success;"
      ((successful_tests++))
    else
      echo ""
      echo -e "${RED}❌ TEST FAILED${NC} (no output file created)"
      test_results="${test_results}${test_id}:failed_no_output;"
    fi
  elif [ $exit_code -eq 124 ]; then
    echo ""
    echo -e "${YELLOW}⏱️  TEST TIMEOUT${NC} (>${timeout_seconds}s)"
    test_results="${test_results}${test_id}:timeout;"
  elif [ $exit_code -eq 130 ] || [ $exit_code -eq 143 ]; then
    echo ""
    echo -e "${YELLOW}⚠️  TEST INTERRUPTED${NC}"
    test_results="${test_results}${test_id}:interrupted;"
  else
    echo ""
    echo -e "${RED}❌ TEST FAILED${NC} (exit code: $exit_code)"
    test_results="${test_results}${test_id}:failed_error;"
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
echo "All test logs saved by run_analytics in: logs/runs/"
echo ""

# Exit with appropriate code
if [ $success_rate -eq 100 ]; then
  exit 0
else
  exit 1
fi
