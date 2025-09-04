#!/usr/bin/env python
"""Test that the new prompt formats work correctly."""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.utils.file_operations import load_prompt

# Test paths
prompts_dir = Path("config/prompts")

# Test initial prompt
print("Testing initial.md format...")
initial_template = load_prompt("agents/analyst/user/initial.md", prompts_dir)
initial_result = initial_template.format(
    idea="AI-powered test idea", output_file="/path/to/output.md"
)
print("✅ Initial prompt formatted successfully")
print("-" * 40)
print(initial_result[:200] + "...")
print()

# Test revision prompt without fact-check
print("Testing revision.md format (without fact-check)...")
revision_template = load_prompt("agents/analyst/user/revision.md", prompts_dir)
revision_result = revision_template.format(
    idea="AI-powered test idea",
    previous_analysis_file="/path/to/previous.md",
    feedback_file="/path/to/feedback.json",
    fact_check_line="",  # Empty for no fact-check
    output_file="/path/to/output.md",
)
print("✅ Revision prompt (no fact-check) formatted successfully")
print("-" * 40)
print(revision_result[:200] + "...")
print()

# Test revision prompt with fact-check
print("Testing revision.md format (with fact-check)...")
revision_with_fc = revision_template.format(
    idea="AI-powered test idea",
    previous_analysis_file="/path/to/previous.md",
    feedback_file="/path/to/feedback.json",
    fact_check_line="- Fact-check results: /path/to/fact-check.json",
    output_file="/path/to/output.md",
)
print("✅ Revision prompt (with fact-check) formatted successfully")
print("-" * 40)
print(revision_with_fc[:300] + "...")
print()

print("✅ All prompt format tests passed!")
