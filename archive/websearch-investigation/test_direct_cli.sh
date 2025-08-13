#!/bin/bash
# Test Claude CLI directly with same flags SDK uses

echo "Testing Claude CLI directly with WebSearch..."
echo "Type this prompt when ready:"
echo "Please search for 'Python programming' and tell me one fact"
echo ""

claude --output-format stream-json --verbose --allowedTools WebSearch --max-turns 5